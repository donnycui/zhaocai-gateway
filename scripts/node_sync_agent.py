#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

import httpx


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=str(path.parent)) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def run_reload_command(command: str) -> None:
    if not command:
        return
    result = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Reload command failed: {result.stderr.strip()}")


def sync_once(
    base_url: str,
    node_id: int,
    pull_token: str,
    output: Path,
    etag: Optional[str],
    timeout: int,
) -> tuple[Optional[str], bool]:
    url = f"{base_url.rstrip('/')}/control/v1/nodes/{node_id}/openclaw-json"
    headers = {"Authorization": f"Bearer {pull_token}"}
    if etag:
        headers["If-None-Match"] = etag

    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, headers=headers)

    if resp.status_code == 304:
        return etag, False
    if resp.status_code != 200:
        raise RuntimeError(f"Sync failed with {resp.status_code}: {resp.text[:500]}")

    payload = resp.json()
    atomic_write_json(output, payload)
    return resp.headers.get("ETag"), True


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull and apply node-specific openclaw.json")
    parser.add_argument("--base-url", required=True, help="Control plane base URL, e.g. http://127.0.0.1:8000")
    parser.add_argument("--node-id", required=True, type=int, help="Node ID")
    parser.add_argument("--pull-token", required=True, help="Node pull token")
    parser.add_argument("--output", required=True, help="Path to write openclaw.json")
    parser.add_argument("--interval", type=int, default=60, help="Sync interval seconds")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    parser.add_argument("--reload-cmd", default="", help="Optional command to reload OpenClaw after config update")
    parser.add_argument("--once", action="store_true", help="Run one sync cycle only")
    args = parser.parse_args()

    output_path = Path(args.output)
    etag: Optional[str] = None
    while True:
        try:
            etag, changed = sync_once(
                base_url=args.base_url,
                node_id=args.node_id,
                pull_token=args.pull_token,
                output=output_path,
                etag=etag,
                timeout=args.timeout,
            )
            if changed:
                print(f"[sync] config updated at {output_path}. ETag={etag}")
                run_reload_command(args.reload_cmd)
            else:
                print("[sync] no change")
        except Exception as exc:  # noqa: BLE001
            print(f"[sync] error: {exc}")

        if args.once:
            return
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    main()

