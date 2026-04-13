from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkflowRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=255)
    business_domain: str = Field(min_length=2, max_length=120)
    objective: str = Field(min_length=10, max_length=3000)
    problem_statement: str = Field(min_length=10, max_length=3000)
    target_users: str = Field(min_length=3, max_length=500)
    desired_channels: str = Field(min_length=3, max_length=500)
    expected_result: str = Field(min_length=10, max_length=3000)
    user_examples: str = Field(min_length=10, max_length=3000)
    known_inputs: str | None = Field(default=None, max_length=3000)
    systems_involved: str | None = Field(default=None, max_length=1000)
    dependencies: str | None = Field(default=None, max_length=1000)
    responsible_area: str | None = Field(default=None, max_length=255)
    usage_frequency: str | None = Field(default=None, max_length=255)
    execution_profile: str = Field(default="action", pattern="^(query|action|hybrid)$")
    sensitivity_level: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    requires_human_confirmation: str = Field(default="yes", pattern="^(yes|no|unknown)$")
    data_summary: str | None = Field(default=None, max_length=3000)
    source_channel: str = Field(default="ui_workflows_catalog", min_length=2, max_length=64)
    urgency: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    notes: str | None = Field(default=None, max_length=3000)
