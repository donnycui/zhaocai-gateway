from fastapi.testclient import TestClient

from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def create_hermes_provider_and_model(client: TestClient) -> tuple[dict, dict]:
    provider = client.post(
        "/admin/hermes/providers",
        headers=admin_headers(),
        json={
            "name": "relay-device",
            "base_url": "https://relay-device.example.com/v1",
            "api_key": "sk-device",
            "plugin_mode": "default_headers",
            "default_headers_json": {
                "HTTP-Referer": "https://hermes-agent.nousresearch.com",
                "X-Title": "Hermes",
            },
        },
    ).json()["provider"]
    model = client.post(
        "/admin/hermes/models",
        headers=admin_headers(),
        json={
            "provider_id": provider["id"],
            "upstream_model": "gpt-5.5",
            "display_name": "GPT-5.5",
            "enabled": True,
        },
    ).json()["model"]
    return provider, model


def test_create_and_list_hermes_devices():
    client = create_test_client()

    created = client.post(
        "/admin/hermes/devices",
        headers=admin_headers(),
        json={
            "name": "hermes-worker-1",
            "device_type": "vps",
            "hostname": "worker.internal",
            "platform": "linux",
            "active": True,
        },
    )

    assert created.status_code == 200
    device = created.json()["device"]
    assert device["name"] == "hermes-worker-1"
    assert device["model_ids"] == []

    listed = client.get("/admin/hermes/devices", headers=admin_headers())
    assert listed.status_code == 200
    payload = listed.json()["devices"]
    assert len(payload) == 1
    assert payload[0]["name"] == "hermes-worker-1"


def test_assign_hermes_models_and_preview_config():
    client = create_test_client()
    _provider, model = create_hermes_provider_and_model(client)
    device = client.post(
        "/admin/hermes/devices",
        headers=admin_headers(),
        json={
            "name": "hermes-preview",
            "device_type": "vps",
        },
    ).json()["device"]

    assign = client.put(
        f"/admin/hermes/devices/{device['id']}/models",
        headers=admin_headers(),
        json={"model_ids": [model["id"]]},
    )
    assert assign.status_code == 200
    assert assign.json()["device"]["model_ids"] == [model["id"]]

    preview = client.get(
        f"/admin/hermes/devices/{device['id']}/config-preview",
        headers=admin_headers(),
    )
    assert preview.status_code == 200
    payload = preview.json()
    assert "config_yaml" in payload
    assert "relay-device/gpt-5.5" in payload["config_yaml"]
    assert "plugin_files" in payload
    assert "relay-device" in payload["plugin_files"]


def test_issue_hermes_pairing_token():
    client = create_test_client()
    device = client.post(
        "/admin/hermes/devices",
        headers=admin_headers(),
        json={
            "name": "hermes-pair",
            "device_type": "mac",
        },
    ).json()["device"]

    response = client.post(
        f"/admin/hermes/devices/{device['id']}/pairing-token",
        headers=admin_headers(),
        json={},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["device_id"] == device["id"]
    assert isinstance(payload["pairing_token"], str)
    assert payload["pairing_token"] != ""
    assert payload["install_command"]
    assert f"--token {payload['pairing_token']}" in payload["install_command"]
    assert "git switch codex/hermes-module" in payload["install_command"]
    assert "--reload-cmd /usr/bin/true" in payload["install_command"]


def test_issue_hermes_pairing_token_for_selected_macos_platform():
    client = create_test_client()
    device = client.post(
        "/admin/hermes/devices",
        headers=admin_headers(),
        json={
            "name": "hermes-mac-selected",
            "device_type": "vps",
            "platform": "linux",
        },
    ).json()["device"]

    response = client.post(
        f"/admin/hermes/devices/{device['id']}/pairing-token",
        headers=admin_headers(),
        json={"platform_family": "macos"},
    )

    assert response.status_code == 200
    install_command = response.json()["install_command"]
    assert "launchctl load ~/Library/LaunchAgents/com.zhaocai.hermes-agent.plist" in install_command
    assert "--reload-cmd /usr/bin/true" in install_command
    assert "systemctl --user" not in install_command
    assert "sudo apt" not in install_command


def test_issue_hermes_pairing_token_for_selected_linux_platform():
    client = create_test_client()
    device = client.post(
        "/admin/hermes/devices",
        headers=admin_headers(),
        json={
            "name": "hermes-linux-selected",
            "device_type": "mac",
            "platform": "darwin",
        },
    ).json()["device"]

    response = client.post(
        f"/admin/hermes/devices/{device['id']}/pairing-token",
        headers=admin_headers(),
        json={"platform_family": "linux"},
    )

    assert response.status_code == 200
    install_command = response.json()["install_command"]
    assert "sudo apt install -y python3-venv" in install_command
    assert "--service-manager systemd" in install_command
    assert "systemctl --user enable --now zhaocai-hermes-agent.service" in install_command
    assert "launchctl" not in install_command
    assert "--reload-cmd /usr/bin/true" not in install_command
