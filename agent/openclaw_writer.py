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


def _replace_model_sections(target: dict, source: dict) -> dict:
    if not isinstance(target, dict) or not isinstance(source, dict):
        return source

    merged = _deep_merge(target, source)

    source_models = source.get("models")
    if isinstance(source_models, dict):
        merged_models = merged.setdefault("models", {})
        if "mode" in source_models:
            merged_models["mode"] = source_models["mode"]
        if "providers" in source_models:
            merged_models["providers"] = source_models.get("providers", {})

    source_agents = source.get("agents")
    if isinstance(source_agents, dict):
        source_defaults = source_agents.get("defaults")
        if isinstance(source_defaults, dict):
            merged_agents = merged.setdefault("agents", {})
            merged_defaults = merged_agents.setdefault("defaults", {})
            if "model" in source_defaults:
                merged_defaults["model"] = source_defaults.get("model")
            else:
                merged_defaults.pop("model", None)
            if "models" in source_defaults:
                merged_defaults["models"] = source_defaults.get("models", {})
            else:
                merged_defaults.pop("models", None)

    return merged


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
                merged_payload = _replace_model_sections(current_payload, payload)
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
