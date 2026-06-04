from __future__ import annotations

import json
from collections import OrderedDict

import yaml

from zhaocai_gateway.db.store import SQLiteStore


class HermesConfigCompilerService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def compile_device_config(self, device_id: int) -> dict:
        device = self.store.get_hermes_device(device_id)
        if device is None:
            raise ValueError(f"Hermes device {device_id} not found")

        providers: OrderedDict[str, dict[str, str]] = OrderedDict()
        plugin_files: dict[str, str] = {}
        ordered_model_keys: list[str] = []

        for model in self.store.list_hermes_models_for_device(device_id):
            if not model.enabled:
                continue
            provider = self.store.get_hermes_provider(model.provider_id)
            if provider is None or not provider.enabled:
                continue

            provider_name = provider.name
            if provider_name not in providers:
                providers[provider_name] = {
                    "base_url": provider.base_url,
                    "api_key": provider.api_key_encrypted,
                }
                if provider.plugin_mode == "default_headers":
                    plugin_files[provider_name] = self._render_default_headers_plugin(
                        provider_name=provider_name,
                        base_url=provider.base_url,
                        headers=provider.default_headers_json,
                    )

            ordered_model_keys.append(f"{provider_name}/{model.upstream_model}")

        config_payload: OrderedDict[str, object] = OrderedDict()
        config_payload["providers"] = providers

        model_payload: OrderedDict[str, object] = OrderedDict()
        if ordered_model_keys:
            model_payload["default"] = ordered_model_keys[0]
            if len(ordered_model_keys) > 1:
                model_payload["fallbacks"] = ordered_model_keys[1:]
        config_payload["model"] = model_payload

        config_yaml = yaml.safe_dump(
            json.loads(json.dumps(config_payload, ensure_ascii=False)),
            sort_keys=False,
            allow_unicode=True,
        )
        return {
            "config_yaml": config_yaml,
            "plugin_files": plugin_files,
        }

    def create_snapshot(self, device_id: int):
        payload = self.compile_device_config(device_id)
        return self.store.save_hermes_config_snapshot(device_id=device_id, payload=payload)

    def get_or_create_latest_snapshot(self, device_id: int):
        latest = self.store.get_latest_hermes_config_snapshot(device_id)
        if latest is not None:
            return latest
        return self.create_snapshot(device_id)

    @staticmethod
    def _render_default_headers_plugin(
        *,
        provider_name: str,
        base_url: str,
        headers: dict[str, str],
    ) -> str:
        hostname = base_url.split("://", 1)[-1].split("/", 1)[0]
        display_name = provider_name.replace("-", " ").replace("_", " ").title()
        rendered_headers = json.dumps(headers, ensure_ascii=False, indent=12)
        return (
            "from providers import ProviderProfile, register_provider\n\n"
            "register_provider(\n"
            "    ProviderProfile(\n"
            f'        name="{provider_name}",\n'
            f'        display_name="{display_name}",\n'
            f'        base_url="{base_url}",\n'
            f'        hostname="{hostname}",\n'
            f"        default_headers={rendered_headers},\n"
            "    )\n"
            ")\n"
        )
