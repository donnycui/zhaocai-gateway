from fastapi.testclient import TestClient

from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def test_create_media_provider():
    client = create_test_client()

    response = client.post(
        "/admin/media/providers",
        headers=admin_headers(),
        json={
            "name": "siliconflow-media",
            "base_url": "https://api.siliconflow.cn/v1",
            "auth_type": "bearer",
            "api_key": "sk-test",
            "notes": "tts upstream",
        },
    )

    assert response.status_code == 200
    payload = response.json()["provider"]
    assert payload["name"] == "siliconflow-media"
    assert payload["auth_type"] == "bearer"
    assert payload["enabled"] is True


def test_create_media_template():
    client = create_test_client()
    provider = client.post(
        "/admin/media/providers",
        headers=admin_headers(),
        json={
            "name": "bizyair",
            "base_url": "https://bizyair.example.com/api",
            "auth_type": "bearer",
            "api_key": "sk-test",
            "notes": "",
        },
    ).json()["provider"]

    response = client.post(
        "/admin/media/templates",
        headers=admin_headers(),
        json={
            "provider_id": provider["id"],
            "model_key": "image/bizyair/default",
            "name": "BizyAir Default",
            "capability": "image",
            "template_type": "bizyair_webapp",
            "upstream_model": "bizyair-default",
            "ui_group": "image",
            "ui_label": "BizyAir Default",
            "ui_description": "Default image template",
            "ui_badge": "new",
            "ui_order": 10,
            "input_schema_json": {"prompt": {"type": "string", "required": True}},
            "request_template_json": {"web_app_id": "app-1", "input_values": {"prompt": "{{prompt}}"}},
            "response_mapping_json": {"image_url": "$.data.url"},
            "defaults_json": {"ratio": "1:1"},
            "enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()["template"]
    assert payload["model_key"] == "image/bizyair/default"
    assert payload["template_type"] == "bizyair_webapp"
    assert payload["provider_id"] == provider["id"]


def test_validate_media_template_payload():
    client = create_test_client()
    provider = client.post(
        "/admin/media/providers",
        headers=admin_headers(),
        json={
            "name": "gemini-media",
            "base_url": "https://generativelanguage.googleapis.com",
            "auth_type": "x-api-key",
            "api_key": "sk-test",
            "notes": "",
        },
    ).json()["provider"]

    response = client.post(
        "/admin/media/templates/validate",
        headers=admin_headers(),
        json={
            "provider_id": provider["id"],
            "model_key": "image/gemini/pro",
            "name": "Gemini Image",
            "capability": "image",
            "template_type": "gemini_generate_content",
            "upstream_model": "gemini-2.5-pro",
            "ui_group": "image",
            "ui_label": "Gemini Image",
            "ui_description": "Gemini image generation",
            "ui_badge": "",
            "ui_order": 20,
            "input_schema_json": {"prompt": {"type": "string", "required": True}},
            "request_template_json": {"contents": [{"parts": [{"text": "{{prompt}}"}]}]},
            "response_mapping_json": {"image_url": "$.candidates[0].content.parts[0].inlineData"},
            "defaults_json": {"ratio": "1:1"},
            "enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["errors"] == []


def test_validate_media_template_rejects_unknown_provider():
    client = create_test_client()

    response = client.post(
        "/admin/media/templates/validate",
        headers=admin_headers(),
        json={
            "provider_id": 999,
            "model_key": "tts/missing/provider",
            "name": "Broken Template",
            "capability": "tts",
            "template_type": "siliconflow_tts",
            "upstream_model": "tts-1",
            "ui_group": "tts",
            "ui_label": "Broken",
            "ui_description": "",
            "ui_badge": "",
            "ui_order": 5,
            "input_schema_json": {},
            "request_template_json": {},
            "response_mapping_json": {},
            "defaults_json": {},
            "enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert "provider_id does not exist" in payload["errors"]
