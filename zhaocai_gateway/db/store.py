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
    GatewayAlias,
    GatewayAliasTarget,
    GatewayClientKey,
    GatewayModel,
    GatewayUpstreamAccount,
    MediaProvider,
    MediaTemplate,
    Model,
    PairingToken,
    Provider,
    UniversalProviderTemplate,
    UniversalProviderTemplateModel,
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
        self._ensure_device_column(
            "preserve_providers_json",
            "ALTER TABLE devices ADD COLUMN preserve_providers_json TEXT NOT NULL DEFAULT '[]'",
        )
        self._ensure_device_column(
            "preserve_models_json",
            "ALTER TABLE devices ADD COLUMN preserve_models_json TEXT NOT NULL DEFAULT '[]'",
        )
        self.conn.commit()

    def _ensure_model_column(self, column: str, ddl: str) -> None:
        columns = [row[1] for row in self.conn.execute("PRAGMA table_info(models)").fetchall()]
        if column not in columns:
            self.conn.execute(ddl)
            self.conn.commit()

    def _ensure_device_column(self, column: str, ddl: str) -> None:
        columns = [row[1] for row in self.conn.execute("PRAGMA table_info(devices)").fetchall()]
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

    @staticmethod
    def _row_to_gateway_upstream_account(row: sqlite3.Row) -> GatewayUpstreamAccount:
        synced_models_count = row["synced_models_count"] if "synced_models_count" in row.keys() else 0
        return GatewayUpstreamAccount(
            id=int(row["id"]),
            name=str(row["name"]),
            base_url=str(row["base_url"]),
            auth_type=str(row["auth_type"]),
            api_key_encrypted=str(row["api_key_encrypted"]),
            protocol=str(row["protocol"]),
            enabled=bool(row["enabled"]),
            health_status=str(row["health_status"]),
            cooldown_until=str(row["cooldown_until"]) if row["cooldown_until"] is not None else None,
            last_checked_at=str(row["last_checked_at"]) if row["last_checked_at"] is not None else None,
            last_synced_at=str(row["last_synced_at"]) if row["last_synced_at"] is not None else None,
            notes=str(row["notes"] or ""),
            synced_models_count=int(synced_models_count or 0),
        )

    @staticmethod
    def _row_to_gateway_model(row: sqlite3.Row) -> GatewayModel:
        account_name = row["account_name"] if "account_name" in row.keys() else None
        family = row["family"] if "family" in row.keys() else None
        return GatewayModel(
            id=int(row["id"]),
            account_id=int(row["account_id"]),
            upstream_model=str(row["upstream_model"]),
            display_name=str(row["display_name"]),
            family=str(family) if family is not None else None,
            supports_chat=bool(row["supports_chat"]),
            supports_responses=bool(row["supports_responses"]),
            enabled=bool(row["enabled"]),
            account_name=str(account_name) if account_name is not None else None,
        )

    @staticmethod
    def _row_to_gateway_alias(row: sqlite3.Row) -> GatewayAlias:
        return GatewayAlias(
            id=int(row["id"]),
            alias_key=str(row["alias_key"]),
            display_name=str(row["display_name"]),
            alias_type=str(row["alias_type"]),
            enabled=bool(row["enabled"]),
            visibility=str(row["visibility"]),
            notes=str(row["notes"] or ""),
        )

    @staticmethod
    def _row_to_gateway_alias_target(row: sqlite3.Row) -> GatewayAliasTarget:
        account_name = row["account_name"] if "account_name" in row.keys() else None
        model_display_name = row["model_display_name"] if "model_display_name" in row.keys() else None
        upstream_model = row["upstream_model"] if "upstream_model" in row.keys() else None
        return GatewayAliasTarget(
            id=int(row["id"]),
            alias_id=int(row["alias_id"]),
            account_id=int(row["account_id"]),
            model_id=int(row["model_id"]),
            priority=int(row["priority"]),
            enabled=bool(row["enabled"]),
            fallback_on_timeout=bool(row["fallback_on_timeout"]),
            fallback_on_5xx=bool(row["fallback_on_5xx"]),
            fallback_on_429=bool(row["fallback_on_429"]),
            cooldown_seconds=int(row["cooldown_seconds"]),
            account_name=str(account_name) if account_name is not None else None,
            model_display_name=str(model_display_name) if model_display_name is not None else None,
            upstream_model=str(upstream_model) if upstream_model is not None else None,
        )

    @staticmethod
    def _row_to_gateway_client_key(row: sqlite3.Row) -> GatewayClientKey:
        return GatewayClientKey(
            id=int(row["id"]),
            name=str(row["name"]),
            api_key_hash=str(row["api_key_hash"]),
            key_hint=str(row["key_hint"]),
            enabled=bool(row["enabled"]),
            notes=str(row["notes"] or ""),
            last_used_at=str(row["last_used_at"]) if row["last_used_at"] is not None else None,
        )

    @staticmethod
    def _row_to_media_provider(row: sqlite3.Row) -> MediaProvider:
        return MediaProvider(
            id=int(row["id"]),
            name=str(row["name"]),
            base_url=str(row["base_url"]),
            auth_type=str(row["auth_type"]),
            api_key_encrypted=str(row["api_key_encrypted"]),
            enabled=bool(row["enabled"]),
            notes=str(row["notes"] or ""),
        )

    @staticmethod
    def _row_to_media_template(row: sqlite3.Row) -> MediaTemplate:
        provider_name = row["provider_name"] if "provider_name" in row.keys() else None
        return MediaTemplate(
            id=int(row["id"]),
            provider_id=int(row["provider_id"]),
            model_key=str(row["model_key"]),
            name=str(row["name"]),
            capability=str(row["capability"]),
            template_type=str(row["template_type"]),
            upstream_model=str(row["upstream_model"]),
            ui_group=str(row["ui_group"] or ""),
            ui_label=str(row["ui_label"] or ""),
            ui_description=str(row["ui_description"] or ""),
            ui_badge=str(row["ui_badge"] or ""),
            ui_order=int(row["ui_order"]),
            input_schema_json=json.loads(row["input_schema_json"] or "{}"),
            request_template_json=json.loads(row["request_template_json"] or "{}"),
            response_mapping_json=json.loads(row["response_mapping_json"] or "{}"),
            defaults_json=json.loads(row["defaults_json"] or "{}"),
            enabled=bool(row["enabled"]),
            provider_name=str(provider_name) if provider_name is not None else None,
        )

    @staticmethod
    def _row_to_universal_provider_template(row: sqlite3.Row) -> UniversalProviderTemplate:
        return UniversalProviderTemplate(
            id=int(row["id"]),
            name=str(row["name"]),
            base_url=str(row["base_url"]),
            auth_type=str(row["auth_type"]),
            api_key_encrypted=str(row["api_key_encrypted"]),
            protocol=str(row["protocol"]),
            notes=str(row["notes"] or ""),
        )

    @staticmethod
    def _row_to_universal_provider_template_model(row: sqlite3.Row) -> UniversalProviderTemplateModel:
        return UniversalProviderTemplateModel(
            id=int(row["id"]),
            template_id=int(row["template_id"]),
            upstream_model=str(row["upstream_model"]),
            display_name=str(row["display_name"]),
            capabilities=json.loads(row["capabilities"] or "[]"),
            reasoning=bool(row["reasoning"]),
            input_modalities=json.loads(row["input_modalities"] or '["text"]'),
            context_window=row["context_window"],
            max_tokens=row["max_tokens"],
            enabled=bool(row["enabled"]),
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

    @staticmethod
    def _row_to_provider(row: sqlite3.Row) -> Provider:
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
        return self._row_to_provider(row)

    def get_provider_by_name(self, name: str) -> Provider | None:
        row = self.conn.execute(
            "SELECT * FROM providers WHERE name = ?",
            (name,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_provider(row)

    def list_providers(self) -> list[Provider]:
        rows = self.conn.execute(
            "SELECT * FROM providers ORDER BY id ASC",
        ).fetchall()
        return [self._row_to_provider(row) for row in rows]

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

    def create_gateway_upstream_account(
        self,
        *,
        name: str,
        base_url: str,
        auth_type: str,
        api_key_encrypted: str,
        protocol: str,
        enabled: bool,
        notes: str,
    ) -> GatewayUpstreamAccount:
        cursor = self.conn.execute(
            """
            INSERT INTO gateway_upstream_accounts
            (name, base_url, auth_type, api_key_encrypted, protocol, enabled, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                base_url,
                auth_type,
                api_key_encrypted,
                protocol,
                int(enabled),
                notes,
            ),
        )
        self.conn.commit()
        account = self.get_gateway_upstream_account(int(cursor.lastrowid))
        if account is None:
            raise RuntimeError("Failed to create gateway upstream account")
        return account

    def get_gateway_upstream_account(self, account_id: int) -> GatewayUpstreamAccount | None:
        row = self.conn.execute(
            """
            SELECT gua.*,
                   (
                       SELECT COUNT(*)
                       FROM gateway_models gm
                       WHERE gm.account_id = gua.id AND gm.enabled = 1
                   ) AS synced_models_count
            FROM gateway_upstream_accounts gua
            WHERE gua.id = ?
            """,
            (account_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_gateway_upstream_account(row)

    def list_gateway_upstream_accounts(self) -> list[GatewayUpstreamAccount]:
        rows = self.conn.execute(
            """
            SELECT gua.*,
                   (
                       SELECT COUNT(*)
                       FROM gateway_models gm
                       WHERE gm.account_id = gua.id AND gm.enabled = 1
                   ) AS synced_models_count
            FROM gateway_upstream_accounts gua
            ORDER BY gua.id ASC
            """
        ).fetchall()
        return [self._row_to_gateway_upstream_account(row) for row in rows]

    def update_gateway_upstream_account_status(
        self,
        account_id: int,
        *,
        health_status: str,
        last_checked_at: str | None = None,
        cooldown_until: str | None = None,
        last_synced_at: str | None = None,
    ) -> GatewayUpstreamAccount:
        self.conn.execute(
            """
            UPDATE gateway_upstream_accounts
            SET health_status = ?,
                last_checked_at = COALESCE(?, last_checked_at),
                cooldown_until = ?,
                last_synced_at = COALESCE(?, last_synced_at),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                health_status,
                last_checked_at,
                cooldown_until,
                last_synced_at,
                account_id,
            ),
        )
        self.conn.commit()
        account = self.get_gateway_upstream_account(account_id)
        if account is None:
            raise RuntimeError("Failed to update gateway upstream account")
        return account

    def list_gateway_models(self, account_id: int | None = None) -> list[GatewayModel]:
        params: tuple[Any, ...] = ()
        where = ""
        if account_id is not None:
            where = "WHERE gm.account_id = ?"
            params = (account_id,)

        rows = self.conn.execute(
            f"""
            SELECT gm.*, gua.name AS account_name
            FROM gateway_models gm
            JOIN gateway_upstream_accounts gua ON gua.id = gm.account_id
            {where}
            ORDER BY gm.id ASC
            """,
            params,
        ).fetchall()
        return [self._row_to_gateway_model(row) for row in rows]

    def get_gateway_model_by_account_and_upstream(
        self,
        account_id: int,
        upstream_model: str,
    ) -> GatewayModel | None:
        row = self.conn.execute(
            """
            SELECT gm.*, gua.name AS account_name
            FROM gateway_models gm
            JOIN gateway_upstream_accounts gua ON gua.id = gm.account_id
            WHERE gm.account_id = ? AND gm.upstream_model = ?
            LIMIT 1
            """,
            (account_id, upstream_model),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_gateway_model(row)

    def get_gateway_model(self, model_id: int) -> GatewayModel | None:
        row = self.conn.execute(
            """
            SELECT gm.*, gua.name AS account_name
            FROM gateway_models gm
            JOIN gateway_upstream_accounts gua ON gua.id = gm.account_id
            WHERE gm.id = ?
            LIMIT 1
            """,
            (model_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_gateway_model(row)

    def upsert_gateway_model(
        self,
        *,
        account_id: int,
        upstream_model: str,
        display_name: str,
        family: str | None,
        supports_chat: bool,
        supports_responses: bool,
        enabled: bool,
    ) -> GatewayModel:
        existing = self.get_gateway_model_by_account_and_upstream(account_id, upstream_model)
        if existing is None:
            cursor = self.conn.execute(
                """
                INSERT INTO gateway_models
                (account_id, upstream_model, display_name, family, supports_chat, supports_responses, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id,
                    upstream_model,
                    display_name,
                    family,
                    int(supports_chat),
                    int(supports_responses),
                    int(enabled),
                ),
            )
            self.conn.commit()
            model = self.conn.execute(
                """
                SELECT gm.*, gua.name AS account_name
                FROM gateway_models gm
                JOIN gateway_upstream_accounts gua ON gua.id = gm.account_id
                WHERE gm.id = ?
                """,
                (int(cursor.lastrowid),),
            ).fetchone()
            if model is None:
                raise RuntimeError("Failed to create gateway model")
            return self._row_to_gateway_model(model)

        self.conn.execute(
            """
            UPDATE gateway_models
            SET display_name = ?,
                family = ?,
                supports_chat = ?,
                supports_responses = ?,
                enabled = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                display_name,
                family,
                int(supports_chat),
                int(supports_responses),
                int(enabled),
                existing.id,
            ),
        )
        self.conn.commit()
        model = self.get_gateway_model_by_account_and_upstream(account_id, upstream_model)
        if model is None:
            raise RuntimeError("Failed to update gateway model")
        return model

    def disable_missing_gateway_models(self, account_id: int, keep_upstream_models: set[str]) -> None:
        rows = self.conn.execute(
            "SELECT id, upstream_model FROM gateway_models WHERE account_id = ?",
            (account_id,),
        ).fetchall()
        for row in rows:
            if str(row["upstream_model"]) not in keep_upstream_models:
                self.conn.execute(
                    """
                    UPDATE gateway_models
                    SET enabled = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (int(row["id"]),),
                )
        self.conn.commit()

    def create_gateway_alias(
        self,
        *,
        alias_key: str,
        display_name: str,
        alias_type: str,
        enabled: bool,
        visibility: str,
        notes: str,
    ) -> GatewayAlias:
        cursor = self.conn.execute(
            """
            INSERT INTO gateway_aliases
            (alias_key, display_name, alias_type, enabled, visibility, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                alias_key,
                display_name,
                alias_type,
                int(enabled),
                visibility,
                notes,
            ),
        )
        self.conn.commit()
        alias = self.get_gateway_alias(int(cursor.lastrowid))
        if alias is None:
            raise RuntimeError("Failed to create gateway alias")
        return alias

    def get_gateway_alias(self, alias_id: int) -> GatewayAlias | None:
        row = self.conn.execute(
            "SELECT * FROM gateway_aliases WHERE id = ?",
            (alias_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_gateway_alias(row)

    def get_gateway_alias_by_key(self, alias_key: str) -> GatewayAlias | None:
        row = self.conn.execute(
            "SELECT * FROM gateway_aliases WHERE alias_key = ? LIMIT 1",
            (alias_key,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_gateway_alias(row)

    def list_gateway_aliases(self) -> list[GatewayAlias]:
        rows = self.conn.execute(
            "SELECT * FROM gateway_aliases ORDER BY id ASC",
        ).fetchall()
        return [self._row_to_gateway_alias(row) for row in rows]

    def update_gateway_alias(
        self,
        alias_id: int,
        *,
        display_name: str,
        enabled: bool,
        visibility: str,
        notes: str,
    ) -> GatewayAlias:
        self.conn.execute(
            """
            UPDATE gateway_aliases
            SET display_name = ?,
                enabled = ?,
                visibility = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                display_name,
                int(enabled),
                visibility,
                notes,
                alias_id,
            ),
        )
        self.conn.commit()
        alias = self.get_gateway_alias(alias_id)
        if alias is None:
            raise RuntimeError("Failed to update gateway alias")
        return alias

    def list_gateway_alias_targets(self, alias_id: int) -> list[GatewayAliasTarget]:
        rows = self.conn.execute(
            """
            SELECT gat.*, gua.name AS account_name, gm.display_name AS model_display_name, gm.upstream_model
            FROM gateway_alias_targets gat
            JOIN gateway_upstream_accounts gua ON gua.id = gat.account_id
            JOIN gateway_models gm ON gm.id = gat.model_id
            WHERE gat.alias_id = ?
            ORDER BY gat.priority ASC, gat.id ASC
            """,
            (alias_id,),
        ).fetchall()
        return [self._row_to_gateway_alias_target(row) for row in rows]

    def replace_gateway_alias_targets(
        self,
        alias_id: int,
        *,
        targets: list[dict[str, Any]],
    ) -> list[GatewayAliasTarget]:
        self.conn.execute("DELETE FROM gateway_alias_targets WHERE alias_id = ?", (alias_id,))
        for target in targets:
            self.conn.execute(
                """
                INSERT INTO gateway_alias_targets
                (
                    alias_id,
                    account_id,
                    model_id,
                    priority,
                    enabled,
                    fallback_on_timeout,
                    fallback_on_5xx,
                    fallback_on_429,
                    cooldown_seconds
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alias_id,
                    int(target["account_id"]),
                    int(target["model_id"]),
                    int(target["priority"]),
                    int(bool(target["enabled"])),
                    int(bool(target["fallback_on_timeout"])),
                    int(bool(target["fallback_on_5xx"])),
                    int(bool(target["fallback_on_429"])),
                    int(target["cooldown_seconds"]),
                ),
            )
        self.conn.commit()
        return self.list_gateway_alias_targets(alias_id)

    def create_gateway_client_key(
        self,
        *,
        name: str,
        api_key_hash: str,
        key_hint: str,
        enabled: bool,
        notes: str,
    ) -> GatewayClientKey:
        cursor = self.conn.execute(
            """
            INSERT INTO gateway_client_keys
            (name, api_key_hash, key_hint, enabled, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                api_key_hash,
                key_hint,
                int(enabled),
                notes,
            ),
        )
        self.conn.commit()
        client_key = self.get_gateway_client_key(int(cursor.lastrowid))
        if client_key is None:
            raise RuntimeError("Failed to create gateway client key")
        return client_key

    def get_gateway_client_key(self, client_key_id: int) -> GatewayClientKey | None:
        row = self.conn.execute(
            "SELECT * FROM gateway_client_keys WHERE id = ?",
            (client_key_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_gateway_client_key(row)

    def list_gateway_client_keys(self) -> list[GatewayClientKey]:
        rows = self.conn.execute(
            "SELECT * FROM gateway_client_keys ORDER BY id ASC",
        ).fetchall()
        return [self._row_to_gateway_client_key(row) for row in rows]

    def update_gateway_client_key(
        self,
        client_key_id: int,
        *,
        enabled: bool,
        notes: str,
    ) -> GatewayClientKey:
        self.conn.execute(
            """
            UPDATE gateway_client_keys
            SET enabled = ?,
                notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                int(enabled),
                notes,
                client_key_id,
            ),
        )
        self.conn.commit()
        client_key = self.get_gateway_client_key(client_key_id)
        if client_key is None:
            raise RuntimeError("Failed to update gateway client key")
        return client_key

    def get_gateway_client_key_by_hash(self, api_key_hash: str) -> GatewayClientKey | None:
        row = self.conn.execute(
            "SELECT * FROM gateway_client_keys WHERE api_key_hash = ? LIMIT 1",
            (api_key_hash,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_gateway_client_key(row)

    def touch_gateway_client_key(self, client_key_id: int, *, last_used_at: str) -> GatewayClientKey:
        self.conn.execute(
            """
            UPDATE gateway_client_keys
            SET last_used_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (last_used_at, client_key_id),
        )
        self.conn.commit()
        client_key = self.get_gateway_client_key(client_key_id)
        if client_key is None:
            raise RuntimeError("Failed to touch gateway client key")
        return client_key

    def has_enabled_gateway_client_keys(self) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM gateway_client_keys WHERE enabled = 1 LIMIT 1",
        ).fetchone()
        return row is not None

    def create_media_provider(
        self,
        *,
        name: str,
        base_url: str,
        auth_type: str,
        api_key_encrypted: str,
        enabled: bool,
        notes: str,
    ) -> MediaProvider:
        cursor = self.conn.execute(
            """
            INSERT INTO media_providers
            (name, base_url, auth_type, api_key_encrypted, enabled, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                base_url,
                auth_type,
                api_key_encrypted,
                int(enabled),
                notes,
            ),
        )
        self.conn.commit()
        provider = self.get_media_provider(int(cursor.lastrowid))
        if provider is None:
            raise RuntimeError("Failed to create media provider")
        return provider

    def get_media_provider(self, provider_id: int) -> MediaProvider | None:
        row = self.conn.execute(
            "SELECT * FROM media_providers WHERE id = ?",
            (provider_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_media_provider(row)

    def list_media_providers(self) -> list[MediaProvider]:
        rows = self.conn.execute(
            "SELECT * FROM media_providers ORDER BY id ASC",
        ).fetchall()
        return [self._row_to_media_provider(row) for row in rows]

    def create_media_template(
        self,
        *,
        provider_id: int,
        model_key: str,
        name: str,
        capability: str,
        template_type: str,
        upstream_model: str,
        ui_group: str,
        ui_label: str,
        ui_description: str,
        ui_badge: str,
        ui_order: int,
        input_schema_json: dict[str, Any],
        request_template_json: dict[str, Any],
        response_mapping_json: dict[str, Any],
        defaults_json: dict[str, Any],
        enabled: bool,
    ) -> MediaTemplate:
        cursor = self.conn.execute(
            """
            INSERT INTO media_templates
            (
                provider_id,
                model_key,
                name,
                capability,
                template_type,
                upstream_model,
                ui_group,
                ui_label,
                ui_description,
                ui_badge,
                ui_order,
                input_schema_json,
                request_template_json,
                response_mapping_json,
                defaults_json,
                enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider_id,
                model_key,
                name,
                capability,
                template_type,
                upstream_model,
                ui_group,
                ui_label,
                ui_description,
                ui_badge,
                ui_order,
                json.dumps(input_schema_json, ensure_ascii=False),
                json.dumps(request_template_json, ensure_ascii=False),
                json.dumps(response_mapping_json, ensure_ascii=False),
                json.dumps(defaults_json, ensure_ascii=False),
                int(enabled),
            ),
        )
        self.conn.commit()
        template = self.get_media_template(int(cursor.lastrowid))
        if template is None:
            raise RuntimeError("Failed to create media template")
        return template

    def get_media_template(self, template_id: int) -> MediaTemplate | None:
        row = self.conn.execute(
            """
            SELECT mt.*, mp.name AS provider_name
            FROM media_templates mt
            JOIN media_providers mp ON mp.id = mt.provider_id
            WHERE mt.id = ?
            """,
            (template_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_media_template(row)

    def list_media_templates(self) -> list[MediaTemplate]:
        rows = self.conn.execute(
            """
            SELECT mt.*, mp.name AS provider_name
            FROM media_templates mt
            JOIN media_providers mp ON mp.id = mt.provider_id
            ORDER BY mt.ui_order ASC, mt.id ASC
            """
        ).fetchall()
        return [self._row_to_media_template(row) for row in rows]

    def create_universal_provider_template(
        self,
        *,
        name: str,
        base_url: str,
        auth_type: str,
        api_key_encrypted: str,
        protocol: str,
        notes: str,
    ) -> UniversalProviderTemplate:
        cursor = self.conn.execute(
            """
            INSERT INTO universal_provider_templates
            (name, base_url, auth_type, api_key_encrypted, protocol, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                base_url,
                auth_type,
                api_key_encrypted,
                protocol,
                notes,
            ),
        )
        self.conn.commit()
        template = self.get_universal_provider_template(int(cursor.lastrowid))
        if template is None:
            raise RuntimeError("Failed to create universal provider template")
        return template

    def get_universal_provider_template(self, template_id: int) -> UniversalProviderTemplate | None:
        row = self.conn.execute(
            "SELECT * FROM universal_provider_templates WHERE id = ?",
            (template_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_universal_provider_template(row)

    def list_universal_provider_templates(self) -> list[UniversalProviderTemplate]:
        rows = self.conn.execute(
            "SELECT * FROM universal_provider_templates ORDER BY id ASC",
        ).fetchall()
        return [self._row_to_universal_provider_template(row) for row in rows]

    def create_universal_provider_template_model(
        self,
        *,
        template_id: int,
        upstream_model: str,
        display_name: str,
        capabilities: list[str],
        reasoning: bool,
        input_modalities: list[str],
        context_window: int | None,
        max_tokens: int | None,
        enabled: bool,
    ) -> UniversalProviderTemplateModel:
        cursor = self.conn.execute(
            """
            INSERT INTO universal_provider_template_models
            (
                template_id,
                upstream_model,
                display_name,
                capabilities,
                reasoning,
                input_modalities,
                context_window,
                max_tokens,
                enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_id,
                upstream_model,
                display_name,
                json.dumps(capabilities, ensure_ascii=False),
                int(reasoning),
                json.dumps(input_modalities, ensure_ascii=False),
                context_window,
                max_tokens,
                int(enabled),
            ),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM universal_provider_template_models WHERE id = ?",
            (int(cursor.lastrowid),),
        ).fetchone()
        if row is None:
            raise RuntimeError("Failed to create universal provider template model")
        return self._row_to_universal_provider_template_model(row)

    def list_universal_provider_template_models(self, template_id: int) -> list[UniversalProviderTemplateModel]:
        rows = self.conn.execute(
            """
            SELECT *
            FROM universal_provider_template_models
            WHERE template_id = ?
            ORDER BY id ASC
            """,
            (template_id,),
        ).fetchall()
        return [self._row_to_universal_provider_template_model(row) for row in rows]

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

    def update_device(
        self,
        device_id: int,
        *,
        name: str,
        device_type: str,
        hostname: str,
        platform: str,
        active: bool,
    ) -> Device:
        self.conn.execute(
            """
            UPDATE devices
            SET name = ?,
                device_type = ?,
                hostname = ?,
                platform = ?,
                active = ?
            WHERE id = ?
            """,
            (name, device_type, hostname, platform, int(active), device_id),
        )
        self.conn.commit()
        device = self.get_device(device_id)
        if device is None:
            raise RuntimeError("Failed to update device")
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
            preserve_providers=json.loads(row["preserve_providers_json"] or "[]"),
            preserve_models=json.loads(row["preserve_models_json"] or "[]"),
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
                preserve_providers=json.loads(row["preserve_providers_json"] or "[]"),
                preserve_models=json.loads(row["preserve_models_json"] or "[]"),
            )
            for row in rows
        ]

    def update_device_preserve_config(
        self,
        device_id: int,
        *,
        preserve_providers: list[str],
        preserve_models: list[str],
    ) -> Device:
        self.conn.execute(
            """
            UPDATE devices
            SET preserve_providers_json = ?,
                preserve_models_json = ?
            WHERE id = ?
            """,
            (
                json.dumps(preserve_providers, ensure_ascii=False),
                json.dumps(preserve_models, ensure_ascii=False),
                device_id,
            ),
        )
        self.conn.commit()
        device = self.get_device(device_id)
        if device is None:
            raise RuntimeError("Failed to update device preserve config")
        return device

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
            preserve_providers=json.loads(row["preserve_providers_json"] or "[]"),
            preserve_models=json.loads(row["preserve_models_json"] or "[]"),
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
