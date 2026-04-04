from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable

WEEKDAY_LABELS = {
    0: 'Seg',
    1: 'Ter',
    2: 'Qua',
    3: 'Qui',
    4: 'Sex',
    5: 'Sáb',
    6: 'Dom',
}

ITEM_TYPE_LABELS = {
    'manual': 'Tarefa Avulsa',
    'process_instance': 'Instância de Processo',
    'project_task': 'Atividade de Projeto',
    'meeting': 'Reunião',
}

BLOCK_MODE_LABELS = {
    'operational': 'Operacional',
    'reserved_full': 'Capacidade ocupada',
    'buffer': 'Vazio / Buffer',
}

STATUS_LABELS = {
    'pending': 'Pendente',
    'in_progress': 'Em andamento',
    'completed': 'Concluída',
    'postponed': 'Adiada',
    'suspended': 'Suspensa',
}

PRIORITY_ORDER = {'low': 0, 'normal': 1, 'high': 2, 'urgent': 3}


def parse_time(value: str) -> time:
    return datetime.strptime(value, '%H:%M').time()


def time_to_minutes(value: time | None) -> int:
    if value is None:
        return 0
    return value.hour * 60 + value.minute



def date_range(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)



def clamp_period(scope: str, anchor: date) -> tuple[date, date]:
    scope = str(scope or 'day').strip().lower()
    if scope == 'week':
        # Semana operacional alinhada ao calendário brasileiro: domingo → sábado.
        start = anchor - timedelta(days=(anchor.weekday() + 1) % 7)
        return start, start + timedelta(days=6)
    if scope == 'month':
        start = anchor.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1)
        else:
            next_month = start.replace(month=start.month + 1)
        return start, next_month - timedelta(days=1)
    return anchor, anchor



def duration_minutes(start: time | None, end: time | None) -> int:
    return max(time_to_minutes(end) - time_to_minutes(start), 0)



def rule_matches_date(recurrence_type: str, config: dict, current: date) -> bool:
    normalized = str(recurrence_type or 'daily').strip().lower()
    config = dict(config or {})

    if normalized == 'daily':
        return True

    if normalized == 'weekly':
        weekdays = [int(item) for item in config.get('weekdays', []) if str(item).isdigit()]
        return current.weekday() in weekdays if weekdays else current.weekday() == 0

    if normalized == 'monthly':
        days = [int(item) for item in config.get('days', []) if str(item).isdigit()]
        return current.day in days if days else current.day == 1

    if normalized == 'annual':
        start_token = str(config.get('start_mmdd') or '').strip()
        end_token = str(config.get('end_mmdd') or '').strip()
        current_token = current.strftime('%m-%d')
        if start_token and end_token:
            return start_token <= current_token <= end_token
        specific = str(config.get('mmdd') or '').strip()
        return current_token == specific if specific else False

    if normalized == 'sporadic':
        if config.get('date'):
            return current.isoformat() == str(config['date'])
        start_date = str(config.get('start_date') or '').strip()
        end_date = str(config.get('end_date') or '').strip()
        return bool(start_date and end_date and start_date <= current.isoformat() <= end_date)

    return False



def summarize_weekdays(days: list[int]) -> str:
    if not days:
        return 'Todos os dias úteis'
    return ', '.join(WEEKDAY_LABELS.get(day, str(day)) for day in days)


def block_chronology_key(block) -> tuple[int, int, int, str, int]:
    weekdays = sorted(int(day) for day in (getattr(block, 'weekdays_json', None) or []))
    first_weekday = weekdays[0] if weekdays else 7
    start_minutes = time_to_minutes(getattr(block, 'start_time', None))
    end_minutes = time_to_minutes(getattr(block, 'end_time', None))
    name = str(getattr(block, 'name', '') or '').strip().lower()
    identifier = int(getattr(block, 'id', 0) or 0)
    return (first_weekday, start_minutes, end_minutes, name, identifier)
