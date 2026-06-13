import json

from fastapi.testclient import TestClient
import yaml

from agent.config import AgentConfig
from agent.hermes_writer import write_hermes_config
from agent.sync import sync_once
from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def register_hermes_device(client: TestClient, name: str = "hermes-worker-1") -> dict:
    device = client.post(
        "/admin/hermes/devices",
        headers=admin_headers(),
        json={"name": name, "device_type": "vps"},
    ).json()["device"]
    pairing_token = client.post(
        f"/admin/hermes/devices/{device['id']}/pairing-token",
        headers=admin_headers(),
        json={},
    ).json()["pairing_token"]
    return client.post(
        "/hermes-agent/v1/register",
        json={
            "pairing_token": pairing_token,
            "hostname": f"{name}.internal",
            "platform": "linux",
        },
    ).json()


def test_hermes_agent_register_and_heartbeat():
    client = create_test_client()

    response = register_hermes_device(client)

    assert response["device"]["hostname"] == "hermes-worker-1.internal"
    assert response["sync_token"] != ""

    heartbeat = client.post(
        "/hermes-agent/v1/heartbeat",
        json={"sync_token": response["sync_token"]},
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["device"]["last_seen_at"] is not None


def test_hermes_agent_get_config_and_apply(tmp_path):
    client = create_test_client()
    provider = client.post(
        "/admin/hermes/providers",
        headers=admin_headers(),
        json={
            "name": "relay-hermes",
            "base_url": "https://relay-hermes.example.com/v1",
            "api_key": "sk-hermes",
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
    registration = register_hermes_device(client, name="hermes-sync")
    client.put(
        f"/admin/hermes/devices/{registration['device']['id']}/models",
        headers=admin_headers(),
        json={"model_ids": [model["id"]]},
    )

    meta = client.get(
        "/hermes-agent/v1/config/meta",
        headers={"Authorization": f"Bearer {registration['sync_token']}"},
    )
    assert meta.status_code == 200
    assert meta.json()["version"] == 1

    config = client.get(
        "/hermes-agent/v1/config",
        headers={"Authorization": f"Bearer {registration['sync_token']}"},
    )
    assert config.status_code == 200
    payload = config.json()
    assert "config_yaml" in payload
    parsed_payload = yaml.safe_load(payload["config_yaml"])
    assert parsed_payload["model"]["default"] == "relay-hermes/gpt-5.5"
    assert "provider" not in parsed_payload["model"]
    assert parsed_payload["providers"]["relay-hermes"]["default_headers"] == {
        "HTTP-Referer": "https://hermes-agent.nousresearch.com",
        "X-Title": "Hermes",
    }

    output_path = tmp_path / "config.yaml"
    agent_config = AgentConfig(
        server_url="https://zhaocai.example.com",
        sync_token=registration["sync_token"],
        device_id=registration["device"]["id"],
        target="hermes",
        output_path=str(output_path),
        reload_command="",
    )

    class DummyHermesClient:
        def __init__(self, body: dict):
            self.body = body
            self.applied_reports: list[tuple[int, str]] = []

        def get_config_meta(self, *, sync_token: str) -> dict:
            del sync_token
            return {"version": 2, "etag": '"hermes-etag-2"'}

        def get_config(self, *, sync_token: str) -> dict:
            del sync_token
            return self.body

        def report_applied(self, *, sync_token: str, version: int, status: str) -> None:
            del sync_token
            self.applied_reports.append((version, status))

    sync_client = DummyHermesClient(payload)
    result = sync_once(agent_config, sync_client)
    assert result.changed is True
    parsed_output = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert parsed_output["model"]["default"] == "relay-hermes/gpt-5.5"
    assert "provider" not in parsed_output["model"]
    assert "default_headers" not in parsed_output["model"]
    assert parsed_output["providers"]["relay-hermes"]["default_headers"] == {
        "HTTP-Referer": "https://hermes-agent.nousresearch.com",
        "X-Title": "Hermes",
    }
    assert parsed_output["providers"]["relay-hermes"]["models"] == {"gpt-5.5": {}}
    manifest_path = output_path.parent / ".zhaocai-hermes-managed-plugins.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "relay-hermes" in manifest
    plugin_path = output_path.parent / "plugins" / "model-providers" / "relay-hermes" / "__init__.py"
    assert plugin_path.exists()
    assert sync_client.applied_reports == [(2, "applied")]


def test_hermes_writer_adds_provider_model_indexes_for_picker(tmp_path):
    output_path = tmp_path / "config.yaml"
    payload = {
        "config_yaml": """providers:
  relay-hermes:
    base_url: https://relay-hermes.example.com/v1
    api_key: sk-hermes
    default_headers:
      User-Agent: curl/8.5.0
model:
  default: relay-hermes/gpt-5.5
  fallbacks:
  - relay-hermes/gpt-5.5-mini
""",
        "plugin_files": {},
    }

    write_hermes_config(output_path, payload)

    parsed = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    provider_config = parsed["providers"]["relay-hermes"]
    assert provider_config["model"] == "gpt-5.5"
    assert provider_config["default_model"] == "gpt-5.5"
    assert list(provider_config["models"]) == ["gpt-5.5", "gpt-5.5-mini"]
    assert parsed["model"]["default"] == "relay-hermes/gpt-5.5"
    assert parsed["model"]["fallbacks"] == ["relay-hermes/gpt-5.5-mini"]
    assert "provider" not in parsed["model"]
    assert "fallback_model" not in parsed


def test_hermes_writer_recovers_split_model_config(tmp_path):
    output_path = tmp_path / "config.yaml"
    payload = {
        "config_yaml": """providers:
  relay-hermes:
    base_url: https://relay-hermes.example.com/v1
    api_key: sk-hermes
    default_headers:
      User-Agent: curl/8.5.0
model:
  provider: relay-hermes
  default: gpt-5.5
  base_url: https://relay-hermes.example.com/v1
  api_key: sk-hermes
  default_headers:
    User-Agent: curl/8.5.0
fallback_model:
  provider: relay-hermes
  model: gpt-5.5-mini
  base_url: https://relay-hermes.example.com/v1
  api_key: sk-hermes
""",
        "plugin_files": {},
    }

    write_hermes_config(output_path, payload)

    parsed = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert parsed["model"]["default"] == "relay-hermes/gpt-5.5"
    assert parsed["model"]["fallbacks"] == ["relay-hermes/gpt-5.5-mini"]
    assert "provider" not in parsed["model"]
    assert "base_url" not in parsed["model"]
    assert "api_key" not in parsed["model"]
    assert "default_headers" not in parsed["model"]
    assert "fallback_model" not in parsed
    assert parsed["providers"]["relay-hermes"]["models"] == {"gpt-5.5": {}, "gpt-5.5-mini": {}}
