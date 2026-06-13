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

        providers: OrderedDict[str, dict[str, object]] = OrderedDict()
        plugin_files: dict[str, str] = {}
        ordered_model_refs: list[tuple[str, str]] = []
        provider_model_ids: OrderedDict[str, list[str]] = OrderedDict()

        for model in self.store.list_hermes_models_for_device(device_id):
            if not model.enabled:
                continue
            provider = self.store.get_hermes_provider(model.provider_id)
            if provider is None or not provider.enabled:
                continue

            provider_name = provider.name
            if provider_name not in providers:
                provider_headers = self._headers_for_provider_config(
                    plugin_mode=provider.plugin_mode,
                    headers=provider.default_headers_json,
                )
                providers[provider_name] = {
                    "base_url": provider.base_url,
                    "api_key": provider.api_key_encrypted,
                }
                if provider_headers:
                    providers[provider_name]["default_headers"] = provider_headers
                if provider.plugin_mode == "default_headers":
                    plugin_files[provider_name] = self._render_default_headers_plugin(
                        provider_name=provider_name,
                        base_url=provider.base_url,
                        headers=provider.default_headers_json,
                    )

            provider_model_ids.setdefault(provider_name, [])
            if model.upstream_model not in provider_model_ids[provider_name]:
                provider_model_ids[provider_name].append(model.upstream_model)
            ordered_model_refs.append((provider_name, model.upstream_model))

        for provider_name, model_ids in provider_model_ids.items():
            if not model_ids:
                continue
            provider_config = providers[provider_name]
            provider_config["model"] = model_ids[0]
            provider_config["default_model"] = model_ids[0]
            provider_config["models"] = OrderedDict((model_id, {}) for model_id in model_ids)

        config_payload: OrderedDict[str, object] = OrderedDict()
        config_payload["providers"] = providers

        model_payload: OrderedDict[str, object] = OrderedDict()
        if ordered_model_refs:
            primary_provider, primary_model = ordered_model_refs[0]
            model_payload["default"] = f"{primary_provider}/{primary_model}"
            if len(ordered_model_refs) > 1:
                model_payload["fallbacks"] = [
                    f"{provider_name}/{upstream_model}"
                    for provider_name, upstream_model in ordered_model_refs[1:]
                ]
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
    def _headers_for_provider_config(
        *,
        plugin_mode: str,
        headers: dict[str, str],
    ) -> dict[str, str]:
        if plugin_mode != "default_headers":
            return {}
        return dict(headers or {})

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
