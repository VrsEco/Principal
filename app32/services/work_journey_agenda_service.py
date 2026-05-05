from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import joinedload

from models import (
    Employee,
    ProcessInstance,
    ProcessInstanceExecution,
    WorkCalendarEvent,
    WorkJourneyAgenda,
    WorkJourneyAgendaItem,
    WorkJourneyBlock,
    db,
)
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
    scope: str = 'week',
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
    entry.metadata_json = _updated_entry_metadata(getattr(entry, 'metadata_json', None), payload.get('source_scope'))
    entry.updated_at = datetime.utcnow()
    db.session.add(entry)
    apply_date_change_to_source(entry.journey_item, target_date)
    db.session.commit()
    recompute_agenda_summary(agenda)
    db.session.commit()
    return _serialize(agenda, employee)


def _normalize_scope(scope: str) -> str:
    normalized = str(scope or 'week').strip().lower()
    return normalized if normalized in {'day', 'week'} else 'week'


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
    calendar_events = (
        WorkCalendarEvent.query.options(joinedload(WorkCalendarEvent.block), joinedload(WorkCalendarEvent.employee))
        .filter(WorkCalendarEvent.company_id == agenda.company_id)
        .filter(WorkCalendarEvent.employee_id == agenda.employee_id)
        .filter(WorkCalendarEvent.event_date >= period_start)
        .filter(WorkCalendarEvent.event_date <= period_end)
        .order_by(WorkCalendarEvent.event_date.asc(), WorkCalendarEvent.start_time.asc().nullsfirst(), WorkCalendarEvent.id.asc())
        .all()
    )
    process_instance_cards = _build_process_instance_cards(agenda, entries, calendar_events)
    payload = serialize_agenda_payload(agenda, employee, blocks, entries, calendar_events, process_instance_cards)
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


def _updated_entry_metadata(current_metadata: Any, source_scope: str | None) -> dict[str, Any]:
    metadata = dict(current_metadata or {})
    if source_scope == 'overdue':
        metadata['hide_from_overdue_lane'] = True
    return metadata


INSTANCE_STATUS_LABELS = {
    'pending': 'Pendente',
    'in_progress': 'Em andamento',
    'paused': 'Pausada',
    'waiting_external': 'Aguardando externo',
    'completed': 'Concluída',
    'failed': 'Falhou',
    'cancelled': 'Cancelada',
    'overdue': 'Atrasada',
}

INSTANCE_PRIORITY_LABELS = {
    'low': 'Baixa',
    'normal': 'Normal',
    'high': 'Alta',
    'urgent': 'Urgente',
}

EXECUTION_STATUS_LABELS = {
    'pending': 'Pendente',
    'ready': 'Pronta',
    'in_progress': 'Em execução',
    'paused': 'Pausada',
    'waiting_external': 'Aguardando externo',
    'completed': 'Concluída',
    'failed': 'Falhou',
    'skipped': 'Ignorada',
}

EXECUTION_MODE_LABELS = {
    'human_task': 'Humana',
    'manual_external': 'Humana externa',
    'automatic': 'Automática',
    'external_rest': 'Integração REST',
    'external_mcp': 'Integração MCP',
}

ACTIVE_EXECUTION_PRIORITY = {
    'in_progress': 0,
    'ready': 1,
    'waiting_external': 2,
    'paused': 3,
    'pending': 4,
    'completed': 9,
    'failed': 10,
    'skipped': 11,
}

ACTIVE_HUMAN_EXECUTION_MODES = {'human_task', 'manual_external'}


