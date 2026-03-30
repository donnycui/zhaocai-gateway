from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

import httpx

from zhaocai_gateway.db.store import SQLiteStore


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class GatewayAccountService:
    """Gateway upstream-account service for the modular provider center."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list(self) -> list[dict]:
        return [asdict(account) for account in self.store.list_gateway_upstream_accounts()]

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

    def test_connection(self, account_id: int) -> dict:
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

    @staticmethod
    def _infer_family(item: dict, model_id: str) -> str | None:
        owned_by = item.get("owned_by")
        if isinstance(owned_by, str) and owned_by.strip():
            return owned_by.strip()
        prefix, _, _ = model_id.partition("/")
        return prefix.strip() or None
