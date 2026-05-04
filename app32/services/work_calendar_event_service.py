from __future__ import annotations

from datetime import date, datetime
from typing import Any

from models import ProcessInstance, ProjectTask, WorkCalendarEvent, db
from services.work_journey_base import WorkJourneyError, ensure_employee
from services.work_journey_sync import build_process_instance_source_url, build_project_task_source_url

ALLOWED_SOURCE_TYPES = {"manual", "project_task", "process_instance"}
ALLOWED_STATUSES = {"planned", "confirmed", "in_progress", "done", "cancelled", "postponed"}
ALLOWED_PRIORITIES = {"low", "normal", "high", "urgent"}


def list_calendar_events(
    company_id: int,
    employee_id: int,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    source_type: str | None = None,
    source_id: int | None = None,
) -> list[dict[str, Any]]:
    ensure_employee(company_id, employee_id)
    query = WorkCalendarEvent.query.filter_by(company_id=company_id, employee_id=employee_id)
    if start_date:
        query = query.filter(WorkCalendarEvent.event_date >= start_date)
    if end_date:
        query = query.filter(WorkCalendarEvent.event_date <= end_date)
    if source_type:
        query = query.filter(WorkCalendarEvent.source_type == source_type)
    if source_id:
        query = query.filter(WorkCalendarEvent.source_id == source_id)
    events = query.order_by(
        WorkCalendarEvent.event_date.asc(),
        WorkCalendarEvent.start_time.asc().nullsfirst(),
        WorkCalendarEvent.id.asc(),
    ).all()
    return [serialize_calendar_event(event) for event in events]


