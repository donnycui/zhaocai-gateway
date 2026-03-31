from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import secrets

from zhaocai_gateway.db.store import SQLiteStore


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash_key(raw_api_key: str) -> str:
    return hashlib.sha256(raw_api_key.encode("utf-8")).hexdigest()


def _key_hint(raw_api_key: str) -> str:
    if len(raw_api_key) <= 8:
        return raw_api_key
    return f"{raw_api_key[:4]}...{raw_api_key[-4:]}"


class GatewayClientKeyService:
    """Gateway client-key service for project-facing unified access."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [asdict(item) for item in self.store.list_gateway_client_keys()]

    def create(
        self,
        *,
        name: str,
        api_key: str,
        notes: str,
    ) -> dict:
        raw_api_key = api_key.strip() or self._generate_key()
        client_key = self.store.create_gateway_client_key(
            name=name.strip(),
            api_key_hash=_hash_key(raw_api_key),
            key_hint=_key_hint(raw_api_key),
            enabled=True,
            notes=notes.strip(),
        )
        payload = asdict(client_key)
        payload["raw_api_key"] = raw_api_key
        return payload

    def update(
        self,
        client_key_id: int,
        *,
        enabled: bool,
        notes: str,
    ) -> dict:
        client_key = self.store.update_gateway_client_key(
            client_key_id,
            enabled=enabled,
            notes=notes.strip(),
        )
        return asdict(client_key)

    def authenticate(self, raw_api_key: str) -> dict | None:
        client_key = self.store.get_gateway_client_key_by_hash(_hash_key(raw_api_key.strip()))
        if client_key is None or not client_key.enabled:
            return None
        touched = self.store.touch_gateway_client_key(client_key.id, last_used_at=_utc_now_iso())
        return asdict(touched)

    def has_enabled_keys(self) -> bool:
        return self.store.has_enabled_gateway_client_keys()

    @staticmethod
    def _generate_key() -> str:
        return f"zgk_{secrets.token_urlsafe(24)}"
