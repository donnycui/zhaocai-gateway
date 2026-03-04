#!/usr/bin/env python3
from __future__ import annotations

import argparse
from typing import List

import httpx


def parse_models(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def api_post(base_url: str, path: str, payload: dict, admin_token: str) -> dict:
    url = f"{base_url.rstrip('/')}{path}"
    headers = {"X-Admin-Token": admin_token, "Content-Type": "application/json"}
    with httpx.Client(timeout=20) as client:
        resp = client.post(url, json=payload, headers=headers)
    if resp.status_code >= 300:
        raise RuntimeError(f"POST {path} failed: {resp.status_code} {resp.text[:500]}")
    return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap provider + models in control plane")
    parser.add_argument("--base-url", required=True, help="Control plane base URL")
    parser.add_argument("--admin-token", required=True, help="X-Admin-Token value")
    parser.add_argument("--name", required=True, help="Provider name")
    parser.add_argument("--provider-type", default="openai", help="openai/anthropic")
    parser.add_argument("--provider-base-url", required=True, help="Upstream provider base URL")
    parser.add_argument("--auth-scheme", default="bearer", help="bearer/x-api-key")
    parser.add_argument("--api-key", required=True, help="Provider API key")
    parser.add_argument("--models", required=True, help="Comma-separated models")
    parser.add_argument("--profile-id", type=int, default=0, help="Optional profile_id for auto binding")
    args = parser.parse_args()

    provider_resp = api_post(
        args.base_url,
        "/control/v1/providers",
        {
            "name": args.name,
            "provider_type": args.provider_type,
            "base_url": args.provider_base_url,
            "auth_scheme": args.auth_scheme,
            "api_key": args.api_key,
            "enabled": True,
            "extra_headers": {},
        },
        args.admin_token,
    )
    provider_id = provider_resp["provider"]["id"]
    print(f"Created provider id={provider_id}")

    created_model_ids: List[int] = []
    for model_name in parse_models(args.models):
        model_resp = api_post(
            args.base_url,
            "/control/v1/models",
            {
                "provider_id": provider_id,
                "upstream_model": model_name,
                "alias": model_name,
                "enabled": True,
                "capabilities": ["chat"],
            },
            args.admin_token,
        )
        model_id = model_resp["model"]["id"]
        created_model_ids.append(model_id)
        print(f"Created model id={model_id} alias={model_name}")

    if args.profile_id > 0 and created_model_ids:
        bind_resp = api_post(
            args.base_url,
            f"/control/v1/profiles/{args.profile_id}/bindings",
            {"model_ids": created_model_ids},
            args.admin_token,
        )
        print(f"Updated profile bindings profile_id={args.profile_id} model_ids={bind_resp['profile']['model_ids']}")


if __name__ == "__main__":
    main()

