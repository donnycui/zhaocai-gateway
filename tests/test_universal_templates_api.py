from fastapi.testclient import TestClient

from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def create_universal_template(client: TestClient) -> dict:
    response = client.post(
        "/admin/universal/templates",
        headers=admin_headers(),
        json={
            "name": "openai-template",
            "base_url": "https://api.openai.com/v1",
            "auth_type": "bearer",
            "api_key": "sk-template",
            "protocol": "openai-compatible",
            "notes": "shared template",
            "models": [
                {
                    "upstream_model": "gpt-5.4",
                    "display_name": "GPT-5.4",
                    "capabilities": ["text", "reasoning"],
                    "reasoning": True,
                    "input_modalities": ["text"],
                    "context_window": 200000,
                    "max_tokens": 32000,
                    "enabled": True,
                }
            ],
        },
    )
    assert response.status_code == 200
    return response.json()["template"]


def test_import_universal_template_into_openclaw_creates_independent_copy():
    client = create_test_client()
    template = create_universal_template(client)

    response = client.post(
        f"/admin/universal/templates/{template['id']}/import/openclaw",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"]["name"] == "openai-template"
    assert payload["models"][0]["upstream_model"] == "gpt-5.4"

    provider_id = payload["provider"]["id"]
    client.patch(
        f"/admin/providers/{provider_id}",
        headers=admin_headers(),
        json={
            "name": "openai-openclaw-copy",
            "base_url": "https://api.openai.com/v1",
            "provider_type": "openai-completions",
            "auth_scheme": "bearer",
            "api_key": "sk-template",
            "enabled": True,
            "extra_headers": {},
        },
    )

    templates = client.get("/admin/universal/templates", headers=admin_headers()).json()["templates"]
    assert templates[0]["name"] == "openai-template"


def test_import_universal_template_into_gateway_creates_account_and_models():
    client = create_test_client()
    template = create_universal_template(client)

    response = client.post(
        f"/admin/universal/templates/{template['id']}/import/gateway",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["account"]["name"] == "openai-template"
    assert payload["models"][0]["upstream_model"] == "gpt-5.4"


def test_import_universal_template_into_media_creates_provider_copy():
    client = create_test_client()
    template = create_universal_template(client)

    response = client.post(
        f"/admin/universal/templates/{template['id']}/import/media",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"]["name"] == "openai-template"
    assert payload["provider"]["base_url"] == "https://api.openai.com/v1"
