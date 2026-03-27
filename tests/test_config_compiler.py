from zhaocai_gateway.services.config_compiler import ConfigCompilerService


def test_compile_device_specific_model_list(store):
    provider = store.create_provider(
        name="openai",
        provider_type="openai",
        base_url="https://api.openai.com/v1",
        auth_scheme="bearer",
        api_key_encrypted="enc:test",
        extra_headers={},
        enabled=True,
    )
    model = store.create_model(
        provider_id=provider.id,
        upstream_model="gpt-4.1",
        display_name="GPT-4.1",
        capabilities=["text"],
        context_window=128000,
        max_tokens=16000,
        enabled=True,
    )
    device = store.create_device(
        name="macbook-pro",
        device_type="mac",
        hostname="macbook-pro.local",
        platform="darwin",
        active=True,
    )
    store.set_device_model_bindings(device_id=device.id, model_ids=[model.id])

    payload = ConfigCompilerService(store).compile_device_config(device.id)

    assert payload["models"]["mode"] == "merge"
    assert "openai" in payload["models"]["providers"]
    assert payload["models"]["providers"]["openai"]["api"] == "openai-completions"
    assert payload["models"]["providers"]["openai"]["models"][0]["id"] == "gpt-4.1"
    assert payload["agents"]["defaults"]["model"]["primary"] == "openai/gpt-4.1"
    assert payload["agents"]["defaults"]["models"]["openai/gpt-4.1"]["alias"] == "GPT-4.1"


def test_compile_skips_disabled_models(store):
    provider = store.create_provider(
        name="anthropic",
        provider_type="anthropic",
        base_url="https://api.anthropic.com",
        auth_scheme="x-api-key",
        api_key_encrypted="enc:test",
        extra_headers={},
        enabled=True,
    )
    disabled_model = store.create_model(
        provider_id=provider.id,
        upstream_model="claude-sonnet-4.5",
        display_name="Claude Sonnet 4.5",
        capabilities=["text"],
        context_window=200000,
        max_tokens=16000,
        enabled=False,
    )
    device = store.create_device(
        name="worker-1",
        device_type="vps",
        hostname="worker-1.internal",
        platform="linux",
        active=True,
    )
    store.set_device_model_bindings(device_id=device.id, model_ids=[disabled_model.id])

    payload = ConfigCompilerService(store).compile_device_config(device.id)

    assert payload["models"]["providers"] == {}
    assert payload.get("agents", {}).get("defaults", {}) == {}


def test_snapshot_etag_changes_when_payload_changes(store):
    provider = store.create_provider(
        name="openrouter",
        provider_type="openai",
        base_url="https://openrouter.ai/api/v1",
        auth_scheme="bearer",
        api_key_encrypted="enc:test",
        extra_headers={},
        enabled=True,
    )
    first_model = store.create_model(
        provider_id=provider.id,
        upstream_model="gpt-4.1",
        display_name="GPT-4.1",
        capabilities=["text"],
        context_window=128000,
        max_tokens=16000,
        enabled=True,
    )
    second_model = store.create_model(
        provider_id=provider.id,
        upstream_model="gpt-4.1-mini",
        display_name="GPT-4.1 mini",
        capabilities=["text"],
        context_window=128000,
        max_tokens=16000,
        enabled=True,
    )
    device = store.create_device(
        name="vps-2",
        device_type="vps",
        hostname="vps-2.internal",
        platform="linux",
        active=True,
    )
    compiler = ConfigCompilerService(store)

    store.set_device_model_bindings(device_id=device.id, model_ids=[first_model.id])
    first_snapshot = compiler.create_snapshot(device.id)

    store.set_device_model_bindings(device_id=device.id, model_ids=[second_model.id])
    second_snapshot = compiler.create_snapshot(device.id)

    assert first_snapshot.version == 1
    assert second_snapshot.version == 2
    assert first_snapshot.etag != second_snapshot.etag


def test_compile_uses_openai_responses_protocol(store):
    provider = store.create_provider(
        name="responses-provider",
        provider_type="openai-responses",
        base_url="https://example.com/v1",
        auth_scheme="bearer",
        api_key_encrypted="enc:test",
        extra_headers={},
        enabled=True,
    )
    model = store.create_model(
        provider_id=provider.id,
        upstream_model="gpt-5.4",
        display_name="GPT-5.4",
        capabilities=["text"],
        context_window=200000,
        max_tokens=32000,
        enabled=True,
    )
    device = store.create_device(
        name="mac",
        device_type="mac",
        hostname="mac.local",
        platform="darwin",
        active=True,
    )
    store.set_device_model_bindings(device_id=device.id, model_ids=[model.id])

    payload = ConfigCompilerService(store).compile_device_config(device.id)

    assert payload["models"]["providers"]["responses-provider"]["api"] == "openai-responses"


def test_compile_omits_null_numeric_fields_and_keeps_modalities(store):
    provider = store.create_provider(
        name="siliconflow",
        provider_type="openai-completions",
        base_url="https://api.siliconflow.cn/v1",
        auth_scheme="bearer",
        api_key_encrypted="enc:test",
        extra_headers={},
        enabled=True,
    )
    model = store.create_model(
        provider_id=provider.id,
        upstream_model="vision-model",
        display_name="Vision Model",
        capabilities=["text", "multimodal"],
        reasoning=False,
        input_modalities=["text", "image"],
        context_window=None,
        max_tokens=None,
        enabled=True,
    )
    device = store.create_device(
        name="mac",
        device_type="mac",
        hostname="mac.local",
        platform="darwin",
        active=True,
    )
    store.set_device_model_bindings(device_id=device.id, model_ids=[model.id])

    payload = ConfigCompilerService(store).compile_device_config(device.id)
    model_payload = payload["models"]["providers"]["siliconflow"]["models"][0]

    assert model_payload["input"] == ["text", "image"]
    assert "contextWindow" not in model_payload
    assert "maxTokens" not in model_payload


def test_compile_uses_reasoning_boolean_not_capabilities(store):
    provider = store.create_provider(
        name="reasoning-provider",
        provider_type="openai-completions",
        base_url="https://example.com/v1",
        auth_scheme="bearer",
        api_key_encrypted="enc:test",
        extra_headers={},
        enabled=True,
    )
    model = store.create_model(
        provider_id=provider.id,
        upstream_model="reasoning-model",
        display_name="Reasoning Model",
        capabilities=["text"],
        reasoning=True,
        input_modalities=["text"],
        context_window=128000,
        max_tokens=16000,
        enabled=True,
    )
    device = store.create_device(
        name="reasoner",
        device_type="mac",
        hostname="reasoner.local",
        platform="darwin",
        active=True,
    )
    store.set_device_model_bindings(device_id=device.id, model_ids=[model.id])

    payload = ConfigCompilerService(store).compile_device_config(device.id)
    model_payload = payload["models"]["providers"]["reasoning-provider"]["models"][0]

    assert model_payload["reasoning"] is True
