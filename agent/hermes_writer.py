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


def _augment_config_yaml_for_hermes_runtime(config_yaml: str) -> str:
    """Add picker fields without changing Hermes provider/model routes."""
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
    default_value = model_payload.get("default")
    default_ref = _split_provider_model(default_value)
    if default_ref is not None:
        ordered_model_refs.append(default_ref)
    else:
        existing_provider = model_payload.get("provider")
        if (
            isinstance(existing_provider, str)
            and existing_provider.strip()
            and isinstance(default_value, str)
            and default_value.strip()
        ):
            provider_name = existing_provider.strip()
            upstream_model = default_value.strip()
            ordered_model_refs.append((provider_name, upstream_model))
            model_payload["default"] = f"{provider_name}/{upstream_model}"
            changed = True

    fallbacks = model_payload.get("fallbacks")
    if isinstance(fallbacks, list):
        normalized_fallbacks = []
        for item in fallbacks:
            fallback_ref = _split_provider_model(item)
            if fallback_ref is not None:
                ordered_model_refs.append(fallback_ref)
                normalized_fallbacks.append(f"{fallback_ref[0]}/{fallback_ref[1]}")
            else:
                normalized_fallbacks.append(item)
        if normalized_fallbacks != fallbacks:
            model_payload["fallbacks"] = normalized_fallbacks
            changed = True

    fallback_model = config_payload.get("fallback_model")
    fallback_model_items = (
        fallback_model
        if isinstance(fallback_model, list)
        else [fallback_model]
        if isinstance(fallback_model, dict)
        else []
    )
    recovered_fallbacks = []
    for item in fallback_model_items:
        if not isinstance(item, dict):
            continue
        provider_name = item.get("provider")
        upstream_model = item.get("model")
        if (
            isinstance(provider_name, str)
            and provider_name.strip()
            and isinstance(upstream_model, str)
            and upstream_model.strip()
        ):
            provider_name = provider_name.strip()
            upstream_model = upstream_model.strip()
            ordered_model_refs.append((provider_name, upstream_model))
            recovered_fallbacks.append(f"{provider_name}/{upstream_model}")

    if recovered_fallbacks:
        existing_fallbacks = model_payload.get("fallbacks")
        next_fallbacks = list(existing_fallbacks) if isinstance(existing_fallbacks, list) else []
        for fallback_key in recovered_fallbacks:
            if fallback_key not in next_fallbacks:
                next_fallbacks.append(fallback_key)
        if next_fallbacks != existing_fallbacks:
            model_payload["fallbacks"] = next_fallbacks
            changed = True

    if "fallback_model" in config_payload:
        config_payload.pop("fallback_model", None)
        changed = True

    for obsolete_key in ("provider", "base_url", "api_key", "default_headers"):
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
        return config_yaml

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
