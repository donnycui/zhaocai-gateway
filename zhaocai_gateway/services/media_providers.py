from __future__ import annotations

from dataclasses import asdict

from zhaocai_gateway.db.store import SQLiteStore


class MediaProviderService:
    """Dedicated provider inventory for the Media module."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [asdict(provider) for provider in self.store.list_media_providers()]

    def get(self, provider_id: int) -> dict | None:
        provider = self.store.get_media_provider(provider_id)
        if provider is None:
            return None
        return asdict(provider)

    def create(
        self,
        *,
        name: str,
        base_url: str,
        auth_type: str,
        api_key: str,
        notes: str,
    ) -> dict:
        provider = self.store.create_media_provider(
            name=name.strip(),
            base_url=base_url.strip().rstrip("/"),
            auth_type=auth_type.strip().lower(),
            api_key_encrypted=api_key,
            enabled=True,
            notes=notes.strip(),
        )
        return asdict(provider)

    def update(
        self,
        provider_id: int,
        *,
        name: str,
        base_url: str,
        auth_type: str,
        api_key: str,
        enabled: bool,
        notes: str,
    ) -> dict:
        provider = self.store.update_media_provider(
            provider_id,
            name=name.strip(),
            base_url=base_url.strip().rstrip("/"),
            auth_type=auth_type.strip().lower(),
            api_key_encrypted=api_key,
            enabled=enabled,
            notes=notes.strip(),
        )
        return asdict(provider)

    def delete(self, provider_id: int) -> None:
        provider = self.store.get_media_provider(provider_id)
        if provider is None:
            raise ValueError(f"Media provider {provider_id} not found")
        self.store.delete_media_provider(provider_id)
