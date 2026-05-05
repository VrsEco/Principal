from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from models import Employee, WorkCalendarEvent, WorkJourneyAgenda, WorkJourneyAgendaItem, WorkJourneyBlock
from services.work_journey_base import is_actionable_status
from services.work_journey_helpers import BLOCK_MODE_LABELS, ITEM_TYPE_LABELS, STATUS_LABELS, WEEKDAY_LABELS, block_chronology_key, clamp_period, duration_minutes
from services.work_journey_service import build_item_display_code

ITEM_TYPE_COLORS = {
    'process_instance': {'bg': '#dbeafe', 'border': '#2563eb', 'text': '#1e3a8a'},
    'project_task': {'bg': '#ede9fe', 'border': '#7c3aed', 'text': '#5b21b6'},
    'meeting': {'bg': '#fef3c7', 'border': '#d97706', 'text': '#92400e'},
    'manual': {'bg': '#ccfbf1', 'border': '#0f766e', 'text': '#115e59'},
}


EVENT_SOURCE_LABELS = {
    'manual': 'Evento livre',
    'process_instance': 'Instância de processo',
    'project_task': 'Atividade de projeto',
}


def serialize_agenda_payload(
    agenda: WorkJourneyAgenda,
    employee: Employee,
    blocks: list[WorkJourneyBlock],
    entries: list[WorkJourneyAgendaItem],
    calendar_events: list[WorkCalendarEvent] | None = None,
) -> dict[str, Any]:
    period_start, period_end = clamp_period(agenda.scope, agenda.anchor_date)
    entries = [entry for entry in entries if not entry.journey_item or is_actionable_status(entry.journey_item.status)]
    calendar_events = list(calendar_events or [])
    blocks_by_id = {block.id: block for block in blocks}
    entries_by_day_block: dict[tuple[date, int | None], list[WorkJourneyAgendaItem]] = defaultdict(list)
    events_by_day_block: dict[tuple[date, int | None], list[WorkCalendarEvent]] = defaultdict(list)
    serialized_entries: dict[int, dict[str, Any]] = {}
    for entry in entries:
        entries_by_day_block[(entry.planned_date, entry.block_id)].append(entry)
        serialized_entries[entry.id] = serialize_agenda_entry(entry)
    serialized_events: dict[int, dict[str, Any]] = {}
    for event in calendar_events:
        events_by_day_block[(event.event_date, event.block_id)].append(event)
        serialized_events[event.id] = serialize_calendar_event_for_agenda(event)

    overdue_entries = _unique_task_entries(entry for entry in entries if _entry_is_overdue(entry) and not _entry_hidden_from_overdue_lane(entry))
    unassigned_entries = _unique_task_entries(entry for entry in entries if entry.block_id is None)
    unassigned_events = sorted(
        [serialized_events[event.id] for event in calendar_events if event.block_id is None],
        key=_calendar_sort_key,
    )

    days = []
    current = period_start
    while current <= period_end:
        day_blocks = [block for block in sorted(blocks_by_id.values(), key=block_chronology_key) if current.weekday() in (block.weekdays_json or [])]
        block_payloads = []
        day_entries = [entry for entry in entries if entry.planned_date == current]
        day_events = sorted([serialized_events[event.id] for event in calendar_events if event.event_date == current], key=_calendar_sort_key)
        day_overdue_entries = _unique_task_entries(entry for entry in day_entries if _entry_is_overdue(entry))
        for block in day_blocks:
            block_entries = entries_by_day_block.get((current, block.id), [])
            block_events = sorted(
                [serialized_events[event.id] for event in events_by_day_block.get((current, block.id), [])],
                key=_calendar_sort_key,
            )
            block_capacity = duration_minutes(block.start_time, block.end_time)
            operational_capacity = block_capacity if block.block_mode == 'operational' else 0
            reserved_minutes = block_capacity if block.block_mode == 'reserved_full' else 0
            buffer_minutes = block_capacity if block.block_mode == 'buffer' else 0
            planned_task_minutes = sum(int(entry.allocated_minutes or 0) for entry in block_entries)
            planned_event_minutes = sum(int(event.get('estimated_minutes') or 0) for event in block_events)
            planned = reserved_minutes if block.block_mode == 'reserved_full' else planned_task_minutes + planned_event_minutes
            overload = 0 if block.block_mode == 'reserved_full' else max(planned - block_capacity, 0)
            worked_minutes = sum(int(entry.journey_item.worked_minutes or 0) if entry.journey_item else 0 for entry in block_entries)
            block_payloads.append(
                {
                    'id': block.id,
                    'name': block.name,
                    'description': block.description,
                    'start_time': block.start_time.strftime('%H:%M') if block.start_time else None,
                    'end_time': block.end_time.strftime('%H:%M') if block.end_time else None,
                    'block_mode': block.block_mode,
                    'block_mode_label': BLOCK_MODE_LABELS.get(block.block_mode, block.block_mode),
                    'capacity_minutes': block_capacity,
                    'operational_capacity_minutes': operational_capacity,
                    'fixed_reserved_minutes': reserved_minutes,
                    'buffer_minutes': buffer_minutes,
                    'planned_task_minutes': planned_task_minutes,
                    'planned_event_minutes': planned_event_minutes,
                    'planned_minutes': planned,
                    'worked_minutes': worked_minutes,
                    'overload_minutes': overload,
                    'overload_label': format_minutes_label(overload),
                    'items': [serialized_entries[entry.id] for entry in block_entries],
                    'events': block_events,
                }
            )
        days.append(
            {
                'date': current.isoformat(),
                'label': current.strftime('%d/%m/%Y'),
                'subtitle': WEEKDAY_LABELS.get(current.weekday(), ''),
                'weekday': current.weekday(),
                'weekday_label': WEEKDAY_LABELS.get(current.weekday(), ''),
                'day_number': current.day,
                'is_today': current == date.today(),
                'blocks': block_payloads,
                'items': [serialized_entries[entry.id] for entry in day_entries],
                'events': day_events,
                'overdue_items': [serialized_entries[entry.id] for entry in day_overdue_entries],
                'overdue_count': len(day_overdue_entries),
                'unassigned_items': [serialized_entries[entry.id] for entry in _unique_task_entries(entry for entry in day_entries if entry.block_id is None)],
                'unassigned_events': [serialized_events[event.id] for event in events_by_day_block.get((current, None), [])],
                'day_capacity_minutes': sum(block['operational_capacity_minutes'] for block in block_payloads),
                'day_planned_minutes': sum(block['planned_minutes'] for block in block_payloads),
                'day_overload_minutes': sum(block['overload_minutes'] for block in block_payloads),
                'day_event_count': len(day_events),
            }
        )
        current += timedelta(days=1)

    summary = dict(agenda.summary_json or {})
    worked_minutes = sum(int(entry.journey_item.worked_minutes or 0) if entry.journey_item else 0 for entry in entries)
    planned_minutes = sum(day['day_planned_minutes'] for day in days)
    overload_minutes = sum(int(entry.overflow_minutes or 0) for entry in entries)
    daily_capacity_minutes = sum(day['day_capacity_minutes'] for day in days)
    unassigned_count = len(unassigned_entries)
    overdue_count = len(overdue_entries)
    event_count = len(calendar_events)
    linked_event_count = len([event for event in calendar_events if event.source_type != 'manual'])
    return {
        'id': agenda.id,
        'employee': employee.to_dict(),
        'employee_name': employee.name,
        'anchor_date': agenda.anchor_date.isoformat(),
        'scope': agenda.scope,
        'scope_label': 'Diária' if agenda.scope == 'day' else 'Semanal',
        'status': agenda.status,
        'status_label': 'Travada' if agenda.status == 'locked' else 'Sugerida',
        'engine_version': agenda.engine_version,
        'period_start': period_start.isoformat(),
        'period_end': period_end.isoformat(),
        'summary': {
            **summary,
            'daily_capacity_minutes': daily_capacity_minutes,
            'planned_minutes': planned_minutes,
            'worked_minutes': worked_minutes,
            'overload_minutes': overload_minutes,
            'unassigned_count': unassigned_count,
            'pending_count': len([entry for entry in entries if entry.journey_item and entry.journey_item.status != 'completed']),
            'completed_count': len([entry for entry in entries if entry.journey_item and entry.journey_item.status == 'completed']),
            'locked': agenda.status == 'locked',
            'agenda_status': agenda.status,
            'daily_capacity_label': format_minutes_label(daily_capacity_minutes),
            'planned_label': format_minutes_label(planned_minutes),
            'buffer_label': format_minutes_label(summary.get('buffer_minutes', 0)),
            'reserved_label': format_minutes_label(summary.get('reserved_minutes', 0)),
            'overload_label': format_minutes_label(overload_minutes),
            'overdue_count': overdue_count,
            'event_count': event_count,
            'linked_event_count': linked_event_count,
            'manual_event_count': max(event_count - linked_event_count, 0),
        },
        'days': days,
        'overdue_items': [serialized_entries[entry.id] for entry in overdue_entries],
        'unassigned_items': [serialized_entries[entry.id] for entry in unassigned_entries],
        'calendar_events': sorted(serialized_events.values(), key=_calendar_sort_key),
        'unassigned_events': unassigned_events,
    }


