from __future__ import annotations

from datetime import date, datetime
from typing import Any

from models import Company, db, Employee, WorkJourneyBlock, WorkJourneyItem, WorkJourneyRule
from services.work_journey_base import WorkJourneyError, ensure_employee, is_actionable_status
from services.work_journey_helpers import (
    BLOCK_MODE_LABELS,
    ITEM_TYPE_LABELS,
    PRIORITY_ORDER,
    STATUS_LABELS,
    block_chronology_key,
    clamp_period,
    duration_minutes,
)
from services.work_journey_sync import (
    load_period_items,
    propagate_item_status,
    sync_meetings,
    sync_process_instances,
    sync_project_tasks,
)


def list_employee_blocks(company_id: int, employee_id: int) -> list[dict[str, Any]]:
    ensure_employee(company_id, employee_id)
    blocks = WorkJourneyBlock.query.filter_by(company_id=company_id, employee_id=employee_id).all()
    blocks = sorted(blocks, key=block_chronology_key)
    return [block.to_dict() for block in blocks]


def save_block(company_id: int, payload: dict[str, Any], block_id: int | None = None) -> dict[str, Any]:
    employee = ensure_employee(company_id, payload['employee_id'])
    block = (
        WorkJourneyBlock.query.filter_by(company_id=company_id, id=block_id).first()
        if block_id
        else WorkJourneyBlock(company_id=company_id, employee_id=employee.id)
    )
    if block_id and not block:
        raise WorkJourneyError('Bloco não encontrado.')

    block.employee_id = employee.id
    block.name = payload['name']
    block.description = payload.get('description') or None
    block.start_time = datetime.strptime(payload['start_time'], '%H:%M').time()
    block.end_time = datetime.strptime(payload['end_time'], '%H:%M').time()
    block.block_mode = payload.get('block_mode') or 'operational'
    block.weekdays_json = payload.get('weekdays') or [0, 1, 2, 3, 4]
    accepted_item_types = payload.get('accepted_item_types')
    if accepted_item_types is None:
        accepted_item_types = ['manual', 'process_instance', 'project_task', 'meeting']
    block.accepted_item_types = list(accepted_item_types)
    block.order_index = int(payload.get('order_index') or 0)
    block.is_active = bool(payload.get('is_active', True))

    if duration_minutes(block.start_time, block.end_time) <= 0:
        raise WorkJourneyError('O horário final do bloco deve ser maior que o horário inicial.')

    db.session.add(block)
    db.session.commit()
    return block.to_dict()


def delete_block(company_id: int, block_id: int) -> None:
    block = WorkJourneyBlock.query.filter_by(company_id=company_id, id=block_id).first()
    if not block:
        raise WorkJourneyError('Bloco não encontrado.')
    db.session.delete(block)
    db.session.commit()


def list_employee_rules(company_id: int, employee_id: int) -> list[dict[str, Any]]:
    ensure_employee(company_id, employee_id)
    rules = (
        WorkJourneyRule.query.filter_by(company_id=company_id, employee_id=employee_id)
        .order_by(WorkJourneyRule.title.asc(), WorkJourneyRule.id.asc())
        .all()
    )
    return [rule.to_dict() for rule in rules]


def list_manual_tasks(company_id: int, employee_id: int) -> dict[str, Any]:
    ensure_employee(company_id, employee_id)
    items = (
        WorkJourneyItem.query.filter(
            WorkJourneyItem.company_id == company_id,
            WorkJourneyItem.employee_id == employee_id,
            WorkJourneyItem.item_type == 'manual',
            WorkJourneyItem.rule_id.is_(None),
            WorkJourneyItem.source_id.is_(None),
        )
        .order_by(WorkJourneyItem.due_date.desc().nullslast(), WorkJourneyItem.updated_at.desc(), WorkJourneyItem.id.desc())
        .all()
    )
    serialized = [serialize_item(item) for item in items]
    return {
        'items': serialized,
        'summary': {
            'total_count': len(serialized),
            'completed_count': len([item for item in items if item.status == 'completed']),
            'pending_count': len([item for item in items if item.status != 'completed']),
            'planned_minutes': sum(int(item.estimated_minutes or 0) for item in items),
            'worked_minutes': sum(int(item.worked_minutes or 0) for item in items),
        },
    }


