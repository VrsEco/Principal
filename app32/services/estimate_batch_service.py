"""Estimativas da Agenda (Fase 2): itens sem estimativa e gravacao em lote.

Regras: docs/spec/agenda_unificada_blocos_pessoa_v1.md, secoes 5.9 e 8.2.
- Itens existentes NAO sao preenchidos em massa; a pessoa estima pelos atalhos.
- Cada item e gravado respeitando a permissao de edicao daquele item.
- A estimativa e guardada em horas na origem (atividade/instancia) e espelhada
  nos itens da jornada que ja existem, para os sinais refletirem na hora.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Callable, Iterable

from sqlalchemy import or_

from models import Employee, Process, ProcessInstance, Project, ProjectTask, WorkJourneyItem, db

ESTIMATE_STEP_MINUTES = 15
ESTIMATE_MIN_MINUTES = 15
ESTIMATE_MAX_MINUTES = 24 * 60
SHORTCUT_MINUTES = (30, 60, 120, 240)
LIST_LIMIT = 200
ESTIMATE_TYPES = ("project_task", "process_instance")
_CLOSED = {
    "project_task": {"completed", "cancelled"},
    "process_instance": {"completed", "failed", "cancelled"},
}


class EstimateError(ValueError):
    pass


def valid_minutes(value: Any) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        raise EstimateError("Informe a estimativa em minutos.")
    if minutes < ESTIMATE_MIN_MINUTES or minutes > ESTIMATE_MAX_MINUTES or minutes % ESTIMATE_STEP_MINUTES:
        raise EstimateError("Estimativa inválida: use múltiplos de 15 minutos, de 15 min a 24 h.")
    return minutes


def _without_estimate(column):
    return or_(column.is_(None), column <= 0)


def _employee(company_id: int, employee_id: int | None) -> Employee | None:
    if not employee_id:
        return None
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
    if employee is None:
        raise EstimateError("Colaborador não encontrado.")
    return employee


def _sort_key(item: dict[str, Any]):
    return (item["due_date"] is None, item["due_date"] or "", item["type"], item["id"])


def list_without_estimate(
    company_id: int,
    *,
    employee_id: int | None = None,
    types: Iterable[str] | None = None,
    limit: int = LIST_LIMIT,
) -> dict[str, Any]:
    """Itens abertos sem estimativa, do prazo mais proximo ao mais distante."""
    wanted = {t for t in (types or ESTIMATE_TYPES) if t in ESTIMATE_TYPES}
    employee = _employee(company_id, employee_id)
    items: list[dict[str, Any]] = []

    if "project_task" in wanted:
        query = (
            db.session.query(ProjectTask, Project)
            .join(Project, Project.id == ProjectTask.project_id)
            .filter(
                Project.company_id == company_id,
                ProjectTask.is_deleted.is_(False),
                _without_estimate(ProjectTask.estimated_hours),
                or_(ProjectTask.status.is_(None), ProjectTask.status.notin_(list(_CLOSED["project_task"]))),
            )
        )
        if employee:
            query = query.filter(ProjectTask.employee_id == employee.id)
        for task, project in query.all():
            items.append(
                {
                    "key": f"project_task:{task.id}",
                    "type": "project_task",
                    "id": task.id,
                    "title": task.what,
                    "subtitle": project.name,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "url": f"/my-work/project-task/{task.id}?from=agenda",
                }
            )

    if "process_instance" in wanted:
        query = (
            db.session.query(ProcessInstance, Process.name)
            .outerjoin(Process, Process.id == ProcessInstance.process_id)
            .filter(
                ProcessInstance.company_id == company_id,
                _without_estimate(ProcessInstance.estimated_hours),
                or_(ProcessInstance.status.is_(None), ProcessInstance.status.notin_(list(_CLOSED["process_instance"]))),
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
        for instance, process_name in query.all():
            items.append(
                {
                    "key": f"process_instance:{instance.id}",
                    "type": "process_instance",
                    "id": instance.id,
                    "title": instance.title,
                    "subtitle": process_name,
                    "due_date": instance.due_date.isoformat() if instance.due_date else None,
                    "url": f"/my-work/process-instance/{instance.id}?company_id={company_id}&from=agenda",
                }
            )

    items.sort(key=_sort_key)
    total = len(items)
    limit = max(1, min(int(limit or LIST_LIMIT), LIST_LIMIT))
    return {"items": items[:limit], "total": total, "shortcuts": list(SHORTCUT_MINUTES)}


def save_estimates(
    company_id: int,
    entries: Iterable[dict[str, Any]],
    *,
    can_edit_task: Callable[[ProjectTask, Project], bool],
    can_edit_instance: Callable[[ProcessInstance], bool],
) -> dict[str, Any]:
    """Grava estimativas em lote. Cada item e validado e autorizado individualmente."""
    saved: list[str] = []
    skipped: list[dict[str, str]] = []
    seen: set[str] = set()
    entries = list(entries or [])
    if not entries:
        raise EstimateError("Nenhuma estimativa informada.")
    if len(entries) > LIST_LIMIT:
        raise EstimateError("Muitos itens de uma vez.")

    for entry in entries:
        etype = str(entry.get("type") or "")
        try:
            item_id = int(entry.get("id"))
        except (TypeError, ValueError):
            skipped.append({"key": f"{etype}:?", "reason": "Item inválido."})
            continue
        key = f"{etype}:{item_id}"
        if key in seen:
            continue
        seen.add(key)
        try:
            minutes = valid_minutes(entry.get("minutes"))
        except EstimateError as exc:
            skipped.append({"key": key, "reason": str(exc)})
            continue
        hours = Decimal(minutes) / Decimal(60)

        if etype == "project_task":
            row = (
                db.session.query(ProjectTask, Project)
                .join(Project, Project.id == ProjectTask.project_id)
                .filter(ProjectTask.id == item_id, Project.company_id == company_id, ProjectTask.is_deleted.is_(False))
                .first()
            )
            if row is None:
                skipped.append({"key": key, "reason": "Atividade não encontrada."})
                continue
            task, project = row
            if not can_edit_task(task, project):
                skipped.append({"key": key, "reason": "Sem permissão para estimar esta atividade."})
                continue
            task.estimated_hours = hours
        elif etype == "process_instance":
            instance = ProcessInstance.query.filter_by(id=item_id, company_id=company_id).first()
            if instance is None:
                skipped.append({"key": key, "reason": "Instância não encontrada."})
                continue
            if not can_edit_instance(instance):
                skipped.append({"key": key, "reason": "Sem permissão para estimar esta instância."})
                continue
            instance.estimated_hours = hours
        else:
            skipped.append({"key": key, "reason": "Tipo inválido."})
            continue

        WorkJourneyItem.query.filter_by(company_id=company_id, item_type=etype, source_id=item_id).update(
            {"estimated_minutes": minutes}, synchronize_session=False
        )
        saved.append(key)

    db.session.commit()
    return {"saved": saved, "skipped": skipped}
