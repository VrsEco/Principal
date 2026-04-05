from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import and_, or_

from models import (
    ProcessInstance,
    ProjectTask,
    WorkJourneyAgenda,
    WorkJourneyAgendaItem,
    WorkJourneyBlock,
    WorkJourneyItem,
    db,
)
from services.work_journey_base import ACTIVE_ITEM_STATUSES
from services.work_journey_helpers import block_chronology_key, clamp_period, duration_minutes, parse_time, time_to_minutes


def load_source_items(company_id: int, employee_id: int, period_start: date, period_end: date) -> list[WorkJourneyItem]:
    planning_limit = period_end + timedelta(days=7)
    return (
        WorkJourneyItem.query.filter(
            WorkJourneyItem.company_id == company_id,
            WorkJourneyItem.employee_id == employee_id,
            WorkJourneyItem.rule_id.is_(None),
            WorkJourneyItem.status.in_(list(ACTIVE_ITEM_STATUSES)),
            or_(
                and_(WorkJourneyItem.item_type == 'meeting', WorkJourneyItem.due_date.between(period_start, period_end)),
                and_(
                    WorkJourneyItem.item_type == 'manual',
                    or_(
                        WorkJourneyItem.due_date.between(period_start, period_end),
                        and_(WorkJourneyItem.due_date < period_start, WorkJourneyItem.status.in_(list(ACTIVE_ITEM_STATUSES))),
                    ),
                ),
                and_(
                    WorkJourneyItem.item_type == 'process_instance',
                    or_(
                        WorkJourneyItem.due_date.between(period_start, period_end),
                        and_(WorkJourneyItem.due_date < period_start, WorkJourneyItem.status.in_(list(ACTIVE_ITEM_STATUSES))),
                    ),
                ),
                and_(
                    WorkJourneyItem.item_type == 'project_task',
                    or_(
                        WorkJourneyItem.due_date.between(period_start, planning_limit),
                        and_(WorkJourneyItem.due_date < period_start, WorkJourneyItem.status.in_(list(ACTIVE_ITEM_STATUSES))),
                    ),
                ),
            ),
        )
        .order_by(WorkJourneyItem.due_date.asc().nulls_last(), WorkJourneyItem.id.asc())
        .all()
    )


def load_blocks_by_day(company_id: int, employee_id: int, period_start: date, period_end: date) -> dict[date, list[WorkJourneyBlock]]:
    blocks = WorkJourneyBlock.query.filter_by(company_id=company_id, employee_id=employee_id, is_active=True).all()
    blocks = sorted(blocks, key=block_chronology_key)
    result: dict[date, list[WorkJourneyBlock]] = {}
    current = period_start
    while current <= period_end:
        result[current] = [block for block in blocks if current.weekday() in (block.weekdays_json or [])]
        current += timedelta(days=1)
    return result


def allocate_item(
    item: WorkJourneyItem,
    agenda: WorkJourneyAgenda,
    blocks_by_day: dict[date, list[WorkJourneyBlock]],
    used_capacity: dict[tuple[date, int], int],
    period_start: date,
    period_end: date,
) -> list[WorkJourneyAgendaItem]:
    remaining = max(int(item.estimated_minutes or 0), 0) or 15
    candidates = candidate_slots_for_item(item, blocks_by_day, period_start, period_end)
    if not candidates:
        target = item.occurrence_date or item.due_date or agenda.anchor_date
        return [build_unassigned_entry(agenda, item, target, remaining)]

    if item.item_type == 'meeting':
        return [_allocate_meeting(item, agenda, candidates[0], remaining, used_capacity)]

    compatible_slots = [(day, block) for day, block, _ in candidates if block is not None]
    if not compatible_slots:
        return [build_unassigned_entry(agenda, item, candidates[0][0], remaining)]

    entries: list[WorkJourneyAgendaItem] = []
    last_day, last_block = compatible_slots[-1]
    for target_day, target_block in compatible_slots:
        key = (target_day, target_block.id)
        capacity = duration_minutes(target_block.start_time, target_block.end_time)
        available = max(capacity - used_capacity[key], 0)
        if available <= 0:
            continue

        allocation = min(remaining, available)
        entries.append(
            build_entry(
                agenda,
                item,
                planned_date=target_day,
                block=target_block,
                allocated_minutes=allocation,
                position_index=next_position_for_group(agenda.id, target_day, target_block.id),
                is_fixed=False,
                is_over_capacity=False,
                overflow_minutes=0,
            )
        )
        used_capacity[key] += allocation
        remaining -= allocation
        if remaining <= 0:
            return entries

    used_capacity[(last_day, last_block.id)] += remaining
    entries.append(
        build_entry(
            agenda,
            item,
            planned_date=last_day,
            block=last_block,
            allocated_minutes=remaining,
            position_index=next_position_for_group(agenda.id, last_day, last_block.id),
            is_fixed=False,
            is_over_capacity=True,
            overflow_minutes=remaining,
        )
    )
    return entries


