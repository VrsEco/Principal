"""Visao de blocos da Agenda: carrega blocos, itens e eventos e aplica os sinais.

Somente leitura: nao gera agendas, nao move nada. Os itens consomem capacidade
apenas quando ja estao atribuidos a um bloco em uma agenda existente do dia.

Dois modos (adaptador de blocos efetivos, SPEC secao 6.4):
- legado: blocos por empresa e colaborador (`work_journey_blocks`);
- pessoa: blocos do USUARIO (`person_work_blocks`) agregando os itens de todas as
  empresas dele. So vale quando o proprio usuario olha a propria agenda; o gestor
  continua vendo cada empresa isolada (privacidade, SPEC secao 8.3).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable

from models import Company, Employee, WorkJourneyAgenda, WorkJourneyAgendaItem, WorkJourneyItem
from services.block_signal_service import DEFAULT_IDLE_THRESHOLD_MINUTES, compute_block_signals
from services.effective_blocks_service import SOURCE_LEGACY, SOURCE_PERSON, legacy_blocks, person_blocks, user_has_person_blocks
from services.unified_calendar_service import list_unified_events

MAX_DAYS = 14
_CLOSED_ITEM_STATUSES = {"completed", "done", "cancelled", "postponed", "suspended"}
_TIMED_TYPES = {"meeting", "manual", "google_event"}


class BlockViewError(ValueError):
    pass


def _hhmm_to_minutes(value: str) -> int:
    hours, minutes = value.split(":")[:2]
    return int(hours) * 60 + int(minutes)


def _check_period(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise BlockViewError("Período inválido.")
    if (end_date - start_date) > timedelta(days=MAX_DAYS):
        raise BlockViewError("Período máximo excedido.")


def _assemble(
    *,
    blocks: list[dict[str, Any]],
    entries: list[WorkJourneyAgendaItem],
    journey_by_id: dict[int, WorkJourneyItem],
    events: list[dict[str, Any]],
    start_date: date,
    end_date: date,
    idle_threshold: int,
    block_of: Callable[[WorkJourneyAgendaItem], Any],
    company_names: dict[int, str] | None = None,
) -> list[dict[str, Any]]:
    """Nucleo comum: sinais dia a dia a partir de blocos, entradas de agenda e eventos."""
    days: list[dict[str, Any]] = []
    current = start_date
    while current <= end_date:
        day_blocks = [
            {k: b[k] for k in ("id", "name", "mode", "start_minutes", "end_minutes", "start", "end")}
            for b in blocks
            if current.weekday() in b["weekdays"]
        ]

        items = []
        listing: dict[Any, list[dict[str, Any]]] = {}
        suggested = 0
        # O mesmo item pode estar em agendas diferentes (dia e semana): conta uma vez, preferindo o que a pessoa atribuiu.
        chosen: dict[int, WorkJourneyAgendaItem] = {}
        for entry in entries:
            if entry.planned_date != current or not entry.journey_item_id:
                continue
            best = chosen.get(entry.journey_item_id)
            if best is None or (bool(entry.manual_override), entry.id) > (bool(best.manual_override), best.id):
                chosen[entry.journey_item_id] = entry
        for entry in chosen.values():
            journey = journey_by_id.get(entry.journey_item_id)
            if journey is None:
                continue
            # RF-SIN-3: atrasado só consome depois de planejado pela pessoa; a sugestão automática do motor não conta.
            if not entry.manual_override and journey.due_date and journey.due_date < current:
                continue
            closed = (journey.status or "") in _CLOSED_ITEM_STATUSES
            is_suggested = (entry.metadata_json or {}).get("suggested_by") == "system"
            block_ref = block_of(entry)
            items.append({"block_id": block_ref, "estimated_minutes": journey.estimated_minutes, "completed": closed})
            if not closed:
                suggested += 1 if is_suggested else 0
                row = {
                    "key": f"{journey.item_type}:{journey.source_id}" if journey.source_id else None,
                    "type": journey.item_type,
                    "title": journey.title,
                    "minutes": int(journey.estimated_minutes or 0),
                    "suggested": is_suggested,
                }
                if company_names:
                    row["company"] = company_names.get(entry.company_id)
                listing.setdefault(block_ref, []).append(row)

        timed = []
        for event in events:
            if event.get("date") != current.isoformat() or event.get("all_day") or not event.get("time"):
                continue
            if event.get("type") not in _TIMED_TYPES or event.get("closed"):
                continue
            timed.append({"start_minutes": _hhmm_to_minutes(event["time"]), "duration_minutes": event.get("duration_minutes") or 0})

        computed = compute_block_signals(day_blocks, items, timed, idle_threshold)
        label_by_id = {b["id"]: b for b in day_blocks}
        for block in computed["blocks"]:
            block["start"] = label_by_id[block["id"]]["start"]
            block["end"] = label_by_id[block["id"]]["end"]
            block["items"] = listing.get(block["id"], [])
        computed["day"]["suggested_count"] = suggested
        days.append({"date": current.isoformat(), **computed})
        current += timedelta(days=1)
    return days


def _journey_map(item_ids: set[int]) -> dict[int, WorkJourneyItem]:
    if not item_ids:
        return {}
    return {j.id: j for j in WorkJourneyItem.query.filter(WorkJourneyItem.id.in_(item_ids)).all()}


def build_block_view(
    company_id: int,
    employee_id: int,
    start_date: date,
    end_date: date,
    *,
    idle_threshold: int = DEFAULT_IDLE_THRESHOLD_MINUTES,
    extra_events: list[dict[str, Any]] | None = None,
    viewer_user_id: int | None = None,
) -> dict[str, Any]:
    """Sinais por bloco, dia a dia.

    Com `viewer_user_id` igual ao dono do colaborador e blocos da pessoa ativos, devolve o dia
    UNICO da pessoa (todas as empresas dela). Em qualquer outro caso, UM colaborador de UMA empresa.
    """
    _check_period(start_date, end_date)
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
    if employee is None:
        raise BlockViewError("Colaborador não encontrado.")

    if viewer_user_id is not None and employee.user_id == viewer_user_id and user_has_person_blocks(viewer_user_id):
        return _build_person_view(viewer_user_id, employee_id, start_date, end_date, idle_threshold, extra_events)

    blocks = legacy_blocks(company_id, employee_id)
    entries = (
        WorkJourneyAgendaItem.query.join(WorkJourneyAgenda, WorkJourneyAgenda.id == WorkJourneyAgendaItem.agenda_id)
        .filter(
            WorkJourneyAgendaItem.company_id == company_id,
            WorkJourneyAgendaItem.employee_id == employee_id,
            WorkJourneyAgendaItem.planned_date >= start_date,
            WorkJourneyAgendaItem.planned_date <= end_date,
            WorkJourneyAgendaItem.block_id.isnot(None),
        )
        .all()
    )
    journey_by_id = _journey_map({e.journey_item_id for e in entries if e.journey_item_id})
    events = list_unified_events(company_id, start_date, end_date, employee_id=employee_id, types={"meeting", "manual"})
    events = events + list(extra_events or [])
    days = _assemble(
        blocks=blocks, entries=entries, journey_by_id=journey_by_id, events=events, start_date=start_date,
        end_date=end_date, idle_threshold=idle_threshold, block_of=lambda e: e.block_id,
    )
    return {"employee_id": employee_id, "source": SOURCE_LEGACY, "idle_threshold": idle_threshold, "days": days}


def _build_person_view(
    user_id: int,
    employee_id: int,
    start_date: date,
    end_date: date,
    idle_threshold: int,
    extra_events: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    employees = Employee.query.filter(Employee.user_id == user_id, Employee.status == "active").all()
    employee_ids = {e.id for e in employees}
    company_ids = sorted({e.company_id for e in employees})
    company_names = {c.id: c.name for c in Company.query.filter(Company.id.in_(company_ids)).all()} if company_ids else {}

    entries = (
        WorkJourneyAgendaItem.query.filter(
            WorkJourneyAgendaItem.employee_id.in_(employee_ids),
            WorkJourneyAgendaItem.planned_date >= start_date,
            WorkJourneyAgendaItem.planned_date <= end_date,
            WorkJourneyAgendaItem.person_block_id.isnot(None),
        ).all()
        if employee_ids
        else []
    )
    journey_by_id = _journey_map({e.journey_item_id for e in entries if e.journey_item_id})

    events: list[dict[str, Any]] = []
    for employee in employees:
        events.extend(
            list_unified_events(employee.company_id, start_date, end_date, employee_id=employee.id, types={"meeting", "manual"})
        )
    events.extend(extra_events or [])

    days = _assemble(
        blocks=person_blocks(user_id), entries=entries, journey_by_id=journey_by_id, events=events,
        start_date=start_date, end_date=end_date, idle_threshold=idle_threshold,
        block_of=lambda e: e.person_block_id, company_names=company_names if len(company_ids) > 1 else None,
    )
    return {
        "employee_id": employee_id,
        "source": SOURCE_PERSON,
        "companies": len(company_ids),
        "idle_threshold": idle_threshold,
        "days": days,
    }