def serialize_agenda_entry(entry: WorkJourneyAgendaItem) -> dict[str, Any]:
    item = entry.journey_item
    metadata = dict(item.metadata_json or {}) if item else {}
    display_code = build_item_display_code(item) if item else ''
    is_overdue = _item_is_overdue(item)
    return {
        'id': entry.id,
        'agenda_item_id': entry.id,
        'journey_item_id': entry.journey_item_id,
        'block_id': entry.block_id,
        'block_name': entry.block.name if entry.block else None,
        'planned_date': entry.planned_date.isoformat() if entry.planned_date else None,
        'position_index': int(entry.position_index or 0),
        'allocated_minutes': int(entry.allocated_minutes or 0),
        'allocated_label': format_minutes_label(entry.allocated_minutes or 0),
        'planned_minutes': int(entry.allocated_minutes or 0),
        'estimated_minutes': int(entry.allocated_minutes or 0),
        'overflow_minutes': int(entry.overflow_minutes or 0),
        'overflow_label': format_minutes_label(entry.overflow_minutes or 0),
        'is_fixed': bool(entry.is_fixed),
        'is_over_capacity': bool(entry.is_over_capacity),
        'manual_override': bool(entry.manual_override),
        'planned_window_label': planned_window_label(entry),
        'planned_start_time': minutes_to_hhmm(entry.planned_start_minutes) if entry.planned_start_minutes is not None else None,
        'planned_end_time': minutes_to_hhmm(entry.planned_end_minutes) if entry.planned_end_minutes is not None else None,
        'title': item.title if item else 'Tarefa indisponível',
        'description': item.description if item else None,
        'item_type': item.item_type if item else 'manual',
        'item_type_label': ITEM_TYPE_LABELS.get(item.item_type, item.item_type) if item else 'Tarefa',
        'status': item.status if item else 'pending',
        'status_label': STATUS_LABELS.get(item.status, item.status) if item else 'Pendente',
        'priority': item.priority if item else 'normal',
        'is_overdue': is_overdue,
        'display_code': display_code,
        'display_title': f'{display_code} - {item.title}' if item and display_code else (item.title if item else 'Tarefa indisponível'),
        'source_label': metadata.get('source_label'),
        'source_url': metadata.get('source_url'),
        'source_type': item.item_type if item else 'manual',
        'source_ref_id': item.source_id or item.id if item else None,
        'can_drag': bool(item and item.item_type != 'meeting'),
        'can_move': bool(item and item.item_type != 'meeting'),
        'source_warning': 'Reunião: altere no módulo de reuniões.' if item and item.item_type == 'meeting' else None,
        'meeting_locked': bool(item and item.item_type == 'meeting'),
        'item_type_colors': ITEM_TYPE_COLORS.get(item.item_type if item else 'manual', ITEM_TYPE_COLORS['manual']),
        'new_after_lock': bool((entry.metadata_json or {}).get('new_after_lock')),
        'block_mode': entry.block.block_mode if entry.block else None,
        'block_mode_label': BLOCK_MODE_LABELS.get(entry.block.block_mode if entry.block else '', entry.block.block_mode if entry.block else None),
        'block_name_snapshot': entry.block.name if entry.block else None,
    }


