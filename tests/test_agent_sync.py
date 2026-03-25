from fastapi.testclient import TestClient

from zhaocai_gateway.app import create_app


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:")
    return TestClient(app)


def register_device(client: TestClient, device_name: str = "worker-1") -> dict:
    device = client.post(
        "/admin/devices",
        json={"name": device_name, "device_type": "vps"},
    ).json()["device"]
    pairing_token = client.post(
        f"/admin/devices/{device['id']}/pairing-token",
        json={},
    ).json()["pairing_token"]
    return client.post(
        "/agent/v1/register",
        json={
            "pairing_token": pairing_token,
            "hostname": f"{device_name}.internal",
            "platform": "linux",
        },
    ).json()


def test_get_config_meta():
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
    registration = register_device(client)
    client.put(
        f"/admin/devices/{registration['device']['id']}/models",
        json={"model_ids": [model["id"]]},
    )

    response = client.get(
        "/agent/v1/config/meta",
        headers={"Authorization": f"Bearer {registration['sync_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == 1
    assert payload["etag"] != ""


def test_get_config_meta_reuses_version_when_payload_unchanged():
    client = create_test_client()
    provider = client.post(
        "/admin/providers",
        json={
            "name": "reuse-provider",
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
    registration = register_device(client, device_name="reuse-worker")
    client.put(
        f"/admin/devices/{registration['device']['id']}/models",
        json={"model_ids": [model["id"]]},
    )

    first = client.get(
        "/agent/v1/config/meta",
        headers={"Authorization": f"Bearer {registration['sync_token']}"},
    ).json()
    second = client.get(
        "/agent/v1/config/meta",
        headers={"Authorization": f"Bearer {registration['sync_token']}"},
    ).json()

    assert first["version"] == 1
    assert second["version"] == 1
    assert first["etag"] == second["etag"]


def test_get_full_config():
    client = create_test_client()
    provider = client.post(
        "/admin/providers",
        json={
            "name": "anthropic",
            "base_url": "https://api.anthropic.com",
            "provider_type": "anthropic",
            "auth_scheme": "x-api-key",
            "api_key": "sk-ant-test",
            "extra_headers": {},
        },
    ).json()["provider"]
    model = client.post(
        "/admin/models",
        json={
            "provider_id": provider["id"],
            "upstream_model": "claude-sonnet-4.5",
            "display_name": "Claude Sonnet 4.5",
            "capabilities": ["text"],
            "context_window": 200000,
            "max_tokens": 16000,
            "enabled": True,
        },
    ).json()["model"]
    registration = register_device(client, device_name="worker-2")
    client.put(
        f"/admin/devices/{registration['device']['id']}/models",
        json={"model_ids": [model["id"]]},
    )

    response = client.get(
        "/agent/v1/config",
        headers={"Authorization": f"Bearer {registration['sync_token']}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["device"]["id"] == registration["device"]["id"]
    assert len(payload["models"]) == 1
    assert payload["models"][0]["display_name"] == "Claude Sonnet 4.5"


def test_post_config_applied():
    client = create_test_client()
    registration = register_device(client, device_name="worker-3")

    response = client.post(
        "/agent/v1/config/applied",
        headers={"Authorization": f"Bearer {registration['sync_token']}"},
        json={"version": 1, "status": "applied"},
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