def candidate_slots_for_item(
    item: WorkJourneyItem,
    blocks_by_day: dict[date, list[WorkJourneyBlock]],
    period_start: date,
    period_end: date,
) -> list[tuple[date, WorkJourneyBlock | None, int | None]]:
    if is_overdue_for_period(item, period_start):
        preferred_block_id = item.block_id if item.item_type == 'manual' and item.block_id else None
        return expand_blocks_for_dates(
            item.item_type,
            blocks_by_day,
            sorted(blocks_by_day.keys()),
            reverse_within_day=False,
            preferred_block_id=preferred_block_id,
        )

    if item.item_type == 'meeting':
        meeting_date = item.due_date or item.occurrence_date
        if not meeting_date or meeting_date not in blocks_by_day:
            return []
        scheduled_time = str((item.metadata_json or {}).get('scheduled_time') or '').strip()
        scheduled_minutes = time_to_minutes(parse_time(scheduled_time)) if scheduled_time else None
        block = meeting_block_for_time(blocks_by_day[meeting_date], item.item_type, scheduled_minutes)
        return [(meeting_date, block, scheduled_minutes)]

    if item.item_type == 'manual' and item.block_id:
        manual_date = item.due_date or item.occurrence_date
        if manual_date and manual_date in blocks_by_day:
            block = next((candidate for candidate in blocks_by_day[manual_date] if candidate.id == item.block_id), None)
            return [(manual_date, block, None)] if block else [(manual_date, None, None)]

    if item.item_type == 'project_task':
        due = item.due_date or period_end
        target = min(due - timedelta(days=1), period_end) if due > period_start else period_start
        dates: list[date] = []
        current = target
        while current >= period_start:
            dates.append(current)
            current -= timedelta(days=1)
        return expand_blocks_for_dates(item.item_type, blocks_by_day, dates, reverse_within_day=True)

    preferred_date = item.occurrence_date or item.due_date or period_start
    preferred_date = max(period_start, min(preferred_date, period_end))
    return expand_blocks_for_dates(item.item_type, blocks_by_day, [preferred_date], reverse_within_day=False)


def expand_blocks_for_dates(
    item_type: str,
    blocks_by_day: dict[date, list[WorkJourneyBlock]],
    dates: list[date],
    reverse_within_day: bool,
    preferred_block_id: int | None = None,
) -> list[tuple[date, WorkJourneyBlock | None, int | None]]:
    slots: list[tuple[date, WorkJourneyBlock | None, int | None]] = []
    for current in dates:
        compatible = [
            block
            for block in blocks_by_day.get(current, [])
            if block.block_mode == 'operational'
            and item_type in (block.accepted_item_types or [])
            and (preferred_block_id is None or block.id == preferred_block_id)
        ]
        compatible = list(reversed(compatible)) if reverse_within_day else compatible
        for block in compatible:
            slots.append((current, block, None))
    return slots


def is_overdue_for_period(item: WorkJourneyItem, period_start: date) -> bool:
    if item.item_type == 'meeting':
        return False
    if item.status not in ACTIVE_ITEM_STATUSES:
        return False
    due_date = item.due_date or item.occurrence_date
    return bool(due_date and due_date < period_start)


def meeting_block_for_time(blocks: list[WorkJourneyBlock], item_type: str, scheduled_minutes: int | None) -> WorkJourneyBlock | None:
    compatible = [block for block in blocks if block.block_mode == 'operational' and item_type in (block.accepted_item_types or [])]
    if scheduled_minutes is None:
        return compatible[0] if compatible else None
    for block in compatible:
        if time_to_minutes(block.start_time) <= scheduled_minutes < time_to_minutes(block.end_time):
            return block
    return compatible[0] if compatible else None


def build_entry(
    agenda: WorkJourneyAgenda,
    item: WorkJourneyItem,
    planned_date: date,
    block: WorkJourneyBlock | None,
    allocated_minutes: int,
    position_index: int,
    is_fixed: bool,
    is_over_capacity: bool,
    overflow_minutes: int,
    planned_start_minutes: int | None = None,
    planned_end_minutes: int | None = None,
) -> WorkJourneyAgendaItem:
    return WorkJourneyAgendaItem(
        agenda_id=agenda.id,
        company_id=agenda.company_id,
        employee_id=agenda.employee_id,
        journey_item_id=item.id,
        block_id=block.id if block else None,
        planned_date=planned_date,
        position_index=position_index,
        allocated_minutes=int(allocated_minutes or 0),
        planned_start_minutes=planned_start_minutes,
        planned_end_minutes=planned_end_minutes,
        overflow_minutes=int(overflow_minutes or 0),
        is_fixed=is_fixed,
        is_over_capacity=is_over_capacity,
        manual_override=False,
        metadata_json={},
    )


