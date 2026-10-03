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
_CLOSED_ITEM_STATUSES = {"completed", "done", "cancelled", "postponed", "suspended"}
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
            items.append({"block_id": entry.block_id, "estimated_minutes": journey.estimated_minutes, "completed": closed})
            if not closed:
                suggested += 1 if is_suggested else 0
                listing.setdefault(entry.block_id, []).append(
                    {
                        "key": f"{journey.item_type}:{journey.source_id}" if journey.source_id else None,
                        "type": journey.item_type,
                        "title": journey.title,
                        "minutes": int(journey.estimated_minutes or 0),
                        "suggested": is_suggested,
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
            block["items"] = listing.get(block["id"], [])
        computed["day"]["suggested_count"] = suggested
        days.append({"date": current.isoformat(), **computed})
        current += timedelta(days=1)

    return {"employee_id": employee_id, "idle_threshold": idle_threshold, "days": days}
