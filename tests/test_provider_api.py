from fastapi.testclient import TestClient

from zhaocai_gateway.app import create_app


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:")
    return TestClient(app)


def test_create_provider():
    client = create_test_client()

    response = client.post(
        "/admin/providers",
        json={
            "name": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "provider_type": "openai",
            "auth_scheme": "bearer",
            "api_key": "sk-test",
            "extra_headers": {"HTTP-Referer": "https://example.com"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"]["name"] == "openrouter"
    assert payload["provider"]["provider_type"] == "openai"


def test_validate_provider_input():
    client = create_test_client()

    response = client.post(
        "/admin/providers/validate",
        json={
            "name": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "provider_type": "openai",
            "auth_scheme": "bearer",
            "api_key": "sk-test",
            "extra_headers": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_create_model_under_provider():
    client = create_test_client()
    provider_response = client.post(
        "/admin/providers",
        json={
            "name": "openai",
            "base_url": "https://api.openai.com/v1",
            "provider_type": "openai",
            "auth_scheme": "bearer",
            "api_key": "sk-test",
            "extra_headers": {},
        },
    )
    provider_id = provider_response.json()["provider"]["id"]

    response = client.post(
        "/admin/models",
        json={
            "provider_id": provider_id,
            "upstream_model": "gpt-4.1",
            "display_name": "GPT-4.1",
            "capabilities": ["text"],
            "context_window": 128000,
            "max_tokens": 16000,
            "enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"]["provider_id"] == provider_id
    assert payload["model"]["upstream_model"] == "gpt-4.1"


def test_list_providers_and_models():
    client = create_test_client()
    provider_response = client.post(
        "/admin/providers",
        json={
            "name": "anthropic",
            "base_url": "https://api.anthropic.com",
            "provider_type": "anthropic",
            "auth_scheme": "x-api-key",
            "api_key": "sk-ant-test",
            "extra_headers": {},
        },
    )
    provider_id = provider_response.json()["provider"]["id"]
    client.post(
        "/admin/models",
        json={
            "provider_id": provider_id,
            "upstream_model": "claude-sonnet-4.5",
            "display_name": "Claude Sonnet 4.5",
            "capabilities": ["text"],
            "context_window": 200000,
            "max_tokens": 16000,
            "enabled": True,
        },
    )

    providers_response = client.get("/admin/providers")
    models_response = client.get("/admin/models")

    assert providers_response.status_code == 200
    assert models_response.status_code == 200
    assert len(providers_response.json()["providers"]) == 1
    assert len(models_response.json()["models"]) == 1
