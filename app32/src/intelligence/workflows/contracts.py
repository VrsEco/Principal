from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkflowFieldDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    required: bool = True


class WorkflowDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    title: str
    action_key: str
    description: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    required_fields: List[WorkflowFieldDefinition] = Field(default_factory=list)
    confirmation_template: Optional[str] = None
    execution_template: Optional[str] = None
    sort_order: int = 0
    company_id: Optional[int] = None
    source_option_id: Optional[int] = None


class WorkflowMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow: WorkflowDefinition
    score: int
    reasons: List[str] = Field(default_factory=list)


class WorkflowDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    company_id: Optional[int] = None
    channel: str = "web"
    top_k: int = 5


class WorkflowDiscoveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: WorkflowDiscoveryRequest
    matches: List[WorkflowMatch] = Field(default_factory=list)

    @property
    def selected(self) -> Optional[WorkflowDefinition]:
        if not self.matches:
            return None
        return self.matches[0].workflow
