from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from zhaocai_gateway.db.store import SQLiteStore


class GatewayUsageService:
    """Aggregated gateway model usage reporting."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list_model_usage(
        self,
        *,
        window: str = "24h",
        account_id: int | None = None,
        model_id: int | None = None,
    ) -> dict:
        hours = self._parse_window_hours(window)
        since_iso = (
            datetime.now(timezone.utc) - timedelta(hours=hours)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        items = [
            asdict(item)
            for item in self.store.list_gateway_model_usage_summaries(
                since_iso=since_iso,
                account_id=account_id,
                model_id=model_id,
            )
        ]
        return {
            "window": window,
            "hours": hours,
            "items": items,
        }

    @staticmethod
    def _parse_window_hours(window: str) -> int:
        normalized = (window or "24h").strip().lower()
        if normalized == "7d":
            return 24 * 7
        return 24
