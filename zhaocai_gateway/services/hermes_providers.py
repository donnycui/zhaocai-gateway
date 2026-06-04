from __future__ import annotations

from dataclasses import asdict
import sqlite3

from zhaocai_gateway.db.store import SQLiteStore


ALLOWED_HERMES_PLUGIN_MODES = {"none", "default_headers"}


class HermesProviderService:
    """Dedicated provider inventory for Hermes nodes."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [asdict(provider) for provider in self.store.list_hermes_providers()]

    def get(self, provider_id: int) -> dict | None:
        provider = self.store.get_hermes_provider(provider_id)
        if provider is None:
            return None
        return asdict(provider)

    def create(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str,
        enabled: bool,
        notes: str,
        plugin_mode: str,
        default_headers_json: dict[str, str],
        source_openclaw_provider_id: int | None = None,
    ) -> dict:
        try:
            provider = self.store.create_hermes_provider(
                name=name.strip(),
                base_url=base_url.strip().rstrip("/"),
                api_key_encrypted=api_key,
                enabled=enabled,
                notes=notes.strip(),
                plugin_mode=self._normalize_plugin_mode(plugin_mode),
                default_headers_json=self._normalize_headers(default_headers_json),
                source_openclaw_provider_id=source_openclaw_provider_id,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Hermes provider name already exists") from exc
        return asdict(provider)

    def update(
        self,
        provider_id: int,
        *,
        name: str,
        base_url: str,
        api_key: str,
        enabled: bool,
        notes: str,
        plugin_mode: str,
        default_headers_json: dict[str, str],
        source_openclaw_provider_id: int | None = None,
    ) -> dict:
        try:
            provider = self.store.update_hermes_provider(
                provider_id,
                name=name.strip(),
                base_url=base_url.strip().rstrip("/"),
                api_key_encrypted=api_key,
                enabled=enabled,
                notes=notes.strip(),
                plugin_mode=self._normalize_plugin_mode(plugin_mode),
                default_headers_json=self._normalize_headers(default_headers_json),
                source_openclaw_provider_id=source_openclaw_provider_id,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Hermes provider name already exists") from exc
        return asdict(provider)

    def delete(self, provider_id: int) -> None:
        provider = self.store.get_hermes_provider(provider_id)
        if provider is None:
            raise ValueError(f"Hermes provider {provider_id} not found")
        self.store.delete_hermes_provider(provider_id)

    def import_openclaw_provider(self, openclaw_provider_id: int) -> dict:
        source = self.store.get_provider(openclaw_provider_id)
        if source is None:
            raise ValueError(f"OpenClaw provider {openclaw_provider_id} not found")

        existing = self.store.get_hermes_provider_by_name(source.name)
        if existing is None:
            provider = self.store.create_hermes_provider(
                name=source.name,
                base_url=source.base_url,
                api_key_encrypted=source.api_key_encrypted,
                enabled=source.enabled,
                notes=f"Imported from OpenClaw provider {source.id}",
                plugin_mode="none",
                default_headers_json={},
                source_openclaw_provider_id=source.id,
            )
            return {"provider": asdict(provider), "action": "created"}

        provider = self.store.update_hermes_provider(
            existing.id,
            name=existing.name,
            base_url=source.base_url,
            api_key_encrypted=source.api_key_encrypted,
            enabled=source.enabled,
            notes=existing.notes or f"Imported from OpenClaw provider {source.id}",
            plugin_mode=existing.plugin_mode,
            default_headers_json=existing.default_headers_json,
            source_openclaw_provider_id=source.id,
        )
        return {"provider": asdict(provider), "action": "updated"}

    @staticmethod
    def _normalize_plugin_mode(plugin_mode: str) -> str:
        normalized = plugin_mode.strip().lower() or "none"
        if normalized not in ALLOWED_HERMES_PLUGIN_MODES:
            raise ValueError("plugin_mode is invalid")
        return normalized

    @staticmethod
    def _normalize_headers(headers: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, value in (headers or {}).items():
            header_key = str(key).strip()
            header_value = str(value).strip()
            if header_key and header_value:
                normalized[header_key] = header_value
        return normalized
