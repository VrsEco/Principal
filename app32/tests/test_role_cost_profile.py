from decimal import Decimal
import pytest
from models import RoleCostProfile, Role
from services.role_cost_profile_service import normalize_cost_profile
from services.role_cost_profile_service import planned_cost_snapshot
from datetime import date


def payload(**kwargs):
    return {"starts_on": "2026-09-01", "currency": "BRL", **kwargs}


def test_components_unknown_not_zero():
    profile = RoleCostProfile(**normalize_cost_profile(payload(base_salary="3000", charges="900")))
    assert profile.amounts() == {"known_subtotal": Decimal("3900"), "known_components": 2, "monthly_cost_per_fte": None}


def test_all_components_explicit_produces_total():
    profile = RoleCostProfile(**normalize_cost_profile(payload(base_salary="3000", charges="900", benefits="400", other_costs=0)))
    assert profile.amounts()["monthly_cost_per_fte"] == Decimal("4300")


@pytest.mark.parametrize("value", [-1, True, "NaN", "Infinity", "0.001", "1000000000000", {}, ""])
def test_invalid_amount(value):
    with pytest.raises(ValueError):
        normalize_cost_profile(payload(base_salary=value))


@pytest.mark.parametrize("currency", [None, "brl", "BR", "BRLL", 123])
def test_currency_required(currency):
    with pytest.raises(ValueError):
        normalize_cost_profile(payload(currency=currency))


def test_general_role_serializer_does_not_expose_costs():
    assert not any("cost" in key or "salary" in key for key in Role(title="Analista").to_dict())


def test_end_date_exclusive():
    with pytest.raises(ValueError):
        normalize_cost_profile(payload(ends_on="2026-09-01"))


def test_planned_snapshot_uses_selected_profile_without_exposing_components():
    role = Role(id=1, company_id=7, title="Analista", headcount_planned=2, weekly_hours=40)
    profile = RoleCostProfile(company_id=7, role_id=1, **normalize_cost_profile(payload(base_salary=3000, charges=0, benefits=0, other_costs=0)))
    result = planned_cost_snapshot(7, date(2026, 9, 4), [role], [profile])
    assert result["planned_monthly_total"] == "6000.00"
    assert result["roles"] == [{"role_id": 1, "role_title": "Analista", "planned_monthly_cost": "6000.00"}]
    assert "base_salary" not in str(result)
    assert "Não é folha" in result["basis"]


def test_missing_profile_preserves_unknown_total():
    role = Role(id=1, company_id=7, title="Analista", headcount_planned=2)
    assert planned_cost_snapshot(7, date(2026, 9, 4), [role], [])["planned_monthly_total"] is None


def test_overlapping_profiles_rejected():
    role = Role(id=1, company_id=7, title="Analista", headcount_planned=2)
    profile = RoleCostProfile(company_id=7, role_id=1, **normalize_cost_profile(payload()))
    with pytest.raises(ValueError, match="sobrepostos"):
        planned_cost_snapshot(7, date(2026, 9, 4), [role], [profile, profile])
