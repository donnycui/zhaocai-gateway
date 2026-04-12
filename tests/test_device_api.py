from fastapi.testclient import TestClient

from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def test_create_device():
    client = create_test_client()

    response = client.post(
        "/admin/devices",
        headers=admin_headers(),
        json={
            "name": "macbook-pro",
            "device_type": "mac",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["device"]["name"] == "macbook-pro"
    assert payload["device"]["device_type"] == "mac"
    assert payload["device"]["model_ids"] == []


def test_issue_pairing_token():
    client = create_test_client()
    device = client.post(
        "/admin/devices",
        headers=admin_headers(),
        json={
            "name": "vps-1",
            "device_type": "vps",
        },
    ).json()["device"]

    response = client.post(
        f"/admin/devices/{device['id']}/pairing-token",
        headers=admin_headers(),
        json={},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["device_id"] == device["id"]
    assert isinstance(payload["pairing_token"], str)
    assert payload["pairing_token"] != ""


def test_update_device():
    client = create_test_client()
    device = client.post(
        "/admin/devices",
        headers=admin_headers(),
        json={
            "name": "worker-a",
            "device_type": "vps",
            "hostname": "old-host",
            "platform": "linux",
        },
    ).json()["device"]

    response = client.patch(
        f"/admin/devices/{device['id']}",
        headers=admin_headers(),
        json={
            "name": "worker-b",
            "device_type": "raspberrypi",
            "hostname": "new-host",
            "platform": "linux-arm64",
            "active": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()["device"]
    assert payload["name"] == "worker-b"
    assert payload["device_type"] == "raspberrypi"
    assert payload["hostname"] == "new-host"
    assert payload["platform"] == "linux-arm64"
    assert payload["active"] is False


def test_assign_models_to_device():
    client = create_test_client()
    provider = client.post(
        "/admin/providers",
        headers=admin_headers(),
        json={
            "name": "openai",
            "base_url": "https://api.openai.com/v1",
            "provider_type": "openai",
            "auth_scheme": "bearer",
            "api_key": "sk-test",
            "extra_headers": {},
        },
    ).json()["provider"]
    model = client.post(
        "/admin/models",
        headers=admin_headers(),
        json={
            "provider_id": provider["id"],
            "upstream_model": "gpt-4.1",
            "display_name": "GPT-4.1",
            "capabilities": ["text"],
            "context_window": 128000,
            "max_tokens": 16000,
            "enabled": True,
        },
    ).json()["model"]
    device = client.post(
        "/admin/devices",
        headers=admin_headers(),
        json={
            "name": "mac-mini",
            "device_type": "mac",
        },
    ).json()["device"]

    response = client.put(
        f"/admin/devices/{device['id']}/models",
        headers=admin_headers(),
        json={"model_ids": [model["id"]]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["device"]["model_ids"] == [model["id"]]


def test_list_devices():
    client = create_test_client()
    client.post(
        "/admin/devices",
        headers=admin_headers(),
        json={
            "name": "raspberrypi",
            "device_type": "raspberrypi",
        },
    )

    response = client.get("/admin/devices", headers=admin_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["devices"]) == 1
    assert payload["devices"][0]["name"] == "raspberrypi"
    assert payload["devices"][0]["preserve_providers"] == []
    assert payload["devices"][0]["preserve_models"] == []


def test_update_device_preserve_config():
    client = create_test_client()
    device = client.post(
        "/admin/devices",
        headers=admin_headers(),
        json={
            "name": "preserve-worker",
            "device_type": "vps",
        },
    ).json()["device"]

    response = client.put(
        f"/admin/devices/{device['id']}/preserve-config",
        headers=admin_headers(),
        json={
            "preserve_providers": ["zhipu", "custom-local"],
            "preserve_models": ["zhipu/glm-4-plus", "custom-local/dev-model"],
        },
    )

    assert response.status_code == 200
    payload = response.json()["device"]
    assert payload["preserve_providers"] == ["zhipu", "custom-local"]
    assert payload["preserve_models"] == ["zhipu/glm-4-plus", "custom-local/dev-model"]


def test_get_device_config_preview():
    client = create_test_client()
    provider = client.post(
        "/admin/providers",
        headers=admin_headers(),
        json={
            "name": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "provider_type": "openai",
            "auth_scheme": "bearer",
            "api_key": "sk-test",
            "extra_headers": {},
        },
    ).json()["provider"]
    model = client.post(
        "/admin/models",
        headers=admin_headers(),
        json={
            "provider_id": provider["id"],
            "upstream_model": "gpt-4.1-mini",
            "display_name": "GPT-4.1 mini",
            "capabilities": ["text"],
            "context_window": 128000,
            "max_tokens": 16000,
            "enabled": True,
        },
    ).json()["model"]
    device = client.post(
        "/admin/devices",
        headers=admin_headers(),
        json={
            "name": "worker-preview",
            "device_type": "vps",
        },
    ).json()["device"]
    client.put(
        f"/admin/devices/{device['id']}/models",
        headers=admin_headers(),
        json={"model_ids": [model["id"]]},
    )

    response = client.get(
        f"/admin/devices/{device['id']}/config-preview",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert "device" not in payload
    assert payload["models"]["providers"]["openrouter"]["models"][0]["id"] == "gpt-4.1-mini"
    assert payload["agents"]["defaults"]["model"]["primary"] == "openrouter/gpt-4.1-mini"
    assert payload["_zhaocai"]["preserveProviders"] == []
    assert payload["_zhaocai"]["preserveModels"] == []
