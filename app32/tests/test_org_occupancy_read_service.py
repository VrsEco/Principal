from datetime import date
from types import SimpleNamespace as Row
import pytest
from services.org_occupancy_read_service import resolve_snapshot


TODAY = date(2026, 9, 4)


def data():
    roles = [Row(id=1, company_id=7, title="Analista"), Row(id=2, company_id=7, title="Gestor")]
    employees = [Row(id=9, company_id=7, role_id=1, name="Ana", status="active")]
    return roles, employees


def occupancy(role=1, end=None):
    return Row(company_id=7, employee_id=9, role_id=role, starts_on=date(2026, 9, 1), ends_on=end, weekly_hours=20)


def resolve(history, reference=TODAY):
    return resolve_snapshot(7, reference, *data(), history, current_date=TODAY)


def test_legacy_current_is_marked_unverified_without_assumed_hours():
    result = resolve([])
    assert result["assignments"][0]["source"] == "legacy_unverified"
    assert result["assignments"][0]["weekly_hours"] is None
    assert not result["legacy_reconciliation_complete"]


@pytest.mark.parametrize("reference", [date(2026, 8, 1), date(2026, 10, 1)])
def test_legacy_does_not_invent_history_or_future(reference):
    result = resolve([], reference)
    assert result["assignments"] == []
    assert result["legacy_pending_employee_ids"] == [9]


def test_multiple_roles_one_person():
    result = resolve([occupancy(), occupancy(role=2)])
    assert len(result["assignments"]) == 2
    assert result["distinct_people_count"] == 1


def test_ended_occupancy_not_resurrected_from_legacy():
    assert resolve([occupancy(end=TODAY)])["assignments"] == []


def test_overlap_rejected():
    with pytest.raises(ValueError, match="sobrepostas"):
        resolve([occupancy(), occupancy()])


def test_tenant_crossing_rejected():
    item = occupancy()
    item.company_id = 8
    with pytest.raises(ValueError, match="empresa"):
        resolve([item])


def test_no_sensitive_fields():
    result = resolve([occupancy()])
    assert set(result["assignments"][0]) == {"employee_id", "role_id", "employee_name", "role_title", "weekly_hours", "source", "capacity_pending"}