def save_rule(company_id: int, payload: dict[str, Any], rule_id: int | None = None) -> dict[str, Any]:
    employee = ensure_employee(company_id, payload['employee_id'])
    rule = (
        WorkJourneyRule.query.filter_by(company_id=company_id, id=rule_id).first()
        if rule_id
        else WorkJourneyRule(company_id=company_id, employee_id=employee.id)
    )
    if rule_id and not rule:
        raise WorkJourneyError('Obrigação recorrente não encontrada.')

    preferred_block_id = payload.get('preferred_block_id')
    if preferred_block_id:
        block = WorkJourneyBlock.query.filter_by(company_id=company_id, id=preferred_block_id, employee_id=employee.id).first()
        if not block:
            raise WorkJourneyError('Bloco preferencial inválido para o colaborador.')
        rule.preferred_block_id = block.id
    else:
        rule.preferred_block_id = None

    rule.employee_id = employee.id
    rule.title = payload['title']
    rule.description = payload.get('description') or None
    rule.item_type = payload['item_type']
    rule.recurrence_type = payload['recurrence_type']
    rule.recurrence_config = dict(payload.get('recurrence_config') or {})
    rule.estimated_minutes = int(payload['estimated_minutes'])
    rule.priority = payload['priority']
    rule.start_date = payload.get('start_date')
    rule.end_date = payload.get('end_date')
    rule.is_active = bool(payload.get('is_active', True))

    db.session.add(rule)
    db.session.commit()
    return rule.to_dict()


def delete_rule(company_id: int, rule_id: int) -> None:
    rule = WorkJourneyRule.query.filter_by(company_id=company_id, id=rule_id).first()
    if not rule:
        raise WorkJourneyError('Obrigação recorrente não encontrada.')
    db.session.delete(rule)
    db.session.commit()


def get_work_journey_board(company_id: int, employee_id: int, anchor: date, scope: str = 'week') -> dict[str, Any]:
    employee = ensure_employee(company_id, employee_id)
    period_start, period_end = clamp_period(scope, anchor)
    sync_work_journey_items(company_id, employee_id, period_start, period_end)

    blocks = WorkJourneyBlock.query.filter_by(company_id=company_id, employee_id=employee_id, is_active=True).all()
    blocks = sorted(blocks, key=block_chronology_key)
    weekday = anchor.weekday()
    active_blocks = [block for block in blocks if weekday in (block.weekdays_json or [])]

    items = load_period_items(company_id, employee_id, period_start, period_end)
    items = [item for item in items if is_actionable_status(item.status)]
    suggest_blocks(active_blocks, items, anchor)

    board_blocks = []
    for block in active_blocks:
        block_items = [item for item in items if item.block_id == block.id and item_matches_anchor(item, anchor, scope)]
        capacity_minutes = duration_minutes(block.start_time, block.end_time)
        task_minutes = sum(int(item.estimated_minutes or 0) for item in block_items)
        fixed_reserved_minutes = capacity_minutes if block.block_mode == 'reserved_full' else 0
        block_payload = block.to_dict()
        block_payload['capacity_minutes'] = capacity_minutes
        block_payload['operational_capacity_minutes'] = 0 if block.block_mode == 'reserved_full' else capacity_minutes
        block_payload['fixed_reserved_minutes'] = fixed_reserved_minutes
        block_payload['planned_task_minutes'] = task_minutes
        block_payload['planned_minutes'] = task_minutes + fixed_reserved_minutes
        block_payload['worked_minutes'] = sum(int(item.worked_minutes or 0) for item in block_items)
        block_payload['block_mode_label'] = BLOCK_MODE_LABELS.get(block.block_mode, block.block_mode)
        block_payload['items'] = [serialize_item(item) for item in sorted(block_items, key=item_sort_key)]
        board_blocks.append(block_payload)

    unassigned = [serialize_item(item) for item in sorted(items, key=item_sort_key) if not item.block_id and item_matches_anchor(item, anchor, scope)]
    summary = build_summary(employee, active_blocks, items, anchor, scope)

    return {
        'employee': employee.to_dict(),
        'anchor_date': anchor.isoformat(),
        'scope': scope,
        'period_start': period_start.isoformat(),
        'period_end': period_end.isoformat(),
        'summary': summary,
        'blocks': board_blocks,
        'unassigned_items': unassigned,
        'period_items': [serialize_item(item) for item in sorted(items, key=item_sort_key)],
        'available_item_types': ITEM_TYPE_LABELS,
        'status_labels': STATUS_LABELS,
    }


