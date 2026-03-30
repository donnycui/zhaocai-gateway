from fastapi.testclient import TestClient
import httpx

from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def test_create_gateway_account():
    client = create_test_client()

    response = client.post(
        "/admin/gateway/accounts",
        headers=admin_headers(),
        json={
            "name": "公益站 A",
            "base_url": "https://example.com/v1",
            "auth_type": "bearer",
            "api_key": "sk-test",
            "protocol": "openai-compatible",
            "notes": "primary upstream",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["account"]["name"] == "公益站 A"
    assert payload["account"]["auth_type"] == "bearer"
    assert payload["account"]["health_status"] == "UNKNOWN"
    assert payload["account"]["synced_models_count"] == 0


def test_test_gateway_account_connectivity_uses_models_endpoint(monkeypatch):
    client = create_test_client()
    account = client.post(
        "/admin/gateway/accounts",
        headers=admin_headers(),
        json={
            "name": "公益站 A",
            "base_url": "https://example.com/v1",
            "auth_type": "bearer",
            "api_key": "sk-test",
            "protocol": "openai-compatible",
        },
    ).json()["account"]

    calls: list[dict] = []

    class DummyResponse:
        status_code = 200
        is_success = True
        text = ""

        def json(self) -> dict:
            return {"data": []}

    def fake_request(method: str, url: str, headers: dict, timeout: float) -> DummyResponse:
        calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return DummyResponse()

    monkeypatch.setattr(httpx, "request", fake_request)

    response = client.post(
        f"/admin/gateway/accounts/{account['id']}/test",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["healthy"] is True
    assert payload["models_status"] == 200
    assert calls == [
        {
            "method": "GET",
            "url": "https://example.com/v1/models",
            "headers": {"Authorization": "Bearer sk-test"},
            "timeout": 20.0,
        }
    ]

    list_response = client.get("/admin/gateway/accounts", headers=admin_headers())
    listed = list_response.json()["accounts"][0]
    assert listed["health_status"] == "HEALTHY"


def test_sync_gateway_account_models_stores_synced_model_count(monkeypatch):
    client = create_test_client()
    account = client.post(
        "/admin/gateway/accounts",
        headers=admin_headers(),
        json={
            "name": "公益站 B",
            "base_url": "https://example.com/v1",
            "auth_type": "x-api-key",
            "api_key": "sk-test",
            "protocol": "openai-compatible",
        },
    ).json()["account"]

    class DummyResponse:
        status_code = 200
        is_success = True
        text = ""

        def json(self) -> dict:
            return {
                "data": [
                    {"id": "gpt-5.4", "owned_by": "openai"},
                    {"id": "claude-opus-4.6", "owned_by": "anthropic"},
                ]
            }

    def fake_request(method: str, url: str, headers: dict, timeout: float) -> DummyResponse:
        assert method == "GET"
        assert url == "https://example.com/v1/models"
        assert headers == {"x-api-key": "sk-test"}
        assert timeout == 20.0
        return DummyResponse()

    monkeypatch.setattr(httpx, "request", fake_request)

    response = client.post(
        f"/admin/gateway/accounts/{account['id']}/sync-models",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["account_id"] == account["id"]
    assert payload["models_count"] == 2
    assert payload["upserted_count"] == 2

    list_response = client.get("/admin/gateway/accounts", headers=admin_headers())
    listed = list_response.json()["accounts"][0]
    assert listed["health_status"] == "HEALTHY"
    assert listed["synced_models_count"] == 2
