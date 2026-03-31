from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from zhaocai_gateway.api import create_admin_router, create_agent_router, create_runtime_router
from zhaocai_gateway.config import load_runtime_config, load_server_config
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
    static_dir: str | Path | None = None,
    admin_token: str = "",
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
    app.include_router(create_admin_router(store, admin_token=admin_token))
    app.include_router(create_agent_router(store))
    app.include_router(create_runtime_router(store))

    resolved_static_dir = Path(static_dir).resolve() if static_dir is not None else None
    has_static_index = bool(
        resolved_static_dir
        and resolved_static_dir.exists()
        and (resolved_static_dir / "index.html").exists()
    )
    if resolved_static_dir and resolved_static_dir.exists():
        assets_dir = resolved_static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    if register_defaults:

        async def render_index_or_status():
            if has_static_index and resolved_static_dir is not None:
                return FileResponse(resolved_static_dir / "index.html")
            return {
                "name": app.title,
                "version": app.version,
                "status": "running",
            }

        @app.get("/")
        async def root():
            return await render_index_or_status()

        @app.get("/control")
        @app.get("/control/")
        async def control_root():
            return await render_index_or_status()

        @app.get("/api/health")
        @app.get("/health")
        async def health(request: Request) -> dict[str, Any]:
            del request
            return {"status": "healthy"}

    return app


def create_default_app() -> FastAPI:
    runtime_config = load_runtime_config()
    server_config = load_server_config()
    return create_app(
        title=runtime_config.title,
        description=runtime_config.description,
        version=runtime_config.version,
        db_path=server_config.db_path,
        static_dir=server_config.web_dist_path,
        admin_token=server_config.admin_token,
    )
