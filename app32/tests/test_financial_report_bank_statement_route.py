import os
import sys
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import financial as financial_route
from api.routes import financial_reports as financial_reports_route
from utils import permissions as permission_utils


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


def test_bank_statement_filters_page_builds_report_context(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(
        financial_reports_route,
        "get_active_company",
        lambda: SimpleNamespace(id=7, name="Empresa Teste"),
    )
    monkeypatch.setattr(financial_reports_route, "get_accessible_company_ids", lambda: [7])
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "get_report_definition_or_error",
        lambda slug: (
            {
                "code": "bank_statement",
                "slug": "extrato-bancario",
                "label": "Extrato Bancário",
                "description": "Extrato gerencial.",
            },
            None,
        ),
    )
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "get_filter_options",
        lambda **kwargs: ({"bank_accounts": []}, None),
    )
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "default_period",
        lambda: (__import__("datetime").date(2026, 4, 1), __import__("datetime").date(2026, 4, 19)),
    )
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "build_management_report",
        lambda **kwargs: (
            {
                "title": "Extrato Bancário",
                "summary_cards": [],
                "general_info": [],
                "rows": [],
                "filters": [],
            },
            None,
        ),
    )
    monkeypatch.setattr(
        financial_reports_route,
        "render_template",
        lambda template_name, **context: f"{template_name}|report={context.get('report') is not None}|slug={context['report_definition']['slug']}",
    )

    client = app.test_client()
    response = client.get("/financial/reports/extrato-bancario", follow_redirects=False)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "modules/financial/report_filters.html" in html
    assert "report=True" in html
    assert "slug=extrato-bancario" in html


def test_bank_statement_view_redirects_to_filters(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)

    client = app.test_client()
    response = client.get("/financial/reports/extrato-bancario/view?period_start=2026-04-01&period_end=2026-04-19", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/financial/reports/extrato-bancario?period_start=2026-04-01&period_end=2026-04-19"
    )


def test_income_statement_filters_page_builds_report_context(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(
        financial_reports_route,
        "get_active_company",
        lambda: SimpleNamespace(id=7, name="Empresa Teste"),
    )
    monkeypatch.setattr(financial_reports_route, "get_accessible_company_ids", lambda: [7])
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "get_report_definition_or_error",
        lambda slug: (
            {
                "code": "income_statement",
                "slug": "demonstrativo-resultados",
                "label": "Demonstrações de Resultados",
                "description": "DRE contábil.",
            },
            None,
        ),
    )
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "get_filter_options",
        lambda **kwargs: ({"chart_accounts": [], "cost_centers": [], "projects": []}, None),
    )
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "default_period",
        lambda: (__import__("datetime").date(2026, 4, 1), __import__("datetime").date(2026, 4, 19)),
    )
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "build_management_report",
        lambda **kwargs: (
            {
                "title": "Demonstrações de Resultados",
                "summary_cards": [],
                "general_info": [],
                "rows": [],
                "hierarchy_rows": [],
                "filters": [],
            },
            None,
        ),
    )
    monkeypatch.setattr(
        financial_reports_route,
        "render_template",
        lambda template_name, **context: f"{template_name}|report={context.get('report') is not None}|slug={context['report_definition']['slug']}",
    )

    client = app.test_client()
    response = client.get("/financial/reports/demonstrativo-resultados", follow_redirects=False)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "modules/financial/report_filters.html" in html
    assert "report=True" in html
    assert "slug=demonstrativo-resultados" in html


def test_income_statement_view_redirects_to_filters(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)

    client = app.test_client()
    response = client.get(
        "/financial/reports/demonstrativo-resultados/view?competence_start=2026-04-01&competence_end=2026-04-19",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/financial/reports/demonstrativo-resultados?competence_start=2026-04-01&competence_end=2026-04-19"
    )
