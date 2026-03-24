def test_create_app_smoke():
    from zhaocai_gateway.app import create_app

    app = create_app()
    assert app is not None
