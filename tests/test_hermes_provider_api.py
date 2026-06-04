from fastapi.testclient import TestClient

from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def test_create_hermes_provider():
    client = create_test_client()

    response = client.post(
        "/admin/hermes/providers",
        headers=admin_headers(),
        json={
            "name": "hermes-relay",
            "base_url": "https://relay.example.com/v1",
            "api_key": "sk-hermes",
            "enabled": True,
            "notes": "primary relay",
            "plugin_mode": "default_headers",
            "default_headers_json": {
                "HTTP-Referer": "https://hermes-agent.nousresearch.com",
                "X-Title": "Hermes",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()["provider"]
    assert payload["name"] == "hermes-relay"
    assert payload["plugin_mode"] == "default_headers"
    assert payload["default_headers_json"]["X-Title"] == "Hermes"


def test_import_openclaw_provider_into_hermes():
    client = create_test_client()
    provider = client.post(
        "/admin/providers",
        headers=admin_headers(),
        json={
            "name": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "provider_type": "openai",
            "auth_scheme": "bearer",
            "api_key": "sk-openrouter",
            "extra_headers": {},
        },
    ).json()["provider"]

    response = client.post(
        "/admin/hermes/providers/import-openclaw",
        headers=admin_headers(),
        json={"openclaw_provider_id": provider["id"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "created"
    assert payload["provider"]["name"] == "openrouter"
    assert payload["provider"]["source_openclaw_provider_id"] == provider["id"]


def test_create_and_update_hermes_model():
    client = create_test_client()
    provider = client.post(
        "/admin/hermes/providers",
        headers=admin_headers(),
        json={
            "name": "relay-a",
            "base_url": "https://relay-a.example.com/v1",
            "api_key": "sk-a",
            "plugin_mode": "none",
            "default_headers_json": {},
        },
    ).json()["provider"]

    created = client.post(
        "/admin/hermes/models",
        headers=admin_headers(),
        json={
            "provider_id": provider["id"],
            "upstream_model": "gpt-5.5",
            "display_name": "GPT-5.5",
            "enabled": True,
        },
    )
    assert created.status_code == 200
    model = created.json()["model"]
    assert model["provider_name"] == "relay-a"

    updated = client.patch(
        f"/admin/hermes/models/{model['id']}",
        headers=admin_headers(),
        json={
            "upstream_model": "gpt-5.5-mini",
            "display_name": "GPT-5.5 Mini",
            "enabled": False,
        },
    )
    assert updated.status_code == 200
    updated_model = updated.json()["model"]
    assert updated_model["upstream_model"] == "gpt-5.5-mini"
    assert updated_model["enabled"] is False


def test_get_hermes_provider_includes_models():
    client = create_test_client()
    provider = client.post(
        "/admin/hermes/providers",
        headers=admin_headers(),
        json={
            "name": "relay-b",
            "base_url": "https://relay-b.example.com/v1",
            "api_key": "sk-b",
            "plugin_mode": "none",
            "default_headers_json": {},
        },
    ).json()["provider"]
    client.post(
        "/admin/hermes/models",
        headers=admin_headers(),
        json={
            "provider_id": provider["id"],
            "upstream_model": "claude-4.1-sonnet",
            "display_name": "Claude 4.1 Sonnet",
            "enabled": True,
        },
    )

    response = client.get(
        f"/admin/hermes/providers/{provider['id']}",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"]["name"] == "relay-b"
    assert len(payload["models"]) == 1
    assert payload["models"][0]["display_name"] == "Claude 4.1 Sonnet"
