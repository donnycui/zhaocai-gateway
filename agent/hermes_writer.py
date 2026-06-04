from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path


MANAGED_PLUGIN_MANIFEST = ".zhaocai-hermes-managed-plugins.json"


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        delete=False,
        encoding="utf-8",
        dir=str(path.parent),
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)


def _load_managed_plugins(manifest_path: Path) -> list[str]:
    if not manifest_path.exists():
        return []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item).strip() for item in payload if str(item).strip()]


def write_hermes_config(
    path: str | Path,
    payload: dict,
) -> str | None:
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    backup_path: str | None = None
    if target_path.exists():
        backup = target_path.with_suffix(target_path.suffix + ".bak")
        shutil.copy2(target_path, backup)
        backup_path = str(backup)

    config_yaml = str(payload.get("config_yaml", ""))
    plugin_files = payload.get("plugin_files", {})
    if not isinstance(plugin_files, dict):
        plugin_files = {}

    _write_text_atomic(target_path, config_yaml)

    plugin_root = target_path.parent / "plugins" / "model-providers"
    manifest_path = target_path.parent / MANAGED_PLUGIN_MANIFEST
    previous_plugins = set(_load_managed_plugins(manifest_path))
    next_plugins = {str(provider_name).strip() for provider_name in plugin_files if str(provider_name).strip()}

    for provider_name, plugin_source in plugin_files.items():
        if not str(provider_name).strip():
            continue
        plugin_file = plugin_root / str(provider_name) / "__init__.py"
        _write_text_atomic(plugin_file, str(plugin_source))

    for stale_provider in sorted(previous_plugins - next_plugins):
        stale_dir = plugin_root / stale_provider
        if stale_dir.exists():
            shutil.rmtree(stale_dir)

    _write_text_atomic(
        manifest_path,
        json.dumps(sorted(next_plugins), ensure_ascii=False, indent=2),
    )
    return backup_path
