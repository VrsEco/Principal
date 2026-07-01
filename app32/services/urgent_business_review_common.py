from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from models import (
    Company,
    Indicator,
    Meeting,
    Occurrence,
    Process,
    ProcessInstance,
    Project,
    ProjectTask,
    Routine,
)


class UrgentBusinessReviewError(ValueError):
    """Erro de domínio para overlays de urgência, Business Review e aprendizado."""


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_choice(value: Any, *, allowed: tuple[str, ...], default: str, field: str) -> str:
    normalized = clean_text(value) or default
    normalized = normalized.lower().replace("-", "_").replace(" ", "_")
    if normalized not in allowed:
        raise UrgentBusinessReviewError(
            f"Valor inválido para {field}: {value}. Use um de: {', '.join(allowed)}."
        )
    return normalized


def decimal_or_none(value: Any, *, field: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise UrgentBusinessReviewError(f"Valor numérico inválido para {field}: {value}.") from exc


def require_company(company_id: int) -> Company:
    company = Company.query.filter_by(id=company_id).first()
    if company is None:
        raise UrgentBusinessReviewError(f"Empresa não encontrada: company_id={company_id}.")
    return company


def require_project(company_id: int, project_id: int | None) -> Project | None:
    if not project_id:
        return None
    row = Project.query.filter_by(id=project_id, company_id=company_id, is_deleted=False).first()
    if row is None:
        raise UrgentBusinessReviewError(f"Projeto não encontrado no tenant: project_id={project_id}.")
    return row


def require_project_task(company_id: int, project_task_id: int | None) -> ProjectTask | None:
    if not project_task_id:
        return None
    row = (
        ProjectTask.query.join(Project, Project.id == ProjectTask.project_id)
        .filter(ProjectTask.id == project_task_id)
        .filter(Project.company_id == company_id)
        .filter(Project.is_deleted.is_(False))
        .filter(ProjectTask.is_deleted.is_(False))
        .first()
    )
    if row is None:
        raise UrgentBusinessReviewError(f"Atividade não encontrada no tenant: project_task_id={project_task_id}.")
    return row


def require_process(company_id: int, process_id: int | None) -> Process | None:
    if not process_id:
        return None
    row = Process.query.filter_by(id=process_id, company_id=company_id).first()
    if row is None:
        raise UrgentBusinessReviewError(f"Processo não encontrado no tenant: process_id={process_id}.")
    return row


def require_process_instance(company_id: int, process_instance_id: int | None) -> ProcessInstance | None:
    if not process_instance_id:
        return None
    row = ProcessInstance.query.filter_by(id=process_instance_id, company_id=company_id).first()
    if row is None:
        raise UrgentBusinessReviewError(
            f"Instância de processo não encontrada no tenant: process_instance_id={process_instance_id}."
        )
    return row


def require_routine(company_id: int, routine_id: int | None) -> Routine | None:
    if not routine_id:
        return None
    row = Routine.query.filter_by(id=routine_id, company_id=company_id).first()
    if row is None:
        raise UrgentBusinessReviewError(f"Rotina não encontrada no tenant: routine_id={routine_id}.")
    return row


def require_indicator(company_id: int, indicator_id: int | None) -> Indicator | None:
    if not indicator_id:
        return None
    row = Indicator.query.filter_by(id=indicator_id, company_id=company_id).first()
    if row is None:
        raise UrgentBusinessReviewError(f"Indicador não encontrado no tenant: indicator_id={indicator_id}.")
    return row


def require_meeting(company_id: int, meeting_id: int | None) -> Meeting | None:
    if not meeting_id:
        return None
    row = Meeting.query.filter_by(id=meeting_id, company_id=company_id).first()
    if row is None:
        raise UrgentBusinessReviewError(f"Reunião não encontrada no tenant: meeting_id={meeting_id}.")
    return row


def require_occurrence(company_id: int, occurrence_id: int | None) -> Occurrence | None:
    if not occurrence_id:
        return None
    row = Occurrence.query.filter_by(id=occurrence_id, company_id=company_id).first()
    if row is None:
        raise UrgentBusinessReviewError(f"Ocorrência não encontrada no tenant: occurrence_id={occurrence_id}.")
    return row


def validate_canonical_links(
    *,
    company_id: int,
    project_id: int | None = None,
    project_task_id: int | None = None,
    process_id: int | None = None,
    process_instance_id: int | None = None,
    routine_id: int | None = None,
    indicator_id: int | None = None,
    meeting_id: int | None = None,
    occurrence_id: int | None = None,
    financial_ref_id: int | None = None,
    require_any: bool = True,
) -> dict[str, Any]:
    require_company(company_id)
    links = {
        "project": require_project(company_id, project_id),
        "project_task": require_project_task(company_id, project_task_id),
        "process": require_process(company_id, process_id),
        "process_instance": require_process_instance(company_id, process_instance_id),
        "routine": require_routine(company_id, routine_id),
        "indicator": require_indicator(company_id, indicator_id),
        "meeting": require_meeting(company_id, meeting_id),
        "occurrence": require_occurrence(company_id, occurrence_id),
    }
    if require_any and not any(value is not None for value in links.values()):
        raise UrgentBusinessReviewError("Informe ao menos um vínculo canônico para o overlay consultivo.")
    links["financial_ref_id"] = financial_ref_id
    return links
