from fastapi.testclient import TestClient

from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def test_create_gateway_client_key_returns_raw_key_once():
    client = create_test_client()

    response = client.post(
        "/admin/gateway/client-keys",
        headers=admin_headers(),
        json={
            "name": "Content-IP-Strategy",
            "api_key": "gateway-test-key",
            "notes": "primary consumer",
        },
    )

    assert response.status_code == 200
    payload = response.json()["client_key"]
    assert payload["name"] == "Content-IP-Strategy"
    assert payload["enabled"] is True
    assert payload["raw_api_key"] == "gateway-test-key"
    assert payload["key_hint"].startswith("gate")

    list_response = client.get("/admin/gateway/client-keys", headers=admin_headers())
    listed = list_response.json()["client_keys"][0]
    assert listed["name"] == "Content-IP-Strategy"
    assert listed["key_hint"] == payload["key_hint"]
    assert "raw_api_key" not in listed


def test_runtime_requires_gateway_client_key():
    client = create_test_client()

    response = client.post(
        "/v1/chat/completions",
        json={"model": "signal/deep", "messages": [{"role": "user", "content": "hello"}]},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Gateway client access is not configured"


def test_runtime_rejects_missing_or_invalid_gateway_client_key():
    client = create_test_client()
    client.post(
        "/admin/gateway/client-keys",
        headers=admin_headers(),
        json={
            "name": "Content-IP-Strategy",
            "api_key": "gateway-test-key",
            "notes": "",
        },
    )

    missing_response = client.post(
        "/v1/chat/completions",
        json={"model": "signal/deep", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert missing_response.status_code == 401
    assert missing_response.json()["detail"] == "Missing gateway client key"

    invalid_response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer wrong-key"},
        json={"model": "signal/deep", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert invalid_response.status_code == 401
    assert invalid_response.json()["detail"] == "Invalid gateway client key"


def test_update_gateway_client_key_can_disable_access():
    client = create_test_client()
    created = client.post(
        "/admin/gateway/client-keys",
        headers=admin_headers(),
        json={
            "name": "Content-IP-Strategy",
            "api_key": "gateway-test-key",
            "notes": "disable me",
        },
    ).json()["client_key"]

    response = client.patch(
        f"/admin/gateway/client-keys/{created['id']}",
        headers=admin_headers(),
        json={"enabled": False, "notes": "disabled"},
    )

    assert response.status_code == 200
    payload = response.json()["client_key"]
    assert payload["enabled"] is False
    assert payload["notes"] == "disabled"

    invalid_response = client.post(
        "/v1/chat/completions",
        headers={"x-api-key": "gateway-test-key"},
        json={"model": "signal/deep", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert invalid_response.status_code == 503
    assert invalid_response.json()["detail"] == "Gateway client access is not configured"
