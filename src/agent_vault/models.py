from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ProviderType = Literal["upstream", "gateway", "local", "free_tier"]


class ProviderConfig(BaseModel):
    vault_key: str | None = None
    env_var: str | None = None
    type: ProviderType
    endpoint: str | None = None
    priority: int | None = None


class Manifest(BaseModel):
    version: str = Field(min_length=1)
    identity: str | None = None
    providers: dict[str, ProviderConfig]
