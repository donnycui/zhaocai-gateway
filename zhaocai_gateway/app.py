from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Any, Callable, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zhaocai_gateway.api import create_admin_router, create_agent_router
from zhaocai_gateway.config import load_runtime_config
from zhaocai_gateway.db.store import SQLiteStore


Lifespan = Optional[Callable[[FastAPI], AbstractAsyncContextManager[Any]]]


def _default_cors_origins() -> list[str]:
    return [
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:4174",
        "http://127.0.0.1:4174",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:4015",
        "http://127.0.0.1:4015",
    ]


def create_app(
    *,
    title: str | None = None,
    description: str | None = None,
    version: str | None = None,
    lifespan: Lifespan = None,
    register_defaults: bool = True,
    db_path: str = ":memory:",
    cors_origins: list[str] | None = None,
) -> FastAPI:
    runtime_config = load_runtime_config()
    store = SQLiteStore(db_path)
    store.init_schema()
    app = FastAPI(
        title=title or runtime_config.title,
        description=description or runtime_config.description,
        version=version or runtime_config.version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or _default_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.store = store
    app.include_router(create_admin_router(store))
    app.include_router(create_agent_router(store))

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