def serialize_calendar_event_for_agenda(event: WorkCalendarEvent) -> dict[str, Any]:
    duration_minutes = _event_duration_minutes(event)
    source_label = EVENT_SOURCE_LABELS.get(event.source_type, event.source_type)
    source_title = _event_source_title(event)
    source_code = _event_source_code(event)
    display_code = source_code or source_label
    display_title = f'{display_code} - {event.title}' if display_code else event.title
    return {
        'id': f'event-{event.id}',
        'event_id': event.id,
        'journey_item_id': None,
        'block_id': event.block_id,
        'block_name': event.block.name if event.block else None,
        'planned_date': event.event_date.isoformat() if event.event_date else None,
        'agenda_date': event.event_date.isoformat() if event.event_date else None,
        'position_index': 0,
        'allocated_minutes': duration_minutes,
        'allocated_label': format_minutes_label(duration_minutes),
        'planned_minutes': duration_minutes,
        'estimated_minutes': duration_minutes,
        'overflow_minutes': 0,
        'overflow_label': format_minutes_label(0),
        'is_fixed': True,
        'is_over_capacity': False,
        'manual_override': False,
        'planned_window_label': _event_window_label(event),
        'planned_start_time': event.start_time.strftime('%H:%M') if event.start_time else None,
        'planned_end_time': event.end_time.strftime('%H:%M') if event.end_time else None,
        'title': event.title,
        'description': event.description,
        'item_type': event.source_type,
        'item_kind': 'calendar_event',
        'item_type_label': source_label,
        'status': event.status,
        'status_label': _event_status_label(event.status),
        'priority': event.priority,
        'is_overdue': False,
        'display_code': display_code,
        'display_title': display_title,
        'source_label': source_label,
        'source_url': _event_source_url(event),
        'source_type': event.source_type,
        'source_ref_id': event.source_id,
        'source_code': source_code,
        'source_title': source_title,
        'can_drag': False,
        'can_move': False,
        'source_warning': 'Evento de calendário: movimente pelo formulário do Calendário.',
        'meeting_locked': False,
        'item_type_colors': ITEM_TYPE_COLORS.get(event.source_type, ITEM_TYPE_COLORS['manual']),
        'new_after_lock': False,
        'block_mode': event.block.block_mode if event.block else None,
        'block_mode_label': BLOCK_MODE_LABELS.get(event.block.block_mode if event.block else '', event.block.block_mode if event.block else None),
        'block_name_snapshot': event.block.name if event.block else None,
        'execution_notes': event.execution_notes,
        'employee_name': getattr(event.employee, 'name', None),
        'event_date': event.event_date.isoformat() if event.event_date else None,
    }