def build_unassigned_entry(agenda: WorkJourneyAgenda, item: WorkJourneyItem, planned_date: date, allocated_minutes: int) -> WorkJourneyAgendaItem:
    return WorkJourneyAgendaItem(
        agenda_id=agenda.id,
        company_id=agenda.company_id,
        employee_id=agenda.employee_id,
        journey_item_id=item.id,
        block_id=None,
        planned_date=planned_date,
        position_index=next_position_for_group(agenda.id, planned_date, None),
        allocated_minutes=int(allocated_minutes or 0),
        overflow_minutes=0,
        is_fixed=False,
        is_over_capacity=False,
        manual_override=False,
        metadata_json={'unassigned_reason': 'Sem bloco compatível disponível'},
    )


def next_position_for_group(agenda_id: int, planned_date: date, block_id: int | None) -> int:
    query = WorkJourneyAgendaItem.query.filter_by(agenda_id=agenda_id, planned_date=planned_date)
    query = query.filter(WorkJourneyAgendaItem.block_id.is_(None)) if block_id is None else query.filter_by(block_id=block_id)
    last = query.order_by(WorkJourneyAgendaItem.position_index.desc(), WorkJourneyAgendaItem.id.desc()).first()
    return int(last.position_index or 0) + 1 if last else 0


def shift_positions_before_insert(agenda_id: int, planned_date: date, block_id: int | None, position_index: int, exclude_item_id: int | None = None) -> None:
    query = WorkJourneyAgendaItem.query.filter_by(agenda_id=agenda_id, planned_date=planned_date)
    query = query.filter(WorkJourneyAgendaItem.block_id.is_(None)) if block_id is None else query.filter_by(block_id=block_id)
    if exclude_item_id:
        query = query.filter(WorkJourneyAgendaItem.id != exclude_item_id)
    for sibling in query.filter(WorkJourneyAgendaItem.position_index >= position_index).all():
        sibling.position_index = int(sibling.position_index or 0) + 1
        db.session.add(sibling)


def apply_date_change_to_source(item: WorkJourneyItem, target_date: date) -> None:
    item.occurrence_date = target_date
    if item.item_type in {'manual', 'process_instance', 'project_task'}:
        item.due_date = target_date
    db.session.add(item)

    if item.item_type == 'manual':
        return
    if item.item_type == 'process_instance' and item.source_id:
        instance = ProcessInstance.query.get(item.source_id)
        if instance:
            instance.due_date = target_date
            db.session.add(instance)
    elif item.item_type == 'project_task' and item.source_id:
        task = ProjectTask.query.get(item.source_id)
        if task and not task.completion_date:
            task.due_date = target_date
            db.session.add(task)


def recompute_agenda_summary(agenda: WorkJourneyAgenda, entries: list[WorkJourneyAgendaItem] | None = None) -> None:
    all_entries = entries if entries is not None else list(agenda.items)
    blocks = WorkJourneyBlock.query.filter_by(company_id=agenda.company_id, employee_id=agenda.employee_id, is_active=True).all()
    period_start, period_end = clamp_period(agenda.scope, agenda.anchor_date)
    dates = [period_start + timedelta(days=offset) for offset in range((period_end - period_start).days + 1)]
    operational = reserved = buffer = 0
    for current in dates:
        for block in blocks:
            if current.weekday() not in (block.weekdays_json or []):
                continue
            minutes = duration_minutes(block.start_time, block.end_time)
            if block.block_mode == 'operational':
                operational += minutes
            elif block.block_mode == 'reserved_full':
                reserved += minutes
            elif block.block_mode == 'buffer':
                buffer += minutes

    agenda.summary_json = {
        'daily_capacity_minutes': operational,
        'planned_minutes': sum(int(entry.allocated_minutes or 0) for entry in all_entries),
        'buffer_minutes': buffer,
        'reserved_minutes': reserved,
        'overload_minutes': sum(int(entry.overflow_minutes or 0) for entry in all_entries),
        'unassigned_count': len([entry for entry in all_entries if entry.block_id is None]),
        'days_count': len(dates),
    }


def _allocate_meeting(
    item: WorkJourneyItem,
    agenda: WorkJourneyAgenda,
    candidate: tuple[date, WorkJourneyBlock | None, int | None],
    remaining: int,
    used_capacity: dict[tuple[date, int], int],
) -> WorkJourneyAgendaItem:
    target_day, target_block, planned_start = candidate
    overflow = 0
    if target_block:
        key = (target_day, target_block.id)
        capacity = duration_minutes(target_block.start_time, target_block.end_time)
        overflow = max(used_capacity[key] + remaining - capacity, 0)
        used_capacity[key] += remaining
    end_minutes = planned_start + remaining if planned_start is not None else None
    return build_entry(
        agenda,
        item,
        planned_date=target_day,
        block=target_block,
        allocated_minutes=remaining,
        position_index=next_position_for_group(agenda.id, target_day, target_block.id if target_block else None),
        planned_start_minutes=planned_start,
        planned_end_minutes=end_minutes,
        is_fixed=True,
        is_over_capacity=overflow > 0,
        overflow_minutes=overflow,
    )
