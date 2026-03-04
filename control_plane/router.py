from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Tuple

from fastapi import APIRouter, Header, HTTPException, Response, status
from fastapi.responses import HTMLResponse, JSONResponse

from control_plane.compiler import compile_openclaw_config
from control_plane.models import (
    ModelCreate,
    ModelUpdate,
    NodeCreate,
    NodeUpdate,
    ProfileBindingUpdate,
    ProfileCreate,
    ProviderCreate,
    ProviderUpdate,
)
from control_plane.store import SQLiteControlPlaneStore


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    prefix = "bearer "
    if authorization.lower().startswith(prefix):
        return authorization[len(prefix) :].strip()
    return ""


def _handle_data_error(exc: Exception) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, sqlite3.IntegrityError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


def create_control_plane_routers(
    store: SQLiteControlPlaneStore,
    admin_token: str,
) -> Tuple[APIRouter, APIRouter]:
    api_router = APIRouter(prefix="/control/v1", tags=["control-plane"])
    panel_router = APIRouter(tags=["control-panel"])

    def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
        if not admin_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="ZHAOCAI_ADMIN_TOKEN is not configured",
            )
        if x_admin_token != admin_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")

    def require_node_or_admin(
        node_id: int,
        authorization: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> None:
        if admin_token and x_admin_token == admin_token:
            return
        pull_token = _extract_bearer_token(authorization)
        if not pull_token or not store.verify_node_token(node_id, pull_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid node token")

    @api_router.get("/providers")
    def list_providers(x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        return {"providers": store.list_providers(include_secrets=False)}

    @api_router.post("/providers")
    def create_provider(payload: ProviderCreate, x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            provider = store.create_provider(payload.model_dump())
            return {"provider": provider}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.patch("/providers/{provider_id}")
    def patch_provider(
        provider_id: int,
        payload: ProviderUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            provider = store.update_provider(provider_id, payload.model_dump(exclude_none=True))
            return {"provider": provider}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.get("/models")
    def list_models(x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        return {"models": store.list_models()}

    @api_router.post("/models")
    def create_model(payload: ModelCreate, x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            model = store.create_model(payload.model_dump())
            return {"model": model}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.patch("/models/{model_id}")
    def patch_model(
        model_id: int,
        payload: ModelUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            model = store.update_model(model_id, payload.model_dump(exclude_none=True))
            return {"model": model}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.get("/profiles")
    def list_profiles(x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        return {"profiles": store.list_profiles()}

    @api_router.post("/profiles")
    def create_profile(payload: ProfileCreate, x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            profile = store.create_profile(payload.model_dump())
            return {"profile": profile}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.post("/profiles/{profile_id}/bindings")
    def set_profile_bindings(
        profile_id: int,
        payload: ProfileBindingUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            profile = store.set_profile_bindings(profile_id, payload.model_ids)
            return {"profile": profile}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.get("/nodes")
    def list_nodes(x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        return {"nodes": store.list_nodes()}

    @api_router.post("/nodes")
    def create_node(payload: NodeCreate, x_admin_token: str | None = Header(default=None)) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            node = store.create_node(payload.model_dump())
            return {"node": node}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.patch("/nodes/{node_id}")
    def patch_node(
        node_id: int,
        payload: NodeUpdate,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            node = store.update_node(node_id, payload.model_dump(exclude_none=True))
            return {"node": node}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.get("/nodes/{node_id}/openclaw-json")
    def get_node_openclaw_json(
        node_id: int,
        if_none_match: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> Response:
        require_node_or_admin(node_id=node_id, authorization=authorization, x_admin_token=x_admin_token)
        try:
            payload = compile_openclaw_config(store, node_id)
            version_row, _ = store.save_node_config_version(node_id, payload)
            etag = version_row["etag"]
            headers = {
                "ETag": etag,
                "X-Config-Version": str(version_row["version"]),
            }
            if if_none_match and if_none_match.strip() == etag:
                return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
            return JSONResponse(content=version_row["payload"], headers=headers)
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.post("/nodes/{node_id}/sync-token/rotate")
    def rotate_node_sync_token(
        node_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            pull_token = store.rotate_node_token(node_id)
            return {"node_id": node_id, "pull_token": pull_token}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @api_router.get("/nodes/{node_id}/versions")
    def list_node_versions(
        node_id: int,
        x_admin_token: str | None = Header(default=None),
    ) -> Dict[str, Any]:
        require_admin(x_admin_token)
        try:
            store.get_node(node_id, include_token_hash=False)
            versions = store.list_node_versions(node_id)
            return {"node_id": node_id, "versions": versions}
        except Exception as exc:  # noqa: BLE001
            _handle_data_error(exc)
            raise

    @panel_router.get("/control", response_class=HTMLResponse)
    def control_panel() -> HTMLResponse:
        panel_path = Path(__file__).parent / "static" / "control_panel.html"
        if not panel_path.exists():
            raise HTTPException(status_code=404, detail="Control panel UI is missing")
        return HTMLResponse(panel_path.read_text(encoding="utf-8"))

    @panel_router.get("/health", response_class=HTMLResponse)
    def health_panel() -> HTMLResponse:
        health_path = Path(__file__).parent / "static" / "health.html"
        if not health_path.exists():
            raise HTTPException(status_code=404, detail="Health panel UI is missing")
        return HTMLResponse(health_path.read_text(encoding="utf-8"))

    return api_router, panel_router