def sync_work_journey_items(company_id: int, employee_id: int, period_start: date, period_end: date) -> None:
    ensure_employee(company_id, employee_id)
    sync_process_instances(company_id, employee_id, period_start, period_end)
    sync_project_tasks(company_id, employee_id, period_start, period_end)
    sync_meetings(company_id, employee_id, period_start, period_end)
    db.session.commit()


def update_work_item(company_id: int, item_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    item = WorkJourneyItem.query.filter_by(company_id=company_id, id=item_id).first()
    if not item:
        raise WorkJourneyError('Tarefa não encontrada.')

    if 'block_id' in payload:
        block_id = payload.get('block_id')
        if block_id:
            block = WorkJourneyBlock.query.filter_by(company_id=company_id, id=block_id, employee_id=item.employee_id).first()
            if not block:
                raise WorkJourneyError('Bloco inválido para o colaborador da tarefa.')
            if block.block_mode == 'reserved_full':
                raise WorkJourneyError('Blocos com capacidade ocupada não aceitam tarefas.')
            if item.item_type not in (block.accepted_item_types or []):
                raise WorkJourneyError('O bloco informado não aceita este tipo de tarefa.')
            item.block_id = block.id
        else:
            item.block_id = None

    if item.item_type == 'manual' and item.rule_id is None:
        if payload.get('title') is not None:
            item.title = str(payload['title']).strip()
        if payload.get('description') is not None:
            item.description = payload.get('description') or None
        if payload.get('due_date') is not None:
            item.due_date = payload.get('due_date')
            item.occurrence_date = payload.get('due_date')
        if payload.get('estimated_minutes') is not None:
            item.estimated_minutes = int(payload['estimated_minutes'])
        if payload.get('priority') is not None:
            item.priority = payload['priority']

    if payload.get('worked_minutes') is not None:
        item.worked_minutes = int(payload['worked_minutes'])

    if payload.get('status'):
        item.status = payload['status']
        if item.status == 'completed':
            item.completed_at = datetime.utcnow()
        elif item.status != 'completed':
            item.completed_at = None
        propagate_item_status(item)

    if payload.get('notes') is not None:
        metadata = dict(item.metadata_json or {})
        metadata['board_notes'] = payload.get('notes') or ''
        item.metadata_json = metadata

    item.updated_at = datetime.utcnow()
    db.session.add(item)
    db.session.commit()
    return serialize_item(item)


def create_manual_task(company_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    employee = ensure_employee(company_id, payload['employee_id'])
    block_id = payload.get('block_id')
    block = None
    if block_id:
        block = WorkJourneyBlock.query.filter_by(company_id=company_id, id=block_id, employee_id=employee.id, is_active=True).first()
        if not block:
            raise WorkJourneyError('Bloco inválido para o colaborador informado.')
        if block.block_mode == 'reserved_full':
            raise WorkJourneyError('Blocos com capacidade ocupada não aceitam tarefas.')
        if 'manual' not in (block.accepted_item_types or []):
            raise WorkJourneyError('O bloco informado não aceita tarefa avulsa.')

    due_date = payload['due_date']
    item = WorkJourneyItem(
        company_id=company_id,
        employee_id=employee.id,
        block_id=block.id if block else None,
        item_type='manual',
        title=payload['title'],
        description=payload.get('description') or None,
        occurrence_date=due_date,
        due_date=due_date,
        estimated_minutes=int(payload['estimated_minutes']),
        worked_minutes=int(payload.get('worked_minutes') or 0),
        priority=payload['priority'],
        status=payload.get('status') or 'pending',
        metadata_json={'source_label': 'Tarefa Avulsa'},
    )
    if item.status == 'completed':
        item.completed_at = datetime.utcnow()

    db.session.add(item)
    db.session.commit()
    return serialize_item(item)


def delete_work_item(company_id: int, item_id: int) -> None:
    item = WorkJourneyItem.query.filter_by(company_id=company_id, id=item_id).first()
    if not item:
        raise WorkJourneyError('Tarefa não encontrada.')
    if item.item_type != 'manual' or item.source_id or item.rule_id:
        raise WorkJourneyError('Somente tarefas avulsas podem ser excluídas diretamente na jornada.')
    db.session.delete(item)
    db.session.commit()


def suggest_blocks(blocks: list[WorkJourneyBlock], items: list[WorkJourneyItem], anchor: date) -> None:
    if not blocks:
        return
    for item in items:
        if item.block_id or not item_matches_anchor(item, anchor, 'day'):
            continue
        preferred = item.rule.preferred_block_id if item.rule else None
        candidates = [
            block for block in blocks
            if block.block_mode == 'operational' and item.item_type in (block.accepted_item_types or [])
        ]
        if preferred and any(block.id == preferred for block in candidates):
            item.block_id = preferred
        elif candidates:
            item.block_id = candidates[0].id


def build_summary(employee: Employee, blocks: list[WorkJourneyBlock], items: list[WorkJourneyItem], anchor: date, scope: str) -> dict[str, Any]:
    relevant = [item for item in items if item_matches_anchor(item, anchor, scope)]
    operational_capacity_minutes = sum(
        duration_minutes(block.start_time, block.end_time)
        for block in blocks
        if block.block_mode != 'reserved_full'
    )
    reserved_minutes = sum(
        duration_minutes(block.start_time, block.end_time)
        for block in blocks
        if block.block_mode == 'reserved_full'
    )
    buffer_minutes = sum(
        duration_minutes(block.start_time, block.end_time)
        for block in blocks
        if block.block_mode == 'buffer'
    )
    planned_minutes = sum(int(item.estimated_minutes or 0) for item in relevant)
    worked_minutes = sum(int(item.worked_minutes or 0) for item in relevant)
    overload_minutes = max(planned_minutes - operational_capacity_minutes, 0)
    return {
        'weekly_capacity_minutes': int(float(employee.weekly_hours or 0) * 60),
        'daily_capacity_minutes': operational_capacity_minutes,
        'reserved_minutes': reserved_minutes,
        'buffer_minutes': buffer_minutes,
        'planned_minutes': planned_minutes,
        'worked_minutes': worked_minutes,
        'overload_minutes': overload_minutes,
        'pending_count': len([item for item in relevant if item.status != 'completed']),
        'completed_count': len([item for item in relevant if item.status == 'completed']),
    }


def serialize_item(item: WorkJourneyItem) -> dict[str, Any]:
    payload = item.to_dict()
    display_code = build_item_display_code(item)
    payload['item_type_label'] = ITEM_TYPE_LABELS.get(item.item_type, item.item_type)
    payload['status_label'] = STATUS_LABELS.get(item.status, item.status)
    payload['is_overdue'] = bool(item.due_date and item.due_date < date.today() and item.status != 'completed')
    payload['source_label'] = (item.metadata_json or {}).get('source_label')
    payload['source_url'] = (item.metadata_json or {}).get('source_url')
    payload['block_name'] = item.block.name if getattr(item, 'block', None) else None
    payload['display_code'] = display_code
    payload['display_title'] = f'{display_code} - {item.title}' if display_code else item.title
    return payload


def build_item_display_code(item: WorkJourneyItem) -> str:
    metadata = dict(item.metadata_json or {})
    company_code = resolve_company_code(item.company_id)

    if item.item_type == 'process_instance':
        return str(metadata.get('source_code') or f'{company_code}.IP.{item.source_id or item.id}')

    if item.item_type == 'project_task':
        return str(metadata.get('source_code') or f'{company_code}.J.{item.source_id or item.id}')

    if item.item_type == 'meeting':
        return str(metadata.get('source_code') or f'{company_code}.R.{item.source_id or item.id}')

    if item.item_type == 'manual' and not item.source_id and not item.rule_id:
        return f'{company_code}.V.{item.id}'

    return str(metadata.get('source_code') or f'{company_code}.T.{item.id}')


def resolve_company_code(company_id: int) -> str:
    company = Company.query.get(company_id)
    if not company:
        return 'AA'
    code = str(company.client_code or '').strip().upper()
    if code:
        return code
    fallback = ''.join(char for char in str(company.name or '').upper() if char.isalnum())
    return (fallback[:2] or 'AA')


def item_matches_anchor(item: WorkJourneyItem, anchor: date, scope: str) -> bool:
    target = item.occurrence_date or item.due_date
    if scope == 'week':
        start, end = clamp_period('week', anchor)
        return bool(target and start <= target <= end) or bool(item.due_date and item.due_date < start and item.status != 'completed')
    if scope == 'month':
        start, end = clamp_period('month', anchor)
        return bool(target and start <= target <= end) or bool(item.due_date and item.due_date < start and item.status != 'completed')
    return target == anchor or bool(item.due_date and item.due_date < anchor and item.status != 'completed')


def item_sort_key(item: WorkJourneyItem):
    target = item.occurrence_date or item.due_date or date.max
    return (target, -PRIORITY_ORDER.get(item.priority, 1), item.title.lower())
