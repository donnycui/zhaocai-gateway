import yaml

from zhaocai_gateway.services.hermes_config_compiler import HermesConfigCompilerService


def test_compile_hermes_device_yaml_and_plugin(store):
    provider = store.create_hermes_provider(
        name="relay-a",
        base_url="https://relay-a.example.com/v1",
        api_key_encrypted="sk-a",
        enabled=True,
        notes="",
        plugin_mode="default_headers",
        default_headers_json={
            "HTTP-Referer": "https://hermes-agent.nousresearch.com",
            "X-Title": "Hermes",
        },
        source_openclaw_provider_id=None,
    )
    model = store.create_hermes_model(
        provider_id=provider.id,
        upstream_model="gpt-5.5",
        display_name="GPT-5.5",
        enabled=True,
    )
    fallback_model = store.create_hermes_model(
        provider_id=provider.id,
        upstream_model="gpt-5.5-mini",
        display_name="GPT-5.5 Mini",
        enabled=True,
    )
    device = store.create_hermes_device(
        name="hermes-compiler",
        device_type="vps",
        hostname="compiler.internal",
        platform="linux",
        active=True,
    )
    store.set_hermes_device_model_bindings(
        device_id=device.id,
        model_ids=[model.id, fallback_model.id],
    )

    payload = HermesConfigCompilerService(store).compile_device_config(device.id)

    parsed = yaml.safe_load(payload["config_yaml"])
    provider_config = parsed["providers"]["relay-a"]
    assert provider_config["base_url"] == "https://relay-a.example.com/v1"
    assert provider_config["default_headers"] == {
        "HTTP-Referer": "https://hermes-agent.nousresearch.com",
        "X-Title": "Hermes",
    }
    assert provider_config["model"] == "gpt-5.5"
    assert provider_config["default_model"] == "gpt-5.5"
    assert list(provider_config["models"]) == ["gpt-5.5", "gpt-5.5-mini"]
    assert parsed["model"]["default"] == "relay-a/gpt-5.5"
    assert parsed["model"]["fallbacks"] == ["relay-a/gpt-5.5-mini"]
    assert "fallback_model" not in parsed
    assert "relay-a" in payload["plugin_files"]
    assert 'name="relay-a"' in payload["plugin_files"]["relay-a"]
    assert (
        '"HTTP-Referer": "https://hermes-agent.nousresearch.com"'
        in payload["plugin_files"]["relay-a"]
    )


def test_hermes_snapshot_reuses_version_when_payload_unchanged(store):
    provider = store.create_hermes_provider(
        name="relay-b",
        base_url="https://relay-b.example.com/v1",
        api_key_encrypted="sk-b",
        enabled=True,
        notes="",
        plugin_mode="none",
        default_headers_json={},
        source_openclaw_provider_id=None,
    )
    model = store.create_hermes_model(
        provider_id=provider.id,
        upstream_model="claude-4.1-sonnet",
        display_name="Claude 4.1 Sonnet",
        enabled=True,
    )
    device = store.create_hermes_device(
        name="hermes-snapshot",
        device_type="vps",
        hostname="snapshot.internal",
        platform="linux",
        active=True,
    )
    store.set_hermes_device_model_bindings(device_id=device.id, model_ids=[model.id])
    compiler = HermesConfigCompilerService(store)

    first = compiler.create_snapshot(device.id)
    second = compiler.create_snapshot(device.id)

    assert first.version == 1
    assert second.version == 1
    assert first.etag == second.etag
