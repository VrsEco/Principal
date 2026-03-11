from datetime import datetime
from types import SimpleNamespace

from services.process_routine_scheduler_service import (
    build_automatic_instance_code,
    calculate_due_date_for_routine,
    is_routine_due,
)


def _routine(**overrides):
    base = {
        "id": 99,
        "process_id": 12,
        "schedule_type": "weekly",
        "schedule_value": "segunda,quarta",
        "deadline_days": 0,
        "deadline_hours": 0,
        "deadline_date": None,
        "process": SimpleNamespace(code="PROC.12"),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_is_routine_due_supports_daily_time_precision():
    routine = _routine(schedule_type="daily", schedule_value="09:15")

    assert is_routine_due(routine, datetime(2026, 3, 11, 9, 15))
    assert not is_routine_due(routine, datetime(2026, 3, 11, 9, 14))


def test_is_routine_due_supports_weekly_portuguese_days():
    routine = _routine(schedule_type="weekly", schedule_value="quarta,sexta")

    assert is_routine_due(routine, datetime(2026, 3, 11, 8, 0))
    assert not is_routine_due(routine, datetime(2026, 3, 12, 8, 0))


def test_is_routine_due_supports_monthly_quarterly_yearly_and_specific():
    assert is_routine_due(_routine(schedule_type="monthly", schedule_value="31"), datetime(2026, 2, 28, 0, 0))
    assert is_routine_due(_routine(schedule_type="quarterly", schedule_value="3-31"), datetime(2026, 3, 31, 0, 0))
    assert is_routine_due(_routine(schedule_type="yearly", schedule_value="29/02"), datetime(2026, 2, 28, 0, 0))
    assert is_routine_due(_routine(schedule_type="specific", schedule_value="2026-03-11"), datetime(2026, 3, 11, 10, 0))


def test_build_automatic_instance_code_is_deterministic_per_day():
    routine = _routine(id=7, process_id=44, process=SimpleNamespace(code="FIN.44"))

    code = build_automatic_instance_code(routine, datetime(2026, 3, 11, 14, 30))

    assert code == "FIN.44-RT7-20260311"


def test_calculate_due_date_for_routine_uses_relative_deadline():
    routine = _routine(deadline_days=1, deadline_hours=6)

    due_date = calculate_due_date_for_routine(routine, datetime(2026, 3, 11, 20, 0))

    assert due_date.isoformat() == "2026-03-13"
