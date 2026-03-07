from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from models.agent_menu import AgentMenuOption

from .runtime import WorkflowRuntime


class WorkflowEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    expected_action_key: str
    company_id: Optional[int] = None
    channel: str = "web"
    domain: str = "general"
    label: Optional[str] = None


class WorkflowEvaluationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    expected_action_key: str
    selected_action_key: Optional[str] = None
    selected_code: Optional[str] = None
    selected_score: int = 0
    success: bool = False
    top_k_hit: bool = False
    expected_rank: Optional[int] = None
    reciprocal_rank: float = 0.0
    domain: str = "general"
    label: Optional[str] = None
    top_matches: List[str] = Field(default_factory=list)


class WorkflowEvaluationDomainReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str
    total_cases: int
    success_count: int
    top_k_success_count: int
    accuracy: float
    top_k_accuracy: float
    mean_reciprocal_rank: float


class WorkflowEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_cases: int
    success_count: int
    top_k_success_count: int
    accuracy: float
    top_k_accuracy: float
    mean_reciprocal_rank: float
    items: List[WorkflowEvaluationItem] = Field(default_factory=list)
    domain_breakdown: List[WorkflowEvaluationDomainReport] = Field(default_factory=list)


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
        selected_match = result.selected_match
        top_matches = [
            match.workflow.action_key
            for match in result.matches
            if match.workflow.action_key
        ]
        expected_rank = _find_expected_rank(top_matches, case.expected_action_key)
        reciprocal_rank = (1.0 / expected_rank) if expected_rank else 0.0
        items.append(
            WorkflowEvaluationItem(
                text=case.text,
                expected_action_key=case.expected_action_key,
                selected_action_key=selected_match.workflow.action_key if selected_match else None,
                selected_code=selected_match.workflow.code if selected_match else None,
                selected_score=int(selected_match.score or 0) if selected_match else 0,
                success=(selected_match.workflow.action_key == case.expected_action_key) if selected_match else False,
                top_k_hit=expected_rank is not None,
                expected_rank=expected_rank,
                reciprocal_rank=reciprocal_rank,
                domain=case.domain,
                label=case.label,
                top_matches=top_matches,
            )
        )

    success_count = sum(1 for item in items if item.success)
    total_cases = len(items)
    top_k_success_count = sum(1 for item in items if item.top_k_hit)
    accuracy = (success_count / total_cases) if total_cases else 0.0
    top_k_accuracy = (top_k_success_count / total_cases) if total_cases else 0.0
    mean_reciprocal_rank = (
        sum(item.reciprocal_rank for item in items) / total_cases
        if total_cases else 0.0
    )

    return WorkflowEvaluationReport(
        total_cases=total_cases,
        success_count=success_count,
        top_k_success_count=top_k_success_count,
        accuracy=accuracy,
        top_k_accuracy=top_k_accuracy,
        mean_reciprocal_rank=mean_reciprocal_rank,
        items=items,
        domain_breakdown=_build_domain_breakdown(items),
    )


def _find_expected_rank(
    top_matches: Sequence[str],
    expected_action_key: str,
) -> Optional[int]:
    normalized_expected = str(expected_action_key or "").strip().lower()
    if not normalized_expected:
        return None
    for index, match in enumerate(top_matches, start=1):
        if str(match or "").strip().lower() == normalized_expected:
            return index
    return None


def _build_domain_breakdown(
    items: Sequence[WorkflowEvaluationItem],
) -> List[WorkflowEvaluationDomainReport]:
    by_domain: Dict[str, List[WorkflowEvaluationItem]] = {}
    for item in items:
        domain = str(item.domain or "general").strip() or "general"
        by_domain.setdefault(domain, []).append(item)

    reports: List[WorkflowEvaluationDomainReport] = []
    for domain in sorted(by_domain.keys()):
        domain_items = by_domain[domain]
        total_cases = len(domain_items)
        success_count = sum(1 for item in domain_items if item.success)
        top_k_success_count = sum(1 for item in domain_items if item.top_k_hit)
        mean_reciprocal_rank = (
            sum(item.reciprocal_rank for item in domain_items) / total_cases
            if total_cases else 0.0
        )
        reports.append(
            WorkflowEvaluationDomainReport(
                domain=domain,
                total_cases=total_cases,
                success_count=success_count,
                top_k_success_count=top_k_success_count,
                accuracy=(success_count / total_cases) if total_cases else 0.0,
                top_k_accuracy=(top_k_success_count / total_cases) if total_cases else 0.0,
                mean_reciprocal_rank=mean_reciprocal_rank,
            )
        )
    return reports
