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


def _normalize_preserve_list(raw_values: object) -> set[str]:
    if not isinstance(raw_values, list):
        return set()

    normalized: set[str] = set()
    for item in raw_values:
        text = str(item).strip()
        if text:
            normalized.add(text)
    return normalized


def _load_preserve_rules(preserve_path: str | Path | None) -> tuple[set[str], set[str]]:
    if preserve_path is None:
        return set(), set()

    path = Path(preserve_path)
    if not path.exists():
        return set(), set()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set(), set()

    if not isinstance(payload, dict):
        return set(), set()

    preserve_providers = _normalize_preserve_list(payload.get("preserveProviders"))
    preserve_models = _normalize_preserve_list(payload.get("preserveModels"))

    for model_key in preserve_models:
        provider_key, _, _ = model_key.partition("/")
        if provider_key:
            preserve_providers.add(provider_key)

    return preserve_providers, preserve_models


def _select_preserved_entries(entries: object, preserve_keys: set[str]) -> dict:
    if not isinstance(entries, dict):
        return {}
    return {
        key: value
        for key, value in entries.items()
        if key in preserve_keys
    }


def _replace_model_sections(
    target: dict,
    source: dict,
    *,
    preserve_path: str | Path | None = None,
) -> dict:
    if not isinstance(target, dict) or not isinstance(source, dict):
        return source

    merged = _deep_merge(target, source)
    preserve_providers, preserve_models = _load_preserve_rules(preserve_path)

    source_models = source.get("models")
    if isinstance(source_models, dict):
        merged_models = merged.setdefault("models", {})
        current_models = target.get("models", {})
        if "mode" in source_models:
            merged_models["mode"] = source_models["mode"]

        current_providers = current_models.get("providers") if isinstance(current_models, dict) else {}
        preserved_providers = _select_preserved_entries(current_providers, preserve_providers)
        source_providers = source_models.get("providers")
        next_providers = dict(preserved_providers)
        if isinstance(source_providers, dict):
            next_providers.update(source_providers)
        if next_providers:
            merged_models["providers"] = next_providers
        else:
            merged_models.pop("providers", None)

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

            current_agents = target.get("agents", {})
            current_defaults = current_agents.get("defaults") if isinstance(current_agents, dict) else {}
            current_alias_models = current_defaults.get("models") if isinstance(current_defaults, dict) else {}
            preserved_alias_models = _select_preserved_entries(current_alias_models, preserve_models)
            source_alias_models = source_defaults.get("models")
            next_alias_models = dict(preserved_alias_models)
            if isinstance(source_alias_models, dict):
                next_alias_models.update(source_alias_models)
            if next_alias_models:
                merged_defaults["models"] = next_alias_models
            else:
                merged_defaults.pop("models", None)

    return merged


def write_openclaw_config(
    path: str | Path,
    payload: dict,
    *,
    preserve_path: str | Path | None = None,
) -> str | None:
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
                merged_payload = _replace_model_sections(
                    current_payload,
                    payload,
                    preserve_path=preserve_path,
                )
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
