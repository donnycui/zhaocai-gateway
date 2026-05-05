from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Provider:
    id: int
    name: str
    provider_type: str
    base_url: str
    auth_scheme: str
    api_key_encrypted: str
    extra_headers: dict[str, str]
    enabled: bool


@dataclass(frozen=True)
class Model:
    id: int
    provider_id: int
    upstream_model: str
    display_name: str
    capabilities: list[str]
    reasoning: bool
    input_modalities: list[str]
    context_window: int | None
    max_tokens: int | None
    cost_input: float | None
    cost_output: float | None
    cost_cache_read: float | None
    cost_cache_write: float | None
    enabled: bool
    provider_name: str | None = None


@dataclass(frozen=True)
class GatewayUpstreamAccount:
    id: int
    name: str
    base_url: str
    auth_type: str
    api_key_encrypted: str
    protocol: str
    enabled: bool
    health_status: str
    cooldown_until: str | None
    last_checked_at: str | None
    last_synced_at: str | None
    notes: str
    synced_models_count: int = 0


@dataclass(frozen=True)
class GatewayModel:
    id: int
    account_id: int
    upstream_model: str
    display_name: str
    family: str | None
    supports_chat: bool
    supports_responses: bool
    enabled: bool
    account_name: str | None = None


@dataclass(frozen=True)
class GatewayModelUsageSummary:
    account_id: int
    account_name: str
    model_id: int
    upstream_model: str
    display_name: str
    total_calls: int
    success_calls: int
    failure_calls: int
    last_called_at: str | None
    avg_latency_ms: float | None = None


@dataclass(frozen=True)
class GatewayAlias:
    id: int
    alias_key: str
    display_name: str
    alias_type: str
    enabled: bool
    visibility: str
    notes: str


@dataclass(frozen=True)
class GatewayAliasTarget:
    id: int
    alias_id: int
    account_id: int
    model_id: int
    priority: int
    enabled: bool
    fallback_on_timeout: bool
    fallback_on_5xx: bool
    fallback_on_429: bool
    cooldown_seconds: int
    account_name: str | None = None
    model_display_name: str | None = None
    upstream_model: str | None = None


@dataclass(frozen=True)
class GatewayClientKey:
    id: int
    name: str
    api_key_hash: str
    key_hint: str
    enabled: bool
    notes: str
    last_used_at: str | None


@dataclass(frozen=True)
class MediaProvider:
    id: int
    name: str
    base_url: str
    auth_type: str
    api_key_encrypted: str
    enabled: bool
    notes: str


@dataclass(frozen=True)
class MediaTemplate:
    id: int
    provider_id: int
    model_key: str
    name: str
    capability: str
    template_type: str
    upstream_model: str
    ui_group: str
    ui_label: str
    ui_description: str
    ui_badge: str
    ui_order: int
    input_schema_json: dict[str, Any]
    request_template_json: dict[str, Any]
    response_mapping_json: dict[str, Any]
    defaults_json: dict[str, Any]
    enabled: bool
    provider_name: str | None = None


@dataclass(frozen=True)
class UniversalProviderTemplate:
    id: int
    name: str
    base_url: str
    auth_type: str
    api_key_encrypted: str
    protocol: str
    notes: str


@dataclass(frozen=True)
class UniversalProviderTemplateModel:
    id: int
    template_id: int
    upstream_model: str
    display_name: str
    capabilities: list[str]
    reasoning: bool
    input_modalities: list[str]
    context_window: int | None
    max_tokens: int | None
    enabled: bool


@dataclass(frozen=True)
class Device:
    id: int
    name: str
    device_type: str
    hostname: str
    platform: str
    active: bool
    last_seen_at: str | None
    sync_token_hash: str
    current_config_version: int
    preserve_providers: list[str]
    preserve_models: list[str]


@dataclass(frozen=True)
class PairingToken:
    id: int
    device_id: int
    token_hash: str
    expires_at: str
    used_at: str | None
    created_at: str


@dataclass(frozen=True)
class ConfigSnapshot:
    id: int
    device_id: int
    version: int
    etag: str
    payload_json: dict[str, Any]
    content_hash: str
    created_at: str


@dataclass(frozen=True)
class AppliedConfigReport:
    device_id: int
    version: int
    status: str
