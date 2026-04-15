from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class IntegrationAdminUpsertSchema(_StrictModel):
    id: str | None = Field(default=None, min_length=1, max_length=160)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    type: str = Field(min_length=1, max_length=40)
    provider: str | None = Field(default=None, min_length=1, max_length=80)
    auth_type: str | None = Field(default=None, min_length=1, max_length=80)
    config: dict[str, Any] = Field(default_factory=dict)


class LegacyIntegrationSaveSchema(_StrictModel):
    service: str = Field(min_length=1, max_length=40)
    config: dict[str, Any] = Field(default_factory=dict)
