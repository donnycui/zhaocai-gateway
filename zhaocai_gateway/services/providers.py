from __future__ import annotations

from dataclasses import asdict
from urllib.parse import urlparse

from zhaocai_gateway.db.store import SQLiteStore


class ProviderService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [asdict(provider) for provider in self.store.list_providers()]

    def get(self, provider_id: int) -> dict | None:
        provider = self.store.get_provider(provider_id)
        if provider is None:
            return None
        return asdict(provider)

    def create(
        self,
        *,
        name: str,
        base_url: str,
        provider_type: str,
        auth_scheme: str,
        api_key: str,
        extra_headers: dict[str, str],
    ) -> dict:
        provider = self.store.create_provider(
            name=name,
            provider_type=provider_type,
            base_url=base_url,
            auth_scheme=auth_scheme,
            api_key_encrypted=api_key,
            extra_headers=extra_headers,
            enabled=True,
        )
        return asdict(provider)

    def update(
        self,
        provider_id: int,
        *,
        name: str,
        base_url: str,
        provider_type: str,
        auth_scheme: str,
        api_key: str,
        extra_headers: dict[str, str],
        enabled: bool,
    ) -> dict:
        provider = self.store.update_provider(
            provider_id,
            name=name,
            base_url=base_url,
            provider_type=provider_type,
            auth_scheme=auth_scheme,
            api_key_encrypted=api_key,
            extra_headers=extra_headers,
            enabled=enabled,
        )
        return asdict(provider)

    def delete(self, provider_id: int) -> None:
        self.store.delete_provider(provider_id)

    def validate(
        self,
        *,
        base_url: str,
        auth_scheme: str,
    ) -> dict:
        parsed = urlparse(base_url)
        ok = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        auth_ok = auth_scheme in {"bearer", "x-api-key", "basic"}
        return {
            "ok": bool(ok and auth_ok),
            "message": "Provider input looks valid" if ok and auth_ok else "Invalid provider input",
        }
