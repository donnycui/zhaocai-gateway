from __future__ import annotations

from zhaocai_gateway.db.store import SQLiteStore


class ConfigCompilerService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def compile_device_config(self, device_id: int) -> dict:
        device = self.store.get_device(device_id)
        if device is None:
            raise ValueError(f"Device {device_id} not found")

        models = []
        provider_map: dict[int, dict] = {}
        for model in self.store.list_models_for_device(device_id):
            if not model.enabled:
                continue
            provider = self.store.get_provider(model.provider_id)
            if provider is None or not provider.enabled:
                continue

            provider_map[provider.id] = {
                "id": provider.id,
                "name": provider.name,
                "provider_type": provider.provider_type,
                "base_url": provider.base_url,
                "auth_scheme": provider.auth_scheme,
                "extra_headers": provider.extra_headers,
            }
            models.append(
                {
                    "id": model.id,
                    "provider_id": model.provider_id,
                    "upstream_model": model.upstream_model,
                    "display_name": model.display_name,
                    "capabilities": model.capabilities,
                    "context_window": model.context_window,
                    "max_tokens": model.max_tokens,
                    "enabled": model.enabled,
                }
            )

        return {
            "device": {
                "id": device.id,
                "name": device.name,
                "device_type": device.device_type,
                "hostname": device.hostname,
                "platform": device.platform,
                "active": device.active,
            },
            "providers": list(provider_map.values()),
            "models": models,
        }

    def create_snapshot(self, device_id: int):
        payload = self.compile_device_config(device_id)
        return self.store.save_config_snapshot(device_id=device_id, payload=payload)

    def get_or_create_latest_snapshot(self, device_id: int):
        latest = self.store.get_latest_config_snapshot(device_id)
        if latest is not None:
            return latest
        return self.create_snapshot(device_id)