def _entry_is_overdue(entry: WorkJourneyAgendaItem) -> bool:
    return _item_is_overdue(getattr(entry, 'journey_item', None))


def _entry_hidden_from_overdue_lane(entry: WorkJourneyAgendaItem) -> bool:
    return bool((getattr(entry, 'metadata_json', None) or {}).get('hide_from_overdue_lane'))


def _item_is_overdue(item: Any) -> bool:
    if not item or getattr(item, 'status', None) == 'completed':
        return False
    explicit_flag = getattr(item, 'is_overdue', None)
    if explicit_flag is not None:
        return bool(explicit_flag)
    due_date = getattr(item, 'due_date', None)
    return bool(due_date and due_date < date.today())


def _unique_task_entries(entries: Any) -> list[WorkJourneyAgendaItem]:
    unique: list[WorkJourneyAgendaItem] = []
    seen: set[int | tuple[str, int]] = set()
    for entry in entries:
        task_key = getattr(entry, 'journey_item_id', None)
        if task_key is None:
            task_key = ('entry', int(getattr(entry, 'id', 0) or 0))
        if task_key in seen:
            continue
        seen.add(task_key)
        unique.append(entry)
    return unique


def planned_window_label(entry: WorkJourneyAgendaItem) -> str | None:
    if entry.planned_start_minutes is None or entry.planned_end_minutes is None:
        return None
    return f'{minutes_to_hhmm(entry.planned_start_minutes)} → {minutes_to_hhmm(entry.planned_end_minutes)}'


def minutes_to_hhmm(value: int) -> str:
    total = max(int(value or 0), 0)
    return f'{total // 60:02d}:{total % 60:02d}'


def format_minutes_label(minutes: int) -> str:
    total = max(int(minutes or 0), 0)
    hours = total // 60
    remainder = total % 60
    if not hours:
        return f'{remainder} min'
    if not remainder:
        return f'{hours}h'
    return f'{hours}h{remainder:02d}'


def _event_duration_minutes(event: WorkCalendarEvent) -> int:
    if event.start_time and event.end_time:
        start = (event.start_time.hour * 60) + event.start_time.minute
        end = (event.end_time.hour * 60) + event.end_time.minute
        return max(end - start, 0)
    metadata = dict(event.metadata_json or {})
    return max(int(metadata.get('duration_minutes') or 0), 0)


def _event_window_label(event: WorkCalendarEvent) -> str | None:
    if not event.start_time and not event.end_time:
        return None
    start = event.start_time.strftime('%H:%M') if event.start_time else '--:--'
    end = event.end_time.strftime('%H:%M') if event.end_time else '--:--'
    return f'{start} → {end}'


def _event_status_label(status: str) -> str:
    return {
        'planned': 'Planejado',
        'confirmed': 'Confirmado',
        'in_progress': 'Em execução',
        'done': 'Concluído',
        'cancelled': 'Cancelado',
        'postponed': 'Adiado',
    }.get(status, status)


def _event_source_url(event: WorkCalendarEvent) -> str | None:
    metadata = dict(event.metadata_json or {})
    return metadata.get('source_url')


def _event_source_code(event: WorkCalendarEvent) -> str | None:
    metadata = dict(event.metadata_json or {})
    return metadata.get('source_code')


def _event_source_title(event: WorkCalendarEvent) -> str | None:
    metadata = dict(event.metadata_json or {})
    return metadata.get('source_title')


def _calendar_sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(item.get('agenda_date') or item.get('event_date') or '9999-12-31'),
        str(item.get('planned_start_time') or '99:99'),
        str(item.get('display_title') or item.get('title') or ''),
    )
