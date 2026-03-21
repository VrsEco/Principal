import os
import sys
from types import SimpleNamespace

from flask import Flask, session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import incentives as incentives_route


class _FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter_by(self, **kwargs):
        rows = self._rows
        for key, value in kwargs.items():
            rows = [row for row in rows if getattr(row, key, None) == value]
        return _FakeQuery(rows)

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)


def _build_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.secret_key = "test"
    return app


def test_closings_list_route_renders_only_active_rule_sets(monkeypatch):
    app = _build_app()

    closings = [
        SimpleNamespace(
            id=501,
            company_id=9,
            period_start=SimpleNamespace(strftime=lambda fmt: "03/2026"),
            created_at=SimpleNamespace(strftime=lambda fmt: "18/03/2026 10:00"),
            participants_count=3,
            total_distributed=1500,
            status="approved",
        )
    ]
    active_rule_sets = [
        SimpleNamespace(id=101, name="Plano Ativo", periodicity="monthly", is_active=True),
    ]

    monkeypatch.setattr(
        incentives_route,
        "IncentiveCalculation",
        SimpleNamespace(
            period_start=SimpleNamespace(desc=lambda: None),
            query=_FakeQuery(closings),
        ),
    )
    monkeypatch.setattr(
        incentives_route,
        "IncentiveService",
        SimpleNamespace(
            get_active_rule_sets_query=lambda company_id: _FakeQuery(active_rule_sets),
            get_active_calculations_query=lambda company_id: _FakeQuery(closings),
        ),
    )

    captured = {}

    def _fake_render(template_name, **context):
        captured["template"] = template_name
        captured["context"] = context
        return "ok"

    monkeypatch.setattr(incentives_route, "render_template", _fake_render)
    monkeypatch.setattr(incentives_route, "is_administrator", lambda company_id: True)

    with app.test_request_context("/incentives/closings"):
        session["active_company_id"] = 9
        response = incentives_route.closings_list.__wrapped__()

    assert response == "ok"
    assert captured["template"] == "modules/incentives/closings_list.html"
    assert len(captured["context"]["closings"]) == 1
    assert [rs.name for rs in captured["context"]["rule_sets"]] == ["Plano Ativo"]