def create_calendar_event(company_id: int, payload: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
    employee = ensure_employee(company_id, payload["employee_id"])
    source_type = _normalize_source_type(payload.get("source_type"))
    source_id = payload.get("source_id")
    _validate_source(company_id, source_type, source_id)
    event = WorkCalendarEvent(
        company_id=company_id,
        employee_id=employee.id,
        created_by_user_id=user_id,
        updated_by_user_id=user_id,
        source_type=source_type,
        source_id=source_id,
        title=payload["title"],
        description=payload.get("description") or None,
        event_date=payload["event_date"],
        start_time=payload.get("start_time"),
        end_time=payload.get("end_time"),
        status=_normalize_status(payload.get("status")),
        priority=_normalize_priority(payload.get("priority")),
        execution_notes=payload.get("execution_notes") or None,
        metadata_json=dict(payload.get("metadata_json") or {}),
    )
    db.session.add(event)
    db.session.commit()
    return serialize_calendar_event(event)


def update_calendar_event(company_id: int, event_id: int, payload: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
    event = _load_event(company_id, event_id)

    if payload.get("employee_id") is not None and payload["employee_id"] != event.employee_id:
        employee = ensure_employee(company_id, payload["employee_id"])
        event.employee_id = employee.id

    if payload.get("source_type") is not None:
        source_type = _normalize_source_type(payload.get("source_type"))
        source_id = payload.get("source_id", event.source_id)
        _validate_source(company_id, source_type, source_id)
        event.source_type = source_type
        event.source_id = source_id
    elif "source_id" in payload:
        _validate_source(company_id, event.source_type, payload.get("source_id"))
        event.source_id = payload.get("source_id")

    for field in ("title", "event_date", "start_time", "end_time"):
        if field in payload:
            setattr(event, field, payload.get(field))
    for field in ("description", "execution_notes"):
        if field in payload:
            setattr(event, field, payload.get(field) or None)

    if payload.get("status") is not None:
        event.status = _normalize_status(payload.get("status"))
    if payload.get("priority") is not None:
        event.priority = _normalize_priority(payload.get("priority"))
    if payload.get("metadata_json") is not None:
        event.metadata_json = dict(payload.get("metadata_json") or {})

    event.updated_by_user_id = user_id
    event.updated_at = datetime.utcnow()
    db.session.add(event)
    db.session.commit()
    return serialize_calendar_event(event)


def delete_calendar_event(company_id: int, event_id: int) -> None:
    event = _load_event(company_id, event_id)
    db.session.delete(event)
    db.session.commit()


def serialize_calendar_event(event: WorkCalendarEvent) -> dict[str, Any]:
    payload = event.to_dict()
    source = _resolve_source_context(event.company_id, event.source_type, event.source_id)
    payload["employee_name"] = getattr(event.employee, "name", None)
    payload["status_label"] = {
        "planned": "Planejado",
        "confirmed": "Confirmado",
        "in_progress": "Em execução",
        "done": "Concluído",
        "cancelled": "Cancelado",
        "postponed": "Adiado",
    }.get(event.status, event.status)
    payload["priority_label"] = {
        "low": "Baixa",
        "normal": "Normal",
        "high": "Alta",
        "urgent": "Urgente",
    }.get(event.priority, event.priority)
    payload.update(source)
    return payload


def suggest_employee_for_source(company_id: int, source_type: str, source_id: int | None) -> int | None:
    source_type = _normalize_source_type(source_type)
    if source_type == "project_task" and source_id:
        task = (
            ProjectTask.query.filter(ProjectTask.id == source_id)
            .filter(ProjectTask.project.has(company_id=company_id))
            .first()
        )
        return getattr(task, "employee_id", None) if task else None
    if source_type == "process_instance" and source_id:
        instance = ProcessInstance.query.filter_by(company_id=company_id, id=source_id).first()
        return (
            getattr(instance, "executor_id", None)
            or getattr(instance, "responsible_id", None)
            or getattr(instance, "owner_employee_id", None)
        ) if instance else None
    return None


def _load_event(company_id: int, event_id: int) -> WorkCalendarEvent:
    event = WorkCalendarEvent.query.filter_by(company_id=company_id, id=event_id).first()
    if not event:
        raise WorkJourneyError("Evento de calendário não encontrado.")
    return event


def _normalize_source_type(value: str | None) -> str:
    normalized = str(value or "manual").strip().lower()
    if normalized not in ALLOWED_SOURCE_TYPES:
        raise WorkJourneyError("Tipo de origem do evento inválido.")
    return normalized


def _normalize_status(value: str | None) -> str:
    normalized = str(value or "planned").strip().lower()
    if normalized not in ALLOWED_STATUSES:
        raise WorkJourneyError("Status do evento inválido.")
    return normalized


def _normalize_priority(value: str | None) -> str:
    normalized = str(value or "normal").strip().lower()
    if normalized not in ALLOWED_PRIORITIES:
        raise WorkJourneyError("Prioridade do evento inválida.")
    return normalized


def _validate_source(company_id: int, source_type: str, source_id: int | None) -> None:
    if source_type == "manual":
        return
    if not source_id:
        raise WorkJourneyError("Informe a origem do evento.")
    if source_type == "project_task":
        task_exists = (
            ProjectTask.query.filter(ProjectTask.id == source_id)
            .filter(ProjectTask.project.has(company_id=company_id))
            .first()
        )
        if not task_exists:
            raise WorkJourneyError("Atividade de projeto não encontrada para a empresa.")
        return
    if source_type == "process_instance":
        instance_exists = ProcessInstance.query.filter_by(company_id=company_id, id=source_id).first()
        if not instance_exists:
            raise WorkJourneyError("Instância de processo não encontrada para a empresa.")


def _resolve_source_context(company_id: int, source_type: str, source_id: int | None) -> dict[str, Any]:
    if source_type == "project_task" and source_id:
        task = (
            ProjectTask.query.filter(ProjectTask.id == source_id)
            .filter(ProjectTask.project.has(company_id=company_id))
            .first()
        )
        if task:
            return {
                "source_label": "Atividade de projeto",
                "source_code": getattr(task, "code", None) or f"J.{task.id}",
                "source_title": getattr(task, "what", None),
                "source_url": build_project_task_source_url(task.project_id, task.id),
            }
    if source_type == "process_instance" and source_id:
        instance = ProcessInstance.query.filter_by(company_id=company_id, id=source_id).first()
        if instance:
            return {
                "source_label": "Instância de processo",
                "source_code": getattr(instance, "instance_code", None) or f"IP.{instance.id}",
                "source_title": getattr(instance, "title", None),
                "source_url": build_process_instance_source_url(company_id, instance.id),
            }
    return {
        "source_label": "Evento livre" if source_type == "manual" else source_type,
        "source_code": None,
        "source_title": None,
        "source_url": None,
    }
