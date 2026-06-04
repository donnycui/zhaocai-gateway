from __future__ import annotations

from typing import Any

import httpx

from agent.config import AgentTarget


class AgentClient:
    def __init__(
        self,
        server_url: str,
        timeout: float = 30.0,
        *,
        target: AgentTarget = "openclaw",
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.target = target

    @property
    def _base_path(self) -> str:
        if self.target == "hermes":
            return "/hermes-agent/v1"
        return "/agent/v1"

    def register(self, *, pairing_token: str, hostname: str, platform: str) -> dict[str, Any]:
        response = httpx.post(
            f"{self.server_url}{self._base_path}/register",
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
            f"{self.server_url}{self._base_path}/config/meta",
            headers={"Authorization": f"Bearer {sync_token}"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_config(self, *, sync_token: str) -> dict[str, Any]:
        response = httpx.get(
            f"{self.server_url}{self._base_path}/config",
            headers={"Authorization": f"Bearer {sync_token}"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def report_applied(self, *, sync_token: str, version: int, status: str = "applied") -> dict[str, Any]:
        response = httpx.post(
            f"{self.server_url}{self._base_path}/config/applied",
            headers={"Authorization": f"Bearer {sync_token}"},
            json={"version": version, "status": status},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
