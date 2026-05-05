from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


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


def select_current_execution(executions: list[Any], current_bpmn_element_id: str | None) -> Any | None:
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


def resolve_execution_due(execution: Any) -> dict[str, Any]:
    metadata = dict(getattr(execution, 'metadata_json', None) or {})
    datetime_keys = ('due_at', 'deadline_at', 'target_at', 'scheduled_at')
    date_keys = ('due_date', 'deadline_date', 'target_date')

    for key in datetime_keys:
        parsed = _parse_datetime_value(metadata.get(key))
        if parsed:
            return {
                'activity_due_at': parsed.isoformat(),
                'activity_due_date': parsed.date().isoformat(),
                'activity_due': parsed.date(),
                'activity_due_label': parsed.strftime('%d/%m/%Y %H:%M'),
                'is_activity_overdue': parsed < datetime.utcnow(),
            }

    for key in date_keys:
        parsed_date = _parse_date_value(metadata.get(key))
        if parsed_date:
            return {
                'activity_due_at': None,
                'activity_due_date': parsed_date.isoformat(),
                'activity_due': parsed_date,
                'activity_due_label': parsed_date.strftime('%d/%m/%Y'),
                'is_activity_overdue': parsed_date < date.today(),
            }

    sla_minutes = metadata.get('sla_minutes')
    anchor = getattr(execution, 'waiting_since', None) or getattr(execution, 'started_at', None) or getattr(execution, 'created_at', None)
    if anchor and sla_minutes not in (None, ''):
        try:
            due_at = anchor + timedelta(minutes=int(sla_minutes))
        except (TypeError, ValueError):
            due_at = None
        if due_at:
            return {
                'activity_due_at': due_at.isoformat(),
                'activity_due_date': due_at.date().isoformat(),
                'activity_due': due_at.date(),
                'activity_due_label': due_at.strftime('%d/%m/%Y %H:%M'),
                'is_activity_overdue': due_at < datetime.utcnow(),
            }

    return {
        'activity_due_at': None,
        'activity_due_date': None,
        'activity_due': None,
        'activity_due_label': None,
        'is_activity_overdue': False,
    }


def build_operational_projection(instance: Any, executions: list[Any]) -> dict[str, Any]:
    current_execution = select_current_execution(executions, getattr(instance, 'current_bpmn_element_id', None))
    if not current_execution:
        return {
            'current_execution': None,
            'operational_title': getattr(instance, 'title', None),
            'operational_description': getattr(instance, 'description', None),
            'operational_due_date': getattr(instance, 'due_date', None),
            'operational_due_label': _format_date_label(getattr(instance, 'due_date', None)),
            'estimated_minutes': int(float(getattr(instance, 'estimated_hours', 0) or 0) * 60),
            'worked_minutes': int(float((getattr(instance, 'actual_hours', None) or getattr(instance, 'worked_hours', 0)) or 0) * 60),
            'status': str(getattr(instance, 'status', 'pending') or 'pending'),
        }

    due_payload = resolve_execution_due(current_execution)
    status = str(getattr(current_execution, 'status', None) or getattr(instance, 'status', 'pending') or 'pending').strip().lower()
    execution_hours = getattr(current_execution, 'estimated_hours', None)
    actual_hours = getattr(current_execution, 'actual_hours', None)
    return {
        'current_execution': current_execution,
        'operational_title': getattr(current_execution, 'bpmn_element_name', None) or getattr(current_execution, 'bpmn_element_id', None) or getattr(instance, 'title', None),
        'operational_description': getattr(instance, 'title', None),
        'operational_due_date': due_payload.get('activity_due') or getattr(instance, 'due_date', None),
        'operational_due_label': due_payload.get('activity_due_label') or _format_date_label(getattr(instance, 'due_date', None)),
        'estimated_minutes': int(float(execution_hours or getattr(instance, 'estimated_hours', 0) or 0) * 60),
        'worked_minutes': int(float(actual_hours or getattr(instance, 'actual_hours', None) or getattr(instance, 'worked_hours', 0) or 0) * 60),
        'status': status,
        'activity_due_at': due_payload.get('activity_due_at'),
        'activity_due_date': due_payload.get('activity_due_date'),
        'is_activity_overdue': bool(due_payload.get('is_activity_overdue')),
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
