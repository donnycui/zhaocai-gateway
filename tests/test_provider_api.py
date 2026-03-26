from fastapi.testclient import TestClient
import httpx
import pytest

from zhaocai_gateway.app import create_app

ADMIN_TOKEN = "test-admin-token"


def create_test_client() -> TestClient:
    app = create_app(db_path=":memory:", admin_token=ADMIN_TOKEN)
    return TestClient(app)


def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": ADMIN_TOKEN}


def test_create_provider():
    client = create_test_client()

    response = client.post(
        "/admin/providers",
        headers=admin_headers(),
        json={
            "name": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "provider_type": "openai",
            "auth_scheme": "bearer",
            "api_key": "sk-test",
            "extra_headers": {"HTTP-Referer": "https://example.com"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"]["name"] == "openrouter"
    assert payload["provider"]["provider_type"] == "openai"


def test_validate_provider_input():
    client = create_test_client()

    response = client.post(
        "/admin/providers/validate",
        headers=admin_headers(),
        json={
            "name": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "provider_type": "openai",
            "auth_scheme": "bearer",
            "api_key": "sk-test",
            "extra_headers": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True


@pytest.mark.parametrize(
    ("provider_type", "auth_scheme", "expected_suffix", "expected_header"),
    [
        ("openai-completions", "bearer", "/chat/completions", "Authorization"),
        ("openai-responses", "bearer", "/responses", "Authorization"),
        ("anthropic-messages", "x-api-key", "/messages", "x-api-key"),
    ],
)
def test_test_provider_connectivity_uses_protocol_specific_request(
    monkeypatch,
    provider_type: str,
    auth_scheme: str,
    expected_suffix: str,
    expected_header: str,
):
    client = create_test_client()
    provider_response = client.post(
        "/admin/providers",
        headers=admin_headers(),
        json={
            "name": "provider-under-test",
            "base_url": "https://example.com/v1",
            "provider_type": provider_type,
            "auth_scheme": auth_scheme,
            "api_key": "sk-test",
            "extra_headers": {},
        },
    )
    provider_id = provider_response.json()["provider"]["id"]
    client.post(
        "/admin/models",
        headers=admin_headers(),
        json={
            "provider_id": provider_id,
            "upstream_model": "model-a",
            "display_name": "Model A",
            "capabilities": ["text"],
            "context_window": 128000,
            "max_tokens": 16000,
            "enabled": True,
        },
    )

    calls: list[dict] = []

    class DummyResponse:
        status_code = 200
        is_success = True
        text = ""

        def json(self) -> dict:
            return {"ok": True}

    def fake_request(method: str, url: str, headers: dict, json: dict, timeout: float) -> DummyResponse:
        calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return DummyResponse()

    monkeypatch.setattr(httpx, "request", fake_request)

    response = client.post(
        f"/admin/providers/{provider_id}/test",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["results"][0]["ok"] is True
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"] == f"https://example.com/v1{expected_suffix}"
    assert calls[0]["headers"][expected_header] in {"Bearer sk-test", "sk-test"}
    assert calls[0]["timeout"] == 20.0
    assert calls[0]["json"]["model"] == "model-a"
    if provider_type == "openai-responses":
        assert calls[0]["json"]["input"] == "ping"
    elif provider_type == "anthropic-messages":
        assert calls[0]["headers"]["anthropic-version"] == "2023-06-01"
        assert calls[0]["json"]["messages"][0]["content"] == "ping"
    else:
        assert calls[0]["json"]["messages"][0]["content"] == "ping"


def test_test_provider_connectivity_reports_model_failures(monkeypatch):
    client = create_test_client()
    provider_response = client.post(
        "/admin/providers",
        headers=admin_headers(),
        json={
            "name": "openai",
            "base_url": "https://api.example.com/v1",
            "provider_type": "openai-completions",
            "auth_scheme": "bearer",
            "api_key": "sk-test",
            "extra_headers": {},
        },
    )
    provider_id = provider_response.json()["provider"]["id"]
    client.post(
        "/admin/models",
        headers=admin_headers(),
        json={
            "provider_id": provider_id,
            "upstream_model": "good-model",
            "display_name": "Good Model",
            "capabilities": ["text"],
            "context_window": 128000,
            "max_tokens": 16000,
            "enabled": True,
        },
    )
    client.post(
        "/admin/models",
        headers=admin_headers(),
        json={
            "provider_id": provider_id,
            "upstream_model": "bad-model",
            "display_name": "Bad Model",
            "capabilities": ["text"],
            "context_window": 128000,
            "max_tokens": 16000,
            "enabled": True,
        },
    )

    class DummyResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self.is_success = 200 <= status_code < 300
            self._payload = payload
            self.text = ""

        def json(self) -> dict:
            return self._payload

    def fake_request(method: str, url: str, headers: dict, json: dict, timeout: float) -> DummyResponse:
        if json["model"] == "bad-model":
            return DummyResponse(404, {"error": {"message": "Model not found"}})
        return DummyResponse(200, {"ok": True})

    monkeypatch.setattr(httpx, "request", fake_request)

    response = client.post(f"/admin/providers/{provider_id}/test", headers=admin_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert len(payload["results"]) == 2
    assert any(result["ok"] is False for result in payload["results"])
    assert any("Model not found" in result["message"] for result in payload["results"])


def test_create_model_under_provider():
    client = create_test_client()
    provider_response = client.post(
        "/admin/providers",
        headers=admin_headers(),
        json={
            "name": "openai",
            "base_url": "https://api.openai.com/v1",
            "provider_type": "openai",
            "auth_scheme": "bearer",
            "api_key": "sk-test",
            "extra_headers": {},
        },
    )
    provider_id = provider_response.json()["provider"]["id"]

    response = client.post(
        "/admin/models",
        headers=admin_headers(),
        json={
            "provider_id": provider_id,
            "upstream_model": "gpt-4.1",
            "display_name": "GPT-4.1",
            "capabilities": ["text"],
            "context_window": 128000,
            "max_tokens": 16000,
            "enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"]["provider_id"] == provider_id
    assert payload["model"]["upstream_model"] == "gpt-4.1"


def test_list_providers_and_models():
    client = create_test_client()
    provider_response = client.post(
        "/admin/providers",
        headers=admin_headers(),
        json={
            "name": "anthropic",
            "base_url": "https://api.anthropic.com",
            "provider_type": "anthropic",
            "auth_scheme": "x-api-key",
            "api_key": "sk-ant-test",
            "extra_headers": {},
        },
    )
    provider_id = provider_response.json()["provider"]["id"]
    client.post(
        "/admin/models",
        headers=admin_headers(),
        json={
            "provider_id": provider_id,
            "upstream_model": "claude-sonnet-4.5",
            "display_name": "Claude Sonnet 4.5",
            "capabilities": ["text"],
            "context_window": 200000,
            "max_tokens": 16000,
            "enabled": True,
        },
    )

    providers_response = client.get("/admin/providers", headers=admin_headers())
    models_response = client.get("/admin/models", headers=admin_headers())

    assert providers_response.status_code == 200
    assert models_response.status_code == 200
    assert len(providers_response.json()["providers"]) == 1
    assert len(models_response.json()["models"]) == 1


def test_admin_requires_token():
    client = create_test_client()

    response = client.get("/admin/providers")

    assert response.status_code == 401


def test_sync_openrouter_free_models(monkeypatch):
    client = create_test_client()

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {
                        "id": "google/gemini-2.0-flash-exp:free",
                        "name": "Gemini 2.0 Flash Exp",
                        "pricing": {"prompt": "0", "completion": "0"},
                        "context_length": 1048576,
                    },
                    {
                        "id": "openai/gpt-4o-mini",
                        "name": "GPT-4o mini",
                        "pricing": {"prompt": "1", "completion": "1"},
                    },
                ]
            }

    def fake_get(url: str, timeout: float) -> DummyResponse:
        assert url == "https://openrouter.ai/api/v1/models"
        assert timeout == 30.0
        return DummyResponse()

    monkeypatch.setattr(httpx, "get", fake_get)

    response = client.post(
        "/admin/sync/openrouter-free",
        headers=admin_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["free_models_found"] == 1
    assert payload["created"] == 1
    assert payload["selected_top5"] == ["google/gemini-2.0-flash-exp:free"]

    models_response = client.get("/admin/models", headers=admin_headers())
    models = models_response.json()["models"]
    assert len(models) == 1
    assert models[0]["upstream_model"] == "google/gemini-2.0-flash-exp:free"
    assert models[0]["provider_name"] == "openrouter-free"


def test_sync_openrouter_free_models_keeps_only_top_five(monkeypatch):
    client = create_test_client()

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {
                        "id": f"vendor/model-{index}:free",
                        "name": f"Model {index}",
                        "pricing": {"prompt": "0", "completion": "0"},
                        "context_length": 200000 - (index * 1000),
                    }
                    for index in range(8)
                ]
            }

    monkeypatch.setattr(httpx, "get", lambda url, timeout: DummyResponse())

    response = client.post("/admin/sync/openrouter-free", headers=admin_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["selected_top5"]) == 5

    models_response = client.get("/admin/models", headers=admin_headers())
    models = models_response.json()["models"]
    free_models = [
        model
        for model in models
        if model["provider_name"] == "openrouter-free"
    ]
    assert len(free_models) == 5


def test_sync_openrouter_free_models_guarantees_multimodal(monkeypatch):
    client = create_test_client()

    free_models = []
    for index in range(6):
        item = {
            "id": f"vendor/text-{index}:free",
            "name": f"Text {index}",
            "pricing": {"prompt": "0", "completion": "0"},
            "context_length": 200000 - (index * 1000),
        }
        free_models.append(item)

    free_models.append(
        {
            "id": "vendor/vision-1:free",
            "name": "Vision 1",
            "pricing": {"prompt": "0", "completion": "0"},
            "context_length": 64000,
            "input_modalities": ["text", "image"],
        }
    )

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": free_models}

    monkeypatch.setattr(httpx, "get", lambda url, timeout: DummyResponse())

    response = client.post("/admin/sync/openrouter-free", headers=admin_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["selected_top5"]) == 5
    assert "vendor/vision-1:free" in payload["selected_top5"]

    models_response = client.get("/admin/models", headers=admin_headers())
    models = models_response.json()["models"]
    free_models = [
        model
        for model in models
        if model["provider_name"] == "openrouter-free"
    ]
    assert len(free_models) == 5
    assert any(model["upstream_model"] == "vendor/vision-1:free" for model in free_models)


def test_sync_openrouter_free_models_cleans_legacy_free_rows(monkeypatch):
    client = create_test_client()

    provider = client.post(
        "/admin/providers",
        headers=admin_headers(),
        json={
            "name": "openrouter",
            "base_url": "https://openrouter.ai/api/v1",
            "provider_type": "openai",
            "auth_scheme": "bearer",
            "api_key": "sk-test",
            "extra_headers": {},
        },
    ).json()["provider"]
    client.post(
        "/admin/models",
        headers=admin_headers(),
        json={
            "provider_id": provider["id"],
            "upstream_model": "legacy/free-model:free",
            "display_name": "Legacy Free",
            "capabilities": ["text"],
            "context_window": 32000,
            "max_tokens": 4096,
            "enabled": True,
        },
    )

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {
                        "id": "vendor/new-1:free",
                        "name": "New 1",
                        "pricing": {"prompt": "0", "completion": "0"},
                        "context_length": 128000,
                    }
                ]
            }

    monkeypatch.setattr(httpx, "get", lambda url, timeout: DummyResponse())

    response = client.post("/admin/sync/openrouter-free", headers=admin_headers())

    assert response.status_code == 200
    models_response = client.get("/admin/models", headers=admin_headers())
    models = models_response.json()["models"]
    assert all(model["upstream_model"] != "legacy/free-model:free" for model in models)
