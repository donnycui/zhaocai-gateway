from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

import httpx

from zhaocai_gateway.db.store import SQLiteStore
from zhaocai_gateway.services.providers import ProviderService


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class GatewayAccountService:
    """Gateway upstream-account service for the modular provider center."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [asdict(account) for account in self.store.list_gateway_upstream_accounts()]

    def get(self, account_id: int) -> dict | None:
        account = self.store.get_gateway_upstream_account(account_id)
        if account is None:
            return None
        return asdict(account)

    def create(
        self,
        *,
        name: str,
        base_url: str,
        auth_type: str,
        api_key: str,
        protocol: str,
        notes: str,
    ) -> dict:
        account = self.store.create_gateway_upstream_account(
            name=name.strip(),
            base_url=base_url.strip().rstrip("/"),
            auth_type=auth_type.strip().lower(),
            api_key_encrypted=api_key,
            protocol=protocol.strip() or "openai-compatible",
            enabled=True,
            notes=notes.strip(),
        )
        return asdict(account)

    def update(
        self,
        account_id: int,
        *,
        name: str,
        base_url: str,
        auth_type: str,
        api_key: str,
        protocol: str,
        notes: str,
        enabled: bool,
    ) -> dict:
        account = self.store.update_gateway_upstream_account(
            account_id,
            name=name.strip(),
            base_url=base_url.strip().rstrip("/"),
            auth_type=auth_type.strip().lower(),
            api_key_encrypted=api_key,
            protocol=protocol.strip() or "openai-compatible",
            enabled=enabled,
            notes=notes.strip(),
        )
        return asdict(account)

    def delete(self, account_id: int) -> None:
        account = self.store.get_gateway_upstream_account(account_id)
        if account is None:
            raise ValueError(f"Gateway account {account_id} not found")
        self.store.delete_gateway_upstream_account(account_id)

    def test_connection(self, account_id: int) -> dict:
        account = self.store.get_gateway_upstream_account(account_id)
        if account is None:
            raise ValueError(f"Gateway account {account_id} not found")

        if self._normalize_protocol(account.protocol) == "gemini":
            return self._test_gemini_connection(account)

        try:
            response = httpx.request(
                "GET",
                self._build_models_url(account.base_url),
                headers=self._build_headers(account.auth_type, account.api_key_encrypted),
                timeout=20.0,
            )
        except httpx.HTTPError as exc:
            self.store.update_gateway_upstream_account_status(
                account.id,
                health_status="ERROR",
                last_checked_at=_utc_now_iso(),
            )
            raise RuntimeError(str(exc)) from exc

        healthy = response.is_success
        self.store.update_gateway_upstream_account_status(
            account.id,
            health_status="HEALTHY" if healthy else "DEGRADED",
            last_checked_at=_utc_now_iso(),
        )
        return {
            "healthy": healthy,
            "models_status": response.status_code,
        }

    def _test_gemini_connection(self, account) -> dict:
        last_status = None
        last_message = "Unable to reach Gemini upstream"
        for models_url in self._candidate_models_urls(account.base_url, protocol=account.protocol):
            for headers in self._candidate_models_headers(
                account.auth_type,
                account.api_key_encrypted,
                protocol=account.protocol,
            ):
                try:
                    response = ProviderService._request_with_tls_fallback(
                        "GET",
                        url=models_url,
                        headers=headers,
                        timeout=20.0,
                    )
                except httpx.HTTPError as exc:
                    last_message = str(exc)
                    continue

                last_status = response.status_code
                if response.is_success:
                    self.store.update_gateway_upstream_account_status(
                        account.id,
                        health_status="HEALTHY",
                        last_checked_at=_utc_now_iso(),
                    )
                    return {
                        "healthy": True,
                        "models_status": response.status_code,
                    }

                last_message = self._extract_error_message(response)

        self.store.update_gateway_upstream_account_status(
            account.id,
            health_status="DEGRADED" if last_status is not None else "ERROR",
            last_checked_at=_utc_now_iso(),
        )
        return {
            "healthy": False,
            "models_status": last_status or 0,
            "message": last_message,
        }

    def discover_models(self, account_id: int) -> dict:
        account = self.store.get_gateway_upstream_account(account_id)
        if account is None:
            raise ValueError(f"Gateway account {account_id} not found")

        payload = None
        last_error_message = "The upstream /models endpoint returned an unsupported payload"
        for models_url in self._candidate_models_urls(account.base_url, protocol=account.protocol):
            for headers in self._candidate_models_headers(
                account.auth_type,
                account.api_key_encrypted,
                protocol=account.protocol,
            ):
                try:
                    response = ProviderService._request_with_tls_fallback(
                        "GET",
                        url=models_url,
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

                items = ProviderService._extract_model_items(candidate_payload)
                if items is None:
                    last_error_message = "The upstream /models endpoint returned an unsupported payload"
                    continue

                payload = candidate_payload
                break
            if payload is not None:
                break

        if payload is None:
            raise RuntimeError(last_error_message)

        items = ProviderService._extract_model_items(payload)
        if items is None:
            raise RuntimeError(last_error_message)

        normalized_models: list[dict] = []
        seen_model_ids: set[str] = set()
        for item in items:
            normalized = ProviderService._normalize_discovered_model(item)
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

    def import_models(self, account_id: int, models: list[dict]) -> dict:
        account = self.store.get_gateway_upstream_account(account_id)
        if account is None:
            raise ValueError(f"Gateway account {account_id} not found")

        imported_count = 0
        created_count = 0
        for model in models:
            upstream_model = str(model.get("upstream_model", "")).strip()
            display_name = str(model.get("display_name") or upstream_model).strip()
            owner = str(model.get("owner", "")).strip() or None
            if not upstream_model or not display_name:
                continue

            existing = self.store.get_gateway_model_by_account_and_upstream(account_id, upstream_model)
            self.store.upsert_gateway_model(
                account_id=account_id,
                upstream_model=upstream_model,
                display_name=display_name,
                family=owner or self._infer_family({}, upstream_model),
                supports_chat=True,
                supports_responses=True,
                enabled=True,
            )
            imported_count += 1
            if existing is None:
                created_count += 1

        refreshed = self.store.get_gateway_upstream_account(account_id)
        if refreshed is None:
            raise RuntimeError("Failed to reload gateway account after import")

        return {
            "account": asdict(refreshed),
            "imported_count": imported_count,
            "created_count": created_count,
        }

    def delete_model(self, model_id: int) -> None:
        model = self.store.get_gateway_model(model_id)
        if model is None:
            raise ValueError(f"Gateway model {model_id} not found")
        self.store.delete_gateway_model(model_id)

    def sync_models(self, account_id: int) -> dict:
        account = self.store.get_gateway_upstream_account(account_id)
        if account is None:
            raise ValueError(f"Gateway account {account_id} not found")

        try:
            response = httpx.request(
                "GET",
                self._build_models_url(account.base_url),
                headers=self._build_headers(account.auth_type, account.api_key_encrypted),
                timeout=20.0,
            )
        except httpx.HTTPError as exc:
            self.store.update_gateway_upstream_account_status(
                account.id,
                health_status="ERROR",
                last_checked_at=_utc_now_iso(),
            )
            raise RuntimeError(str(exc)) from exc

        if not response.is_success:
            self.store.update_gateway_upstream_account_status(
                account.id,
                health_status="ERROR",
                last_checked_at=_utc_now_iso(),
            )
            raise RuntimeError(f"Gateway upstream returned HTTP {response.status_code}")

        payload = response.json()
        items = payload.get("data", [])
        if not isinstance(items, list):
            items = []

        upserted_count = 0
        discovered: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("id", "")).strip()
            if not model_id:
                continue
            discovered.add(model_id)
            existing = self.store.get_gateway_model_by_account_and_upstream(account.id, model_id)
            self.store.upsert_gateway_model(
                account_id=account.id,
                upstream_model=model_id,
                display_name=str(item.get("name") or model_id).strip(),
                family=self._infer_family(item, model_id),
                supports_chat=True,
                supports_responses=True,
                enabled=True,
            )
            if existing is None:
                upserted_count += 1

        self.store.disable_missing_gateway_models(account.id, discovered)
        self.store.update_gateway_upstream_account_status(
            account.id,
            health_status="HEALTHY",
            last_checked_at=_utc_now_iso(),
            last_synced_at=_utc_now_iso(),
            cooldown_until=None,
        )
        return {
            "account_id": account.id,
            "models_count": len(discovered),
            "upserted_count": upserted_count,
        }

    @staticmethod
    def _build_models_url(base_url: str) -> str:
        normalized = base_url.strip().rstrip("/")
        if normalized.endswith("/models"):
            return normalized
        if normalized.endswith("/v1"):
            return f"{normalized}/models"
        return f"{normalized}/models" if normalized.endswith("/v1") else f"{normalized}/models"

    @classmethod
    def _candidate_models_urls(cls, base_url: str, *, protocol: str = "openai-compatible") -> list[str]:
        normalized_base = base_url.strip().rstrip("/")
        if cls._normalize_protocol(protocol) == "gemini":
            base_no_suffix = normalized_base[:-len("/gemini")] if normalized_base.endswith("/gemini") else normalized_base
            candidates = [
                f"{normalized_base}/v1beta/models",
                f"{normalized_base}/v1/models",
                cls._build_models_url(normalized_base),
                f"{base_no_suffix}/gemini/v1beta/models",
                f"{base_no_suffix}/v1beta/models",
            ]
        else:
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
    def _build_headers(auth_type: str, api_key: str) -> dict[str, str]:
        normalized = (auth_type or "none").strip().lower()
        if normalized == "x-api-key":
            return {"x-api-key": api_key} if api_key else {}
        if normalized == "basic":
            return {"Authorization": f"Basic {api_key}"} if api_key else {}
        if normalized == "passcode":
            return {"x-passcode": api_key} if api_key else {}
        if normalized == "bearer":
            return {"Authorization": f"Bearer {api_key}"} if api_key else {}
        return {}

    @classmethod
    def _candidate_models_headers(cls, auth_type: str, api_key: str, *, protocol: str = "openai-compatible") -> list[dict[str, str]]:
        primary = cls._build_headers(auth_type, api_key)
        candidates = [primary]
        normalized_auth = (auth_type or "").strip().lower()
        if normalized_auth == "x-api-key" and api_key:
            candidates.append({"Authorization": f"Bearer {api_key}"})
        if cls._normalize_protocol(protocol) == "gemini" and api_key:
            if normalized_auth != "x-goog-api-key":
                candidates.append({"x-goog-api-key": api_key})
            if normalized_auth != "x-api-key":
                candidates.append({"x-api-key": api_key})
        return candidates

    @staticmethod
    def _normalize_protocol(protocol: str | None) -> str:
        normalized = (protocol or "openai-compatible").strip().lower()
        return normalized or "openai-compatible"

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                error = payload.get("error")
                if isinstance(error, dict):
                    message = error.get("message")
                    if isinstance(message, str) and message.strip():
                        return message.strip()
                detail = payload.get("detail")
                if isinstance(detail, str) and detail.strip():
                    return detail.strip()
        except ValueError:
            pass
        snippet = response.text.strip()[:200]
        if snippet:
            return f"HTTP {response.status_code}: {snippet}"
        return f"Gateway upstream returned HTTP {response.status_code}"

    @staticmethod
    def _infer_family(item: dict, model_id: str) -> str | None:
        owned_by = item.get("owned_by")
        if isinstance(owned_by, str) and owned_by.strip():
            return owned_by.strip()
        prefix, _, _ = model_id.partition("/")
        return prefix.strip() or None
