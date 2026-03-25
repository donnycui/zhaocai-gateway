from fastapi.testclient import TestClient

from zhaocai_gateway.app import create_app


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:")
    return TestClient(app)


def test_create_device():
    client = create_test_client()

    response = client.post(
        "/admin/devices",
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
        json={
            "name": "vps-1",
            "device_type": "vps",
        },
    ).json()["device"]

    response = client.post(f"/admin/devices/{device['id']}/pairing-token", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["device_id"] == device["id"]
    assert isinstance(payload["pairing_token"], str)
    assert payload["pairing_token"] != ""


def test_assign_models_to_device():
    client = create_test_client()
    provider = client.post(
        "/admin/providers",
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
        json={
            "name": "mac-mini",
            "device_type": "mac",
        },
    ).json()["device"]

    response = client.put(
        f"/admin/devices/{device['id']}/models",
        json={"model_ids": [model["id"]]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["device"]["model_ids"] == [model["id"]]


def test_list_devices():
    client = create_test_client()
    client.post(
        "/admin/devices",
        json={
            "name": "raspberrypi",
            "device_type": "raspberrypi",
        },
    )

    response = client.get("/admin/devices")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["devices"]) == 1
    assert payload["devices"][0]["name"] == "raspberrypi"


def test_get_device_config_preview():
    client = create_test_client()
    provider = client.post(
        "/admin/providers",
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
        json={
            "name": "worker-preview",
            "device_type": "vps",
        },
    ).json()["device"]
    client.put(
        f"/admin/devices/{device['id']}/models",
        json={"model_ids": [model["id"]]},
    )

    response = client.get(f"/admin/devices/{device['id']}/config-preview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["device"]["id"] == device["id"]
    assert payload["models"][0]["upstream_model"] == "gpt-4.1-mini"
