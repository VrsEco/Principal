from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import pytest
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from models import EmployeeRoleOccupancy
from services.employee_role_occupancy_service import validate_schedule
from services.employee_role_occupancy_service import apply_end, validate_legacy_transition, _actor, _date


def row(role=1, start=1, end=None, hours=20):
    return SimpleNamespace(role_id=role, starts_on=date(2026, 9, start),
                           ends_on=date(2026, 9, end) if end else None,
                           weekly_hours=Decimal(hours) if hours is not None else None)


def test_adjacent_periods_allowed():
    validate_schedule(row(start=10), [row(end=10)], Decimal(40))


def test_same_role_overlap_rejected():
    with pytest.raises(ValueError, match="Já existe"):
        validate_schedule(row(start=9), [row(end=10)], Decimal(40))


def test_simultaneous_capacity_rejected():
    with pytest.raises(ValueError, match="excede"):
        validate_schedule(row(hours=30), [row(role=2)], Decimal(40))


def test_disjoint_other_roles_not_added_together():
    validate_schedule(row(hours=20), [row(role=2, end=10), row(role=3, start=10)], Decimal(40))


def test_future_overlap_checked():
    with pytest.raises(ValueError, match="excede"):
        validate_schedule(row(hours=30), [row(role=2, start=20)], Decimal(40))


def test_unknown_capacity_not_invented():
    validate_schedule(row(hours=None), [], None)


def test_bad_dates_rejected():
    with pytest.raises(ValueError, match="Fim"):
        validate_schedule(row(start=10, end=10), [], Decimal(40))


def test_postgres_schema_contains_tenant_foreign_keys():
    ddl = str(CreateTable(EmployeeRoleOccupancy.__table__).compile(dialect=postgresql.dialect()))
    assert 'FOREIGN KEY(company_id, employee_id)' in ddl
    assert 'FOREIGN KEY(company_id, role_id)' in ddl
    assert 'ends_on > starts_on' in ddl
    assert 'weekly_hours <= 168' in ddl


def test_end_preserves_history_and_author_on_retry():
    occupancy = row()
    occupancy.ended_at = None
    apply_end(occupancy, date(2026, 9, 20), 5)
    timestamp = occupancy.ended_at
    apply_end(occupancy, date(2026, 9, 20), 6)
    assert occupancy.starts_on == date(2026, 9, 1)
    assert occupancy.ended_by_user_id == 5
    assert occupancy.ended_at == timestamp
    with pytest.raises(ValueError, match="já encerrada"):
        apply_end(occupancy, date(2026, 9, 21), 6)


def test_end_cannot_extend_or_precede_start():
    occupancy = row(end=15)
    occupancy.ended_at = None
    for day in (1, 16):
        with pytest.raises(ValueError):
            apply_end(occupancy, date(2026, 9, day), 5)


def test_legacy_secondary_requires_primary_cover():
    employee = SimpleNamespace(role_id=1)
    with pytest.raises(ValueError, match="Reconcilie"):
        validate_legacy_transition(employee, row(role=2), [])
    validate_legacy_transition(employee, row(role=2), [row(role=1)])
    with pytest.raises(ValueError):
        validate_legacy_transition(employee, row(role=2), [row(role=1, end=10)])


def test_unknown_primary_dedication_requires_reconciliation():
    with pytest.raises(ValueError):
        validate_legacy_transition(SimpleNamespace(role_id=1), row(role=2), [row(hours=None)])


@pytest.mark.parametrize("actor", [None, True, 0, -1, "1"])
def test_actor_is_required(actor):
    with pytest.raises(ValueError):
        _actor(actor)


@pytest.mark.parametrize("value", [None, "20260904", "2026-02-30", 123])
def test_strict_date(value):
    with pytest.raises(ValueError):
        _date(value, required=True)
