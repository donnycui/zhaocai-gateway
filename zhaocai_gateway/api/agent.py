from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from zhaocai_gateway.db.store import SQLiteStore
from zhaocai_gateway.services import PairingService


class RegisterRequest(BaseModel):
    pairing_token: str = Field(min_length=1)
    hostname: str = Field(min_length=1)
    platform: str = Field(min_length=1)


class HeartbeatRequest(BaseModel):
    sync_token: str = Field(min_length=1)


def create_agent_router(store: SQLiteStore) -> APIRouter:
    pairing_service = PairingService(store)
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

    return router
