from __future__ import annotations

import hashlib

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from zhaocai_gateway.db.store import SQLiteStore
from zhaocai_gateway.services import ConfigCompilerService, PairingService


class RegisterRequest(BaseModel):
    pairing_token: str = Field(min_length=1)
    hostname: str = Field(min_length=1)
    platform: str = Field(min_length=1)


class HeartbeatRequest(BaseModel):
    sync_token: str = Field(min_length=1)


class ConfigAppliedRequest(BaseModel):
    version: int
    status: str = Field(min_length=1)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        return ""
    prefix = "bearer "
    if authorization.lower().startswith(prefix):
        return authorization[len(prefix) :].strip()
    return ""


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_agent_router(store: SQLiteStore) -> APIRouter:
    pairing_service = PairingService(store)
    compiler_service = ConfigCompilerService(store)
    router = APIRouter(prefix="/agent/v1", tags=["agent"])

    @router.post("/register")
    def register(payload: RegisterRequest) -> dict:
        result = pairing_service.register_device(
            pairing_token=payload.pairing_token,
            hostname=payload.hostname,
            platform=payload.platform,
        )
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired pairing token",
            )
        return result

    @router.post("/heartbeat")
    def heartbeat(payload: HeartbeatRequest) -> dict:
        result = pairing_service.heartbeat(sync_token=payload.sync_token)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid sync token",
            )
        return result

    @router.get("/config/meta")
    def get_config_meta(authorization: str | None = Header(default=None)) -> dict:
        raw_token = _extract_bearer_token(authorization)
        device = store.get_device_by_sync_token_hash(_hash_token(raw_token))
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid sync token",
            )
        snapshot = compiler_service.create_snapshot(device.id)
        return {"device_id": device.id, "version": snapshot.version, "etag": snapshot.etag}

    @router.get("/config")
    def get_config(authorization: str | None = Header(default=None)) -> dict:
        raw_token = _extract_bearer_token(authorization)
        device = store.get_device_by_sync_token_hash(_hash_token(raw_token))
        if device is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid sync token",
            )
        snapshot = compiler_service.get_or_create_latest_snapshot(device.id)
        return snapshot.payload_json

    @router.post("/config/applied")
    def post_config_applied(
        payload: ConfigAppliedRequest,
        authorization: str | None = Header(default=None),
    ) -> dict:
        raw_token = _extract_bearer_token(authorization)
        report = store.record_applied_config(
            sync_token_hash=_hash_token(raw_token),
            version=payload.version,
            status=payload.status,
        )
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid sync token",
            )
        return {"ok": True, "device_id": report.device_id, "version": report.version}

    return router
