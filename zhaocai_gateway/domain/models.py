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


@dataclass(frozen=True)
class ConfigSnapshot:
    id: int
    device_id: int
    version: int
    etag: str
    payload_json: dict[str, Any]
    content_hash: str
    created_at: str
