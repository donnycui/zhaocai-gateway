from __future__ import annotations

from collections import defaultdict

from zhaocai_gateway.db.store import SQLiteStore


class ConfigCompilerService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def compile_device_config(self, device_id: int) -> dict:
        device = self.store.get_device(device_id)
        if device is None:
            raise ValueError(f"Device {device_id} not found")

        provider_models: dict[str, list[dict]] = defaultdict(list)
        provider_entries: dict[str, dict] = {}
        catalog_entries: dict[str, dict] = {}
        ordered_model_keys: list[str] = []

        for model in self.store.list_models_for_device(device_id):
            if not model.enabled:
                continue
            provider = self.store.get_provider(model.provider_id)
            if provider is None or not provider.enabled:
                continue

            provider_key = provider.name
            provider_entries[provider_key] = {
                "baseUrl": provider.base_url,
                "apiKey": provider.api_key_encrypted,
                "api": self._to_openclaw_api(provider.provider_type),
                "models": provider_models[provider_key],
            }
            reasoning = "reasoning" in model.capabilities
            input_types = ["text"]
            provider_models[provider_key].append(
                {
                    "id": model.upstream_model,
                    "name": model.display_name,
                    "reasoning": reasoning,
                    "input": input_types,
                    "contextWindow": model.context_window,
                    "maxTokens": model.max_tokens,
                }
            )
            full_model_key = f"{provider_key}/{model.upstream_model}"
            ordered_model_keys.append(full_model_key)
            catalog_entries[full_model_key] = {"alias": model.display_name}

        primary = ordered_model_keys[0] if ordered_model_keys else None
        fallbacks = ordered_model_keys[1:] if len(ordered_model_keys) > 1 else []

        payload = {
            "models": {
                "mode": "merge",
                "providers": dict(provider_entries),
            },
            "agents": {
                "defaults": {
                    "model": {
                        "primary": primary,
                        "fallbacks": fallbacks,
                    }
                    if primary
                    else None,
                    "models": catalog_entries,
                }
            },
        }

        if payload["agents"]["defaults"]["model"] is None:
            payload["agents"]["defaults"].pop("model")
        if not payload["agents"]["defaults"]["models"]:
            payload["agents"]["defaults"].pop("models")
        if not payload["agents"]["defaults"]:
            payload.pop("agents")

        return payload

    @staticmethod
    def _to_openclaw_api(provider_type: str) -> str:
        normalized = (provider_type or "openai-completions").lower()
        if normalized in {"anthropic", "anthropic-messages"}:
            return "anthropic-messages"
        if normalized == "openai-responses":
            return "openai-responses"
        return "openai-completions"

    def create_snapshot(self, device_id: int):
        payload = self.compile_device_config(device_id)
        return self.store.save_config_snapshot(device_id=device_id, payload=payload)

    def get_or_create_latest_snapshot(self, device_id: int):
        latest = self.store.get_latest_config_snapshot(device_id)
        if latest is not None:
            return latest
        return self.create_snapshot(device_id)
