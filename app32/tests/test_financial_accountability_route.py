import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import financial as financial_route
from utils import permissions as permission_utils


class _FakeColumn:
    def __init__(self, attr_name):
        self.attr_name = attr_name

    def __eq__(self, other):
        return lambda row: getattr(row, self.attr_name) == other

    def is_(self, other):
        return lambda row: getattr(row, self.attr_name) is other

    def in_(self, values):
        values = set(values or [])
        return lambda row: getattr(row, self.attr_name) in values

    def asc(self):
        return ("asc", self.attr_name)

    def desc(self):
        return ("desc", self.attr_name)


class _FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *conditions):
        filtered = self._rows
        for condition in conditions:
            if callable(condition):
                filtered = [row for row in filtered if condition(row)]
        return _FakeQuery(filtered)

    def order_by(self, *columns):
        rows = list(self._rows)
        for column in reversed(columns):
            if isinstance(column, tuple):
                direction, attr_name = column
            else:
                direction, attr_name = "asc", getattr(column, "attr_name", "name")
            rows.sort(
                key=lambda row: getattr(row, attr_name, "") if getattr(row, attr_name, "") is not None else "",
                reverse=direction == "desc",
            )
        return _FakeQuery(rows)

    def all(self):
        return list(self._rows)


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")),
    )
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.secret_key = "test"
    login_manager = LoginManager(app)

    @login_manager.user_loader
    def _load_user(user_id):
        return None

    app.register_blueprint(financial_route.financial_bp)
    return app


def test_financial_accountability_route_renders_review_flow(monkeypatch):
    app = _build_app()
    captured = {}

    monkeypatch.setattr(
        financial_route,
        "get_active_company",
        lambda: SimpleNamespace(id=9, name="GanduInvest", client_code="GND"),
    )
    monkeypatch.setattr(financial_route, "has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(
        financial_route,
        "render_template",
        lambda template_name, **context: (
            captured.update(
                {
                    "payload": {
                        "template_name": template_name,
                        "context": context,
                    }
                }
            )
            or "ok"
        ),
    )

    bank_accounts = [
        SimpleNamespace(
            id=1,
            company_id=9,
            deleted_at=None,
            is_active=True,
            name="Conta principal",
            code="CX.1",
            metadata_json={"is_default": True},
        )
    ]
    chart_accounts = [
        SimpleNamespace(
            id=2,
            company_id=9,
            deleted_at=None,
            is_active=True,
            accepts_posting=True,
            code="3.1.01",
            name="Despesas operacionais",
            movement_nature="debit",
            metadata_json={"default_for_accountability": True},
        )
    ]
    cost_centers = [
        SimpleNamespace(
            id=3,
            company_id=9,
            deleted_at=None,
            is_active=True,
            accepts_posting=True,
            name="Comercial",
            code="CC.1",
            is_default_suggestion=True,
        )
    ]
    counterparties = [
        SimpleNamespace(
            id=4,
            company_id=9,
            deleted_at=None,
            is_active=True,
            name="Fornecedor ABC",
            code="F.1",
            default_chart_account_id=2,
            default_cost_center_id=3,
        )
    ]
    enabled_domains = [
        SimpleNamespace(
            company_id=9,
            deleted_at=None,
            is_enabled=True,
            is_default_suggestion=True,
            domain_type="project",
            source_id=50,
            notes="Projeto principal",
        )
    ]
    projects = [SimpleNamespace(id=50, company_id=9, code="AA.J.31", name="Produção")]

    monkeypatch.setattr(
        financial_route,
        "FinancialBankAccount",
        SimpleNamespace(
            query=_FakeQuery(bank_accounts),
            company_id=_FakeColumn("company_id"),
            deleted_at=_FakeColumn("deleted_at"),
            is_active=_FakeColumn("is_active"),
            name=_FakeColumn("name"),
        ),
    )
    monkeypatch.setattr(
        financial_route,
        "FinancialChartAccount",
        SimpleNamespace(
            query=_FakeQuery(chart_accounts),
            company_id=_FakeColumn("company_id"),
            deleted_at=_FakeColumn("deleted_at"),
            is_active=_FakeColumn("is_active"),
            accepts_posting=_FakeColumn("accepts_posting"),
            code=_FakeColumn("code"),
            name=_FakeColumn("name"),
        ),
    )
    monkeypatch.setattr(
        financial_route,
        "FinancialCostCenter",
        SimpleNamespace(
            query=_FakeQuery(cost_centers),
            company_id=_FakeColumn("company_id"),
            deleted_at=_FakeColumn("deleted_at"),
            is_active=_FakeColumn("is_active"),
            accepts_posting=_FakeColumn("accepts_posting"),
            is_default_suggestion=_FakeColumn("is_default_suggestion"),
            name=_FakeColumn("name"),
        ),
    )
    monkeypatch.setattr(
        financial_route,
        "FinancialCounterparty",
        SimpleNamespace(
            query=_FakeQuery(counterparties),
            company_id=_FakeColumn("company_id"),
            deleted_at=_FakeColumn("deleted_at"),
            is_active=_FakeColumn("is_active"),
            name=_FakeColumn("name"),
        ),
    )
    monkeypatch.setattr(
        financial_route,
        "FinancialDomainEnablement",
        SimpleNamespace(
            query=_FakeQuery(enabled_domains),
            company_id=_FakeColumn("company_id"),
            deleted_at=_FakeColumn("deleted_at"),
            is_enabled=_FakeColumn("is_enabled"),
            is_default_suggestion=_FakeColumn("is_default_suggestion"),
            domain_type=_FakeColumn("domain_type"),
            source_id=_FakeColumn("source_id"),
        ),
    )
    monkeypatch.setattr(
        financial_route,
        "Project",
        SimpleNamespace(
            query=_FakeQuery(projects),
            company_id=_FakeColumn("company_id"),
            id=_FakeColumn("id"),
        ),
    )
    monkeypatch.setattr(
        financial_route,
        "Process",
        SimpleNamespace(
            query=_FakeQuery([]),
            company_id=_FakeColumn("company_id"),
            id=_FakeColumn("id"),
        ),
    )

    client = app.test_client()
    response = client.get("/financial/accountability?company_id=9")

    assert response.status_code == 200
    assert captured["payload"]["template_name"] == "modules/financial/accountability.html"
    context = captured["payload"]["context"]
    assert context["company_id"] == 9
    assert context["can_create"] is True
    assert context["counterparties"][0].name == "Fornecedor ABC"
    assert context["default_bank_account_id"] == 1
    assert context["default_chart_account_id"] == 2
    assert context["default_cost_center_id"] == 3
    assert context["default_domain_key"] == "project:50"
    assert context["domain_options"][0]["label"] == "Projeto · AA.J.31 · Produção"
