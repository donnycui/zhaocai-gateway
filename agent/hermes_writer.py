from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import yaml


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


def _split_provider_model(model_key: object) -> tuple[str, str] | None:
    if not isinstance(model_key, str):
        return None
    text = model_key.strip()
    if "/" not in text:
        return None
    provider_name, upstream_model = text.split("/", 1)
    provider_name = provider_name.strip()
    upstream_model = upstream_model.strip()
    if not provider_name or not upstream_model:
        return None
    return provider_name, upstream_model


def _string_value(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _iter_model_entries(raw: object) -> list[dict]:
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _fallback_entry(
    provider_name: str,
    upstream_model: str,
    providers: dict,
    source: dict | None = None,
) -> dict:
    entry = {
        key: value
        for key, value in dict(source or {}).items()
        if key not in {"provider", "model"}
    }
    entry["provider"] = provider_name
    entry["model"] = upstream_model

    provider_config = providers.get(provider_name)
    if isinstance(provider_config, dict):
        for key in ("base_url", "api_key", "key_env", "api_key_env", "api_mode", "transport"):
            if _string_value(entry.get(key)):
                continue
            value = provider_config.get(key)
            if _string_value(value):
                entry[key] = _string_value(value)
    return entry


def _fallback_identity(entry: dict) -> tuple[str, str, str]:
    return (
        _string_value(entry.get("provider")).lower(),
        _string_value(entry.get("model")).lower(),
        _string_value(entry.get("base_url")).rstrip("/").lower(),
    )


def _augment_config_yaml_for_hermes_runtime(config_yaml: str) -> str:
    """Normalize old sync payloads to Hermes runtime fields and picker indexes."""
    try:
        config_payload = yaml.safe_load(config_yaml) or {}
    except Exception:
        return config_yaml
    if not isinstance(config_payload, dict):
        return config_yaml

    providers = config_payload.get("providers")
    model_payload = config_payload.get("model")
    if not isinstance(providers, dict) or not isinstance(model_payload, dict):
        return config_yaml

    changed = False
    ordered_model_refs: list[tuple[str, str]] = []
    seen_model_refs: set[tuple[str, str]] = set()
    fallback_entries: list[dict] = []
    seen_fallbacks: set[tuple[str, str, str]] = set()

    def add_model_ref(provider_name: str, upstream_model: str) -> None:
        provider_name = provider_name.strip()
        upstream_model = upstream_model.strip()
        identity = (provider_name, upstream_model)
        if provider_name and upstream_model and identity not in seen_model_refs:
            seen_model_refs.add(identity)
            ordered_model_refs.append(identity)

    def add_fallback(provider_name: str, upstream_model: str, source: dict | None = None) -> None:
        entry = _fallback_entry(provider_name, upstream_model, providers, source=source)
        identity = _fallback_identity(entry)
        if not identity[0] or not identity[1] or identity in seen_fallbacks:
            return
        seen_fallbacks.add(identity)
        fallback_entries.append(entry)
        add_model_ref(entry["provider"], entry["model"])

    default_value = model_payload.get("default")
    existing_provider = _string_value(model_payload.get("provider"))
    if existing_provider and _string_value(default_value):
        provider_name = existing_provider
        upstream_model = _string_value(default_value)
        add_model_ref(provider_name, upstream_model)
        if model_payload.get("provider") != provider_name:
            model_payload["provider"] = provider_name
            changed = True
        if model_payload.get("default") != upstream_model:
            model_payload["default"] = upstream_model
            changed = True
    else:
        default_ref = _split_provider_model(default_value)
        if default_ref is not None:
            provider_name, upstream_model = default_ref
            add_model_ref(provider_name, upstream_model)
            if model_payload.get("provider") != provider_name:
                model_payload["provider"] = provider_name
                changed = True
            if model_payload.get("default") != upstream_model:
                model_payload["default"] = upstream_model
                changed = True

    primary_provider = _string_value(model_payload.get("provider"))

    fallbacks = model_payload.get("fallbacks")
    if isinstance(fallbacks, list):
        for item in fallbacks:
            if isinstance(item, dict):
                provider_name = _string_value(item.get("provider")) or primary_provider
                upstream_model = _string_value(item.get("model"))
                if provider_name and upstream_model:
                    add_fallback(provider_name, upstream_model, source=item)
                continue
            fallback_ref = _split_provider_model(item)
            if fallback_ref is not None:
                add_fallback(fallback_ref[0], fallback_ref[1])
            elif primary_provider and _string_value(item):
                add_fallback(primary_provider, _string_value(item))
        model_payload.pop("fallbacks", None)
        changed = True

    existing_fallback_model = config_payload.get("fallback_model")
    for item in _iter_model_entries(existing_fallback_model):
        provider_name = _string_value(item.get("provider"))
        upstream_model = _string_value(item.get("model"))
        if provider_name and upstream_model:
            add_fallback(provider_name, upstream_model, source=item)

    for item in _iter_model_entries(config_payload.get("fallback_providers")):
        provider_name = _string_value(item.get("provider"))
        upstream_model = _string_value(item.get("model"))
        if provider_name and upstream_model:
            add_model_ref(provider_name, upstream_model)

    if fallback_entries:
        if config_payload.get("fallback_model") != fallback_entries:
            config_payload["fallback_model"] = fallback_entries
            changed = True
    elif "fallback_model" in config_payload:
        config_payload.pop("fallback_model", None)
        changed = True

    for obsolete_key in ("base_url", "api_key", "default_headers"):
        if obsolete_key in model_payload:
            model_payload.pop(obsolete_key, None)
            changed = True

    provider_models: dict[str, list[str]] = {}
    for provider_name, upstream_model in ordered_model_refs:
        provider_config = providers.get(provider_name)
        if not isinstance(provider_config, dict):
            continue
        provider_models.setdefault(provider_name, [])
        if upstream_model not in provider_models[provider_name]:
            provider_models[provider_name].append(upstream_model)

    if not provider_models:
        if not changed:
            return config_yaml
        return yaml.safe_dump(config_payload, sort_keys=False, allow_unicode=True)

    for provider_name, models in provider_models.items():
        provider_config = providers[provider_name]
        if not provider_config.get("model"):
            provider_config["model"] = models[0]
            changed = True
        if not provider_config.get("default_model"):
            provider_config["default_model"] = models[0]
            changed = True

        configured_models = provider_config.get("models")
        if isinstance(configured_models, dict):
            for model_id in models:
                if model_id not in configured_models:
                    configured_models[model_id] = {}
                    changed = True
        elif isinstance(configured_models, list):
            for model_id in models:
                if model_id not in configured_models:
                    configured_models.append(model_id)
                    changed = True
        else:
            provider_config["models"] = {model_id: {} for model_id in models}
            changed = True

    if not changed:
        return config_yaml
    return yaml.safe_dump(config_payload, sort_keys=False, allow_unicode=True)


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

    config_yaml = _augment_config_yaml_for_hermes_runtime(str(payload.get("config_yaml", "")))
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
