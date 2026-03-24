from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppRuntimeConfig:
    title: str = "Zhaocai Gateway"
    description: str = "AI Provider Gateway + OpenClaw Control Plane"
    version: str = "2.0.0"


def load_runtime_config() -> AppRuntimeConfig:
    return AppRuntimeConfig(
        title=os.getenv("ZHAOCAI_APP_TITLE", "Zhaocai Gateway"),
        description=os.getenv(
            "ZHAOCAI_APP_DESCRIPTION",
            "AI Provider Gateway + OpenClaw Control Plane",
        ),
        version=os.getenv("ZHAOCAI_APP_VERSION", "2.0.0"),
    )
