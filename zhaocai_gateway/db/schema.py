from __future__ import annotations

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    provider_type TEXT NOT NULL,
    base_url TEXT NOT NULL,
    auth_scheme TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    extra_headers TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL,
    upstream_model TEXT NOT NULL,
    display_name TEXT NOT NULL,
    capabilities TEXT NOT NULL DEFAULT '[]',
    reasoning INTEGER NOT NULL DEFAULT 0,
    input_modalities TEXT NOT NULL DEFAULT '["text"]',
    context_window INTEGER,
    max_tokens INTEGER,
    cost_input REAL,
    cost_output REAL,
    cost_cache_read REAL,
    cost_cache_write REAL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(provider_id) REFERENCES providers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    device_type TEXT NOT NULL,
    hostname TEXT NOT NULL,
    platform TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    last_seen_at TEXT,
    sync_token_hash TEXT NOT NULL DEFAULT '',
    current_config_version INTEGER NOT NULL DEFAULT 0,
    preserve_providers_json TEXT NOT NULL DEFAULT '[]',
    preserve_models_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS device_model_bindings (
    device_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,
    PRIMARY KEY (device_id, model_id),
    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY(model_id) REFERENCES models(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pairing_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS config_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    etag TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(device_id, version),
    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS gateway_upstream_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    auth_type TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    protocol TEXT NOT NULL DEFAULT 'openai-compatible',
    enabled INTEGER NOT NULL DEFAULT 1,
    health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    cooldown_until TEXT,
    last_checked_at TEXT,
    last_synced_at TEXT,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gateway_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    upstream_model TEXT NOT NULL,
    display_name TEXT NOT NULL,
    family TEXT,
    supports_chat INTEGER NOT NULL DEFAULT 1,
    supports_responses INTEGER NOT NULL DEFAULT 1,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, upstream_model),
    FOREIGN KEY(account_id) REFERENCES gateway_upstream_accounts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS gateway_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alias_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    visibility TEXT NOT NULL DEFAULT 'project',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gateway_alias_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alias_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,
    priority INTEGER NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    fallback_on_timeout INTEGER NOT NULL DEFAULT 1,
    fallback_on_5xx INTEGER NOT NULL DEFAULT 1,
    fallback_on_429 INTEGER NOT NULL DEFAULT 1,
    cooldown_seconds INTEGER NOT NULL DEFAULT 120,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(alias_id, account_id, model_id),
    FOREIGN KEY(alias_id) REFERENCES gateway_aliases(id) ON DELETE CASCADE,
    FOREIGN KEY(account_id) REFERENCES gateway_upstream_accounts(id) ON DELETE CASCADE,
    FOREIGN KEY(model_id) REFERENCES gateway_models(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS gateway_client_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    api_key_hash TEXT NOT NULL UNIQUE,
    key_hint TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    notes TEXT NOT NULL DEFAULT '',
    last_used_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS media_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    auth_type TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS media_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id INTEGER NOT NULL,
    model_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    capability TEXT NOT NULL,
    template_type TEXT NOT NULL,
    upstream_model TEXT NOT NULL,
    ui_group TEXT NOT NULL DEFAULT '',
    ui_label TEXT NOT NULL DEFAULT '',
    ui_description TEXT NOT NULL DEFAULT '',
    ui_badge TEXT NOT NULL DEFAULT '',
    ui_order INTEGER NOT NULL DEFAULT 0,
    input_schema_json TEXT NOT NULL DEFAULT '{}',
    request_template_json TEXT NOT NULL DEFAULT '{}',
    response_mapping_json TEXT NOT NULL DEFAULT '{}',
    defaults_json TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(provider_id) REFERENCES media_providers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS universal_provider_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    auth_type TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    protocol TEXT NOT NULL DEFAULT 'openai-compatible',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS universal_provider_template_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    upstream_model TEXT NOT NULL,
    display_name TEXT NOT NULL,
    capabilities TEXT NOT NULL DEFAULT '[]',
    reasoning INTEGER NOT NULL DEFAULT 0,
    input_modalities TEXT NOT NULL DEFAULT '["text"]',
    context_window INTEGER,
    max_tokens INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(template_id) REFERENCES universal_provider_templates(id) ON DELETE CASCADE
);
"""
