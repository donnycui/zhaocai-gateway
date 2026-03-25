from __future__ import annotations

from typing import Any

import httpx


class AgentClient:
    def __init__(self, server_url: str, timeout: float = 30.0) -> None:
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout

    def register(self, *, pairing_token: str, hostname: str, platform: str) -> dict[str, Any]:
        response = httpx.post(
            f"{self.server_url}/agent/v1/register",
            json={
                "pairing_token": pairing_token,
                "hostname": hostname,
                "platform": platform,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_config_meta(self, *, sync_token: str) -> dict[str, Any]:
        response = httpx.get(
            f"{self.server_url}/agent/v1/config/meta",
            headers={"Authorization": f"Bearer {sync_token}"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_config(self, *, sync_token: str) -> dict[str, Any]:
        response = httpx.get(
            f"{self.server_url}/agent/v1/config",
            headers={"Authorization": f"Bearer {sync_token}"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def report_applied(self, *, sync_token: str, version: int, status: str = "applied") -> dict[str, Any]:
        response = httpx.post(
            f"{self.server_url}/agent/v1/config/applied",
            headers={"Authorization": f"Bearer {sync_token}"},
            json={"version": version, "status": status},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
