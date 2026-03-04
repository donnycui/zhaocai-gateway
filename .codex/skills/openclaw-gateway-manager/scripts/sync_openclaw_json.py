#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import httpx


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=str(path.parent)) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch node-scoped openclaw.json from control plane")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--node-id", required=True, type=int)
    parser.add_argument("--pull-token", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--etag", default="", help="Optional existing ETag for conditional pull")
    args = parser.parse_args()

    url = f"{args.base_url.rstrip('/')}/control/v1/nodes/{args.node_id}/openclaw-json"
    headers = {"Authorization": f"Bearer {args.pull_token}"}
    if args.etag:
        headers["If-None-Match"] = args.etag

    with httpx.Client(timeout=20) as client:
        resp = client.get(url, headers=headers)

    if resp.status_code == 304:
        print("not_modified")
        return
    if resp.status_code != 200:
        raise SystemExit(f"pull failed: {resp.status_code} {resp.text[:500]}")

    payload = resp.json()
    output_path = Path(args.output)
    atomic_write(output_path, payload)
    print(f"updated etag={resp.headers.get('ETag', '')} path={output_path}")


if __name__ == "__main__":
    main()

