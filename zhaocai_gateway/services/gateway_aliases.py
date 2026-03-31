from __future__ import annotations

from dataclasses import asdict

from zhaocai_gateway.db.store import SQLiteStore


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
        display_name: str,
        enabled: bool,
        visibility: str,
        notes: str,
    ) -> dict:
        self._require_alias(alias_id)
        alias = self.store.update_gateway_alias(
            alias_id,
            display_name=display_name.strip(),
            enabled=enabled,
            visibility=visibility.strip() or "project",
            notes=notes.strip(),
        )
        return asdict(alias)

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

    def _require_alias(self, alias_id: int) -> None:
        if self.store.get_gateway_alias(alias_id) is None:
            raise ValueError(f"Gateway alias {alias_id} not found")
