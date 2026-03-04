from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider_type: str = Field(default="openai", min_length=1, max_length=64)
    base_url: str = Field(min_length=1, max_length=512)
    auth_scheme: str = Field(default="bearer", min_length=1, max_length=32)
    api_key: str = Field(default="", max_length=4096)
    secret_ref: str = Field(default="", max_length=256)
    enabled: bool = True
    extra_headers: Dict[str, str] = Field(default_factory=dict)


class ProviderUpdate(BaseModel):
    provider_type: Optional[str] = Field(default=None, min_length=1, max_length=64)
    base_url: Optional[str] = Field(default=None, min_length=1, max_length=512)
    auth_scheme: Optional[str] = Field(default=None, min_length=1, max_length=32)
    api_key: Optional[str] = Field(default=None, max_length=4096)
    secret_ref: Optional[str] = Field(default=None, max_length=256)
    enabled: Optional[bool] = None
    extra_headers: Optional[Dict[str, str]] = None


class ModelCreate(BaseModel):
    provider_id: int
    upstream_model: str = Field(min_length=1, max_length=200)
    alias: str = Field(min_length=1, max_length=200)
    enabled: bool = True
    capabilities: List[str] = Field(default_factory=list)


class ModelUpdate(BaseModel):
    upstream_model: Optional[str] = Field(default=None, min_length=1, max_length=200)
    alias: Optional[str] = Field(default=None, min_length=1, max_length=200)
    enabled: Optional[bool] = None
    capabilities: Optional[List[str]] = None


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)


class ProfileBindingUpdate(BaseModel):
    model_ids: List[int] = Field(default_factory=list)


class NodeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    profile_id: int
    sync_mode: str = Field(default="pull", min_length=1, max_length=32)
    active: bool = True


class NodeUpdate(BaseModel):
    profile_id: Optional[int] = None
    sync_mode: Optional[str] = Field(default=None, min_length=1, max_length=32)
    active: Optional[bool] = None

