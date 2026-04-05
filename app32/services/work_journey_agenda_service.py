from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import joinedload

from models import Employee, WorkJourneyAgenda, WorkJourneyAgendaItem, WorkJourneyBlock, db
from services.work_journey_agenda_engine import (
    allocate_item,
    apply_date_change_to_source,
    load_blocks_by_day,
    load_source_items,
    next_position_for_group,
    recompute_agenda_summary,
    shift_positions_before_insert,
)
from services.work_journey_agenda_presenter import serialize_agenda_payload
from services.work_journey_base import WorkJourneyError, ensure_employee
from services.work_journey_helpers import clamp_period
from services.work_journey_service import sync_work_journey_items

AGENDA_ENGINE_VERSION = 'agendas-v1'


def get_work_journey_agenda(
    company_id: int,
    employee_id: int,
    anchor: date,
    scope: str = 'day',
    force_regenerate: bool = False,
) -> dict[str, Any]:
    employee = ensure_employee(company_id, employee_id)
    agenda = _get_or_build_agenda(company_id, employee.id, anchor, _normalize_scope(scope), force_regenerate)
    return _serialize(agenda, employee)


def lock_work_journey_agenda(company_id: int, employee_id: int, anchor: date, scope: str, user_id: int | None = None) -> dict[str, Any]:
    employee = ensure_employee(company_id, employee_id)
    agenda = _get_or_build_agenda(company_id, employee.id, anchor, _normalize_scope(scope), False)
    agenda.status = 'locked'
    agenda.locked_at = datetime.utcnow()
    agenda.locked_by_user_id = user_id
    agenda.updated_at = datetime.utcnow()
    db.session.add(agenda)
    db.session.commit()
    return _serialize(agenda, employee)


def unlock_work_journey_agenda(company_id: int, employee_id: int, anchor: date, scope: str) -> dict[str, Any]:
    employee = ensure_employee(company_id, employee_id)
    agenda = _get_or_build_agenda(company_id, employee.id, anchor, _normalize_scope(scope), False)
    agenda.status = 'suggested'
    agenda.locked_at = None
    agenda.locked_by_user_id = None
    agenda.updated_at = datetime.utcnow()
    db.session.add(agenda)
    db.session.commit()
    return _serialize(agenda, employee)


