from __future__ import annotations

from datetime import date, datetime
from typing import Any

from models import db, Employee, WorkJourneyBlock, WorkJourneyItem, WorkJourneyRule
from services.work_journey_base import WorkJourneyError, ensure_employee
from services.work_journey_helpers import ITEM_TYPE_LABELS, PRIORITY_ORDER, STATUS_LABELS, clamp_period, duration_minutes
from services.work_journey_sync import (
    load_period_items,
    propagate_item_status,
    sync_meetings,
    sync_process_instances,
    sync_project_tasks,
    sync_rule_occurrences,
)


def list_employee_blocks(company_id: int, employee_id: int) -> list[dict[str, Any]]:
    ensure_employee(company_id, employee_id)
    blocks = (
        WorkJourneyBlock.query.filter_by(company_id=company_id, employee_id=employee_id)
        .order_by(WorkJourneyBlock.order_index.asc(), WorkJourneyBlock.start_time.asc(), WorkJourneyBlock.id.asc())
        .all()
    )
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
    block.weekdays_json = payload.get('weekdays') or [0, 1, 2, 3, 4]
    block.accepted_item_types = payload.get('accepted_item_types') or ['manual', 'process_instance', 'project_task', 'meeting']
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


def get_work_journey_board(company_id: int, employee_id: int, anchor: date, scope: str = 'day') -> dict[str, Any]:
    employee = ensure_employee(company_id, employee_id)
    period_start, period_end = clamp_period(scope, anchor)
    sync_work_journey_items(company_id, employee_id, period_start, period_end)

    blocks = (
        WorkJourneyBlock.query.filter_by(company_id=company_id, employee_id=employee_id, is_active=True)
        .order_by(WorkJourneyBlock.order_index.asc(), WorkJourneyBlock.start_time.asc(), WorkJourneyBlock.id.asc())
        .all()
    )
    weekday = anchor.weekday()
    active_blocks = [block for block in blocks if weekday in (block.weekdays_json or [])]

    items = load_period_items(company_id, employee_id, period_start, period_end)
    suggest_blocks(active_blocks, items, anchor)

    board_blocks = []
    for block in active_blocks:
        block_items = [item for item in items if item.block_id == block.id and item_matches_anchor(item, anchor, scope)]
        block_payload = block.to_dict()
        block_payload['capacity_minutes'] = duration_minutes(block.start_time, block.end_time)
        block_payload['planned_minutes'] = sum(int(item.estimated_minutes or 0) for item in block_items)
        block_payload['worked_minutes'] = sum(int(item.worked_minutes or 0) for item in block_items)
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
    sync_rule_occurrences(company_id, employee_id, period_start, period_end)
    sync_process_instances(company_id, employee_id, period_start, period_end)
    sync_project_tasks(company_id, employee_id, period_start, period_end)
    sync_meetings(company_id, employee_id, period_start, period_end)
    db.session.commit()


def update_work_item(company_id: int, item_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    item = WorkJourneyItem.query.filter_by(company_id=company_id, id=item_id).first()
    if not item:
        raise WorkJourneyError('Atividade não encontrada.')

    if 'block_id' in payload:
        block_id = payload.get('block_id')
        if block_id:
            block = WorkJourneyBlock.query.filter_by(company_id=company_id, id=block_id, employee_id=item.employee_id).first()
            if not block:
                raise WorkJourneyError('Bloco inválido para o colaborador da atividade.')
            item.block_id = block.id
        else:
            item.block_id = None

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


def suggest_blocks(blocks: list[WorkJourneyBlock], items: list[WorkJourneyItem], anchor: date) -> None:
    if not blocks:
        return
    for item in items:
        if item.block_id or not item_matches_anchor(item, anchor, 'day'):
            continue
        preferred = item.rule.preferred_block_id if item.rule else None
        candidates = [block for block in blocks if item.item_type in (block.accepted_item_types or [])]
        if preferred and any(block.id == preferred for block in candidates):
            item.block_id = preferred
        elif candidates:
            item.block_id = candidates[0].id


def build_summary(employee: Employee, blocks: list[WorkJourneyBlock], items: list[WorkJourneyItem], anchor: date, scope: str) -> dict[str, Any]:
    relevant = [item for item in items if item_matches_anchor(item, anchor, scope)]
    capacity_minutes = sum(duration_minutes(block.start_time, block.end_time) for block in blocks)
    planned_minutes = sum(int(item.estimated_minutes or 0) for item in relevant)
    worked_minutes = sum(int(item.worked_minutes or 0) for item in relevant)
    overload_minutes = max(planned_minutes - capacity_minutes, 0)
    return {
        'weekly_capacity_minutes': int(float(employee.weekly_hours or 0) * 60),
        'daily_capacity_minutes': capacity_minutes,
        'planned_minutes': planned_minutes,
        'worked_minutes': worked_minutes,
        'overload_minutes': overload_minutes,
        'pending_count': len([item for item in relevant if item.status != 'completed']),
        'completed_count': len([item for item in relevant if item.status == 'completed']),
    }


def serialize_item(item: WorkJourneyItem) -> dict[str, Any]:
    payload = item.to_dict()
    payload['item_type_label'] = ITEM_TYPE_LABELS.get(item.item_type, item.item_type)
    payload['status_label'] = STATUS_LABELS.get(item.status, item.status)
    payload['is_overdue'] = bool(item.due_date and item.due_date < date.today() and item.status != 'completed')
    payload['source_label'] = (item.metadata_json or {}).get('source_label')
    payload['source_url'] = (item.metadata_json or {}).get('source_url')
    return payload


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
