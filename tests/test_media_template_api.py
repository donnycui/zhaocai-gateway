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


def test_validate_media_template_accepts_openai_edit_and_video_types():
    client = create_test_client()
    provider = client.post(
        "/admin/media/providers",
        headers=admin_headers(),
        json={
            "name": "grok-media",
            "base_url": "http://127.0.0.1:8000/v1",
            "auth_type": "bearer",
            "api_key": "sk-test",
            "notes": "",
        },
    ).json()["provider"]

    edit_response = client.post(
        "/admin/media/templates/validate",
        headers=admin_headers(),
        json={
            "provider_id": provider["id"],
            "model_key": "image-edit/grok/imagine-edit",
            "name": "Grok Imagine Image Edit",
            "capability": "image_edit",
            "template_type": "openai_images_edits",
            "upstream_model": "grok-imagine-image-edit",
            "ui_group": "image",
            "ui_label": "Grok Imagine Image Edit",
            "ui_description": "",
            "ui_badge": "grok",
            "ui_order": 10,
            "input_schema_json": {"prompt": {"type": "string", "required": True}},
            "request_template_json": {"endpoint": "/images/edits"},
            "response_mapping_json": {"result_url_path": "$.data[0].url"},
            "defaults_json": {"size": "1024x1024"},
            "enabled": True,
        },
    )
    assert edit_response.status_code == 200
    assert edit_response.json()["ok"] is True

    video_response = client.post(
        "/admin/media/templates/validate",
        headers=admin_headers(),
        json={
            "provider_id": provider["id"],
            "model_key": "video/grok/imagine-video",
            "name": "Grok Imagine Video",
            "capability": "image_to_video",
            "template_type": "openai_videos",
            "upstream_model": "grok-imagine-video",
            "ui_group": "video",
            "ui_label": "Grok Imagine Video",
            "ui_description": "",
            "ui_badge": "grok",
            "ui_order": 20,
            "input_schema_json": {"prompt": {"type": "string", "required": True}},
            "request_template_json": {"create": {"endpoint": "/videos"}},
            "response_mapping_json": {"create_video_id_path": "$.id"},
            "defaults_json": {"size": "720x1280"},
            "enabled": True,
        },
    )
    assert video_response.status_code == 200
    assert video_response.json()["ok"] is True
