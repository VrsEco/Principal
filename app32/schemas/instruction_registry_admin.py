from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class InstructionRegistryEntryUpsertSchema(_StrictModel):
    scope_type: Literal["global", "runtime", "agent", "tenant_override"]
    runtime_profile: str = Field(min_length=3, max_length=80)
    agent_key: str | None = Field(default=None, max_length=80)
    harness_key: str | None = Field(default=None, max_length=120)
    company_id: int | None = None
    channel: Literal["stable", "beta", "hotfix"] = "stable"
    environment: Literal["production", "staging", "development"] = "production"
    status: Literal["active", "paused", "draft", "archived"] = "active"
    rollout_status: Literal["draft", "internal_test", "pilot", "active", "paused", "blocked"] = "active"
    entry_version: str = Field(min_length=2, max_length=40, default="v1")
    cache_ttl_seconds: int = Field(default=1800, ge=60, le=86400)
    payload: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class InstructionRegistryInvalidateSchema(_StrictModel):
    entry_id: int | None = None
    runtime_profile: str | None = Field(default=None, max_length=80)
    company_id: int | None = None
    channel: Literal["stable", "beta", "hotfix"] | None = None
    reason: str = Field(min_length=8, max_length=240)


class InstructionRegistryPromoteSchema(_StrictModel):
    source_entry_id: int = Field(ge=1)
    target_channel: Literal["stable", "beta", "hotfix"]
    target_environment: Literal["production", "staging", "development"] | None = None
    target_status: Literal["active", "paused", "draft", "archived"] = "active"
    target_rollout_status: Literal["draft", "internal_test", "pilot", "active", "paused", "blocked"] = "active"
    entry_version: str | None = Field(default=None, min_length=2, max_length=40)
    notes: str | None = None
