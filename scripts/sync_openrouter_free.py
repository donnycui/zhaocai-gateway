#!/usr/bin/env python3
"""
OpenRouter Free Model Sync — CLI wrapper.

Triggers the control-plane sync endpoint to pull free models from
OpenRouter, score them, and upsert stable aliases.

Usage:
    python scripts/sync_openrouter_free.py \
        --base-url http://127.0.0.1:8000 \
        --admin-token YOUR_TOKEN
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync free models from OpenRouter to Zhaocai Gateway",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Zhaocai Gateway base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--admin-token",
        required=True,
        help="Admin token for control-plane authentication",
    )
    args = parser.parse_args()

    endpoint = f"{args.base_url.rstrip('/')}/control/v1/sync/openrouter-free"
    print(f"Triggering OpenRouter free-model sync at {endpoint} ...")

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                endpoint,
                headers={"X-Admin-Token": args.admin_token},
            )
    except httpx.RequestError as exc:
        print(f"Error: failed to connect to gateway: {exc}", file=sys.stderr)
        sys.exit(1)

    if resp.status_code != 200:
        print(f"Error: HTTP {resp.status_code}", file=sys.stderr)
        print(resp.text, file=sys.stderr)
        sys.exit(1)

    result = resp.json()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(
        f"\nDone: {result.get('created', 0)} created, "
        f"{result.get('updated', 0)} updated, "
        f"{result.get('free_models_found', 0)} free models found on OpenRouter."
    )


if __name__ == "__main__":
    main()
