from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


T = TypeVar("T")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MCPResponseMeta(_StrictModel):
    """Metadados padronizados para envelopes MCP do APP32."""

    schema_version: str = Field(default="app32.mcp.contract.v1", min_length=1, max_length=80)
    domain: str = Field(min_length=1, max_length=80)
    operation: str = Field(min_length=1, max_length=120)
    scope: str = Field(default="mcp_user", min_length=1, max_length=40)
    company_id: int | None = Field(default=None, gt=0)
    user_id: int | None = Field(default=None, gt=0)
    actor_role: str | None = Field(default=None, min_length=1, max_length=40)
    capability: str | None = Field(default=None, min_length=1, max_length=120)
    request_id: str | None = Field(default=None, min_length=1, max_length=120)
    trace_id: str | None = Field(default=None, min_length=1, max_length=120)
    tenant_safe: bool = True
    human_gate_required: bool = False
    permissions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def _ensure_timezone(self):
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at deve ser timezone-aware.")
        return self


class MCPErrorDetail(_StrictModel):
    code: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=240)
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False


class MCPSuccessEnvelope(_StrictModel, Generic[T]):
    success: bool = True
    message: str | None = Field(default=None, min_length=1, max_length=240)
    data: T
    meta: MCPResponseMeta

    @model_validator(mode="after")
    def _ensure_success_flag(self):
        if self.success is not True:
            raise ValueError("Envelopes de sucesso devem ter success=True.")
        return self


class MCPErrorEnvelope(_StrictModel):
    success: bool = False
    message: str | None = Field(default=None, min_length=1, max_length=240)
    error: MCPErrorDetail
    meta: MCPResponseMeta | None = None

    @model_validator(mode="after")
    def _ensure_error_flag(self):
        if self.success is not False:
            raise ValueError("Envelopes de erro devem ter success=False.")
        return self
