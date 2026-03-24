from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Any, Callable, Optional

from fastapi import FastAPI

from zhaocai_gateway.config import load_runtime_config


Lifespan = Optional[Callable[[FastAPI], AbstractAsyncContextManager[Any]]]


def create_app(
    *,
    title: str | None = None,
    description: str | None = None,
    version: str | None = None,
    lifespan: Lifespan = None,
    register_defaults: bool = True,
) -> FastAPI:
    runtime_config = load_runtime_config()
    app = FastAPI(
        title=title or runtime_config.title,
        description=description or runtime_config.description,
        version=version or runtime_config.version,
        lifespan=lifespan,
    )

    if register_defaults:

        @app.get("/")
        async def root() -> dict[str, str]:
            return {
                "name": app.title,
                "version": app.version,
                "status": "running",
            }

        @app.get("/api/health")
        @app.get("/health")
        async def health() -> dict[str, str]:
            return {"status": "healthy"}

    return app
