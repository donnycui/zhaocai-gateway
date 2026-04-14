from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from zhaocai_gateway.db.store import SQLiteStore


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class GatewayAliasService:
    """Gateway alias service for stable model names and ordered target mappings."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list_aliases(self) -> list[dict]:
        return [asdict(alias) for alias in self.store.list_gateway_aliases()]

    def create_alias(
        self,
        *,
        alias_key: str,
        display_name: str,
        alias_type: str,
        visibility: str,
        notes: str,
    ) -> dict:
        alias = self.store.create_gateway_alias(
            alias_key=alias_key.strip(),
            display_name=display_name.strip(),
            alias_type=alias_type.strip(),
            enabled=True,
            visibility=visibility.strip() or "project",
            notes=notes.strip(),
        )
        return asdict(alias)

    def update_alias(
        self,
        alias_id: int,
        *,
        alias_key: str,
        display_name: str,
        alias_type: str,
        enabled: bool,
        visibility: str,
        notes: str,
    ) -> dict:
        self._require_alias(alias_id)
        alias = self.store.update_gateway_alias(
            alias_id,
            alias_key=alias_key.strip(),
            display_name=display_name.strip(),
            alias_type=alias_type.strip(),
            enabled=enabled,
            visibility=visibility.strip() or "project",
            notes=notes.strip(),
        )
        return asdict(alias)

    def delete_alias(self, alias_id: int) -> None:
        self._require_alias(alias_id)
        self.store.delete_gateway_alias(alias_id)

    def list_targets(self, alias_id: int) -> list[dict]:
        self._require_alias(alias_id)
        return [asdict(target) for target in self.store.list_gateway_alias_targets(alias_id)]

    def replace_targets(self, alias_id: int, *, targets: list[dict]) -> list[dict]:
        self._require_alias(alias_id)
        normalized_targets: list[dict] = []
        for target in targets:
            account_id = int(target["account_id"])
            model_id = int(target["model_id"])
            account = self.store.get_gateway_upstream_account(account_id)
            if account is None:
                raise ValueError(f"Gateway account {account_id} not found")

            model = next((item for item in self.store.list_gateway_models(account_id) if item.id == model_id), None)
            if model is None:
                raise ValueError(f"Gateway model {model_id} not found for account {account_id}")

            normalized_targets.append(
                {
                    "account_id": account_id,
                    "model_id": model_id,
                    "priority": int(target["priority"]),
                    "enabled": bool(target["enabled"]),
                    "fallback_on_timeout": bool(target["fallback_on_timeout"]),
                    "fallback_on_5xx": bool(target["fallback_on_5xx"]),
                    "fallback_on_429": bool(target["fallback_on_429"]),
                    "cooldown_seconds": int(target["cooldown_seconds"]),
                }
            )

        ordered = sorted(normalized_targets, key=lambda item: (item["priority"], item["account_id"], item["model_id"]))
        return [asdict(target) for target in self.store.replace_gateway_alias_targets(alias_id, targets=ordered)]

    def list_models(self) -> list[dict]:
        return [asdict(model) for model in self.store.list_gateway_models()]

    def invoke_chat_completions(self, alias_key: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return self._invoke_alias_request(alias_key, "/chat/completions", payload)

    def invoke_responses(self, alias_key: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        return self._invoke_alias_request(alias_key, "/responses", payload)

    def _require_alias(self, alias_id: int) -> None:
        if self.store.get_gateway_alias(alias_id) is None:
            raise ValueError(f"Gateway alias {alias_id} not found")

    def _invoke_alias_request(
        self,
        alias_key: str,
        path: str,
        payload: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
        alias = self.store.get_gateway_alias_by_key(alias_key)
        if alias is None:
            raise ValueError(f"Gateway alias '{alias_key}' not found")

        targets = self.store.list_gateway_alias_targets(alias.id)
        if not targets:
            raise RuntimeError(f"Gateway alias '{alias_key}' has no configured targets")

        last_error_status = 502
        last_error_payload: dict[str, Any] = {"error": {"message": f"No available target for alias '{alias_key}'"}}
        now = datetime.now(UTC)

        for target in targets:
            if not target.enabled:
                continue

            account = self.store.get_gateway_upstream_account(target.account_id)
            model = self.store.get_gateway_model(target.model_id)
            if account is None or model is None or not account.enabled or not model.enabled:
                continue

            if account.cooldown_until:
                try:
                    cooldown_until = datetime.fromisoformat(account.cooldown_until.replace("Z", "+00:00"))
                    if cooldown_until > now:
                        continue
                except ValueError:
                    pass

            request_payload = dict(payload)
            request_payload["model"] = model.upstream_model

            try:
                response = httpx.request(
                    "POST",
                    self._build_url(account.base_url, path),
                    headers=self._build_headers(account.auth_type, account.api_key_encrypted),
                    json=request_payload,
                    timeout=30.0,
                )
            except httpx.RequestError as exc:
                last_error_payload = {"error": {"message": str(exc)}}
                last_error_status = 502
                self._mark_target_failed(account.id, target.cooldown_seconds, health_status="ERROR")
                continue

            payload_json = self._safe_json(response)
            if response.status_code == 429 or response.status_code >= 500:
                last_error_status = response.status_code
                last_error_payload = payload_json
                self._mark_target_failed(account.id, target.cooldown_seconds, health_status="DEGRADED")
                if self._should_failover(response.status_code, target):
                    continue
                return response.status_code, payload_json

            if 400 <= response.status_code < 500:
                self.store.update_gateway_upstream_account_status(
                    account.id,
                    health_status="HEALTHY",
                    last_checked_at=_utc_now_iso(),
                    cooldown_until=None,
                )
                return response.status_code, payload_json

            self.store.update_gateway_upstream_account_status(
                account.id,
                health_status="HEALTHY",
                last_checked_at=_utc_now_iso(),
                cooldown_until=None,
            )
            return response.status_code, payload_json

        return last_error_status, last_error_payload

    def _mark_target_failed(self, account_id: int, cooldown_seconds: int, *, health_status: str) -> None:
        cooldown_until = (
            datetime.now(UTC) + timedelta(seconds=max(0, cooldown_seconds))
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self.store.update_gateway_upstream_account_status(
            account_id,
            health_status=health_status,
            last_checked_at=_utc_now_iso(),
            cooldown_until=cooldown_until,
        )

    @staticmethod
    def _should_failover(status_code: int, target: Any) -> bool:
        if status_code == 429:
            return bool(target.fallback_on_429)
        if status_code >= 500:
            return bool(target.fallback_on_5xx)
        return False

    @staticmethod
    def _build_headers(auth_type: str, api_key: str) -> dict[str, str]:
        normalized = (auth_type or "none").strip().lower()
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if normalized == "x-api-key":
            if api_key:
                headers["x-api-key"] = api_key
            return headers
        if normalized == "basic":
            if api_key:
                headers["Authorization"] = f"Basic {api_key}"
            return headers
        if normalized == "passcode":
            if api_key:
                headers["x-passcode"] = api_key
            return headers
        if normalized == "bearer":
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            return headers
        return headers

    @staticmethod
    def _build_url(base_url: str, path: str) -> str:
        normalized_base = base_url.strip().rstrip("/")
        normalized_path = path if path.startswith("/") else f"/{path}"
        if normalized_base.endswith(normalized_path):
            return normalized_base
        return f"{normalized_base}{normalized_path}"

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            text = response.text.strip()
            return {"error": {"message": text or f"HTTP {response.status_code}"}}
        if isinstance(payload, dict):
            return payload
        return {"data": payload}