def move_work_journey_agenda_item(
    company_id: int,
    employee_id: int,
    anchor: date,
    scope: str,
    agenda_item_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    employee = ensure_employee(company_id, employee_id)
    entry = (
        WorkJourneyAgendaItem.query.options(joinedload(WorkJourneyAgendaItem.journey_item), joinedload(WorkJourneyAgendaItem.agenda))
        .filter_by(company_id=company_id, employee_id=employee.id, id=agenda_item_id)
        .first()
    )
    if not entry:
        raise WorkJourneyError('Item da agenda não encontrado.')

    agenda = entry.agenda
    if not agenda:
        raise WorkJourneyError('Agenda não encontrada para o item informado.')
    if agenda.status == 'locked':
        raise WorkJourneyError('A agenda está travada. Cancele o travamento para continuar.')
    if not entry.journey_item:
        raise WorkJourneyError('A origem da tarefa não está mais disponível.')
    if entry.journey_item.item_type == 'meeting':
        raise WorkJourneyError('Reuniões não podem ser arrastadas. Altere no módulo de reuniões.')

    target_date = payload['target_date']
    if entry.planned_date != target_date and not payload.get('confirm_date_change'):
        raise WorkJourneyError('Confirme a alteração de data antes de mover a tarefa para outro dia.')

    target_block = _resolve_target_block(company_id, employee.id, target_date, entry.journey_item.item_type, payload.get('block_id'))
    target_block_id = target_block.id if target_block else None
    shift_positions_before_insert(agenda.id, target_date, target_block_id, int(payload.get('position_index') or 0), exclude_item_id=entry.id)

    entry.planned_date = target_date
    entry.block_id = target_block_id
    entry.position_index = int(payload.get('position_index') or 0)
    entry.manual_override = True
    entry.updated_at = datetime.utcnow()
    db.session.add(entry)
    apply_date_change_to_source(entry.journey_item, target_date)
    db.session.commit()
    recompute_agenda_summary(agenda)
    db.session.commit()
    return _serialize(agenda, employee)


def _normalize_scope(scope: str) -> str:
    normalized = str(scope or 'day').strip().lower()
    return normalized if normalized in {'day', 'week'} else 'day'


def _get_or_build_agenda(company_id: int, employee_id: int, anchor: date, scope: str, force_regenerate: bool) -> WorkJourneyAgenda:
    agenda = WorkJourneyAgenda.query.filter_by(
        company_id=company_id,
        employee_id=employee_id,
        anchor_date=anchor,
        scope=scope,
    ).first()
    if not agenda:
        agenda = WorkJourneyAgenda(
            company_id=company_id,
            employee_id=employee_id,
            anchor_date=anchor,
            scope=scope,
            status='suggested',
            engine_version=AGENDA_ENGINE_VERSION,
        )
        db.session.add(agenda)
        db.session.flush()
        force_regenerate = True

    if agenda.status == 'locked':
        _append_new_unassigned_items_for_locked_agenda(agenda)
        recompute_agenda_summary(agenda)
        db.session.commit()
        return agenda

    _build_agenda_snapshot(agenda)
    db.session.commit()
    return agenda


def _append_new_unassigned_items_for_locked_agenda(agenda: WorkJourneyAgenda) -> None:
    period_start, period_end = clamp_period(agenda.scope, agenda.anchor_date)
    sync_work_journey_items(agenda.company_id, agenda.employee_id, period_start, period_end)
    source_items = load_source_items(agenda.company_id, agenda.employee_id, period_start, period_end)
    existing_keys = {entry.journey_item_id for entry in agenda.items if entry.journey_item_id}
    for item in source_items:
        if item.id in existing_keys:
            continue
        planned_date = item.occurrence_date or item.due_date or agenda.anchor_date
        db.session.add(
            WorkJourneyAgendaItem(
                agenda_id=agenda.id,
                company_id=agenda.company_id,
                employee_id=agenda.employee_id,
                journey_item_id=item.id,
                block_id=None,
                planned_date=planned_date,
                position_index=next_position_for_group(agenda.id, planned_date, None),
                allocated_minutes=int(item.estimated_minutes or 0),
                overflow_minutes=0,
                is_fixed=False,
                is_over_capacity=False,
                manual_override=False,
                metadata_json={'new_after_lock': True},
            )
        )


def _build_agenda_snapshot(agenda: WorkJourneyAgenda) -> None:
    period_start, period_end = clamp_period(agenda.scope, agenda.anchor_date)
    sync_work_journey_items(agenda.company_id, agenda.employee_id, period_start, period_end + timedelta(days=7))
    source_items = load_source_items(agenda.company_id, agenda.employee_id, period_start, period_end)
    blocks_by_day = load_blocks_by_day(agenda.company_id, agenda.employee_id, period_start, period_end)
    preserved_entries = _preserve_manual_entries(agenda)
    used_capacity: dict[tuple[date, int], int] = defaultdict(int)
    new_entries: list[WorkJourneyAgendaItem] = []

    for item in source_items:
        if item.id in preserved_entries:
            preserved = preserved_entries[item.id]
            new_entries.extend(preserved)
            for entry in preserved:
                if entry.block_id:
                    used_capacity[(entry.planned_date, entry.block_id)] += int(entry.allocated_minutes or 0)
            continue
        new_entries.extend(allocate_item(item, agenda, blocks_by_day, used_capacity, period_start, period_end))

    WorkJourneyAgendaItem.query.filter_by(agenda_id=agenda.id, company_id=agenda.company_id).delete()
    for entry in new_entries:
        db.session.add(entry)

    agenda.generated_at = datetime.utcnow()
    agenda.updated_at = datetime.utcnow()
    agenda.engine_version = AGENDA_ENGINE_VERSION
    agenda.status = 'suggested'
    recompute_agenda_summary(agenda, new_entries)


def _preserve_manual_entries(agenda: WorkJourneyAgenda) -> dict[int, list[WorkJourneyAgendaItem]]:
    preserved: dict[int, list[WorkJourneyAgendaItem]] = defaultdict(list)
    for entry in agenda.items:
        if not entry.journey_item_id or not entry.manual_override:
            continue
        preserved[entry.journey_item_id].append(
            WorkJourneyAgendaItem(
                agenda_id=agenda.id,
                company_id=agenda.company_id,
                employee_id=agenda.employee_id,
                journey_item_id=entry.journey_item_id,
                block_id=entry.block_id,
                planned_date=entry.planned_date,
                position_index=entry.position_index,
                allocated_minutes=entry.allocated_minutes,
                planned_start_minutes=entry.planned_start_minutes,
                planned_end_minutes=entry.planned_end_minutes,
                overflow_minutes=entry.overflow_minutes,
                is_fixed=entry.is_fixed,
                is_over_capacity=entry.is_over_capacity,
                manual_override=True,
                metadata_json=dict(entry.metadata_json or {}),
            )
        )
    return preserved


def _resolve_target_block(company_id: int, employee_id: int, target_date: date, item_type: str, block_id: int | None) -> WorkJourneyBlock | None:
    if not block_id:
        return None
    target_block = WorkJourneyBlock.query.filter_by(
        company_id=company_id,
        employee_id=employee_id,
        id=block_id,
        is_active=True,
    ).first()
    if not target_block:
        raise WorkJourneyError('Bloco de destino inválido para o colaborador informado.')
    if target_block.block_mode == 'reserved_full':
        raise WorkJourneyError('Blocos com capacidade ocupada não aceitam tarefas.')
    if item_type not in (target_block.accepted_item_types or []):
        raise WorkJourneyError('O bloco informado não aceita este tipo de tarefa.')
    if target_date.weekday() not in (target_block.weekdays_json or []):
        raise WorkJourneyError('O bloco informado não está ativo para o dia selecionado.')
    return target_block


def _serialize(agenda: WorkJourneyAgenda, employee: Employee) -> dict[str, Any]:
    period_start, period_end = clamp_period(agenda.scope, agenda.anchor_date)
    blocks = (
        WorkJourneyBlock.query.filter_by(company_id=agenda.company_id, employee_id=agenda.employee_id, is_active=True)
        .order_by(WorkJourneyBlock.order_index.asc(), WorkJourneyBlock.start_time.asc(), WorkJourneyBlock.id.asc())
        .all()
    )
    entries = (
        WorkJourneyAgendaItem.query.options(joinedload(WorkJourneyAgendaItem.journey_item), joinedload(WorkJourneyAgendaItem.block))
        .filter_by(company_id=agenda.company_id, agenda_id=agenda.id)
        .order_by(WorkJourneyAgendaItem.planned_date.asc(), WorkJourneyAgendaItem.position_index.asc(), WorkJourneyAgendaItem.id.asc())
        .all()
    )
    payload = serialize_agenda_payload(agenda, employee, blocks, entries)
    payload['agenda'] = agenda.to_dict()
    payload['agenda']['locked_by_name'] = payload['agenda'].get('locked_by_name') or payload.get('locked_by_name')
    payload['agenda']['locked'] = agenda.status == 'locked'
    payload['agenda']['is_locked'] = agenda.status == 'locked'
    payload['agenda']['employee_name'] = employee.name
    payload['employee_id'] = employee.id
    payload['company_id'] = agenda.company_id
    payload['scope'] = agenda.scope
    payload['anchor_date'] = agenda.anchor_date.isoformat()
    payload['period_start'] = period_start.isoformat()
    payload['period_end'] = period_end.isoformat()
    payload['status'] = agenda.status
    payload['locked'] = agenda.status == 'locked'
    payload['locked_at'] = agenda.locked_at.isoformat() if agenda.locked_at else None
    payload['locked_by_name'] = payload['agenda'].get('locked_by_name')
    payload['engine_version'] = agenda.engine_version
    payload['summary'] = payload.get('summary') or dict(agenda.summary_json or {})
    payload['agenda']['summary_json'] = dict(agenda.summary_json or {})
    return payload
