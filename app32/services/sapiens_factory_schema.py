from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


FactoryChangeType = Literal[
    "create",
    "alter",
    "activate",
    "deactivate",
    "fix",
    "refactor",
    "diagnose",
]

FactoryTargetLayer = Literal[
    "service",
    "tool_contract",
    "rest_mcp",
    "workflow",
    "ui_sapiens",
]

FactoryExecutionMode = Literal["diagnose", "plan", "prepare", "execute_controlled"]
FactoryUrgency = Literal["low", "medium", "high", "critical"]


class SapiensFactoryChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_text: str = Field(min_length=10, max_length=4000)
    change_type: Optional[FactoryChangeType] = None
    target_layers: list[FactoryTargetLayer] = Field(default_factory=list)
    target_object: Optional[str] = Field(default=None, min_length=2, max_length=255)
    domain: Optional[str] = Field(default=None, min_length=2, max_length=120)
    desired_outcome: Optional[str] = Field(default=None, max_length=2000)
    execution_mode: FactoryExecutionMode = "diagnose"
    urgency: FactoryUrgency = "medium"
    company_id: Optional[int] = Field(default=None, gt=0)
    metadata: dict[str, str] = Field(default_factory=dict)


class FactoryActorContext(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    user_id: Optional[int] = Field(default=None, gt=0)
    role: Optional[str] = Field(default=None, min_length=2, max_length=80)
    channel: str = Field(default="web", min_length=2, max_length=32)
    company_id: Optional[int] = Field(default=None, gt=0)
    accessible_company_ids: list[int] = Field(default_factory=list)


class ExternalLLMFactorySessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    client_name: str = Field(min_length=2, max_length=120)
    provider: str = Field(min_length=2, max_length=120)
    requested_surface: str = Field(default="factory", min_length=2, max_length=40)
    user_id: Optional[int] = Field(default=None, gt=0)
    company_id: Optional[int] = Field(default=None, gt=0)
    role: Optional[str] = Field(default=None, min_length=2, max_length=80)
    use_case: str = Field(min_length=5, max_length=1000)
    metadata: dict[str, str] = Field(default_factory=dict)
