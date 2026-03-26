from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def _deep_merge(target: dict, source: dict) -> dict:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value
    return target


def write_openclaw_config(path: str | Path, payload: dict) -> str | None:
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    backup_path: str | None = None
    merged_payload = payload
    if target_path.exists():
        backup = target_path.with_suffix(target_path.suffix + ".bak")
        shutil.copy2(target_path, backup)
        backup_path = str(backup)
        try:
            current_payload = json.loads(target_path.read_text(encoding="utf-8"))
            if isinstance(current_payload, dict) and isinstance(payload, dict):
                merged_payload = _deep_merge(current_payload, payload)
        except Exception:
            merged_payload = payload

    with tempfile.NamedTemporaryFile(
        "w",
        delete=False,
        encoding="utf-8",
        dir=str(target_path.parent),
    ) as tmp:
        json.dump(merged_payload, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name

    os.replace(tmp_name, target_path)
    return backup_path


def run_reload_command(command: str) -> None:
    if not command:
        return
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown reload error"
        raise RuntimeError(f"Reload command failed: {message}")
