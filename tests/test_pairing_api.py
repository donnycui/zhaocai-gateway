from fastapi.testclient import TestClient

from zhaocai_gateway.app import create_app


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:")
    return TestClient(app)


def test_successful_registration_with_pairing_token():
    client = create_test_client()
    device = client.post(
        "/admin/devices",
        json={
            "name": "vps-1",
            "device_type": "vps",
        },
    ).json()["device"]
    pairing_token = client.post(
        f"/admin/devices/{device['id']}/pairing-token",
        json={},
    ).json()["pairing_token"]

    response = client.post(
        "/agent/v1/register",
        json={
            "pairing_token": pairing_token,
            "hostname": "vps-1.internal",
            "platform": "linux",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["device"]["id"] == device["id"]
    assert payload["device"]["hostname"] == "vps-1.internal"
    assert payload["device"]["platform"] == "linux"
    assert isinstance(payload["sync_token"], str)
    assert payload["sync_token"] != ""


def test_expired_token_rejected():
    client = create_test_client()
    device = client.post(
        "/admin/devices",
        json={
            "name": "macbook-pro",
            "device_type": "mac",
        },
    ).json()["device"]
    pairing_token = client.post(
        f"/admin/devices/{device['id']}/pairing-token",
        json={"expires_in_seconds": -10},
    ).json()["pairing_token"]

    response = client.post(
        "/agent/v1/register",
        json={
            "pairing_token": pairing_token,
            "hostname": "macbook-pro.local",
            "platform": "darwin",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired pairing token"


def test_heartbeat_updates_last_seen_at():
    client = create_test_client()
    device = client.post(
        "/admin/devices",
        json={
            "name": "worker-1",
            "device_type": "vps",
        },
    ).json()["device"]
    pairing_token = client.post(
        f"/admin/devices/{device['id']}/pairing-token",
        json={},
    ).json()["pairing_token"]
    register_payload = client.post(
        "/agent/v1/register",
        json={
            "pairing_token": pairing_token,
            "hostname": "worker-1.internal",
            "platform": "linux",
        },
    ).json()

    response = client.post(
        "/agent/v1/heartbeat",
        json={"sync_token": register_payload["sync_token"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["device"]["last_seen_at"] is not None
