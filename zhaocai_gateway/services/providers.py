from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import time
from urllib.parse import urlparse

import httpx

from zhaocai_gateway.db.store import SQLiteStore


class ProviderService:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [asdict(provider) for provider in self.store.list_providers()]

    def get(self, provider_id: int) -> dict | None:
        provider = self.store.get_provider(provider_id)
        if provider is None:
            return None
        return asdict(provider)

    def list_balances(self) -> list[dict]:
        return [asdict(balance) for balance in self.store.list_provider_balances()]

    def create(
        self,
        *,
        name: str,
        base_url: str,
        provider_type: str,
        auth_scheme: str,
        api_key: str,
        balance_query_type: str,
        balance_access_token: str,
        balance_user_id: str,
        balance_auto_refresh_minutes: int,
        extra_headers: dict[str, str],
    ) -> dict:
        normalized_name = name.strip()
        normalized_base_url = base_url.strip()
        normalized_provider_type = provider_type.strip()
        normalized_auth_scheme = auth_scheme.strip()
        provider = self.store.create_provider(
            name=normalized_name,
            provider_type=normalized_provider_type,
            base_url=normalized_base_url,
            auth_scheme=normalized_auth_scheme,
            api_key_encrypted=api_key,
            balance_query_type=balance_query_type.strip(),
            balance_access_token=balance_access_token.strip(),
            balance_user_id=balance_user_id.strip(),
            balance_auto_refresh_minutes=max(0, balance_auto_refresh_minutes),
            extra_headers=extra_headers,
            enabled=True,
        )
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
        balance_query_type: str,
        balance_access_token: str,
        balance_user_id: str,
        balance_auto_refresh_minutes: int,
        extra_headers: dict[str, str],
        enabled: bool,
    ) -> dict:
        normalized_name = name.strip()
        normalized_base_url = base_url.strip()
        normalized_provider_type = provider_type.strip()
        normalized_auth_scheme = auth_scheme.strip()
        provider = self.store.update_provider(
            provider_id,
            name=normalized_name,
            base_url=normalized_base_url,
            provider_type=normalized_provider_type,
            auth_scheme=normalized_auth_scheme,
            api_key_encrypted=api_key,
            balance_query_type=balance_query_type.strip(),
            balance_access_token=balance_access_token.strip(),
            balance_user_id=balance_user_id.strip(),
            balance_auto_refresh_minutes=max(0, balance_auto_refresh_minutes),
            extra_headers=extra_headers,
            enabled=enabled,
        )
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
            "message": "Provider input looks valid" if ok and auth_ok else "Invalid provider input",
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
                "message": "这个供应商还没有可测试的模型。",
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

    def refresh_balance(self, provider_id: int) -> dict:
        provider = self.store.get_provider(provider_id)
        if provider is None:
            raise ValueError(f"Provider {provider_id} not found")

        result = self._query_balance(provider)
        self.store.upsert_provider_balance(
            provider_id=provider.id,
            supported=result["supported"],
            amount=result["amount"],
            currency=result["currency"],
            status=result["status"],
            message=result["message"],
            fetched_at=result["fetched_at"],
        )
        refreshed = self.store.get_provider(provider.id)
        if refreshed is None:
            raise RuntimeError("Failed to refresh provider balance")
        return asdict(refreshed)

    def refresh_balances(self, provider_ids: list[int] | None = None) -> dict:
        providers = self.store.list_providers()
        if provider_ids is not None:
            provider_ids_set = set(provider_ids)
            providers = [provider for provider in providers if provider.id in provider_ids_set]

        refreshed: list[dict] = []
        for provider in providers:
            refreshed.append(self.refresh_balance(provider.id))

        return {"providers": refreshed}

    def _query_balance(self, provider) -> dict:
        query_type = self._resolve_balance_query_type(provider)
        if query_type == "openrouter":
            return self._query_openrouter_balance(provider)
        if query_type == "newapi":
            return self._query_newapi_balance(provider)

        return {
            "supported": False,
            "amount": None,
            "currency": None,
            "status": "unsupported",
            "message": "暂不支持余额查询",
            "fetched_at": None,
        }

    @staticmethod
    def _resolve_balance_query_type(provider) -> str:
        configured = (provider.balance_query_type or "").strip().lower()
        if configured:
            return configured
        if ProviderService._is_openrouter_provider(provider):
            return "openrouter"
        return ""

    @staticmethod
    def _is_openrouter_provider(provider) -> bool:
        name = provider.name.lower()
        base_url = provider.base_url.lower()
        return "openrouter" in name or "openrouter.ai" in base_url

    def _query_openrouter_balance(self, provider) -> dict:
        endpoint = f"{provider.base_url.strip().rstrip('/')}/credits"
        response = httpx.get(
            endpoint,
            headers={"Authorization": f"Bearer {provider.api_key_encrypted}"},
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()

        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        total_credits = self._safe_float(data.get("total_credits"))
        total_usage = self._safe_float(data.get("total_usage"))
        remaining = None
        if total_credits is not None and total_usage is not None:
            remaining = max(total_credits - total_usage, 0.0)
        elif total_credits is not None:
            remaining = total_credits

        return {
            "supported": True,
            "amount": remaining,
            "currency": "USD",
            "status": "ok",
            "message": "余额已刷新",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def _query_newapi_balance(self, provider) -> dict:
        access_token = (provider.balance_access_token or provider.api_key_encrypted or "").strip()
        if not access_token:
            return {
                "supported": True,
                "amount": None,
                "currency": "USD",
                "status": "error",
                "message": "未配置 NewAPI Access Token",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        if provider.balance_user_id.strip():
            headers["New-Api-User"] = provider.balance_user_id.strip()

        endpoint = f"{provider.base_url.strip().rstrip('/')}/api/user/self"
        response = httpx.get(endpoint, headers=headers, timeout=20.0)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        if not payload.get("success", True):
            return {
                "supported": True,
                "amount": None,
                "currency": "USD",
                "status": "error",
                "message": str(payload.get("message") or "余额查询失败"),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        quota = self._safe_float(data.get("quota"))
        amount = None
        if quota is not None:
            amount = max(quota / 500000.0, 0.0)

        return {
            "supported": True,
            "amount": amount,
            "currency": "USD",
            "status": "ok",
            "message": "余额已刷新",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _safe_float(value) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

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
