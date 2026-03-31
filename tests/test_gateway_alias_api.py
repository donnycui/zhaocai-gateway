from fastapi.testclient import TestClient
import httpx

from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def create_gateway_account(client: TestClient, *, name: str, base_url: str, auth_type: str = "bearer") -> dict:
    response = client.post(
        "/admin/gateway/accounts",
        headers=admin_headers(),
        json={
            "name": name,
            "base_url": base_url,
            "auth_type": auth_type,
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


def test_create_gateway_alias():
    client = create_test_client()

    response = client.post(
        "/admin/gateway/aliases",
        headers=admin_headers(),
        json={
            "alias_key": "deep",
            "display_name": "Deep Default",
            "alias_type": "tier",
            "visibility": "project",
            "notes": "default deep alias",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["alias"]["alias_key"] == "deep"
    assert payload["alias"]["display_name"] == "Deep Default"
    assert payload["alias"]["enabled"] is True


def test_assign_multiple_ordered_targets_to_gateway_alias(monkeypatch):
    client = create_test_client()
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

    aliases_response = client.post(
        "/admin/gateway/aliases",
        headers=admin_headers(),
        json={
            "alias_key": "signal/deep",
            "display_name": "Signal Deep",
            "alias_type": "capability",
            "visibility": "project",
            "notes": "",
        },
    )
    alias = aliases_response.json()["alias"]

    accounts = client.get("/admin/gateway/accounts", headers=admin_headers()).json()["accounts"]
    assert len(accounts) == 2

    targets_response = client.put(
        f"/admin/gateway/aliases/{alias['id']}/targets",
        headers=admin_headers(),
        json={
            "targets": [
                {
                    "account_id": primary["id"],
                    "model_id": 1,
                    "priority": 10,
                    "enabled": True,
                    "fallback_on_timeout": True,
                    "fallback_on_5xx": True,
                    "fallback_on_429": True,
                    "cooldown_seconds": 120,
                },
                {
                    "account_id": secondary["id"],
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

    assert targets_response.status_code == 200
    payload = targets_response.json()
    assert [target["priority"] for target in payload["targets"]] == [10, 20]
    assert [target["account_name"] for target in payload["targets"]] == ["公益站 A", "公益站 B"]

    list_response = client.get(
        f"/admin/gateway/aliases/{alias['id']}/targets",
        headers=admin_headers(),
    )
    listed = list_response.json()["targets"]
    assert [target["priority"] for target in listed] == [10, 20]


def test_disable_gateway_alias():
    client = create_test_client()
    alias = client.post(
        "/admin/gateway/aliases",
        headers=admin_headers(),
        json={
            "alias_key": "balanced",
            "display_name": "Balanced",
            "alias_type": "tier",
            "visibility": "project",
            "notes": "",
        },
    ).json()["alias"]

    response = client.patch(
        f"/admin/gateway/aliases/{alias['id']}",
        headers=admin_headers(),
        json={
            "display_name": "Balanced",
            "enabled": False,
            "visibility": "project",
            "notes": "disabled temporarily",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["alias"]["enabled"] is False
    assert payload["alias"]["notes"] == "disabled temporarily"


def test_reorder_gateway_alias_targets(monkeypatch):
    client = create_test_client()
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

    alias = client.post(
        "/admin/gateway/aliases",
        headers=admin_headers(),
        json={
            "alias_key": "draft/deep",
            "display_name": "Draft Deep",
            "alias_type": "capability",
            "visibility": "project",
            "notes": "",
        },
    ).json()["alias"]

    client.put(
        f"/admin/gateway/aliases/{alias['id']}/targets",
        headers=admin_headers(),
        json={
            "targets": [
                {
                    "account_id": primary["id"],
                    "model_id": 1,
                    "priority": 10,
                    "enabled": True,
                    "fallback_on_timeout": True,
                    "fallback_on_5xx": True,
                    "fallback_on_429": True,
                    "cooldown_seconds": 120,
                },
                {
                    "account_id": secondary["id"],
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

    reorder_response = client.put(
        f"/admin/gateway/aliases/{alias['id']}/targets",
        headers=admin_headers(),
        json={
            "targets": [
                {
                    "account_id": secondary["id"],
                    "model_id": 2,
                    "priority": 10,
                    "enabled": True,
                    "fallback_on_timeout": True,
                    "fallback_on_5xx": True,
                    "fallback_on_429": True,
                    "cooldown_seconds": 120,
                },
                {
                    "account_id": primary["id"],
                    "model_id": 1,
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

    assert reorder_response.status_code == 200
    payload = reorder_response.json()
    assert [target["account_name"] for target in payload["targets"]] == ["公益站 B", "公益站 A"]
    assert [target["priority"] for target in payload["targets"]] == [10, 20]
