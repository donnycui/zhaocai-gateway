from fastapi.testclient import TestClient


def test_create_app_smoke():
    from zhaocai_gateway.app import create_app

    app = create_app()
    assert app is not None


def test_create_app_serves_index_when_static_dir_present(tmp_path):
    from zhaocai_gateway.app import create_app

    static_dir = tmp_path / "dist"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html><body>v2 ui</body></html>", encoding="utf-8")

    app = create_app(static_dir=static_dir)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "v2 ui" in response.text


def test_create_app_serves_control_route_when_static_dir_present(tmp_path):
    from zhaocai_gateway.app import create_app

    static_dir = tmp_path / "dist"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html><body>control ui</body></html>", encoding="utf-8")

    app = create_app(static_dir=static_dir)
    client = TestClient(app)

    response = client.get("/control")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "control ui" in response.text


def test_load_server_config_parses_sqlite_url(monkeypatch, tmp_path):
    from zhaocai_gateway.config import load_server_config

    db_path = tmp_path / "control-plane.db"
    monkeypatch.setenv("ZHAOCAI_CONTROL_DB", f"sqlite:///{db_path}")
    monkeypatch.setenv("ZHAOCAI_WEB_DIST", str(tmp_path / "dist"))
    monkeypatch.setenv("ZHAOCAI_HOST", "127.0.0.1")
    monkeypatch.setenv("ZHAOCAI_PORT", "4015")

    config = load_server_config()

    assert config.host == "127.0.0.1"
    assert config.port == 4015
    assert config.db_path == str(db_path)


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
