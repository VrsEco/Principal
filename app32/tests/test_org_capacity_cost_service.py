from decimal import Decimal
import pytest
from services.org_capacity_cost_service import project_organogram


def snapshot():
    roles = [{"id": i, "company_id": 1, "headcount_planned": 1, "weekly_hours": 40,
              "monthly_cost_per_fte": "5000.00", "currency": "BRL"} for i in (1, 2)]
    employees = [{"id": 9, "company_id": 1, "weekly_hours": 40}]
    occupancies = [{"company_id": 1, "role_id": i, "employee_id": 9, "weekly_hours": 20} for i in (1, 2)]
    return roles, employees, occupancies


def test_split_person_counts_once_and_costs_half_each():
    result = project_organogram(1, *snapshot())
    assert result["distinct_people_count"] == 1
    assert result["planned_monthly_total"] == Decimal("10000.00")
    assert all(row["occupied_fte"] == Decimal("0.5") for row in result["roles"])
    assert all(row["occupied_monthly_cost_estimate"] == Decimal("2500.00") for row in result["roles"])


def test_unknown_cost_is_not_zero_or_complete_total():
    roles, employees, occupancies = snapshot()
    roles[0]["monthly_cost_per_fte"] = None
    result = project_organogram(1, roles, employees, occupancies)
    assert result["planned_monthly_total"] is None
    assert result["known_planned_monthly_subtotal"] == Decimal("5000")
    assert result["costed_roles_count"] == 1


def test_zero_cost_is_known():
    roles, employees, occupancies = snapshot()
    roles[0]["monthly_cost_per_fte"] = 0
    assert project_organogram(1, roles, employees, occupancies)["costed_roles_count"] == 2


@pytest.mark.parametrize("collection", [0, 1, 2])
def test_foreign_tenant_rejected(collection):
    data = snapshot()
    data[collection][0]["company_id"] = 2
    with pytest.raises(ValueError, match="outra empresa"):
        project_organogram(1, *data)


def test_overallocation_rejected_across_roles():
    roles, employees, occupancies = snapshot()
    occupancies[0]["weekly_hours"] = 21
    with pytest.raises(ValueError, match="excede"):
        project_organogram(1, roles, employees, occupancies)


def test_unknown_dedication_marks_pending():
    roles, employees, occupancies = snapshot()
    occupancies[0]["weekly_hours"] = None
    row = project_organogram(1, roles, employees, occupancies)["roles"][0]
    assert row["capacity_pending"]
    assert row["occupied_fte"] is None
    assert row["occupied_monthly_cost_estimate"] is None


def test_mixed_currency_rejected():
    roles, employees, occupancies = snapshot()
    roles[0]["currency"] = "USD"
    with pytest.raises(ValueError, match="moedas"):
        project_organogram(1, roles, employees, occupancies)


@pytest.mark.parametrize("value", [-1, True, "NaN", "Infinity", "abc"])
def test_invalid_cost_rejected(value):
    roles, employees, occupancies = snapshot()
    roles[0]["monthly_cost_per_fte"] = value
    with pytest.raises(ValueError):
        project_organogram(1, roles, employees, occupancies)


def test_duplicate_occupancy_rejected():
    roles, employees, occupancies = snapshot()
    occupancies.append(dict(occupancies[0]))
    with pytest.raises(ValueError, match="duplicada"):
        project_organogram(1, roles, employees, occupancies)
