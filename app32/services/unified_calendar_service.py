"""Agenda unificada: projeta reuniões, atividades de projeto e instâncias de processo.

Os registros são lidos diretamente das tabelas de origem (sem duplicação) e
devolvidos em um formato comum de evento, já com a URL da página de gestão.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from sqlalchemy import or_

from models import Employee, Meeting, Process, ProcessInstance, Project, ProjectTask, db

EVENT_TYPES = ("meeting", "project_task", "process_instance")
MAX_RANGE_DAYS = 100
_CLOSED_STATUSES = {
    "meeting": {"completed", "finished", "done", "cancelled"},
    "project_task": {"completed", "cancelled"},
    "process_instance": {"completed", "failed", "cancelled"},
}


class UnifiedCalendarError(ValueError):
    pass


def list_unified_events(
    company_id: int,
    start_date: date,
    end_date: date,
    *,
    employee_id: int | None = None,
    types: set[str] | None = None,
) -> list[dict[str, Any]]:
    if end_date < start_date:
        raise UnifiedCalendarError("Período inválido.")
    if (end_date - start_date) > timedelta(days=MAX_RANGE_DAYS):
        raise UnifiedCalendarError("Período máximo excedido.")

    wanted = {t for t in (types or set(EVENT_TYPES)) if t in EVENT_TYPES}
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first() if employee_id else None
    if employee_id and not employee:
        raise UnifiedCalendarError("Colaborador não encontrado na empresa.")

    events: list[dict[str, Any]] = []
    if "meeting" in wanted:
        events.extend(_meeting_events(company_id, start_date, end_date, employee))
    if "project_task" in wanted:
        events.extend(_task_events(company_id, start_date, end_date, employee))
    if "process_instance" in wanted:
        events.extend(_instance_events(company_id, start_date, end_date, employee))

    events.sort(key=lambda e: (e["date"], e["time"] or "99:99", e["type"], e["id"]))
    return events


def _meeting_events(company_id: int, start: date, end: date, employee: Employee | None) -> list[dict[str, Any]]:
    rows = (
        Meeting.query.filter(
            Meeting.company_id == company_id,
            Meeting.scheduled_date.isnot(None),
            Meeting.scheduled_date.between(start, end),
        )
        .order_by(Meeting.scheduled_date.asc(), Meeting.scheduled_time.asc())
        .all()
    )
    project_names = _project_names({m.project_id for m in rows if m.project_id})
    events = []
    for meeting in rows:
        if employee and not _meeting_includes_employee(meeting, employee):
            continue
        status = (meeting.status or "draft").lower()
        events.append(
            {
                "key": f"meeting:{meeting.id}",
                "type": "meeting",
                "id": meeting.id,
                "title": meeting.title,
                "date": meeting.scheduled_date.isoformat(),
                "time": meeting.scheduled_time or None,
                "duration_minutes": meeting.planned_duration_minutes,
                "all_day": not meeting.scheduled_time,
                "status": status,
                "closed": status in _CLOSED_STATUSES["meeting"],
                "priority": None,
                "subtitle": project_names.get(meeting.project_id),
                "url": f"/meetings/company/{company_id}?meeting_id={meeting.id}",
            }
        )
    return events


def _task_events(company_id: int, start: date, end: date, employee: Employee | None) -> list[dict[str, Any]]:
    query = (
        db.session.query(ProjectTask, Project)
        .join(Project, Project.id == ProjectTask.project_id)
        .filter(
            Project.company_id == company_id,
            ProjectTask.is_deleted.is_(False),
            ProjectTask.due_date.isnot(None),
            ProjectTask.due_date.between(start, end),
        )
    )
    if employee:
        query = query.filter(ProjectTask.employee_id == employee.id)
    events = []
    for task, project in query.order_by(ProjectTask.due_date.asc(), ProjectTask.id.asc()).all():
        status = (task.status or "planned").lower()
        events.append(
            {
                "key": f"project_task:{task.id}",
                "type": "project_task",
                "id": task.id,
                "title": task.what,
                "date": task.due_date.isoformat(),
                "time": None,
                "duration_minutes": None,
                "all_day": True,
                "status": status,
                "closed": status in _CLOSED_STATUSES["project_task"],
                "priority": task.priority,
                "subtitle": project.name,
                "url": f"/my-work/project-task/{task.id}?from=agenda",
            }
        )
    return events


def _instance_events(company_id: int, start: date, end: date, employee: Employee | None) -> list[dict[str, Any]]:
    query = (
        db.session.query(ProcessInstance, Process.name)
        .outerjoin(Process, Process.id == ProcessInstance.process_id)
        .filter(
            ProcessInstance.company_id == company_id,
            ProcessInstance.due_date.isnot(None),
            ProcessInstance.due_date.between(start, end),
        )
    )
    if employee:
        query = query.filter(
            or_(
                ProcessInstance.owner_employee_id == employee.id,
                ProcessInstance.responsible_id == employee.id,
                ProcessInstance.executor_id == employee.id,
            )
        )
    events = []
    for instance, process_name in query.order_by(ProcessInstance.due_date.asc(), ProcessInstance.id.asc()).all():
        status = (instance.status or "pending").lower()
        events.append(
            {
                "key": f"process_instance:{instance.id}",
                "type": "process_instance",
                "id": instance.id,
                "title": instance.title,
                "date": instance.due_date.isoformat(),
                "time": None,
                "duration_minutes": None,
                "all_day": True,
                "status": status,
                "closed": status in _CLOSED_STATUSES["process_instance"],
                "priority": instance.priority,
                "subtitle": process_name,
                "url": f"/my-work/process-instance/{instance.id}?company_id={company_id}&from=agenda",
            }
        )
    return events


def _project_names(project_ids: set[int]) -> dict[int, str]:
    if not project_ids:
        return {}
    rows = Project.query.filter(Project.id.in_(project_ids)).with_entities(Project.id, Project.name).all()
    return {pid: name for pid, name in rows}


def _meeting_includes_employee(meeting: Meeting, employee: Employee) -> bool:
    for raw in (meeting.participants_json, meeting.guests_json):
        if not raw:
            continue
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError):
            continue
        if _contains_employee(data, employee):
            return True
    return False


def _contains_employee(node: Any, employee: Employee) -> bool:
    if isinstance(node, dict):
        for key in ("employee_id", "id"):
            if node.get(key) is not None and str(node.get(key)) == str(employee.id):
                return True
        name = str(node.get("name") or "").strip().lower()
        if name and name == str(employee.name or "").strip().lower():
            return True
        return any(_contains_employee(value, employee) for value in node.values() if isinstance(value, (dict, list)))
    if isinstance(node, list):
        return any(_contains_employee(item, employee) for item in node)
    if isinstance(node, (int, str)):
        return str(node) == str(employee.id)
    return False
