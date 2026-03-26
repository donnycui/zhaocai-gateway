from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any
from pathlib import Path

from zhaocai_gateway.db.schema import SCHEMA_SQL
from zhaocai_gateway.domain.models import (
    AppliedConfigReport,
    ConfigSnapshot,
    Device,
    Model,
    PairingToken,
    Provider,
)


class SQLiteStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def init_schema(self) -> None:
        self.conn.executescript(SCHEMA_SQL)
        self._ensure_model_column("reasoning", "ALTER TABLE models ADD COLUMN reasoning INTEGER NOT NULL DEFAULT 0")
        self._ensure_model_column(
            "input_modalities",
            "ALTER TABLE models ADD COLUMN input_modalities TEXT NOT NULL DEFAULT '[\"text\"]'",
        )
        self._ensure_model_column("cost_input", "ALTER TABLE models ADD COLUMN cost_input REAL")
        self._ensure_model_column("cost_output", "ALTER TABLE models ADD COLUMN cost_output REAL")
        self._ensure_model_column("cost_cache_read", "ALTER TABLE models ADD COLUMN cost_cache_read REAL")
        self._ensure_model_column("cost_cache_write", "ALTER TABLE models ADD COLUMN cost_cache_write REAL")
        self.conn.commit()

    def _ensure_model_column(self, column: str, ddl: str) -> None:
        columns = [row[1] for row in self.conn.execute("PRAGMA table_info(models)").fetchall()]
        if column not in columns:
            self.conn.execute(ddl)
            self.conn.commit()

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> Model:
        provider_name = row["provider_name"] if "provider_name" in row.keys() else None
        return Model(
            id=int(row["id"]),
            provider_id=int(row["provider_id"]),
            upstream_model=str(row["upstream_model"]),
            display_name=str(row["display_name"]),
            capabilities=json.loads(row["capabilities"] or "[]"),
            reasoning=bool(row["reasoning"]),
            input_modalities=json.loads(row["input_modalities"] or '["text"]'),
            context_window=row["context_window"],
            max_tokens=row["max_tokens"],
            cost_input=row["cost_input"],
            cost_output=row["cost_output"],
            cost_cache_read=row["cost_cache_read"],
            cost_cache_write=row["cost_cache_write"],
            enabled=bool(row["enabled"]),
            provider_name=str(provider_name) if provider_name is not None else None,
        )

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

    def update_provider(
        self,
        provider_id: int,
        *,
        name: str,
        provider_type: str,
        base_url: str,
        auth_scheme: str,
        api_key_encrypted: str,
        extra_headers: dict[str, str],
        enabled: bool,
    ) -> Provider:
        self.conn.execute(
            """
            UPDATE providers
            SET name = ?,
                provider_type = ?,
                base_url = ?,
                auth_scheme = ?,
                api_key_encrypted = ?,
                extra_headers = ?,
                enabled = ?
            WHERE id = ?
            """,
            (
                name,
                provider_type,
                base_url,
                auth_scheme,
                api_key_encrypted,
                json.dumps(extra_headers, ensure_ascii=False),
                int(enabled),
                provider_id,
            ),
        )
        self.conn.commit()
        provider = self.get_provider(provider_id)
        if provider is None:
            raise RuntimeError("Failed to update provider")
        return provider

    def delete_provider(self, provider_id: int) -> None:
        self.conn.execute("DELETE FROM providers WHERE id = ?", (provider_id,))
        self.conn.commit()

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

    def get_provider_by_name(self, name: str) -> Provider | None:
        row = self.conn.execute(
            "SELECT * FROM providers WHERE name = ?",
            (name,),
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

    def list_providers(self) -> list[Provider]:
        rows = self.conn.execute(
            "SELECT * FROM providers ORDER BY id ASC",
        ).fetchall()
        return [
            Provider(
                id=int(row["id"]),
                name=str(row["name"]),
                provider_type=str(row["provider_type"]),
                base_url=str(row["base_url"]),
                auth_scheme=str(row["auth_scheme"]),
                api_key_encrypted=str(row["api_key_encrypted"]),
                extra_headers=json.loads(row["extra_headers"] or "{}"),
                enabled=bool(row["enabled"]),
            )
            for row in rows
        ]

    def create_model(
        self,
        *,
        provider_id: int,
        upstream_model: str,
        display_name: str,
        capabilities: list[str],
        reasoning: bool = False,
        input_modalities: list[str] | None = None,
        context_window: int | None,
        max_tokens: int | None,
        cost_input: float | None = None,
        cost_output: float | None = None,
        cost_cache_read: float | None = None,
        cost_cache_write: float | None = None,
        enabled: bool,
    ) -> Model:
        effective_input_modalities = input_modalities or ["text"]
        cursor = self.conn.execute(
            """
            INSERT INTO models
            (
                provider_id,
                upstream_model,
                display_name,
                capabilities,
                reasoning,
                input_modalities,
                context_window,
                max_tokens,
                cost_input,
                cost_output,
                cost_cache_read,
                cost_cache_write,
                enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider_id,
                upstream_model,
                display_name,
                json.dumps(capabilities, ensure_ascii=False),
                int(reasoning),
                json.dumps(effective_input_modalities, ensure_ascii=False),
                context_window,
                max_tokens,
                cost_input,
                cost_output,
                cost_cache_read,
                cost_cache_write,
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
            """
            SELECT m.*, p.name AS provider_name
            FROM models m
            JOIN providers p ON p.id = m.provider_id
            WHERE m.id = ?
            """,
            (model_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_model(row)

    def get_model_by_provider_and_upstream(
        self,
        provider_id: int,
        upstream_model: str,
    ) -> Model | None:
        row = self.conn.execute(
            """
            SELECT m.*, p.name AS provider_name
            FROM models m
            JOIN providers p ON p.id = m.provider_id
            WHERE m.provider_id = ? AND m.upstream_model = ?
            LIMIT 1
            """,
            (provider_id, upstream_model),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_model(row)

    def list_models(self) -> list[Model]:
        rows = self.conn.execute(
            """
            SELECT m.*, p.name AS provider_name
            FROM models m
            JOIN providers p ON p.id = m.provider_id
            ORDER BY m.id ASC
            """,
        ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def update_model(
        self,
        model_id: int,
        *,
        upstream_model: str,
        display_name: str,
        capabilities: list[str],
        reasoning: bool,
        input_modalities: list[str],
        context_window: int | None,
        max_tokens: int | None,
        cost_input: float | None,
        cost_output: float | None,
        cost_cache_read: float | None,
        cost_cache_write: float | None,
        enabled: bool,
    ) -> Model:
        self.conn.execute(
            """
            UPDATE models
            SET upstream_model = ?,
                display_name = ?,
                capabilities = ?,
                reasoning = ?,
                input_modalities = ?,
                context_window = ?,
                max_tokens = ?,
                cost_input = ?,
                cost_output = ?,
                cost_cache_read = ?,
                cost_cache_write = ?,
                enabled = ?
            WHERE id = ?
            """,
            (
                upstream_model,
                display_name,
                json.dumps(capabilities, ensure_ascii=False),
                int(reasoning),
                json.dumps(input_modalities, ensure_ascii=False),
                context_window,
                max_tokens,
                cost_input,
                cost_output,
                cost_cache_read,
                cost_cache_write,
                int(enabled),
                model_id,
            ),
        )
        self.conn.commit()
        model = self.get_model(model_id)
        if model is None:
            raise RuntimeError("Failed to update model")
        return model

    def delete_model(self, model_id: int) -> None:
        self.conn.execute("DELETE FROM models WHERE id = ?", (model_id,))
        self.conn.commit()

    def upsert_model(
        self,
        *,
        provider_id: int,
        upstream_model: str,
        display_name: str,
        capabilities: list[str],
        reasoning: bool = False,
        input_modalities: list[str] | None = None,
        context_window: int | None,
        max_tokens: int | None,
        cost_input: float | None = None,
        cost_output: float | None = None,
        cost_cache_read: float | None = None,
        cost_cache_write: float | None = None,
        enabled: bool,
    ) -> Model:
        effective_input_modalities = input_modalities or ["text"]
        existing = self.get_model_by_provider_and_upstream(provider_id, upstream_model)
        if existing is None:
            return self.create_model(
                provider_id=provider_id,
                upstream_model=upstream_model,
                display_name=display_name,
                capabilities=capabilities,
                reasoning=reasoning,
                input_modalities=effective_input_modalities,
                context_window=context_window,
                max_tokens=max_tokens,
                cost_input=cost_input,
                cost_output=cost_output,
                cost_cache_read=cost_cache_read,
                cost_cache_write=cost_cache_write,
                enabled=enabled,
            )

        self.conn.execute(
            """
            UPDATE models
            SET display_name = ?,
                capabilities = ?,
                reasoning = ?,
                input_modalities = ?,
                context_window = ?,
                max_tokens = ?,
                cost_input = ?,
                cost_output = ?,
                cost_cache_read = ?,
                cost_cache_write = ?,
                enabled = ?
            WHERE id = ?
            """,
            (
                display_name,
                json.dumps(capabilities, ensure_ascii=False),
                int(reasoning),
                json.dumps(effective_input_modalities, ensure_ascii=False),
                context_window,
                max_tokens,
                cost_input,
                cost_output,
                cost_cache_read,
                cost_cache_write,
                int(enabled),
                existing.id,
            ),
        )
        self.conn.commit()
        model = self.get_model(existing.id)
        if model is None:
            raise RuntimeError("Failed to update model")
        return model

    def list_models_for_device(self, device_id: int) -> list[Model]:
        rows = self.conn.execute(
            """
            SELECT m.*, p.name AS provider_name
            FROM device_model_bindings dmb
            JOIN models m ON m.id = dmb.model_id
            JOIN providers p ON p.id = m.provider_id
            WHERE dmb.device_id = ?
            ORDER BY m.id ASC
            """,
            (device_id,),
        ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def delete_device(self, device_id: int) -> None:
        self.conn.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        self.conn.commit()

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

    def list_devices(self) -> list[Device]:
        rows = self.conn.execute(
            "SELECT * FROM devices ORDER BY id ASC",
        ).fetchall()
        return [
            Device(
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
            for row in rows
        ]

    def set_device_model_bindings(self, *, device_id: int, model_ids: list[int]) -> None:
        self.conn.execute(
            "DELETE FROM device_model_bindings WHERE device_id = ?",
            (device_id,),
        )
        self.conn.executemany(
            "INSERT INTO device_model_bindings (device_id, model_id) VALUES (?, ?)",
            [(device_id, model_id) for model_id in model_ids],
        )
        self.conn.commit()

    def get_device_model_ids(self, device_id: int) -> list[int]:
        rows = self.conn.execute(
            "SELECT model_id FROM device_model_bindings WHERE device_id = ? ORDER BY model_id ASC",
            (device_id,),
        ).fetchall()
        return [int(row["model_id"]) for row in rows]

    def create_pairing_token(
        self,
        *,
        device_id: int,
        token_hash: str,
        expires_at: str,
    ) -> PairingToken:
        cursor = self.conn.execute(
            """
            INSERT INTO pairing_tokens (device_id, token_hash, expires_at)
            VALUES (?, ?, ?)
            """,
            (device_id, token_hash, expires_at),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM pairing_tokens WHERE id = ?",
            (int(cursor.lastrowid),),
        ).fetchone()
        if row is None:
            raise RuntimeError("Failed to create pairing token")
        return PairingToken(
            id=int(row["id"]),
            device_id=int(row["device_id"]),
            token_hash=str(row["token_hash"]),
            expires_at=str(row["expires_at"]),
            used_at=row["used_at"],
            created_at=str(row["created_at"]),
        )

    def consume_pairing_token(
        self,
        *,
        token_hash: str,
        used_at: str,
        now: str,
    ) -> PairingToken | None:
        row = self.conn.execute(
            """
            SELECT *
            FROM pairing_tokens
            WHERE token_hash = ?
              AND used_at IS NULL
              AND expires_at > ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (token_hash, now),
        ).fetchone()
        if row is None:
            return None
        self.conn.execute(
            "UPDATE pairing_tokens SET used_at = ? WHERE id = ?",
            (used_at, int(row["id"])),
        )
        self.conn.commit()
        return PairingToken(
            id=int(row["id"]),
            device_id=int(row["device_id"]),
            token_hash=str(row["token_hash"]),
            expires_at=str(row["expires_at"]),
            used_at=used_at,
            created_at=str(row["created_at"]),
        )

    def activate_device_registration(
        self,
        *,
        device_id: int,
        hostname: str,
        platform: str,
        sync_token_hash: str,
        last_seen_at: str,
    ) -> Device:
        self.conn.execute(
            """
            UPDATE devices
            SET hostname = ?, platform = ?, sync_token_hash = ?, last_seen_at = ?
            WHERE id = ?
            """,
            (hostname, platform, sync_token_hash, last_seen_at, device_id),
        )
        self.conn.commit()
        device = self.get_device(device_id)
        if device is None:
            raise RuntimeError("Failed to activate device registration")
        return device

    def touch_device_heartbeat(
        self,
        *,
        sync_token_hash: str,
        last_seen_at: str,
    ) -> Device | None:
        row = self.conn.execute(
            "SELECT id FROM devices WHERE sync_token_hash = ?",
            (sync_token_hash,),
        ).fetchone()
        if row is None:
            return None
        device_id = int(row["id"])
        self.conn.execute(
            "UPDATE devices SET last_seen_at = ? WHERE id = ?",
            (last_seen_at, device_id),
        )
        self.conn.commit()
        return self.get_device(device_id)

    def save_config_snapshot(self, *, device_id: int, payload: dict[str, Any]) -> ConfigSnapshot:
        payload_text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()

        latest_row = self.conn.execute(
            """
            SELECT *
            FROM config_snapshots
            WHERE device_id = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (device_id,),
        ).fetchone()
        if latest_row is not None and str(latest_row["content_hash"]) == content_hash:
            return ConfigSnapshot(
                id=int(latest_row["id"]),
                device_id=int(latest_row["device_id"]),
                version=int(latest_row["version"]),
                etag=str(latest_row["etag"]),
                payload_json=json.loads(latest_row["payload_json"]),
                content_hash=str(latest_row["content_hash"]),
                created_at=str(latest_row["created_at"]),
            )

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

    def get_latest_config_snapshot(self, device_id: int) -> ConfigSnapshot | None:
        row = self.conn.execute(
            """
            SELECT *
            FROM config_snapshots
            WHERE device_id = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (device_id,),
        ).fetchone()
        if row is None:
            return None
        return ConfigSnapshot(
            id=int(row["id"]),
            device_id=int(row["device_id"]),
            version=int(row["version"]),
            etag=str(row["etag"]),
            payload_json=json.loads(row["payload_json"]),
            content_hash=str(row["content_hash"]),
            created_at=str(row["created_at"]),
        )

    def get_device_by_sync_token_hash(self, sync_token_hash: str) -> Device | None:
        row = self.conn.execute(
            "SELECT * FROM devices WHERE sync_token_hash = ?",
            (sync_token_hash,),
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

    def record_applied_config(
        self,
        *,
        sync_token_hash: str,
        version: int,
        status: str,
    ) -> AppliedConfigReport | None:
        device = self.get_device_by_sync_token_hash(sync_token_hash)
        if device is None:
            return None
        return AppliedConfigReport(
            device_id=device.id,
            version=version,
            status=status,
        )
    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> Model:
        provider_name = row["provider_name"] if "provider_name" in row.keys() else None
        return Model(
            id=int(row["id"]),
            provider_id=int(row["provider_id"]),
            upstream_model=str(row["upstream_model"]),
            display_name=str(row["display_name"]),
            capabilities=json.loads(row["capabilities"] or "[]"),
            reasoning=bool(row["reasoning"]),
            input_modalities=json.loads(row["input_modalities"] or '["text"]'),
            context_window=row["context_window"],
            max_tokens=row["max_tokens"],
            cost_input=row["cost_input"],
            cost_output=row["cost_output"],
            cost_cache_read=row["cost_cache_read"],
            cost_cache_write=row["cost_cache_write"],
            enabled=bool(row["enabled"]),
            provider_name=str(provider_name) if provider_name is not None else None,
        )
