from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ENCRYPTED_PREFIX = "enc:v1:"

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:  # pragma: no cover - optional import fallback
    Fernet = None  # type: ignore[assignment]
    InvalidToken = Exception  # type: ignore[assignment]


def _to_bool(value: Any) -> bool:
    return bool(int(value)) if isinstance(value, (int, str)) else bool(value)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return dict(row)


def mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}...{secret[-4:]}"


class SQLiteControlPlaneStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        db_parent = Path(db_path).parent
        db_parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._fernet = self._build_fernet_from_env()
        self._init_schema()

    @contextmanager
    def _locked(self):
        with self._lock:
            yield

    def _init_schema(self) -> None:
        with self._locked():
            self.conn.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS providers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    provider_type TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    auth_scheme TEXT NOT NULL,
                    api_key TEXT NOT NULL DEFAULT '',
                    secret_ref TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    extra_headers TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_id INTEGER NOT NULL,
                    upstream_model TEXT NOT NULL,
                    alias TEXT NOT NULL UNIQUE,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    capabilities TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(provider_id) REFERENCES providers(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS profile_bindings (
                    profile_id INTEGER NOT NULL,
                    model_id INTEGER NOT NULL,
                    PRIMARY KEY(profile_id, model_id),
                    FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE,
                    FOREIGN KEY(model_id) REFERENCES models(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    profile_id INTEGER NOT NULL,
                    token_hash TEXT NOT NULL DEFAULT '',
                    sync_mode TEXT NOT NULL DEFAULT 'pull',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE RESTRICT
                );

                CREATE TABLE IF NOT EXISTS node_config_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id INTEGER NOT NULL,
                    version INTEGER NOT NULL,
                    etag TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(node_id, version),
                    UNIQUE(node_id, etag),
                    FOREIGN KEY(node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );
                """
            )
            self.conn.commit()

    _VALID_TABLES = {"providers", "models", "profiles", "nodes"}

    def _build_fernet_from_env(self) -> Any:
        key = os.getenv("ZHAOCAI_ENCRYPTION_KEY", "").strip()
        if not key:
            return None
        if Fernet is None:
            raise RuntimeError(
                "ZHAOCAI_ENCRYPTION_KEY is set but cryptography is unavailable. "
                "Install dependencies from requirements.txt."
            )
        try:
            return Fernet(key.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("Invalid ZHAOCAI_ENCRYPTION_KEY format (must be valid Fernet key)") from exc

    def _encrypt_api_key(self, value: str) -> str:
        if not value:
            return ""
        if value.startswith(ENCRYPTED_PREFIX):
            return value
        if not self._fernet:
            return value
        token = self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")
        return f"{ENCRYPTED_PREFIX}{token}"

    def _decrypt_api_key(self, value: str) -> str:
        if not value:
            return ""
        if not value.startswith(ENCRYPTED_PREFIX):
            return value
        if not self._fernet:
            raise RuntimeError(
                "Encrypted API key found but ZHAOCAI_ENCRYPTION_KEY is not configured."
            )
        token = value[len(ENCRYPTED_PREFIX) :]
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError("Failed to decrypt API key: invalid ZHAOCAI_ENCRYPTION_KEY") from exc

    def _require_exists(self, table: str, id_value: int) -> None:
        if table not in self._VALID_TABLES:
            raise ValueError(f"Invalid table name: {table}")
        row = self.conn.execute(f"SELECT id FROM {table} WHERE id = ?", (id_value,)).fetchone()
        if row is None:
            raise ValueError(f"{table[:-1].capitalize()} {id_value} does not exist")

    def create_provider(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._locked():
            cursor = self.conn.execute(
                """
                INSERT INTO providers
                (name, provider_type, base_url, auth_scheme, api_key, secret_ref, enabled, extra_headers)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["name"],
                    data["provider_type"],
                    data["base_url"],
                    data["auth_scheme"],
                    self._encrypt_api_key(data.get("api_key", "")),
                    data.get("secret_ref", ""),
                    int(data.get("enabled", True)),
                    json.dumps(data.get("extra_headers", {}), ensure_ascii=False),
                ),
            )
            self.conn.commit()
            return self.get_provider(cursor.lastrowid, include_secrets=False)

    def update_provider(self, provider_id: int, fields: Dict[str, Any]) -> Dict[str, Any]:
        if not fields:
            return self.get_provider(provider_id, include_secrets=False)

        normalized = dict(fields)
        if "extra_headers" in normalized and normalized["extra_headers"] is not None:
            normalized["extra_headers"] = json.dumps(normalized["extra_headers"], ensure_ascii=False)
        if "enabled" in normalized and normalized["enabled"] is not None:
            normalized["enabled"] = int(bool(normalized["enabled"]))
        if "api_key" in normalized and normalized["api_key"] is not None:
            normalized["api_key"] = self._encrypt_api_key(str(normalized["api_key"]))

        assignments = ", ".join(f"{key} = ?" for key in normalized.keys())
        values = list(normalized.values())
        values.append(provider_id)

        with self._locked():
            self._require_exists("providers", provider_id)
            self.conn.execute(
                f"""
                UPDATE providers
                SET {assignments},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                values,
            )
            self.conn.commit()
            return self.get_provider(provider_id, include_secrets=False)

    def get_provider(self, provider_id: int, include_secrets: bool = False) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
        if row is None:
            raise ValueError(f"Provider {provider_id} does not exist")
        data = dict(row)
        data["enabled"] = _to_bool(data["enabled"])
        data["extra_headers"] = json.loads(data["extra_headers"] or "{}")
        data["api_key"] = self._decrypt_api_key(data.get("api_key", ""))
        if include_secrets:
            return data
        data["api_key_masked"] = mask_secret(data.get("api_key", ""))
        data.pop("api_key", None)
        return data

    def list_providers(self, include_secrets: bool = False) -> List[Dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM providers ORDER BY id ASC").fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            data["enabled"] = _to_bool(data["enabled"])
            data["extra_headers"] = json.loads(data["extra_headers"] or "{}")
            data["api_key"] = self._decrypt_api_key(data.get("api_key", ""))
            if include_secrets:
                result.append(data)
            else:
                data["api_key_masked"] = mask_secret(data.get("api_key", ""))
                data.pop("api_key", None)
                result.append(data)
        return result

    def create_model(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._locked():
            self._require_exists("providers", data["provider_id"])
            cursor = self.conn.execute(
                """
                INSERT INTO models
                (provider_id, upstream_model, alias, enabled, capabilities)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    data["provider_id"],
                    data["upstream_model"],
                    data["alias"],
                    int(data.get("enabled", True)),
                    json.dumps(data.get("capabilities", []), ensure_ascii=False),
                ),
            )
            self.conn.commit()
            return self.get_model(cursor.lastrowid)

    def update_model(self, model_id: int, fields: Dict[str, Any]) -> Dict[str, Any]:
        if not fields:
            return self.get_model(model_id)

        normalized = dict(fields)
        if "capabilities" in normalized and normalized["capabilities"] is not None:
            normalized["capabilities"] = json.dumps(normalized["capabilities"], ensure_ascii=False)
        if "enabled" in normalized and normalized["enabled"] is not None:
            normalized["enabled"] = int(bool(normalized["enabled"]))

        assignments = ", ".join(f"{key} = ?" for key in normalized.keys())
        values = list(normalized.values())
        values.append(model_id)

        with self._locked():
            self._require_exists("models", model_id)
            self.conn.execute(
                f"""
                UPDATE models
                SET {assignments},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                values,
            )
            self.conn.commit()
            return self.get_model(model_id)

    def get_model(self, model_id: int) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
        if row is None:
            raise ValueError(f"Model {model_id} does not exist")
        data = dict(row)
        data["enabled"] = _to_bool(data["enabled"])
        data["capabilities"] = json.loads(data["capabilities"] or "[]")
        return data

    def list_models(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM models ORDER BY id ASC").fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            data["enabled"] = _to_bool(data["enabled"])
            data["capabilities"] = json.loads(data["capabilities"] or "[]")
            result.append(data)
        return result

    def create_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._locked():
            cursor = self.conn.execute(
                "INSERT INTO profiles (name, description) VALUES (?, ?)",
                (data["name"], data.get("description", "")),
            )
            self.conn.commit()
            return self.get_profile(cursor.lastrowid)

    def get_profile(self, profile_id: int) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        if row is None:
            raise ValueError(f"Profile {profile_id} does not exist")
        data = dict(row)
        data["model_ids"] = self.get_profile_binding_ids(profile_id)
        return data

    def list_profiles(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM profiles ORDER BY id ASC").fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            data["model_ids"] = self.get_profile_binding_ids(data["id"])
            result.append(data)
        return result

    def set_profile_bindings(self, profile_id: int, model_ids: List[int]) -> Dict[str, Any]:
        with self._locked():
            self._require_exists("profiles", profile_id)
            for model_id in model_ids:
                self._require_exists("models", model_id)
            self.conn.execute("DELETE FROM profile_bindings WHERE profile_id = ?", (profile_id,))
            self.conn.executemany(
                "INSERT INTO profile_bindings (profile_id, model_id) VALUES (?, ?)",
                [(profile_id, model_id) for model_id in model_ids],
            )
            self.conn.commit()
            return self.get_profile(profile_id)

    def get_profile_binding_ids(self, profile_id: int) -> List[int]:
        rows = self.conn.execute(
            "SELECT model_id FROM profile_bindings WHERE profile_id = ? ORDER BY model_id ASC",
            (profile_id,),
        ).fetchall()
        return [int(row["model_id"]) for row in rows]

    def create_node(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._locked():
            self._require_exists("profiles", data["profile_id"])
            cursor = self.conn.execute(
                """
                INSERT INTO nodes (name, profile_id, token_hash, sync_mode, active)
                VALUES (?, ?, '', ?, ?)
                """,
                (
                    data["name"],
                    data["profile_id"],
                    data.get("sync_mode", "pull"),
                    int(data.get("active", True)),
                ),
            )
            node_id = cursor.lastrowid
            pull_token = self._rotate_node_token_locked(node_id)
            self.conn.commit()
            node = self.get_node(node_id, include_token_hash=False)
            node["pull_token"] = pull_token
            return node

    def update_node(self, node_id: int, fields: Dict[str, Any]) -> Dict[str, Any]:
        if not fields:
            return self.get_node(node_id, include_token_hash=False)

        normalized = dict(fields)
        if "active" in normalized and normalized["active"] is not None:
            normalized["active"] = int(bool(normalized["active"]))
        if "profile_id" in normalized and normalized["profile_id"] is not None:
            self._require_exists("profiles", int(normalized["profile_id"]))

        assignments = ", ".join(f"{key} = ?" for key in normalized.keys())
        values = list(normalized.values())
        values.append(node_id)

        with self._locked():
            self._require_exists("nodes", node_id)
            self.conn.execute(
                f"""
                UPDATE nodes
                SET {assignments},
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                values,
            )
            self.conn.commit()
            return self.get_node(node_id, include_token_hash=False)

    def get_node(self, node_id: int, include_token_hash: bool = False) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        if row is None:
            raise ValueError(f"Node {node_id} does not exist")
        data = dict(row)
        data["active"] = _to_bool(data["active"])
        if not include_token_hash:
            data.pop("token_hash", None)
        return data

    def list_nodes(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM nodes ORDER BY id ASC").fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            data["active"] = _to_bool(data["active"])
            data.pop("token_hash", None)
            result.append(data)
        return result

    def _rotate_node_token_locked(self, node_id: int) -> str:
        pull_token = f"zg_node_{node_id}_{secrets.token_urlsafe(24)}"
        token_hash = _hash_token(pull_token)
        self.conn.execute(
            "UPDATE nodes SET token_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (token_hash, node_id),
        )
        return pull_token

    def rotate_node_token(self, node_id: int) -> str:
        with self._locked():
            self._require_exists("nodes", node_id)
            token = self._rotate_node_token_locked(node_id)
            self.conn.commit()
            return token

    def verify_node_token(self, node_id: int, pull_token: str) -> bool:
        row = self.conn.execute(
            "SELECT token_hash, active FROM nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
        if row is None:
            return False
        if not _to_bool(row["active"]):
            return False
        token_hash = row["token_hash"] or ""
        incoming_hash = _hash_token(pull_token)
        return bool(token_hash) and hmac.compare_digest(token_hash, incoming_hash)

    def get_models_for_profile(self, profile_id: int) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT m.*, p.name AS provider_name, p.provider_type, p.base_url, p.auth_scheme, p.api_key,
                   p.secret_ref, p.enabled AS provider_enabled, p.extra_headers
            FROM profile_bindings pb
            JOIN models m ON m.id = pb.model_id
            JOIN providers p ON p.id = m.provider_id
            WHERE pb.profile_id = ?
            ORDER BY m.id ASC
            """,
            (profile_id,),
        ).fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            data["enabled"] = _to_bool(data["enabled"])
            data["provider_enabled"] = _to_bool(data["provider_enabled"])
            data["capabilities"] = json.loads(data["capabilities"] or "[]")
            data["extra_headers"] = json.loads(data["extra_headers"] or "{}")
            data["api_key"] = self._decrypt_api_key(data.get("api_key", ""))
            result.append(data)
        return result

    def list_active_model_routes(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT m.id AS model_id, m.alias, m.upstream_model, m.enabled,
                   p.id AS provider_id, p.name AS provider_name, p.provider_type, p.base_url,
                   p.auth_scheme, p.api_key, p.secret_ref, p.enabled AS provider_enabled,
                   p.extra_headers
            FROM models m
            JOIN providers p ON p.id = m.provider_id
            ORDER BY p.id ASC, m.id ASC
            """
        ).fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            data["enabled"] = _to_bool(data["enabled"])
            data["provider_enabled"] = _to_bool(data["provider_enabled"])
            data["extra_headers"] = json.loads(data["extra_headers"] or "{}")
            data["api_key"] = self._decrypt_api_key(data.get("api_key", ""))
            result.append(data)
        return result

    def get_latest_node_version(self, node_id: int) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            """
            SELECT * FROM node_config_versions
            WHERE node_id = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (node_id,),
        ).fetchone()
        data = _row_to_dict(row)
        if data:
            data["payload"] = json.loads(data["payload"])
        return data

    def list_node_versions(self, node_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT node_id, version, etag, content_sha256, created_at
            FROM node_config_versions
            WHERE node_id = ?
            ORDER BY version DESC
            LIMIT ?
            """,
            (node_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]

    def save_node_config_version(
        self,
        node_id: int,
        payload: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], bool]:
        payload_text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        content_sha256 = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        latest = self.get_latest_node_version(node_id)
        if latest and latest["content_sha256"] == content_sha256:
            return latest, False

        next_version = 1 if latest is None else int(latest["version"]) + 1
        etag = f"\"{content_sha256[:16]}-v{next_version}\""

        with self._locked():
            self.conn.execute(
                """
                INSERT INTO node_config_versions (node_id, version, etag, content_sha256, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (node_id, next_version, etag, content_sha256, payload_text),
            )
            self.conn.commit()

        saved = self.get_latest_node_version(node_id)
        if saved is None:
            raise RuntimeError("Failed to persist node configuration version")
        return saved, True


def create_store_from_env() -> SQLiteControlPlaneStore:
    db_url = os.getenv("ZHAOCAI_CONTROL_DB", "sqlite:///./data/control_plane.db")
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "", 1)
        return SQLiteControlPlaneStore(db_path)

    if db_url.startswith("postgres://") or db_url.startswith("postgresql://"):
        raise RuntimeError(
            "PostgreSQL backend is reserved but not implemented in this build. "
            "Set ZHAOCAI_CONTROL_DB=sqlite:///./data/control_plane.db for now."
        )

    raise RuntimeError(f"Unsupported ZHAOCAI_CONTROL_DB value: {db_url}")
