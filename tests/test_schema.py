def test_create_app_smoke():
    from zhaocai_gateway.app import create_app

    app = create_app()
    assert app is not None


def test_provider_insert_and_read(store):
    provider = store.create_provider(
        name="openrouter",
        provider_type="openai",
        base_url="https://openrouter.ai/api/v1",
        auth_scheme="bearer",
        api_key_encrypted="enc:test",
        extra_headers={"HTTP-Referer": "https://example.com"},
        enabled=True,
    )

    fetched = store.get_provider(provider.id)

    assert fetched is not None
    assert fetched.name == "openrouter"
    assert fetched.base_url == "https://openrouter.ai/api/v1"
    assert fetched.extra_headers == {"HTTP-Referer": "https://example.com"}


def test_model_insert_and_read(store):
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

    fetched = store.get_model(model.id)

    assert fetched is not None
    assert fetched.provider_id == provider.id
    assert fetched.upstream_model == "gpt-4.1"
    assert fetched.capabilities == ["text"]


def test_device_insert_and_read(store):
    device = store.create_device(
        name="macbook-pro",
        device_type="mac",
        hostname="macbook-pro.local",
        platform="darwin",
        active=True,
    )

    fetched = store.get_device(device.id)

    assert fetched is not None
    assert fetched.name == "macbook-pro"
    assert fetched.device_type == "mac"
    assert fetched.platform == "darwin"


def test_snapshot_versions_increment(store):
    device = store.create_device(
        name="vps-1",
        device_type="vps",
        hostname="vps-1",
        platform="linux",
        active=True,
    )

    first = store.save_config_snapshot(device_id=device.id, payload={"a": 1})
    second = store.save_config_snapshot(device_id=device.id, payload={"a": 2})

    assert first.version == 1
    assert second.version == 2
    assert first.device_id == device.id
    assert second.device_id == device.id
