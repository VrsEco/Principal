import os
import sys
from pathlib import Path

from flask import Flask
from flask_login import LoginManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import financial as financial_route
from api.routes import financial_reports as financial_reports_route
from utils import permissions as permission_utils


class _CompanyStub:
    def __init__(self, company_id: int, name: str):
        self.id = company_id
        self.name = name

    def to_dict(self):
        return {"id": self.id, "name": self.name}


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


def test_working_capital_view_uses_dedicated_balance_template(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(
        financial_reports_route,
        "get_active_company",
        lambda: _CompanyStub(7, "Empresa Teste"),
    )
    monkeypatch.setattr(financial_reports_route, "get_accessible_company_ids", lambda: [7])
    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "build_management_report",
        lambda **kwargs: (
            {
                "report_type": "working_capital",
                "report_slug": "capital-circulante-liquido",
                "title": "Capital Circulante Líquido",
                "subtitle": "Balanço gerencial.",
                "generated_at": "2026-04-23 10:00",
                "filters": [],
                "general_info": [],
                "balance_sheet": {
                    "asset": {
                        "title": "Ativo",
                        "current": {"title": "Circulante", "amount": "20.514,93", "groups": []},
                        "non_current": {"title": "Ativo Não Circulante", "amount": "0,00"},
                    },
                    "liability": {
                        "title": "Passivo",
                        "current": {"title": "Circulante", "amount": "4.586,00", "groups": []},
                        "non_current": {"title": "Passivo Não Circulante", "amount": "0,00"},
                        "equity": {"title": "Patrimônio Líquido", "amount": "15.928,93"},
                    },
                    "working_capital": {"title": "Capital Circulante Líquido", "amount": "15.928,93"},
                    "patrimonial_status": {"title": "Situação Patrimonial", "amount": "15.928,93"},
                },
            },
            None,
        ),
    )
    monkeypatch.setattr(
        financial_reports_route,
        "render_template",
        lambda template_name, **context: f"{template_name}|report_type={context['report']['report_type']}|title={context['report']['title']}",
    )

    client = app.test_client()
    response = client.get("/financial/reports/capital-circulante-liquido/view", follow_redirects=False)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "modules/financial/report_view.html" in html
    assert "report_type=working_capital" in html
    assert "title=Capital Circulante Líquido" in html


def test_working_capital_partial_is_registered_in_main_view():
    main_template = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\report_view.html").read_text(encoding="utf-8")
    partial_template = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\partials\report_view_working_capital.html").read_text(encoding="utf-8")

    assert "report_view_working_capital.html" in main_template
    assert "{% block sidebar_right %}{% endblock %}" in main_template
    assert "wc-balance-sheet" in partial_template
    assert "report.balance_sheet.patrimonial_status.title" in partial_template
