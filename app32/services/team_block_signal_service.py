"""Sinais por bloco da EQUIPE, para o gestor (Fase 4 da Agenda unificada).

Privacidade (SPEC secao 8.3), garantida pela construcao do resultado:
- o gestor de uma empresa ve, por colaborador: a ocupacao total (todas as empresas), o sinal de cada
  bloco e o consumo dividido em "desta empresa" e "outras empresas";
- itens desta empresa aparecem com titulo; itens/eventos de OUTRAS empresas e eventos avulsos
  aparecem SOMENTE como minutos, nunca com titulo, projeto, processo ou reuniao;
- a soma entre empresas so ocorre para usuarios que migraram para blocos da pessoa; quem nao migrou
  aparece com os blocos legados desta empresa, sem soma entre empresas.

Carga em lote (poucas consultas, independentes do numero de colaboradores).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from models import (
    Employee,
    Meeting,
    PersonWorkBlock,
    WorkCalendarEvent,
    WorkJourneyAgendaItem,
    WorkJourneyBlock,
    WorkJourneyItem,
)
from services.agenda_block_view_service import MAX_DAYS, _CLOSED_ITEM_STATUSES, BlockViewError
from services.block_signal_service import DEFAULT_IDLE_THRESHOLD_MINUTES, compute_block_signals
from services.effective_blocks_service import legacy_block_def, person_block_def
from services.unified_calendar_service import _CLOSED_STATUSES, _meeting_includes_employee

MAX_EMPLOYEES = 300
SOURCE_PERSON = "person"
SOURCE_LEGACY = "legacy"


def _hhmm_to_minutes(value: str) -> int:
    hours, minutes = str(value).split(":")[:2]
    return int(hours) * 60 + int(minutes)


def _time_minutes(value) -> int:
    return value.hour * 60 + value.minute


def build_team_view(
    company_id: int,
    start_date: date,
    end_date: date,
    *,
    idle_threshold: int = DEFAULT_IDLE_THRESHOLD_MINUTES,
) -> dict[str, Any]:
    if end_date < start_date:
        raise BlockViewError("Período inválido.")
    if (end_date - start_date) > timedelta(days=MAX_DAYS):
        raise BlockViewError("Período máximo excedido.")

    team = (
        Employee.query.filter_by(company_id=company_id, status="active")
        .order_by(Employee.name.asc(), Employee.id.asc())
        .limit(MAX_EMPLOYEES)
        .all()
    )
    user_ids = {e.user_id for e in team if e.user_id}
    person_by_user: dict[int, list[PersonWorkBlock]] = {}
    if user_ids:
        for block in (
            PersonWorkBlock.query.filter(PersonWorkBlock.user_id.in_(user_ids), PersonWorkBlock.is_active.is_(True))
            .order_by(PersonWorkBlock.start_time, PersonWorkBlock.order_index, PersonWorkBlock.id)
            .all()
        ):
            person_by_user.setdefault(block.user_id, []).append(block)
    migrated_users = set(person_by_user)

    # Todos os vinculos (todas as empresas) dos usuarios migrados: usados so para SOMAR minutos.
    all_employees = list(team)
    if migrated_users:
        known = {e.id for e in team}
        all_employees += [
            e for e in Employee.query.filter(Employee.user_id.in_(migrated_users), Employee.status == "active").all() if e.id not in known
        ]
    migrated_employee_ids = {e.id for e in all_employees if e.user_id in migrated_users}
    legacy_team = [e for e in team if e.user_id not in migrated_users]
    legacy_ids = {e.id for e in legacy_team}

    legacy_blocks_by_emp: dict[int, list[WorkJourneyBlock]] = {}
    if legacy_ids:
        for block in (
            WorkJourneyBlock.query.filter(
                WorkJourneyBlock.company_id == company_id, WorkJourneyBlock.employee_id.in_(legacy_ids), WorkJourneyBlock.is_active.is_(True)
            )
            .order_by(WorkJourneyBlock.start_time, WorkJourneyBlock.order_index)
            .all()
        ):
            legacy_blocks_by_emp.setdefault(block.employee_id, []).append(block)

    entry_filters = []
    if migrated_employee_ids:
        entry_filters.append(
            (WorkJourneyAgendaItem.employee_id.in_(migrated_employee_ids)) & (WorkJourneyAgendaItem.person_block_id.isnot(None))
        )
    if legacy_ids:
        entry_filters.append(
            (WorkJourneyAgendaItem.company_id == company_id)
            & (WorkJourneyAgendaItem.employee_id.in_(legacy_ids))
            & (WorkJourneyAgendaItem.block_id.isnot(None))
        )
    entries: list[WorkJourneyAgendaItem] = []
    if entry_filters:
        from sqlalchemy import or_

        entries = WorkJourneyAgendaItem.query.filter(
            or_(*entry_filters), WorkJourneyAgendaItem.planned_date >= start_date, WorkJourneyAgendaItem.planned_date <= end_date
        ).all()
    journey_ids = {e.journey_item_id for e in entries if e.journey_item_id}
    journey_by_id = (
        {j.id: j for j in WorkJourneyItem.query.filter(WorkJourneyItem.id.in_(journey_ids)).all()} if journey_ids else {}
    )

    # Eventos com horario (reunioes e avulsos). Nenhum titulo sai deste servico.
    employees_by_company: dict[int, list[Employee]] = {}
    for emp in all_employees:
        if emp.id in migrated_employee_ids or emp.id in legacy_ids:
            employees_by_company.setdefault(emp.company_id, []).append(emp)
    timed_by_emp: dict[int, list[dict[str, Any]]] = {}
    for cid, emps in employees_by_company.items():
        meetings = Meeting.query.filter(
            Meeting.company_id == cid,
            Meeting.scheduled_date.isnot(None),
            Meeting.scheduled_date.between(start_date, end_date),
            Meeting.scheduled_time.isnot(None),
        ).all()
        for meeting in meetings:
            if (meeting.status or "draft").lower() in _CLOSED_STATUSES["meeting"] or not meeting.scheduled_time:
                continue
            for emp in emps:
                if _meeting_includes_employee(meeting, emp):
                    timed_by_emp.setdefault(emp.id, []).append(
                        {"date": meeting.scheduled_date.isoformat(), "start_minutes": _hhmm_to_minutes(meeting.scheduled_time),
                         "duration_minutes": meeting.planned_duration_minutes or 0, "tag": cid}
                    )
    all_ids = migrated_employee_ids | legacy_ids
    if all_ids:
        for row in WorkCalendarEvent.query.filter(
            WorkCalendarEvent.employee_id.in_(all_ids),
            WorkCalendarEvent.source_type == "manual",
            WorkCalendarEvent.event_date.between(start_date, end_date),
            WorkCalendarEvent.start_time.isnot(None),
        ).all():
            if (row.status or "planned").lower() in _CLOSED_STATUSES["manual"]:
                continue
            minutes = (_time_minutes(row.end_time) - _time_minutes(row.start_time)) if row.end_time else 0
            timed_by_emp.setdefault(row.employee_id, []).append(
                {"date": row.event_date.isoformat(), "start_minutes": _time_minutes(row.start_time),
                 "duration_minutes": max(minutes, 0), "tag": row.company_id}
            )

    entries_by_emp: dict[int, list[WorkJourneyAgendaItem]] = {}
    for entry in entries:
        entries_by_emp.setdefault(entry.employee_id, []).append(entry)
    employees_of_user: dict[int, list[int]] = {}
    for emp in all_employees:
        if emp.user_id in migrated_users and emp.status == "active":
            employees_of_user.setdefault(emp.user_id, []).append(emp.id)

    result_employees = []
    for emp in team:
        migrated = emp.user_id in migrated_users
        if migrated:
            blocks = [person_block_def(b) for b in person_by_user[emp.user_id]]
            scope_ids = employees_of_user.get(emp.user_id, [emp.id])
            block_of = lambda e: e.person_block_id
        else:
            blocks = [legacy_block_def(b) for b in legacy_blocks_by_emp.get(emp.id, [])]
            scope_ids = [emp.id]
            block_of = lambda e: e.block_id
        emp_entries = [e for sid in scope_ids for e in entries_by_emp.get(sid, [])]
        emp_events = [ev for sid in scope_ids for ev in timed_by_emp.get(sid, [])]
        days = _employee_days(blocks, emp_entries, emp_events, journey_by_id, company_id, start_date, end_date, idle_threshold, block_of)
        result_employees.append(
            {
                "id": emp.id,
                "name": emp.name,
                "source": SOURCE_PERSON if migrated else SOURCE_LEGACY,
                "days": days,
            }
        )
    return {"company_id": company_id, "idle_threshold": idle_threshold, "employees": result_employees}


def _employee_days(blocks, entries, events, journey_by_id, company_id, start_date, end_date, idle_threshold, block_of) -> list[dict[str, Any]]:
    days = []
    current = start_date
    while current <= end_date:
        day_blocks = [
            {k: b[k] for k in ("id", "name", "mode", "start_minutes", "end_minutes", "start", "end")}
            for b in blocks
            if current.weekday() in b["weekdays"]
        ]
        chosen: dict[int, WorkJourneyAgendaItem] = {}
        for entry in entries:
            if entry.planned_date != current or not entry.journey_item_id:
                continue
            best = chosen.get(entry.journey_item_id)
            if best is None or (bool(entry.manual_override), entry.id) > (bool(best.manual_override), best.id):
                chosen[entry.journey_item_id] = entry
        items = []
        listing: dict[Any, list[dict[str, Any]]] = {}
        for entry in chosen.values():
            journey = journey_by_id.get(entry.journey_item_id)
            if journey is None:
                continue
            if not entry.manual_override and journey.due_date and journey.due_date < current:
                continue
            closed = (journey.status or "") in _CLOSED_ITEM_STATUSES
            items.append(
                {"block_id": block_of(entry), "estimated_minutes": journey.estimated_minutes, "completed": closed, "tag": entry.company_id}
            )
            if not closed and entry.company_id == company_id:
                listing.setdefault(block_of(entry), []).append(
                    {"type": journey.item_type, "title": journey.title, "minutes": int(journey.estimated_minutes or 0)}
                )
        timed = [ev for ev in events if ev["date"] == current.isoformat()]
        computed = compute_block_signals(day_blocks, items, timed, idle_threshold)

        out_blocks = []
        for block in computed["blocks"]:
            by_tag = block.pop("by_tag", {})
            mine = by_tag.get(company_id, 0)
            out_blocks.append(
                {
                    "id": block["id"],
                    "name": block["name"],
                    "start": next(b["start"] for b in day_blocks if b["id"] == block["id"]),
                    "end": next(b["end"] for b in day_blocks if b["id"] == block["id"]),
                    "mode": block["mode"],
                    "capacity_minutes": block["capacity_minutes"],
                    "consumed_minutes": block["consumed_minutes"],
                    "this_company_minutes": mine,
                    "other_companies_minutes": max(block["consumed_minutes"] - mine, 0),
                    "without_estimate": block["without_estimate"],
                    "signal": block["signal"],
                    "items": listing.get(block["id"], []),  # só desta empresa
                }
            )
        day = computed["day"]
        mine_day = sum(b["this_company_minutes"] for b in out_blocks if b["mode"] == "operational")
        days.append(
            {
                "date": current.isoformat(),
                "day": {
                    "state": day["state"],
                    "label": day["label"],
                    "capacity_minutes": day["capacity_minutes"],
                    "consumed_minutes": day["consumed_minutes"],
                    "this_company_minutes": mine_day,
                    "other_companies_minutes": max(day["consumed_minutes"] - mine_day, 0),
                },
                "blocks": out_blocks,
            }
        )
        current += timedelta(days=1)
    return days
