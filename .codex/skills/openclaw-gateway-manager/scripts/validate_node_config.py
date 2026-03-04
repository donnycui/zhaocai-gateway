#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def require_keys(obj: Dict[str, Any], keys: List[str], path: str) -> None:
    for key in keys:
        if key not in obj:
            raise ValueError(f"missing key '{key}' at {path}")


def validate(payload: Dict[str, Any]) -> None:
    require_keys(payload, ["schema_version", "node", "profile", "providers", "models", "model_routing"], "root")
    require_keys(payload["node"], ["id", "name", "sync_mode", "active"], "node")
    require_keys(payload["profile"], ["id", "name", "description"], "profile")
    if not isinstance(payload["providers"], list):
        raise ValueError("providers must be a list")
    if not isinstance(payload["models"], list):
        raise ValueError("models must be a list")
    if not isinstance(payload["model_routing"], dict):
        raise ValueError("model_routing must be an object")

    for idx, provider in enumerate(payload["providers"]):
        require_keys(
            provider,
            ["id", "type", "base_url", "auth_scheme", "api_key", "enabled"],
            f"providers[{idx}]",
        )

    for idx, model in enumerate(payload["models"]):
        require_keys(
            model,
            ["id", "provider", "upstream_model", "capabilities", "enabled"],
            f"models[{idx}]",
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate compiled openclaw.json shape")
    parser.add_argument("path", help="Path to openclaw.json")
    args = parser.parse_args()

    payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
    validate(payload)
    print("ok")


if __name__ == "__main__":
    main()