def _build_process_instance_cards(
    agenda: WorkJourneyAgenda,
    entries: list[WorkJourneyAgendaItem],
    calendar_events: list[WorkCalendarEvent],
) -> list[dict[str, Any]]:
    instance_ids = {
        int(entry.journey_item.source_id)
        for entry in entries
        if getattr(entry, 'journey_item', None)
        and getattr(entry.journey_item, 'item_type', None) == 'process_instance'
        and getattr(entry.journey_item, 'source_id', None)
    }
    instance_ids.update(
        int(event.source_id)
        for event in calendar_events
        if str(getattr(event, 'source_type', '') or '').strip().lower() == 'process_instance'
        and getattr(event, 'source_id', None)
    )
    if not instance_ids:
        return []

    items_by_instance: dict[int, list[Any]] = defaultdict(list)
    entry_counts_by_instance: dict[int, int] = defaultdict(int)
    event_counts_by_instance: dict[int, int] = defaultdict(int)
    for entry in entries:
        item = getattr(entry, 'journey_item', None)
        if not item or getattr(item, 'item_type', None) != 'process_instance' or not getattr(item, 'source_id', None):
            continue
        source_id = int(item.source_id)
        items_by_instance[source_id].append(item)
        entry_counts_by_instance[source_id] += 1
    for event in calendar_events:
        if str(getattr(event, 'source_type', '') or '').strip().lower() != 'process_instance' or not getattr(event, 'source_id', None):
            continue
        event_counts_by_instance[int(event.source_id)] += 1

    instances = (
        ProcessInstance.query.options(joinedload(ProcessInstance.process_rel), joinedload(ProcessInstance.routine))
        .filter(ProcessInstance.company_id == agenda.company_id)
        .filter(ProcessInstance.id.in_(list(instance_ids)))
        .all()
    )
    executions = (
        ProcessInstanceExecution.query
        .filter(ProcessInstanceExecution.company_id == agenda.company_id)
        .filter(ProcessInstanceExecution.process_instance_id.in_(list(instance_ids)))
        .order_by(
            ProcessInstanceExecution.process_instance_id.asc(),
            ProcessInstanceExecution.updated_at.desc(),
            ProcessInstanceExecution.id.desc(),
        )
        .all()
    )
    executions_by_instance: dict[int, list[ProcessInstanceExecution]] = defaultdict(list)
    for execution in executions:
        executions_by_instance[int(execution.process_instance_id)].append(execution)

    cards = [
        _serialize_process_instance_card(
            instance,
            executions_by_instance.get(int(instance.id), []),
            items_by_instance.get(int(instance.id), []),
            entry_counts_by_instance.get(int(instance.id), 0),
            event_counts_by_instance.get(int(instance.id), 0),
        )
        for instance in instances
    ]
    cards.sort(
        key=lambda card: (
            0 if card.get('is_instance_overdue') else 1,
            card.get('instance_due_date') or '9999-12-31',
            str(card.get('instance_title') or '').lower(),
        )
    )
    return cards


def _serialize_process_instance_card(
    instance: ProcessInstance,
    executions: list[ProcessInstanceExecution],
    related_items: list[Any],
    agenda_entry_count: int,
    linked_event_count: int,
) -> dict[str, Any]:
    current_execution = _select_current_execution(executions, instance.current_bpmn_element_id)
    current_activity = _serialize_current_activity(current_execution, instance)
    source_metadata = dict((related_items[0].metadata_json or {}) if related_items else {})
    instance_due_label = _format_date_label(instance.due_date)
    return {
        'id': f'instance-{instance.id}',
        'instance_id': int(instance.id),
        'instance_code': instance.instance_code or f'IP.{instance.id}',
        'instance_title': instance.title,
        'instance_description': instance.description,
        'instance_status': instance.status,
        'instance_status_label': INSTANCE_STATUS_LABELS.get(instance.status, instance.status),
        'instance_priority': instance.priority,
        'instance_priority_label': INSTANCE_PRIORITY_LABELS.get(instance.priority, instance.priority),
        'instance_due_date': instance.due_date.isoformat() if instance.due_date else None,
        'instance_due_label': instance_due_label,
        'is_instance_overdue': bool(instance.due_date and instance.due_date < date.today() and instance.status != 'completed'),
        'is_instance_due_today': bool(instance.due_date and instance.due_date == date.today()),
        'process_id': instance.process_id,
        'process_name': instance.process_rel.name if instance.process_rel else None,
        'process_code': instance.process_rel.code if instance.process_rel else None,
        'routine_id': instance.routine_id,
        'routine_name': getattr(instance.routine, 'name', None) if getattr(instance, 'routine', None) else None,
        'source_url': source_metadata.get('source_url') or f'/companies/{instance.company_id}/process-instances?instance_id={instance.id}&from=work-journey',
        'agenda_entry_count': int(agenda_entry_count or 0),
        'linked_event_count': int(linked_event_count or 0),
        'current_activity': current_activity,
    }


