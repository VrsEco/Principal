import os
import sys
from datetime import date, datetime
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import indicators as indicators_route
from utils.indicator_ranges import normalize_performance_ranges


class _FakeColumn:
    def __init__(self, attr_name, *, reverse=False):
        self.attr_name = attr_name
        self.reverse = reverse

    def desc(self):
        return _FakeColumn(self.attr_name, reverse=True)


class _FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter_by(self, **kwargs):
        filtered = self._rows
        for key, value in kwargs.items():
            filtered = [row for row in filtered if getattr(row, key, None) == value]
        return _FakeQuery(filtered)

    def order_by(self, *columns):
        rows = list(self._rows)
        for column in reversed(columns):
            attr_name = getattr(column, "attr_name", None)
            reverse = getattr(column, "reverse", False)
            if not attr_name:
                continue
            rows = sorted(rows, key=lambda row: getattr(row, attr_name, None), reverse=reverse)
        return _FakeQuery(rows)

    def all(self):
        return list(self._rows)


def _build_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    return app


def test_normalize_performance_ranges_supports_legacy_band_list():
    legacy_ranges = [
        {"color": "red", "min": 0, "max": 79},
        {"color": "yellow", "min": 80, "max": 94},
        {"color": "green", "min": 95, "max": 109},
        {"color": "blue", "min": 110, "max": 200},
    ]

    assert normalize_performance_ranges(legacy_ranges) == {
        "red": 80.0,
        "yellow": 95.0,
        "green": 110.0,
    }


def test_indicator_dashboard_accepts_legacy_performance_ranges(monkeypatch):
    app = _build_app()

    indicator = SimpleNamespace(
        id=1,
        company_id=15,
        name="Margem Operacional",
        indicator_type="result",
        polarity="positive",
        is_active=True,
    )
    goal = SimpleNamespace(
        id=10,
        company_id=15,
        indicator_id=1,
        goal_value=100,
        status="active",
        created_at=datetime(2026, 3, 1, 10, 0, 0),
        performance_ranges=[
            {"color": "red", "min": 0, "max": 79},
            {"color": "yellow", "min": 80, "max": 94},
            {"color": "green", "min": 95, "max": 109},
            {"color": "blue", "min": 110, "max": 200},
        ],
    )
    last_data = SimpleNamespace(
        id=20,
        company_id=15,
        indicator_id=1,
        measured_value=109,
        measured_date=date(2026, 3, 24),
    )

    monkeypatch.setattr(
        indicators_route,
        "Indicator",
        SimpleNamespace(
            query=_FakeQuery([indicator]),
            indicator_type=_FakeColumn("indicator_type"),
            name=_FakeColumn("name"),
        ),
    )
    monkeypatch.setattr(
        indicators_route,
        "IndicatorGoal",
        SimpleNamespace(
            query=_FakeQuery([goal]),
            indicator_id=_FakeColumn("indicator_id"),
            created_at=_FakeColumn("created_at"),
        ),
    )
    monkeypatch.setattr(
        indicators_route,
        "IndicatorData",
        SimpleNamespace(
            query=_FakeQuery([last_data]),
            indicator_id=_FakeColumn("indicator_id"),
            measured_date=_FakeColumn("measured_date"),
        ),
    )
    monkeypatch.setattr(
        indicators_route,
        "IndicatorTree",
        SimpleNamespace(query=_FakeQuery([]), code=_FakeColumn("code")),
    )
    monkeypatch.setattr(
        indicators_route,
        "IndicatorGoalService",
        SimpleNamespace(
            consolidated_performance_context=lambda company_id, selected_indicator, reference_date: {
                "base": goal,
                "realized_value": 109,
                "target_value": 100,
                "cycle_start": date(2026, 3, 1),
                "cycle_end": date(2026, 3, 31),
                "additive_campaigns": [],
                "independent_campaigns": [],
                "individual_contexts": [],
                "individual_target_sum": None,
                "allocation_gap": None,
                "target_source": "team",
            },
            classify_performance=lambda selected_indicator, selected_goal, target, realized: {
                "status_class": "on_target",
                "performance_pct": 109.0,
            },
        ),
    )

    captured = {}

    def _fake_render(template_name, **context):
        captured["template"] = template_name
        captured["context"] = context
        return "ok"

    monkeypatch.setattr(indicators_route, "render_template", _fake_render)

    with app.test_request_context("/indicators/dashboard"):
        session["active_company_id"] = 15
        response = indicators_route.indicator_dashboard.__wrapped__()

    assert response == "ok"
    assert captured["template"] == "modules/indicators/indicator_dashboard.html"
    assert captured["context"]["kpi_data"][0]["status_class"] == "on_target"
    assert captured["context"]["kpi_data"][0]["performance_pct"] == 109.0
