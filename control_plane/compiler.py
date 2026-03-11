from __future__ import annotations

import datetime as dt
import json
import os
from typing import Any, Dict, List

from control_plane.store import SQLiteControlPlaneStore


def _base_payload(node: Dict[str, Any], profile: Dict[str, Any], generated_at: str) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "node": {
            "id": node["id"],
            "name": node["name"],
            "sync_mode": node["sync_mode"],
            "active": node["active"],
        },
        "profile": {
            "id": profile["id"],
            "name": profile["name"],
            "description": profile["description"],
        },
    }


def _compile_direct_mode(
    rows: List[Dict[str, Any]],
    node: Dict[str, Any],
    profile: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    provider_map: Dict[int, Dict[str, Any]] = {}
    models: List[Dict[str, Any]] = []
    model_routing: Dict[str, str] = {}

    for row in rows:
        if not row["enabled"] or not row["provider_enabled"]:
            continue

        provider_id = int(row["provider_id"])
        provider_cfg = provider_map.get(provider_id)
        if provider_cfg is None:
            provider_cfg = {
                "id": row["provider_name"],
                "type": row["provider_type"],
                "base_url": row["base_url"],
                "auth_scheme": row["auth_scheme"],
                "api_key": row["api_key"],
                "secret_ref": row["secret_ref"],
                "extra_headers": row["extra_headers"],
                "enabled": True,
            }
            provider_map[provider_id] = provider_cfg

        model_alias = row["alias"]
        models.append(
            {
                "id": model_alias,
                "provider": row["provider_name"],
                "upstream_model": row["upstream_model"],
                "capabilities": row["capabilities"],
                "contextWindow": row.get("context_window"),
                "maxTokens": row.get("max_tokens"),
                "input": row.get("input", ["text"]),
                "enabled": True,
            }
        )
        model_routing[model_alias] = row["provider_name"]

    payload = _base_payload(node=node, profile=profile, generated_at=generated_at)
    payload["providers"] = list(provider_map.values())
    payload["models"] = models
    payload["model_routing"] = model_routing
    return payload


def _compile_gateway_mode(
    rows: List[Dict[str, Any]],
    node: Dict[str, Any],
    profile: Dict[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    provider_id = os.getenv("ZHAOCAI_NODE_GATEWAY_PROVIDER_ID", "zhaocai-gateway").strip() or "zhaocai-gateway"
    base_url = os.getenv("ZHAOCAI_NODE_GATEWAY_BASE_URL", "").strip()
    if not base_url:
        gateway_port = os.getenv("ZHAOCAI_PORT", "8000").strip() or "8000"
        base_url = f"http://127.0.0.1:{gateway_port}/v1"

    provider_type = os.getenv("ZHAOCAI_NODE_GATEWAY_PROVIDER_TYPE", "openai").strip() or "openai"
    auth_scheme = os.getenv("ZHAOCAI_NODE_GATEWAY_AUTH_SCHEME", "bearer").strip() or "bearer"
    api_key = os.getenv("ZHAOCAI_NODE_GATEWAY_API_KEY", "").strip()

    raw_headers = os.getenv("ZHAOCAI_NODE_GATEWAY_EXTRA_HEADERS", "").strip()
    extra_headers: Dict[str, str] = {}
    if raw_headers:
        try:
            parsed = json.loads(raw_headers)
            if isinstance(parsed, dict):
                extra_headers = {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            extra_headers = {}

    models: List[Dict[str, Any]] = []
    model_routing: Dict[str, str] = {}
    for row in rows:
        if not row["enabled"] or not row["provider_enabled"]:
            continue
        model_alias = row["alias"]
        models.append(
            {
                "id": model_alias,
                "provider": provider_id,
                "upstream_model": model_alias,
                "capabilities": row["capabilities"],
                "contextWindow": row.get("context_window"),
                "maxTokens": row.get("max_tokens"),
                "input": row.get("input", ["text"]),
                "enabled": True,
            }
        )
        model_routing[model_alias] = provider_id

    payload = _base_payload(node=node, profile=profile, generated_at=generated_at)
    payload["providers"] = [
        {
            "id": provider_id,
            "type": provider_type,
            "base_url": base_url,
            "auth_scheme": auth_scheme,
            "api_key": api_key,
            "secret_ref": "",
            "extra_headers": extra_headers,
            "enabled": True,
        }
    ]
    payload["models"] = models
    payload["model_routing"] = model_routing
    return payload


def compile_openclaw_config(store: SQLiteControlPlaneStore, node_id: int) -> Dict[str, Any]:
    node = store.get_node(node_id, include_token_hash=False)
    profile = store.get_profile(node["profile_id"])
    rows = store.get_models_for_profile(node["profile_id"])
    generated_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    node_provider_mode = os.getenv("ZHAOCAI_NODE_PROVIDER_MODE", "direct").strip().lower()
    if node_provider_mode == "gateway":
        return _compile_gateway_mode(rows=rows, node=node, profile=profile, generated_at=generated_at)

    return _compile_direct_mode(rows=rows, node=node, profile=profile, generated_at=generated_at)
