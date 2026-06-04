from __future__ import annotations

import hashlib
import secrets
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from zhaocai_gateway.db.store import SQLiteStore
from zhaocai_gateway.services.node_onboarding import PlatformFamily, build_install_command


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class HermesPairingService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def issue_pairing_token(
        self,
        *,
        device_id: int,
        expires_in_seconds: int = 600,
        platform_family: PlatformFamily | None = None,
    ) -> dict:
        device = self.store.get_hermes_device(device_id)
        if device is None:
            raise ValueError(f"Hermes device {device_id} not found")
        raw_token = secrets.token_urlsafe(24)
        expires_at = _utcnow() + timedelta(seconds=expires_in_seconds)
        pairing_token = self.store.create_hermes_pairing_token(
            device_id=device_id,
            token_hash=_hash_token(raw_token),
            expires_at=expires_at.isoformat(),
        )
        return {
            "device_id": device_id,
            "pairing_token": raw_token,
            "expires_at": pairing_token.expires_at,
            "install_command": build_install_command(
                target="hermes",
                pairing_token=raw_token,
                platform=device.platform,
                device_type=device.device_type,
                platform_family=platform_family,
            ),
        }

    def register_device(
        self,
        *,
        pairing_token: str,
        hostname: str,
        platform: str,
    ) -> dict | None:
        token_row = self.store.consume_hermes_pairing_token(
            token_hash=_hash_token(pairing_token),
            used_at=_utcnow().isoformat(),
            now=_utcnow().isoformat(),
        )
        if token_row is None:
            return None

        raw_sync_token = secrets.token_urlsafe(32)
        device = self.store.activate_hermes_device_registration(
            device_id=token_row.device_id,
            hostname=hostname,
            platform=platform,
            sync_token_hash=_hash_token(raw_sync_token),
            last_seen_at=_utcnow().isoformat(),
        )
        payload = asdict(device)
        payload["model_ids"] = self.store.get_hermes_device_model_ids(device.id)
        return {
            "device": payload,
            "sync_token": raw_sync_token,
        }

    def heartbeat(self, *, sync_token: str) -> dict | None:
        device = self.store.touch_hermes_device_heartbeat(
            sync_token_hash=_hash_token(sync_token),
            last_seen_at=_utcnow().isoformat(),
        )
        if device is None:
            return None
        payload = asdict(device)
        payload["model_ids"] = self.store.get_hermes_device_model_ids(device.id)
        return {"ok": True, "device": payload}
