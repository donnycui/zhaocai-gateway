from fastapi.testclient import TestClient
import httpx

from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def create_client_key(client: TestClient, *, api_key: str = "gateway-test-key") -> str:
    response = client.post(
        "/admin/gateway/client-keys",
        headers=admin_headers(),
        json={
            "name": "Content-IP-Strategy",
            "api_key": api_key,
            "notes": "runtime access",
        },
    )
    assert response.status_code == 200
    return response.json()["client_key"]["raw_api_key"]


def create_gateway_account(client: TestClient, *, name: str, base_url: str) -> dict:
    response = client.post(
        "/admin/gateway/accounts",
        headers=admin_headers(),
        json={
            "name": name,
            "base_url": base_url,
            "auth_type": "bearer",
            "api_key": "sk-test",
            "protocol": "openai-compatible",
            "notes": "",
        },
    )
    assert response.status_code == 200
    return response.json()["account"]


def sync_gateway_models(
    client: TestClient,
    monkeypatch,
    account_id: int,
    *,
    expected_url: str,
    model_ids: list[str],
) -> None:
    class DummyResponse:
        status_code = 200
        is_success = True
        text = ""

        def json(self) -> dict:
            return {
                "data": [{"id": model_id, "owned_by": model_id.split("-", 1)[0]} for model_id in model_ids]
            }

    def fake_request(method: str, url: str, headers: dict, timeout: float) -> DummyResponse:
        assert method == "GET"
        assert url == expected_url
        assert timeout == 20.0
        return DummyResponse()

    monkeypatch.setattr(httpx, "request", fake_request)

    response = client.post(
        f"/admin/gateway/accounts/{account_id}/sync-models",
        headers=admin_headers(),
    )
    assert response.status_code == 200


def create_alias_with_targets(client: TestClient, *, primary_account: dict, secondary_account: dict) -> None:
    alias = client.post(
        "/admin/gateway/aliases",
        headers=admin_headers(),
        json={
            "alias_key": "signal/deep",
            "display_name": "Signal Deep",
            "alias_type": "capability",
            "visibility": "project",
            "notes": "",
        },
    ).json()["alias"]

    response = client.put(
        f"/admin/gateway/aliases/{alias['id']}/targets",
        headers=admin_headers(),
        json={
            "targets": [
                {
                    "account_id": primary_account["id"],
                    "model_id": 1,
                    "priority": 10,
                    "enabled": True,
                    "fallback_on_timeout": True,
                    "fallback_on_5xx": True,
                    "fallback_on_429": True,
                    "cooldown_seconds": 120,
                },
                {
                    "account_id": secondary_account["id"],
                    "model_id": 2,
                    "priority": 20,
                    "enabled": True,
                    "fallback_on_timeout": True,
                    "fallback_on_5xx": True,
                    "fallback_on_429": True,
                    "cooldown_seconds": 120,
                },
            ]
        },
    )
    assert response.status_code == 200


def prepare_runtime_targets(client: TestClient, monkeypatch) -> tuple[dict, dict]:
    primary = create_gateway_account(client, name="公益站 A", base_url="https://a.example.com/v1")
    secondary = create_gateway_account(client, name="公益站 B", base_url="https://b.example.com/v1")

    sync_gateway_models(
        client,
        monkeypatch,
        primary["id"],
        expected_url="https://a.example.com/v1/models",
        model_ids=["gpt-5.4"],
    )
    sync_gateway_models(
        client,
        monkeypatch,
        secondary["id"],
        expected_url="https://b.example.com/v1/models",
        model_ids=["gpt-5.4"],
    )
    create_alias_with_targets(client, primary_account=primary, secondary_account=secondary)
    return primary, secondary


def test_gateway_failover_on_timeout(monkeypatch):
    client = create_test_client()
    prepare_runtime_targets(client, monkeypatch)
    runtime_key = create_client_key(client)

    calls: list[str] = []

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self.text = ""
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    def fake_request(method: str, url: str, headers: dict, json: dict, timeout: float):
        calls.append(url)
        if len(calls) == 1:
            raise httpx.ReadTimeout("timed out")
        assert json["model"] == "gpt-5.4"
        return DummyResponse(
            200,
            {
                "id": "chatcmpl-1",
                "choices": [{"message": {"role": "assistant", "content": "from secondary"}}],
            },
        )

    monkeypatch.setattr(httpx, "request", fake_request)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {runtime_key}"},
        json={
            "model": "signal/deep",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "from secondary"
    assert calls == [
        "https://a.example.com/v1/chat/completions",
        "https://b.example.com/v1/chat/completions",
    ]


def test_gateway_failover_on_5xx(monkeypatch):
    client = create_test_client()
    prepare_runtime_targets(client, monkeypatch)
    runtime_key = create_client_key(client)

    calls: list[str] = []

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self.text = ""
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    def fake_request(method: str, url: str, headers: dict, json: dict, timeout: float):
        calls.append(url)
        if len(calls) == 1:
            return DummyResponse(503, {"error": {"message": "upstream unavailable"}})
        return DummyResponse(
            200,
            {
                "id": "chatcmpl-2",
                "choices": [{"message": {"role": "assistant", "content": "fallback success"}}],
            },
        )

    monkeypatch.setattr(httpx, "request", fake_request)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {runtime_key}"},
        json={
            "model": "signal/deep",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "fallback success"
    assert len(calls) == 2


def test_gateway_failover_on_429(monkeypatch):
    client = create_test_client()
    prepare_runtime_targets(client, monkeypatch)
    runtime_key = create_client_key(client)

    calls: list[str] = []

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self.text = ""
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    def fake_request(method: str, url: str, headers: dict, json: dict, timeout: float):
        calls.append(url)
        if len(calls) == 1:
            return DummyResponse(429, {"error": {"message": "rate limited"}})
        return DummyResponse(
            200,
            {
                "id": "chatcmpl-3",
                "choices": [{"message": {"role": "assistant", "content": "rate limit fallback"}}],
            },
        )

    monkeypatch.setattr(httpx, "request", fake_request)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {runtime_key}"},
        json={
            "model": "signal/deep",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "rate limit fallback"
    assert len(calls) == 2


def test_gateway_does_not_failover_on_400(monkeypatch):
    client = create_test_client()
    prepare_runtime_targets(client, monkeypatch)
    runtime_key = create_client_key(client)

    calls: list[str] = []

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self.text = ""
            self._payload = payload

        def json(self) -> dict:
            return self._payload

    def fake_request(method: str, url: str, headers: dict, json: dict, timeout: float):
        calls.append(url)
        return DummyResponse(400, {"error": {"message": "bad request"}})

    monkeypatch.setattr(httpx, "request", fake_request)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {runtime_key}"},
        json={
            "model": "signal/deep",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "bad request"
    assert calls == ["https://a.example.com/v1/chat/completions"]
