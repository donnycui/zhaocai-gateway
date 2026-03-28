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
    balance_supported: bool = False
    balance_amount: float | None = None
    balance_currency: str | None = None
    balance_status: str | None = None
    balance_message: str | None = None
    balance_fetched_at: str | None = None


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


@dataclass(frozen=True)
class ProviderBalance:
    provider_id: int
    supported: bool
    amount: float | None
    currency: str | None
    status: str
    message: str
    fetched_at: str | None
