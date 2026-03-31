from __future__ import annotations

from dataclasses import asdict

from zhaocai_gateway.db.store import SQLiteStore


class MediaProviderService:
    """Dedicated provider inventory for the Media module."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [asdict(provider) for provider in self.store.list_media_providers()]

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