def _select_current_execution(
    executions: list[ProcessInstanceExecution],
    current_bpmn_element_id: str | None,
) -> ProcessInstanceExecution | None:
    if not executions:
        return None
    active_executions = [
        execution
        for execution in executions
        if str(getattr(execution, 'status', '') or '').strip().lower() not in {'completed', 'failed', 'skipped'}
    ]
    if not active_executions:
        return None

    prioritized = [
        execution
        for execution in active_executions
        if str(getattr(execution, 'execution_mode', '') or '').strip().lower() in ACTIVE_HUMAN_EXECUTION_MODES
    ] or active_executions

    matching_current = [
        execution
        for execution in prioritized
        if current_bpmn_element_id and str(getattr(execution, 'bpmn_element_id', '') or '').strip() == str(current_bpmn_element_id).strip()
    ]
    pool = matching_current or prioritized
    return min(
        pool,
        key=lambda execution: (
            ACTIVE_EXECUTION_PRIORITY.get(str(getattr(execution, 'status', '') or '').strip().lower(), 99),
            0 if str(getattr(execution, 'execution_mode', '') or '').strip().lower() in ACTIVE_HUMAN_EXECUTION_MODES else 1,
            -(getattr(execution, 'id', 0) or 0),
        ),
    )


def _serialize_current_activity(
    execution: ProcessInstanceExecution | None,
    instance: ProcessInstance,
) -> dict[str, Any]:
    if not execution:
        fallback_label = str(instance.current_bpmn_element_id or 'Sem atividade ativa').strip()
        return {
            'activity_name': fallback_label,
            'activity_code': instance.current_bpmn_element_id,
            'activity_status': 'pending',
            'activity_status_label': 'Aguardando ativação',
            'activity_due_at': None,
            'activity_due_date': None,
            'activity_due_label': 'Sem prazo definido',
            'activity_execution_mode': None,
            'activity_execution_mode_label': 'Sem execução ativa',
            'is_activity_overdue': False,
            'execution_id': None,
        }

    due_payload = _resolve_execution_due(execution)
    execution_mode = str(getattr(execution, 'execution_mode', '') or '').strip().lower()
    status = str(getattr(execution, 'status', '') or '').strip().lower()
    return {
        'activity_name': execution.bpmn_element_name or execution.bpmn_element_id,
        'activity_code': execution.bpmn_element_id,
        'activity_type': execution.bpmn_element_type,
        'activity_status': status,
        'activity_status_label': EXECUTION_STATUS_LABELS.get(status, status),
        'activity_due_at': due_payload.get('activity_due_at'),
        'activity_due_date': due_payload.get('activity_due_date'),
        'activity_due_label': due_payload.get('activity_due_label') or 'Sem prazo definido',
        'activity_execution_mode': execution_mode or None,
        'activity_execution_mode_label': EXECUTION_MODE_LABELS.get(execution_mode, execution_mode or 'Execução'),
        'is_activity_overdue': bool(due_payload.get('is_activity_overdue')),
        'execution_id': int(execution.id),
    }


def _resolve_execution_due(execution: ProcessInstanceExecution) -> dict[str, Any]:
    metadata = dict(getattr(execution, 'metadata_json', None) or {})
    datetime_keys = ('due_at', 'deadline_at', 'target_at', 'scheduled_at')
    date_keys = ('due_date', 'deadline_date', 'target_date')

    for key in datetime_keys:
        parsed = _parse_datetime_value(metadata.get(key))
        if parsed:
            return {
                'activity_due_at': parsed.isoformat(),
                'activity_due_date': parsed.date().isoformat(),
                'activity_due_label': parsed.strftime('%d/%m/%Y %H:%M'),
                'is_activity_overdue': parsed < datetime.utcnow(),
            }

    for key in date_keys:
        parsed_date = _parse_date_value(metadata.get(key))
        if parsed_date:
            return {
                'activity_due_at': None,
                'activity_due_date': parsed_date.isoformat(),
                'activity_due_label': parsed_date.strftime('%d/%m/%Y'),
                'is_activity_overdue': parsed_date < date.today(),
            }

    sla_minutes = metadata.get('sla_minutes')
    anchor = execution.waiting_since or execution.started_at or execution.created_at
    if anchor and sla_minutes not in (None, ''):
        try:
            due_at = anchor + timedelta(minutes=int(sla_minutes))
        except (TypeError, ValueError):
            due_at = None
        if due_at:
            return {
                'activity_due_at': due_at.isoformat(),
                'activity_due_date': due_at.date().isoformat(),
                'activity_due_label': due_at.strftime('%d/%m/%Y %H:%M'),
                'is_activity_overdue': due_at < datetime.utcnow(),
            }

    return {
        'activity_due_at': None,
        'activity_due_date': None,
        'activity_due_label': None,
        'is_activity_overdue': False,
    }


def _parse_datetime_value(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    normalized = raw.replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed


def _parse_date_value(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    parsed = _parse_datetime_value(value)
    if parsed:
        return parsed.date()
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _format_date_label(value: date | None) -> str | None:
    return value.strftime('%d/%m/%Y') if value else None
