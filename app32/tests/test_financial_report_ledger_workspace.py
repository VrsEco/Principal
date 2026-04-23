import os
import sys
from pathlib import Path
from types import SimpleNamespace

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import financial as financial_route
from api.routes import financial_reports as financial_reports_route
from services.financial_report_service import FinancialReportService
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


def test_ledger_filters_page_builds_workspace_report(monkeypatch):
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
                "code": "ledger",
                "slug": "razao",
                "label": "Razão",
                "description": "Razão gerencial.",
                "filters": ("ledger_config",),
            },
            None,
        ),
    )
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "get_filter_options",
        lambda **kwargs: ({"chart_accounts": [], "cost_centers": [], "projects": [], "processes": [], "counterparties": []}, None),
    )
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "default_period",
        lambda: (__import__("datetime").date(2026, 4, 1), __import__("datetime").date(2026, 4, 30)),
    )
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "build_management_report",
        lambda **kwargs: (
            {
                "title": "Razão",
                "summary_cards": [],
                "general_info": [],
                "rows": [],
                "groups": [],
                "filters": [],
                "grouped_by": "code",
                "grouped_by_label": "Plano de Contas",
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
    response = client.get("/financial/reports/razao", follow_redirects=False)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "modules/financial/report_filters.html" in html
    assert "report=True" in html
    assert "slug=razao" in html


def test_ledger_view_redirects_to_filters(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)

    client = app.test_client()
    response = client.get("/financial/reports/razao/view?competence_start=2026-04-01&competence_end=2026-04-30", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/financial/reports/razao?competence_start=2026-04-01&competence_end=2026-04-30"
    )


def test_ledger_normalize_accepts_grouping_and_type_filter():
    filters, error = FinancialReportService._normalize_filters(
        "ledger",
        {
            "competence_start": "2026-04-01",
            "competence_end": "2026-04-30",
            "movement_nature": "credit",
            "order_by": "movement_nature",
            "include_settled": "true",
            "include_budget_vs_actual": "true",
            "include_open": "true",
        },
    )

    assert error is None
    assert filters is not None
    assert filters.movement_nature == "credit"
    assert filters.order_by == "movement_nature"


def test_ledger_templates_use_sidebar_grouping_copy():
    filters_template = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\report_filters.html").read_text(encoding="utf-8")
    sidebar = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\partials\report_filters_ledger_sidebar.html").read_text(encoding="utf-8")
    page = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\partials\report_filters_ledger_page.html").read_text(encoding="utf-8")

    assert "report_filters_ledger_page.html" in filters_template
    assert "report_filters_ledger_sidebar.html" in filters_template
    assert "Agrupado por" in sidebar
    assert "numero_qtd_rateio" in page
