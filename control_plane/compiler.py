from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from control_plane.store import SQLiteControlPlaneStore


def compile_openclaw_config(store: SQLiteControlPlaneStore, node_id: int) -> Dict[str, Any]:
    node = store.get_node(node_id, include_token_hash=False)
    profile = store.get_profile(node["profile_id"])
    rows = store.get_models_for_profile(node["profile_id"])

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
                "enabled": True,
            }
        )
        model_routing[model_alias] = row["provider_name"]

    generated_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
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
        "providers": list(provider_map.values()),
        "models": models,
        "model_routing": model_routing,
    }

