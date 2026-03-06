from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from models.agent_menu import AgentMenuOption

from .runtime import WorkflowRuntime


class WorkflowEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    expected_action_key: str
    company_id: Optional[int] = None
    channel: str = "web"


class WorkflowEvaluationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    expected_action_key: str
    selected_action_key: Optional[str] = None
    success: bool = False
    top_matches: List[str] = Field(default_factory=list)


class WorkflowEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_cases: int
    success_count: int
    accuracy: float
    items: List[WorkflowEvaluationItem] = Field(default_factory=list)


def evaluate_workflow_discovery(
    *,
    runtime: WorkflowRuntime,
    cases: Sequence[WorkflowEvaluationCase],
    options: Iterable[AgentMenuOption],
    preferred_company_id: Optional[int] = None,
    top_k: int = 5,
) -> WorkflowEvaluationReport:
    options_list = list(options)
    items: List[WorkflowEvaluationItem] = []

    for case in cases:
        effective_company_id = (
            case.company_id if case.company_id is not None else preferred_company_id
        )
        result = runtime.discover_from_menu_options(
            text=case.text,
            options=options_list,
            preferred_company_id=effective_company_id,
            top_k=top_k,
            channel=case.channel,
        )
        selected_action_key = result.selected.action_key if result.selected else None
        top_matches = [
            match.workflow.action_key
            for match in result.matches
            if match.workflow.action_key
        ]
        items.append(
            WorkflowEvaluationItem(
                text=case.text,
                expected_action_key=case.expected_action_key,
                selected_action_key=selected_action_key,
                success=selected_action_key == case.expected_action_key,
                top_matches=top_matches,
            )
        )

    success_count = sum(1 for item in items if item.success)
    total_cases = len(items)
    accuracy = (success_count / total_cases) if total_cases else 0.0

    return WorkflowEvaluationReport(
        total_cases=total_cases,
        success_count=success_count,
        accuracy=accuracy,
        items=items,
    )
