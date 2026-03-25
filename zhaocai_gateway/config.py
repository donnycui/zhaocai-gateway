from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppRuntimeConfig:
    title: str = "Zhaocai Gateway"
    description: str = "AI Provider Gateway + OpenClaw Control Plane"
    version: str = "2.0.0"


@dataclass(frozen=True)
class AppServerConfig:
    host: str
    port: int
    db_path: str
    web_dist_path: str


def load_runtime_config() -> AppRuntimeConfig:
    return AppRuntimeConfig(
        title=os.getenv("ZHAOCAI_APP_TITLE", "Zhaocai Gateway"),
        description=os.getenv(
            "ZHAOCAI_APP_DESCRIPTION",
            "AI Provider Gateway + OpenClaw Control Plane",
        ),
        version=os.getenv("ZHAOCAI_APP_VERSION", "2.0.0"),
    )


def _resolve_sqlite_db_path(raw_value: str) -> str:
    if raw_value.startswith("sqlite:///"):
        return raw_value.replace("sqlite:///", "", 1)
    return raw_value


def load_server_config() -> AppServerConfig:
    repo_root = Path(__file__).resolve().parents[1]
    default_dist = repo_root / "web" / "dist"
    return AppServerConfig(
        host=os.getenv("ZHAOCAI_HOST", "0.0.0.0"),
        port=int(os.getenv("ZHAOCAI_PORT", "8000")),
        db_path=_resolve_sqlite_db_path(
            os.getenv("ZHAOCAI_CONTROL_DB", "sqlite:///./data/control_plane.db")
        ),
        web_dist_path=os.getenv("ZHAOCAI_WEB_DIST", str(default_dist)),
    )
