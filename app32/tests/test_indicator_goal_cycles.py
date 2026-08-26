from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from services.indicator_service import (
    IndicatorGoalService,
    aggregate_measurement_values,
    get_goal_cycle_bounds,
    goal_is_effective,
)


class _FakeQuery:
    def __init__(self, items):
        self.items = list(items)

    def filter_by(self, **filters):
        return _FakeQuery([
            item for item in self.items
            if all(getattr(item, key, None) == value for key, value in filters.items())
        ])

    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return list(self.items)

    def first(self):
        return self.items[0] if self.items else None


def _goal(**overrides):
    values = {
        "period_start": date(2026, 9, 1),
        "period_end": None,
        "goal_date": None,
        "goal_type": "monthly",
        "status": "active",
        "created_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_monthly_goal_is_open_ended_and_resolves_each_competency():
    goal = _goal()

    assert goal_is_effective(goal, date(2027, 2, 15)) is True
    assert get_goal_cycle_bounds(goal, date(2026, 9, 15)) == (
        date(2026, 9, 1),
        date(2026, 9, 30),
    )
    assert get_goal_cycle_bounds(goal, date(2027, 2, 15)) == (
        date(2027, 2, 1),
        date(2027, 2, 28),
    )


def test_versioned_goal_stops_before_next_version():
    goal = _goal(period_end=date(2026, 10, 31))

    assert goal_is_effective(goal, date(2026, 10, 31)) is True
    assert goal_is_effective(goal, date(2026, 11, 1)) is False


def test_single_campaign_uses_explicit_window():
    goal = _goal(
        goal_type="single",
        period_start=date(2026, 12, 1),
        period_end=date(2026, 12, 31),
    )

    assert get_goal_cycle_bounds(goal, date(2026, 12, 15)) == (
        date(2026, 12, 1),
        date(2026, 12, 31),
    )


def test_measurement_aggregation_respects_configured_function():
    values = [Decimal("100"), Decimal("250"), Decimal("50")]

    assert aggregate_measurement_values(values, "sum") == Decimal("400")
    assert aggregate_measurement_values(values, "avg") == Decimal("133.3333333333333333333333333")
    assert aggregate_measurement_values(values, "last") == Decimal("50")
    assert aggregate_measurement_values(values, "count") == Decimal("3")
    assert aggregate_measurement_values([], "sum") is None


def test_new_base_version_automatically_closes_previous(monkeypatch):
    from services import indicator_service

    previous = SimpleNamespace(
        id=1,
        company_id=7,
        indicator_id=9,
        responsible_id=None,
        goal_kind="base",
        goal_type="monthly",
        period_start=date(2026, 9, 1),
        period_end=None,
        composition_mode="independent",
        status="active",
    )
    new_version = SimpleNamespace(
        id=None,
        company_id=7,
        indicator_id=9,
        responsible_id=None,
        goal_kind="base",
        goal_type="monthly",
        period_start=date(2026, 11, 1),
        period_end=None,
        composition_mode="independent",
        status="active",
    )
    monkeypatch.setattr(
        IndicatorGoalService,
        "_query",
        staticmethod(lambda: _FakeQuery([previous])),
    )

    IndicatorGoalService.apply_base_versioning(new_version)

    assert previous.period_end == date(2026, 10, 31)
    assert previous.status == "superseded"
    assert new_version.period_end is None


def test_effective_goal_resolution_keeps_additive_and_independent_campaigns(monkeypatch):
    from services import indicator_service

    def item(identifier, kind, composition, value):
        return SimpleNamespace(
            id=identifier,
            company_id=7,
            indicator_id=9,
            responsible_id=None,
            goal_kind=kind,
            goal_scope="team",
            composition_mode=composition,
            goal_value=Decimal(value),
            period_start=date(2026, 12, 1),
            period_end=date(2026, 12, 31) if kind == "campaign" else None,
            goal_date=None,
            status="active",
            created_at=None,
        )

    base = item(1, "base", "independent", "350000")
    additive = item(2, "campaign", "additive", "100000")
    independent = item(3, "campaign", "independent", "50000")
    monkeypatch.setattr(
        IndicatorGoalService,
        "_query",
        staticmethod(lambda: _FakeQuery([base, additive, independent])),
    )

    context = IndicatorGoalService.resolve_effective_goals(7, 9, date(2026, 12, 15))

    assert context["base"] is base
    assert context["additive_campaigns"] == [additive]
    assert context["independent_campaigns"] == [independent]


def test_performance_context_sums_current_cycle_and_additive_campaign(monkeypatch):
    base = SimpleNamespace(
        id=1,
        responsible_id=None,
        goal_value=Decimal("350000"),
        goal_type="monthly",
        period_start=date(2026, 11, 1),
        period_end=None,
        goal_date=None,
    )
    campaign = SimpleNamespace(goal_value=Decimal("100000"))
    measurements = [
        SimpleNamespace(id=1, measured_value=Decimal("200000")),
        SimpleNamespace(id=2, measured_value=Decimal("175000")),
    ]
    indicator = SimpleNamespace(id=9, aggregation_function="sum")
    monkeypatch.setattr(
        IndicatorGoalService,
        "resolve_effective_goals",
        staticmethod(lambda *_args, **_kwargs: {
            "base": base,
            "additive_campaigns": [campaign],
            "independent_campaigns": [],
        }),
    )
    monkeypatch.setattr(
        IndicatorGoalService,
        "_measurement_query",
        staticmethod(lambda: _FakeQuery(measurements)),
    )

    context = IndicatorGoalService.performance_context(7, indicator, date(2026, 12, 15))

    assert context["target_value"] == Decimal("450000")
    assert context["realized_value"] == Decimal("375000")
    assert context["cycle_start"] == date(2026, 12, 1)
    assert context["cycle_end"] == date(2026, 12, 31)


def test_consolidated_context_sums_individual_targets_and_measurements(monkeypatch):
    indicator = SimpleNamespace(id=9, aggregation_function="sum", polarity="positive")
    individual_contexts = [
        {
            "base": SimpleNamespace(performance_ranges=None),
            "target_value": Decimal("80000"),
            "realized_value": Decimal("75000"),
            "cycle_start": date(2026, 12, 1),
            "cycle_end": date(2026, 12, 31),
        },
        {
            "base": SimpleNamespace(performance_ranges=None),
            "target_value": Decimal("90000"),
            "realized_value": Decimal("85000"),
            "cycle_start": date(2026, 12, 1),
            "cycle_end": date(2026, 12, 31),
        },
    ]
    monkeypatch.setattr(
        IndicatorGoalService,
        "performance_context",
        staticmethod(lambda *_args, **_kwargs: {
            "base": None,
            "additive_campaigns": [],
            "independent_campaigns": [],
            "target_value": None,
            "realized_value": None,
            "cycle_start": None,
            "cycle_end": None,
        }),
    )
    monkeypatch.setattr(
        IndicatorGoalService,
        "individual_performance_contexts",
        staticmethod(lambda *_args, **_kwargs: individual_contexts),
    )

    context = IndicatorGoalService.consolidated_performance_context(7, indicator, date(2026, 12, 15))

    assert context["target_value"] == Decimal("170000")
    assert context["realized_value"] == Decimal("160000")
    assert context["target_source"] == "individual_sum"
    assert context["allocation_gap"] == Decimal("0")


def test_measurement_inherits_consultant_from_individual_goal(monkeypatch):
    goal = SimpleNamespace(
        id=11,
        company_id=7,
        indicator_id=9,
        responsible_id=42,
    )
    employee = SimpleNamespace(id=42, company_id=7)
    monkeypatch.setattr(
        IndicatorGoalService,
        "_query",
        staticmethod(lambda: _FakeQuery([goal])),
    )
    monkeypatch.setattr(
        IndicatorGoalService,
        "_employee_query",
        staticmethod(lambda: _FakeQuery([employee])),
    )

    payload = IndicatorGoalService.prepare_measurement_payload(
        7,
        {"goal_id": 11, "indicator_id": 9, "measured_value": 100},
    )

    assert payload["employee_id"] == 42


def test_measurement_rejects_consultant_different_from_individual_goal(monkeypatch):
    import pytest

    goal = SimpleNamespace(
        id=11,
        company_id=7,
        indicator_id=9,
        responsible_id=42,
    )
    monkeypatch.setattr(
        IndicatorGoalService,
        "_query",
        staticmethod(lambda: _FakeQuery([goal])),
    )

    with pytest.raises(ValueError, match="consultor definido"):
        IndicatorGoalService.prepare_measurement_payload(
            7,
            {"goal_id": 11, "indicator_id": 9, "employee_id": 99},
        )


def test_individual_goal_requires_consultant():
    import pytest

    goal = SimpleNamespace(
        period_start=date(2026, 9, 1),
        period_end=None,
        goal_value=Decimal("100000"),
        goal_kind="base",
        goal_scope="individual",
        responsible_id=None,
        composition_mode="independent",
        goal_type="monthly",
    )

    with pytest.raises(ValueError, match="Selecione o consultor"):
        IndicatorGoalService.validate_goal(goal)
