from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from zhaocai_gateway.db.schema import SCHEMA_SQL
from zhaocai_gateway.domain.models import ConfigSnapshot, Device, Model, Provider


class SQLiteStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def init_schema(self) -> None:
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def create_provider(
        self,
        *,
        name: str,
        provider_type: str,
        base_url: str,
        auth_scheme: str,
        api_key_encrypted: str,
        extra_headers: dict[str, str],
        enabled: bool,
    ) -> Provider:
        cursor = self.conn.execute(
            """
            INSERT INTO providers
            (name, provider_type, base_url, auth_scheme, api_key_encrypted, extra_headers, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                provider_type,
                base_url,
                auth_scheme,
                api_key_encrypted,
                json.dumps(extra_headers, ensure_ascii=False),
                int(enabled),
            ),
        )
        self.conn.commit()
        provider = self.get_provider(int(cursor.lastrowid))
        if provider is None:
            raise RuntimeError("Failed to create provider")
        return provider

    def get_provider(self, provider_id: int) -> Provider | None:
        row = self.conn.execute(
            "SELECT * FROM providers WHERE id = ?",
            (provider_id,),
        ).fetchone()
        if row is None:
            return None
        return Provider(
            id=int(row["id"]),
            name=str(row["name"]),
            provider_type=str(row["provider_type"]),
            base_url=str(row["base_url"]),
            auth_scheme=str(row["auth_scheme"]),
            api_key_encrypted=str(row["api_key_encrypted"]),
            extra_headers=json.loads(row["extra_headers"] or "{}"),
            enabled=bool(row["enabled"]),
        )

    def create_model(
        self,
        *,
        provider_id: int,
        upstream_model: str,
        display_name: str,
        capabilities: list[str],
        context_window: int | None,
        max_tokens: int | None,
        enabled: bool,
    ) -> Model:
        cursor = self.conn.execute(
            """
            INSERT INTO models
            (provider_id, upstream_model, display_name, capabilities, context_window, max_tokens, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider_id,
                upstream_model,
                display_name,
                json.dumps(capabilities, ensure_ascii=False),
                context_window,
                max_tokens,
                int(enabled),
            ),
        )
        self.conn.commit()
        model = self.get_model(int(cursor.lastrowid))
        if model is None:
            raise RuntimeError("Failed to create model")
        return model

    def get_model(self, model_id: int) -> Model | None:
        row = self.conn.execute(
            "SELECT * FROM models WHERE id = ?",
            (model_id,),
        ).fetchone()
        if row is None:
            return None
        return Model(
            id=int(row["id"]),
            provider_id=int(row["provider_id"]),
            upstream_model=str(row["upstream_model"]),
            display_name=str(row["display_name"]),
            capabilities=json.loads(row["capabilities"] or "[]"),
            context_window=row["context_window"],
            max_tokens=row["max_tokens"],
            enabled=bool(row["enabled"]),
        )

    def create_device(
        self,
        *,
        name: str,
        device_type: str,
        hostname: str,
        platform: str,
        active: bool,
    ) -> Device:
        cursor = self.conn.execute(
            """
            INSERT INTO devices
            (name, device_type, hostname, platform, active)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, device_type, hostname, platform, int(active)),
        )
        self.conn.commit()
        device = self.get_device(int(cursor.lastrowid))
        if device is None:
            raise RuntimeError("Failed to create device")
        return device

    def get_device(self, device_id: int) -> Device | None:
        row = self.conn.execute(
            "SELECT * FROM devices WHERE id = ?",
            (device_id,),
        ).fetchone()
        if row is None:
            return None
        return Device(
            id=int(row["id"]),
            name=str(row["name"]),
            device_type=str(row["device_type"]),
            hostname=str(row["hostname"]),
            platform=str(row["platform"]),
            active=bool(row["active"]),
            last_seen_at=row["last_seen_at"],
            sync_token_hash=str(row["sync_token_hash"]),
            current_config_version=int(row["current_config_version"]),
        )

    def save_config_snapshot(self, *, device_id: int, payload: dict[str, Any]) -> ConfigSnapshot:
        payload_text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()

        latest_row = self.conn.execute(
            """
            SELECT version
            FROM config_snapshots
            WHERE device_id = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (device_id,),
        ).fetchone()
        next_version = 1 if latest_row is None else int(latest_row["version"]) + 1
        etag = f"\"{content_hash[:16]}-v{next_version}\""

        cursor = self.conn.execute(
            """
            INSERT INTO config_snapshots
            (device_id, version, etag, payload_json, content_hash)
            VALUES (?, ?, ?, ?, ?)
            """,
            (device_id, next_version, etag, payload_text, content_hash),
        )
        self.conn.execute(
            "UPDATE devices SET current_config_version = ? WHERE id = ?",
            (next_version, device_id),
        )
        self.conn.commit()

        row = self.conn.execute(
            "SELECT * FROM config_snapshots WHERE id = ?",
            (int(cursor.lastrowid),),
        ).fetchone()
        if row is None:
            raise RuntimeError("Failed to create config snapshot")
        return ConfigSnapshot(
            id=int(row["id"]),
            device_id=int(row["device_id"]),
            version=int(row["version"]),
            etag=str(row["etag"]),
            payload_json=json.loads(row["payload_json"]),
            content_hash=str(row["content_hash"]),
            created_at=str(row["created_at"]),
        )
