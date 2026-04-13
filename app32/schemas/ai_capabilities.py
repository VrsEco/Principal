from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AICapabilityGrantUpsertSchema(_StrictModel):
    capability_key: str = Field(min_length=1, max_length=160)
    scope_type: Literal["global", "company", "user", "role"]
    company_id: int | None = None
    user_id: int | None = None
    role_id: int | None = None
    is_enabled: bool = True
    channels: list[str] = Field(default_factory=list)
    notes: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope_type == "company" and not self.company_id:
            raise ValueError("company_id é obrigatório para scope_type=company.")
        if self.scope_type == "user":
            if not self.company_id or not self.user_id:
                raise ValueError("company_id e user_id são obrigatórios para scope_type=user.")
        if self.scope_type == "role":
            if not self.company_id or not self.role_id:
                raise ValueError("company_id e role_id são obrigatórios para scope_type=role.")
        if self.scope_type == "global" and any([self.company_id, self.user_id, self.role_id]):
            raise ValueError("Escopo global não aceita company_id, user_id ou role_id.")
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until deve ser maior ou igual a valid_from.")
        return self


class AICapabilityCompanySettingsUpsertSchema(_StrictModel):
    capability_key: str = Field(min_length=1, max_length=160)
    company_id: int
    is_enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)


class AICapabilityRolloutUpdateSchema(_StrictModel):
    capability_key: str = Field(min_length=1, max_length=160)
    rollout_status: Literal["draft", "internal_test", "pilot", "active", "paused", "blocked"]
    status: Literal["draft", "pilot", "active", "paused", "retired"] | None = None
    notes: str | None = None


class AICapabilityAuditLogCreateSchema(_StrictModel):
    capability_key: str = Field(min_length=1, max_length=160)
    event_type: str = Field(min_length=1, max_length=60)
    result: Literal["success", "warning", "danger", "neutral"] = "success"
    company_id: int | None = None
    user_id: int | None = None
    channel: str | None = Field(default=None, max_length=50)
    surface: str | None = Field(default=None, max_length=40)
    detail: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
