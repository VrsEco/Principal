from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

IntentKind = Literal["query", "action", "analysis", "approval"]
EntityType = Literal[
    "project_task",
    "process_instance",
    "meeting",
    "agent_action",
    "collaborator",
    "project",
    "company",
    "mixed",
]
SelectionMode = Literal["explicit", "implicit", "assisted", "multi_company", "all_accessible", "none"]
DateMode = Literal["none", "today", "week", "month", "custom_range", "relative"]
OutputFormat = Literal["executive_summary", "detailed_list", "audit_report", "kanban", "confirmation"]
ResolutionStatus = Literal["ready", "missing_fields", "ambiguous", "invalid"]


class CompanyScopeForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_ids: List[int] = Field(default_factory=list)
    company_labels: List[str] = Field(default_factory=list)
    selection_mode: SelectionMode = "none"
    requires_disambiguation: bool = False
    multi_tenant_guard: bool = True


class SubjectScopeForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    responsible_ids: List[int] = Field(default_factory=list)
    responsible_names: List[str] = Field(default_factory=list)
    project_ids: List[int] = Field(default_factory=list)
    project_codes: List[str] = Field(default_factory=list)
    task_ids: List[int] = Field(default_factory=list)
    task_codes: List[str] = Field(default_factory=list)
    process_ids: List[int] = Field(default_factory=list)
    process_codes: List[str] = Field(default_factory=list)


class FilterScopeForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = None
    date_mode: DateMode = "none"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    period_label: Optional[str] = None
    entity_hint: Optional[EntityType] = None
    limit: Optional[int] = None
    sort: Optional[str] = None
    include_archived: bool = False


class ActionScopeForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Optional[str] = None
    target_ids: List[int] = Field(default_factory=list)
    target_codes: List[str] = Field(default_factory=list)
    due_date: Optional[str] = None
    notes: Optional[str] = None
    approval_decision: Optional[str] = None


class OutputScopeForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: OutputFormat = "executive_summary"
    channel: str = "web"
    verbosity: Literal["compact", "standard", "detailed"] = "standard"


class ConfirmationScopeForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: bool = False
    reason: Optional[str] = None
    confirmation_text: Optional[str] = None
    risk_level: Literal["low", "medium", "high"] = "low"


class ResolutionScopeForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ResolutionStatus = "ready"
    confidence: float = 1.0
    missing_fields: List[str] = Field(default_factory=list)
    ambiguous_fields: List[str] = Field(default_factory=list)
    field_sources: Dict[str, str] = Field(default_factory=dict)
    needs_human_clarification: bool = False


class SourceScopeForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_text: Optional[str] = None
    origin_channel: str = "web"
    detected_action_key: Optional[str] = None


class OperationalIntentForm(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_kind: IntentKind
    intent_code: str
    entity_type: EntityType
    company_scope: CompanyScopeForm = Field(default_factory=CompanyScopeForm)
    subject_scope: SubjectScopeForm = Field(default_factory=SubjectScopeForm)
    filter_scope: FilterScopeForm = Field(default_factory=FilterScopeForm)
    action_scope: Optional[ActionScopeForm] = None
    output_scope: OutputScopeForm = Field(default_factory=OutputScopeForm)
    confirmation_scope: ConfirmationScopeForm = Field(default_factory=ConfirmationScopeForm)
    resolution_scope: ResolutionScopeForm = Field(default_factory=ResolutionScopeForm)
    source_scope: SourceScopeForm = Field(default_factory=SourceScopeForm)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_execution_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if self.company_scope.company_ids:
            payload["company_ids"] = list(self.company_scope.company_ids)
            payload["_selected_company_id"] = int(self.company_scope.company_ids[0])
        if self.subject_scope.responsible_names:
            payload["colaborador"] = self.subject_scope.responsible_names[0]
        if self.subject_scope.responsible_ids:
            payload["employee_ids"] = list(self.subject_scope.responsible_ids)
        if self.filter_scope.status:
            payload["status_consulta"] = self.filter_scope.status
        if self.filter_scope.entity_hint and self.filter_scope.entity_hint != "mixed":
            payload["entidade"] = self.filter_scope.entity_hint
        if self.filter_scope.period_label:
            payload["periodo"] = self.filter_scope.period_label
        if self.filter_scope.start_date:
            payload["data_inicio"] = self.filter_scope.start_date
        if self.filter_scope.end_date:
            payload["data_fim"] = self.filter_scope.end_date
        if self.filter_scope.limit is not None:
            payload["limit"] = self.filter_scope.limit
        if self.action_scope:
            if self.action_scope.operation:
                payload["operation"] = self.action_scope.operation
            if self.action_scope.target_ids:
                payload["ids"] = list(self.action_scope.target_ids)
            if self.action_scope.target_codes:
                payload["target_codes"] = list(self.action_scope.target_codes)
            if self.action_scope.due_date:
                payload["due_date"] = self.action_scope.due_date
            if self.action_scope.notes:
                payload["notes"] = self.action_scope.notes
            if self.action_scope.approval_decision:
                payload["approval_decision"] = self.action_scope.approval_decision
        return payload
