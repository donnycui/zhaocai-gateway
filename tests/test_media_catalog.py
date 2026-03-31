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
