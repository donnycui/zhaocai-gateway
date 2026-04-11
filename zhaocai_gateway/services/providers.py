from __future__ import annotations

from dataclasses import asdict
import sqlite3
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from zhaocai_gateway.db.store import SQLiteStore


class ProviderService:
    """OpenClaw provider inventory service for the current v2 module."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [asdict(provider) for provider in self.store.list_providers()]

    def get(self, provider_id: int) -> dict | None:
        provider = self.store.get_provider(provider_id)
        if provider is None:
            return None
        return asdict(provider)

    def create(
        self,
        *,
        name: str,
        base_url: str,
        provider_type: str,
        auth_scheme: str,
        api_key: str,
        extra_headers: dict[str, str],
    ) -> dict:
        normalized_name = name.strip()
        normalized_base_url = base_url.strip()
        normalized_provider_type = provider_type.strip()
        normalized_auth_scheme = auth_scheme.strip()
        try:
            provider = self.store.create_provider(
                name=normalized_name,
                provider_type=normalized_provider_type,
                base_url=normalized_base_url,
                auth_scheme=normalized_auth_scheme,
                api_key_encrypted=api_key,
                extra_headers=extra_headers,
                enabled=True,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(self._translate_integrity_error(exc)) from exc
        return asdict(provider)

    def update(
        self,
        provider_id: int,
        *,
        name: str,
        base_url: str,
        provider_type: str,
        auth_scheme: str,
        api_key: str,
        extra_headers: dict[str, str],
        enabled: bool,
    ) -> dict:
        normalized_name = name.strip()
        normalized_base_url = base_url.strip()
        normalized_provider_type = provider_type.strip()
        normalized_auth_scheme = auth_scheme.strip()
        try:
            provider = self.store.update_provider(
                provider_id,
                name=normalized_name,
                base_url=normalized_base_url,
                provider_type=normalized_provider_type,
                auth_scheme=normalized_auth_scheme,
                api_key_encrypted=api_key,
                extra_headers=extra_headers,
                enabled=enabled,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(self._translate_integrity_error(exc)) from exc
        return asdict(provider)

    def delete(self, provider_id: int) -> None:
        self.store.delete_provider(provider_id)

    def validate(
        self,
        *,
        base_url: str,
        auth_scheme: str,
    ) -> dict:
        parsed = urlparse(base_url.strip())
        ok = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        auth_ok = auth_scheme.strip().lower() in {"bearer", "x-api-key", "basic"}
        return {
            "ok": bool(ok and auth_ok),
            "message": "OpenClaw provider input looks valid" if ok and auth_ok else "Invalid OpenClaw provider input",
        }

    def discover_models(
        self,
        *,
        base_url: str,
        provider_type: str,
        auth_scheme: str,
        api_key: str,
        extra_headers: dict[str, str],
    ) -> dict:
        validation = self.validate(base_url=base_url, auth_scheme=auth_scheme)
        if not validation["ok"]:
            raise ValueError(validation["message"])

        payload = None
        last_error_message = "The upstream /models endpoint returned an unsupported payload"
        for models_url in self._candidate_models_urls(base_url):
            for headers in self._candidate_models_headers(
                auth_scheme=auth_scheme,
                api_key=api_key,
                extra_headers=extra_headers,
                provider_type=provider_type,
            ):
                try:
                    response = httpx.request(
                        "GET",
                        models_url,
                        headers=headers,
                        timeout=20.0,
                    )
                except httpx.HTTPError as exc:
                    last_error_message = f"Unable to fetch models from upstream: {exc}"
                    continue

                if not response.is_success:
                    last_error_message = self._extract_error_message(response)
                    continue

                try:
                    candidate_payload = response.json()
                except ValueError:
                    last_error_message = "The upstream /models endpoint did not return valid JSON"
                    continue

                items = self._extract_model_items(candidate_payload)
                if items is None:
                    last_error_message = "The upstream /models endpoint returned an unsupported payload"
                    continue

                payload = candidate_payload
                break
            if payload is not None:
                break

        if payload is None:
            raise RuntimeError(last_error_message)

        items = self._extract_model_items(payload)
        if items is None:
            raise RuntimeError(last_error_message)

        normalized_models: list[dict[str, Any]] = []
        seen_model_ids: set[str] = set()
        for item in items:
            normalized = self._normalize_discovered_model(item)
            if normalized is None:
                continue
            model_id = normalized["upstream_model"]
            if model_id in seen_model_ids:
                continue
            seen_model_ids.add(model_id)
            normalized_models.append(normalized)

        return {
            "models": normalized_models,
            "count": len(normalized_models),
        }

    def test_connectivity(self, provider_id: int) -> dict:
        provider = self.store.get_provider(provider_id)
        if provider is None:
            raise ValueError(f"Provider {provider_id} not found")

        models = [
            model
            for model in self.store.list_models()
            if model.provider_id == provider_id and model.enabled
        ]
        if not models:
            return {
                "ok": False,
                "provider": asdict(provider),
                "message": "这个 OpenClaw 供应商还没有可测试的模型。",
                "results": [],
            }

        results: list[dict] = []
        for model in models:
            started_at = time.perf_counter()
            try:
                response = httpx.request(
                    "POST",
                    self._build_test_url(provider.base_url, provider.provider_type),
                    headers=self._build_headers(
                        auth_scheme=provider.auth_scheme,
                        api_key=provider.api_key_encrypted,
                        extra_headers=provider.extra_headers,
                        provider_type=provider.provider_type,
                    ),
                    json=self._build_payload(
                        provider_type=provider.provider_type,
                        model_id=model.upstream_model,
                    ),
                    timeout=20.0,
                )
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                ok = response.is_success
                results.append(
                    {
                        "model_id": model.upstream_model,
                        "display_name": model.display_name,
                        "ok": ok,
                        "status_code": response.status_code,
                        "latency_ms": latency_ms,
                        "message": "测试通过" if ok else self._extract_error_message(response),
                    }
                )
            except httpx.HTTPError as exc:
                latency_ms = int((time.perf_counter() - started_at) * 1000)
                results.append(
                    {
                        "model_id": model.upstream_model,
                        "display_name": model.display_name,
                        "ok": False,
                        "status_code": None,
                        "latency_ms": latency_ms,
                        "message": str(exc),
                    }
                )

        passed = sum(1 for item in results if item["ok"])
        return {
            "ok": passed == len(results),
            "provider": asdict(provider),
            "message": f"已检测 {len(results)} 个模型，成功 {passed} 个，失败 {len(results) - passed} 个。",
            "results": results,
        }

    @staticmethod
    def _build_test_url(base_url: str, provider_type: str) -> str:
        normalized = (provider_type or "openai-completions").strip().lower()
        path = "/chat/completions"
        if normalized == "openai-responses":
            path = "/responses"
        elif normalized in {"anthropic", "anthropic-messages"}:
            path = "/messages"

        normalized_base = base_url.strip().rstrip("/")
        if normalized_base.endswith(path):
            return normalized_base
        return f"{normalized_base}{path}"

    @staticmethod
    def _build_models_url(base_url: str) -> str:
        normalized_base = base_url.strip().rstrip("/")
        if normalized_base.endswith("/models"):
            return normalized_base
        return f"{normalized_base}/models"

    @classmethod
    def _candidate_models_urls(cls, base_url: str) -> list[str]:
        normalized_base = base_url.strip().rstrip("/")
        candidates = [
            cls._build_models_url(normalized_base),
            f"{normalized_base}/v1/models",
        ]
        unique: list[str] = []
        for candidate in candidates:
            if candidate not in unique:
                unique.append(candidate)
        return unique

    @staticmethod
    def _build_payload(*, provider_type: str, model_id: str) -> dict:
        normalized = (provider_type or "openai-completions").strip().lower()
        if normalized == "openai-responses":
            return {
                "model": model_id,
                "input": "ping",
                "max_output_tokens": 1,
            }
        if normalized in {"anthropic", "anthropic-messages"}:
            return {
                "model": model_id,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "ping"}],
            }
        return {
            "model": model_id,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "temperature": 0,
        }

    @staticmethod
    def _build_headers(
        *,
        auth_scheme: str,
        api_key: str,
        extra_headers: dict[str, str],
        provider_type: str,
    ) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            **extra_headers,
        }
        normalized_auth = (auth_scheme or "bearer").strip().lower()
        if api_key:
            if normalized_auth == "x-api-key":
                headers["x-api-key"] = api_key
            elif normalized_auth == "basic":
                headers["Authorization"] = f"Basic {api_key}"
            else:
                headers["Authorization"] = f"Bearer {api_key}"

        normalized_provider = (provider_type or "openai-completions").strip().lower()
        if normalized_provider in {"anthropic", "anthropic-messages"}:
            headers.setdefault("anthropic-version", "2023-06-01")
        return headers

    @classmethod
    def _candidate_models_headers(
        cls,
        *,
        auth_scheme: str,
        api_key: str,
        extra_headers: dict[str, str],
        provider_type: str,
    ) -> list[dict[str, str]]:
        primary = cls._build_headers(
            auth_scheme=auth_scheme,
            api_key=api_key,
            extra_headers=extra_headers,
            provider_type=provider_type,
        )
        candidates = [primary]

        normalized_provider = (provider_type or "openai-completions").strip().lower()
        normalized_auth = (auth_scheme or "bearer").strip().lower()
        if normalized_provider in {"anthropic", "anthropic-messages"} and normalized_auth == "x-api-key" and api_key:
            fallback = {
                key: value
                for key, value in primary.items()
                if key.lower() != "x-api-key"
            }
            fallback["Authorization"] = f"Bearer {api_key}"
            candidates.append(fallback)

        return candidates

    @staticmethod
    def _translate_integrity_error(exc: sqlite3.IntegrityError) -> str:
        text = str(exc)
        if "providers.name" in text:
            return "供应商名称已存在，请更换名称。"
        return "供应商保存失败，请检查输入后重试。"

    @classmethod
    def _extract_model_items(cls, payload: Any) -> list[dict[str, Any]] | None:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return None

        for key in ("data", "models", "items", "results"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
        return None

    @classmethod
    def _normalize_discovered_model(cls, item: dict[str, Any]) -> dict[str, Any] | None:
        raw_model_id = item.get("id") or item.get("model") or item.get("name")
        if not isinstance(raw_model_id, str) or not raw_model_id.strip():
            return None

        model_id = raw_model_id.strip()
        raw_display_name = item.get("display_name") or item.get("name") or model_id
        display_name = raw_display_name.strip() if isinstance(raw_display_name, str) else model_id
        input_modalities = cls._extract_input_modalities(item)
        reasoning = cls._extract_reasoning_flag(item, model_id, display_name)
        capabilities = ["text"]
        if "image" in input_modalities and "multimodal" not in capabilities:
            capabilities.append("multimodal")
        if "audio" in input_modalities and "audio" not in capabilities:
            capabilities.append("audio")
        if reasoning and "reasoning" not in capabilities:
            capabilities.append("reasoning")

        pricing = item.get("pricing") if isinstance(item.get("pricing"), dict) else {}

        return {
            "upstream_model": model_id,
            "display_name": display_name,
            "owner": str(item.get("owned_by") or item.get("provider") or "").strip(),
            "capabilities": capabilities,
            "reasoning": reasoning,
            "input_modalities": input_modalities,
            "context_window": cls._safe_int(item.get("context_window") or item.get("context_length")),
            "max_tokens": cls._safe_int(item.get("max_tokens") or item.get("max_output_tokens")),
            "cost_input": cls._safe_float(pricing.get("prompt") or pricing.get("input") or item.get("cost_input")),
            "cost_output": cls._safe_float(pricing.get("completion") or pricing.get("output") or item.get("cost_output")),
            "cost_cache_read": cls._safe_float(
                pricing.get("cache_read") or pricing.get("cached_input") or item.get("cost_cache_read")
            ),
            "cost_cache_write": cls._safe_float(
                pricing.get("cache_write") or item.get("cost_cache_write")
            ),
        }

    @classmethod
    def _extract_input_modalities(cls, item: dict[str, Any]) -> list[str]:
        raw_candidates: list[Any] = [
            item.get("input_modalities"),
            item.get("modalities"),
            item.get("input"),
        ]
        architecture = item.get("architecture")
        if isinstance(architecture, dict):
            raw_candidates.append(architecture.get("input_modalities"))

        modalities: list[str] = []
        for candidate in raw_candidates:
            if isinstance(candidate, str):
                modalities.extend(part.strip().lower() for part in candidate.split(",") if part.strip())
            elif isinstance(candidate, list):
                modalities.extend(
                    str(part).strip().lower()
                    for part in candidate
                    if isinstance(part, str) and part.strip()
                )

        unique_modalities: list[str] = []
        for modality in modalities:
            if modality not in unique_modalities:
                unique_modalities.append(modality)

        if unique_modalities:
            return unique_modalities

        if cls._looks_multimodal(item):
            return ["text", "image"]
        return ["text"]

    @staticmethod
    def _looks_multimodal(item: dict[str, Any]) -> bool:
        for key in ("supports_vision", "vision", "multimodal"):
            value = item.get(key)
            if isinstance(value, bool) and value:
                return True
        return False

    @staticmethod
    def _extract_reasoning_flag(item: dict[str, Any], model_id: str, display_name: str) -> bool:
        for key in ("reasoning", "supports_reasoning", "reasoning_enabled"):
            value = item.get(key)
            if isinstance(value, bool):
                return value

        lowered = f"{model_id} {display_name}".lower()
        reasoning_markers = (
            "reason",
            "thinking",
            "r1",
            "o1",
            "o3",
            "o4-mini",
        )
        return any(marker in lowered for marker in reasoning_markers)

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        prefix = f"HTTP {response.status_code}"
        try:
            payload = response.json()
        except ValueError:
            body = response.text.strip()
            return f"{prefix}: {body}" if body else prefix

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message") or error.get("type")
                if message:
                    return f"{prefix}: {message}"
            detail = payload.get("detail")
            if isinstance(detail, str) and detail:
                return f"{prefix}: {detail}"
            message = payload.get("message")
            if isinstance(message, str) and message:
                return f"{prefix}: {message}"
        return prefix
