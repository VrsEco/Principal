"""Visao de blocos da Agenda (Fase 2): carrega blocos, itens e eventos e aplica os sinais.

Somente leitura: nao gera agendas, nao move nada. Os itens consumem capacidade
apenas quando ja estao atribuidos a um bloco em uma agenda existente do dia.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from models import (
    Employee,
    WorkJourneyAgenda,
    WorkJourneyAgendaItem,
    WorkJourneyBlock,
    WorkJourneyItem,
)
from services.block_signal_service import DEFAULT_IDLE_THRESHOLD_MINUTES, compute_block_signals
from services.unified_calendar_service import list_unified_events

MAX_DAYS = 14
_CLOSED_ITEM_STATUSES = {"completed", "done", "cancelled"}
_TIMED_TYPES = {"meeting", "manual", "google_event"}


class BlockViewError(ValueError):
    pass


def _minutes(value) -> int:
    return value.hour * 60 + value.minute


def _hhmm_to_minutes(value: str) -> int:
    hours, minutes = value.split(":")[:2]
    return int(hours) * 60 + int(minutes)


def _fmt(value) -> str:
    return value.strftime("%H:%M")


def build_block_view(
    company_id: int,
    employee_id: int,
    start_date: date,
    end_date: date,
    *,
    idle_threshold: int = DEFAULT_IDLE_THRESHOLD_MINUTES,
    extra_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Sinais por bloco, dia a dia, para UM colaborador de UMA empresa."""
    if end_date < start_date:
        raise BlockViewError("Período inválido.")
    if (end_date - start_date) > timedelta(days=MAX_DAYS):
        raise BlockViewError("Período máximo excedido.")

    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
    if employee is None:
        raise BlockViewError("Colaborador não encontrado.")

    blocks = (
        WorkJourneyBlock.query.filter_by(company_id=company_id, employee_id=employee_id, is_active=True)
        .order_by(WorkJourneyBlock.start_time, WorkJourneyBlock.order_index)
        .all()
    )

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
    journey_ids = {e.journey_item_id for e in entries if e.journey_item_id}
    journey_by_id = {}
    if journey_ids:
        journey_by_id = {
            j.id: j
            for j in WorkJourneyItem.query.filter(
                WorkJourneyItem.company_id == company_id, WorkJourneyItem.id.in_(journey_ids)
            ).all()
        }

    events = list_unified_events(company_id, start_date, end_date, employee_id=employee_id, types={"meeting", "manual"})
    events = events + list(extra_events or [])

    days: list[dict[str, Any]] = []
    current = start_date
    seen_entry_ids: set[int] = set()
    while current <= end_date:
        day_blocks = [
            {
                "id": b.id,
                "name": b.name,
                "mode": b.block_mode or "operational",
                "start_minutes": _minutes(b.start_time),
                "end_minutes": _minutes(b.end_time),
                "start": _fmt(b.start_time),
                "end": _fmt(b.end_time),
            }
            for b in blocks
            if current.weekday() in (b.weekdays_json or [])
        ]

        items = []
        for entry in entries:
            if entry.planned_date != current or entry.id in seen_entry_ids:
                continue
            seen_entry_ids.add(entry.id)
            journey = journey_by_id.get(entry.journey_item_id)
            if journey is None:
                continue
            items.append(
                {
                    "block_id": entry.block_id,
                    "estimated_minutes": journey.estimated_minutes,
                    "completed": (journey.status or "") in _CLOSED_ITEM_STATUSES,
                }
            )

        timed = []
        for event in events:
            if event.get("date") != current.isoformat() or event.get("all_day") or not event.get("time"):
                continue
            if event.get("type") not in _TIMED_TYPES or event.get("closed"):
                continue
            timed.append(
                {
                    "start_minutes": _hhmm_to_minutes(event["time"]),
                    "duration_minutes": event.get("duration_minutes") or 0,
                }
            )

        computed = compute_block_signals(day_blocks, items, timed, idle_threshold)
        label_by_id = {b["id"]: b for b in day_blocks}
        for block in computed["blocks"]:
            block["start"] = label_by_id[block["id"]]["start"]
            block["end"] = label_by_id[block["id"]]["end"]
        days.append({"date": current.isoformat(), **computed})
        current += timedelta(days=1)

    return {"employee_id": employee_id, "idle_threshold": idle_threshold, "days": days}
