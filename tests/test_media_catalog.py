from fastapi.testclient import TestClient

from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def test_media_catalog_exports_enabled_templates():
    client = create_test_client()
    provider = client.post(
        "/admin/media/providers",
        headers=admin_headers(),
        json={
            "name": "siliconflow-media",
            "base_url": "https://api.siliconflow.cn/v1",
            "auth_type": "bearer",
            "api_key": "sk-test",
            "notes": "",
        },
    ).json()["provider"]

    client.post(
        "/admin/media/templates",
        headers=admin_headers(),
        json={
            "provider_id": provider["id"],
            "model_key": "tts/siliconflow/default",
            "name": "SiliconFlow TTS",
            "capability": "tts",
            "template_type": "siliconflow_tts",
            "upstream_model": "speech-1",
            "ui_group": "tts",
            "ui_label": "SiliconFlow TTS",
            "ui_description": "tts template",
            "ui_badge": "stable",
            "ui_order": 30,
            "input_schema_json": {"text": {"type": "string", "required": True}},
            "request_template_json": {"input": "{{text}}"},
            "response_mapping_json": {"audio_url": "$.data.url"},
            "defaults_json": {"voice": "female"},
            "enabled": True,
        },
    )

    response = client.get("/admin/media/catalog", headers=admin_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["catalog"]) == 1
    item = payload["catalog"][0]
    assert item["provider"] == "siliconflow-media"
    assert item["template_type"] == "siliconflow_tts"
    assert item["model_key"] == "tts/siliconflow/default"
    assert item["display_name"] == "SiliconFlow TTS"
    assert item["defaults"] == {"voice": "female"}


def test_media_catalog_derives_video_mode_and_edit_flags():
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

    client.post(
        "/admin/media/templates",
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
            "input_schema_json": {
                "prompt": {"type": "string", "required": True},
                "images": {"type": "file[]", "required": True},
                "size": {"type": "enum", "options": ["1024x1024", "1280x720"]},
            },
            "request_template_json": {"endpoint": "/images/edits"},
            "response_mapping_json": {"result_url_path": "$.data[0].url"},
            "defaults_json": {"size": "1024x1024"},
            "enabled": True,
        },
    )

    client.post(
        "/admin/media/templates",
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
            "input_schema_json": {
                "prompt": {"type": "string", "required": True},
                "size": {"type": "enum", "options": ["720x1280", "1280x720"]},
                "seconds": {"type": "enum", "options": [6, 10]},
            },
            "request_template_json": {"create": {"endpoint": "/videos"}},
            "response_mapping_json": {"create_video_id_path": "$.id"},
            "defaults_json": {"size": "720x1280", "seconds": 6},
            "enabled": True,
        },
    )

    response = client.get("/admin/media/catalog", headers=admin_headers())
    assert response.status_code == 200
    catalog = response.json()["catalog"]
    image_edit = next(item for item in catalog if item["model_key"] == "image-edit/grok/imagine-edit")
    video = next(item for item in catalog if item["model_key"] == "video/grok/imagine-video")

    assert image_edit["requires_start_image"] is True
    assert image_edit["ratios"] == ["1:1", "16:9"]
    assert video["mode"] == "video"
    assert video["ratios"] == ["9:16", "16:9"]
