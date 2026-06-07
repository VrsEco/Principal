import os
import sys
from io import BytesIO
from types import SimpleNamespace

from flask import Flask, render_template
from flask_login import LoginManager
from pypdf import PdfReader

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


def test_bank_statement_dossier_filters_page_builds_report_context(monkeypatch):
    app = _build_app()
    captured = {}
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
                "code": "bank_statement_dossier",
                "slug": "dossie-extrato-bancario",
                "label": "Dossiê do Extrato Bancário",
                "description": "Dossiê documental.",
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

    def _fake_build_management_report(**kwargs):
        captured.update(kwargs)
        return (
            {
                "title": "Dossiê do Extrato Bancário",
                "summary_cards": [],
                "general_info": [],
                "rows": [],
                "filters": [],
                "dossier_document_count": 0,
                "dossier_documents": [],
            },
            None,
        )

    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "build_management_report",
        _fake_build_management_report,
    )
    monkeypatch.setattr(
        financial_reports_route,
        "render_template",
        lambda template_name, **context: f"{template_name}|report={context.get('report') is not None}|slug={context['report_definition']['slug']}",
    )

    client = app.test_client()
    response = client.get(
        "/financial/reports/dossie-extrato-bancario?dossier_mode=simple&dossier_mode=complete"
        "&period_start=2026-06-01&period_end=2026-06-30"
        "&include_projected=true&include_reconciled_only=true&include_overdraft=false"
        "&include_settled=true&include_partial=false&include_open=true"
        "&include_receivable=true&include_payable=false"
        "&show_due_date=true&show_balance_amount=false"
        "&order_by=due_date&order_direction=desc",
        follow_redirects=False,
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "modules/financial/report_filters.html" in html
    assert "report=True" in html
    assert "slug=dossie-extrato-bancario" in html
    assert captured["report_type"] == "bank_statement_dossier"
    assert captured["filters"]["dossier_mode"] == "complete"
    assert captured["filters"]["include_projected"] == "true"
    assert captured["filters"]["include_reconciled_only"] == "true"
    assert captured["filters"]["include_overdraft"] == "false"
    assert captured["filters"]["include_partial"] == "false"
    assert captured["filters"]["include_payable"] == "false"
    assert captured["filters"]["show_due_date"] == "true"
    assert captured["filters"]["show_balance_amount"] == "false"
    assert captured["filters"]["order_by"] == "due_date"
    assert captured["filters"]["order_direction"] == "desc"


def test_bank_statement_view_redirects_to_filters(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)

    client = app.test_client()
    response = client.get("/financial/reports/extrato-bancario/view?period_start=2026-04-01&period_end=2026-04-19", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/financial/reports/extrato-bancario?period_start=2026-04-01&period_end=2026-04-19"
    )


def test_bank_statement_dossier_layout_test_forces_landscape(monkeypatch):
    app = _build_app()
    captured = {}
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
                "code": "bank_statement_dossier",
                "slug": "dossie-extrato-bancario",
                "label": "Dossiê do Extrato Bancário",
                "description": "Dossiê documental.",
            },
            None,
        ),
    )

    def _fake_build_management_report(**kwargs):
        captured.update(kwargs)
        return (
            {
                "title": "Dossiê do Extrato Bancário",
                "summary_cards": [],
                "rows": [],
                "filters": [],
                "dossier_document_count": 1,
                "dossier_documents": [
                    {
                        "source_label": "Baixa",
                        "document_name": "comprovante.pdf",
                        "document_url": "/uploads/comprovante.pdf",
                        "content_type": "application/pdf",
                        "attachment": {"url": "/uploads/comprovante.pdf", "content_type": "application/pdf"},
                    }
                ],
            },
            None,
        )

    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "build_management_report",
        _fake_build_management_report,
    )
    monkeypatch.setattr(
        financial_reports_route,
        "render_template",
        lambda template_name, **context: f"{template_name}|docs={context['report']['dossier_document_count']}",
    )

    client = app.test_client()
    response = client.get("/financial/reports/dossie-extrato-bancario/layout-test?period_start=2026-06-01&period_end=2026-06-30")

    assert response.status_code == 200
    assert "modules/financial/report_layout_bank_statement_dossier_landscape_test.html" in response.get_data(as_text=True)
    assert "docs=1" in response.get_data(as_text=True)
    assert captured["report_type"] == "bank_statement_dossier"
    assert captured["filters"]["orientation"] == "landscape"



def test_bank_statement_sidebar_exposes_advanced_filters():
    app = _build_app()
    report_definition = {
        "code": "bank_statement_dossier",
        "slug": "dossie-extrato-bancario",
        "label": "Dossiê do Extrato Bancário",
        "description": "Dossiê documental.",
    }
    options = SimpleNamespace(bank_accounts=[])

    with app.test_request_context("/financial/reports/dossie-extrato-bancario?company_id=7"):
        html = render_template(
            "modules/financial/partials/report_filters_bank_statement_sidebar.html",
            company_id=7,
            default_period_start="2026-06-01",
            default_period_end="2026-06-30",
            filters={},
            options=options,
            report_definition=report_definition,
        )

    for label in [
        "Período inicial",
        "Período final",
        "Projetar abertos",
        "Somente conciliados",
        "Considerar limites",
        "Status considerados",
        "Tipos considerados",
        "Exibir",
        "Ordenar por",
        "Direção",
    ]:
        assert label in html
    for field in [
        "include_projected",
        "include_reconciled_only",
        "include_overdraft",
        "include_settled",
        "include_partial",
        "include_open",
        "include_receivable",
        "include_payable",
        "show_settlement_date",
        "show_code",
        "show_title_number",
        "show_description",
        "show_counterparty",
        "show_title_amount",
        "show_balance_amount",
        "order_by",
        "order_direction",
    ]:
        assert f'name="{field}"' in html

def test_bank_statement_dossier_page_renames_landscape_test_button_to_receipts():
    app = _build_app()
    company = SimpleNamespace(id=7, name="Empresa Teste")
    report = {
        "report_type": "bank_statement_dossier",
        "report_slug": "dossie-extrato-bancario",
        "title": "Dossiê do Extrato Bancário",
        "filters": [],
        "summary_cards": [],
        "rows": [],
        "dossier_document_count": 0,
        "dossier_documents": [],
        "generated_at": "07/06/2026 10:00",
    }

    with app.test_request_context("/financial/reports/dossie-extrato-bancario?company_id=7"):
        html = render_template(
            "modules/financial/partials/report_filters_bank_statement_page.html",
            company=company,
            company_id=company.id,
            report_definition={
                "code": "bank_statement_dossier",
                "slug": "dossie-extrato-bancario",
                "label": "Dossiê do Extrato Bancário",
                "description": "Dossiê documental.",
            },
            report=report,
        )

    assert "Comprovantes" in html
    assert "Página teste (paisagem)" not in html


def test_bank_statement_dossier_pdf_uses_portrait_statement_portrait_dre_and_landscape_receipts():
    pdf_bytes = FinancialReportService.export_pdf(
        {
            "report_type": "bank_statement_dossier",
            "report_slug": "dossie-extrato-bancario",
            "title": "Dossiê do Extrato Bancário",
            "statement_title": "Extrato Bancário",
            "statement_subtitle": "Extrato gerencial.",
            "company_name": "Empresa Teste",
            "generated_at": "07/06/2026 10:00",
            "filters": [{"label": "Período", "value": "2026-06-01 até 2026-06-30"}],
            "summary_cards": [{"label": "Saldo final", "value": "R$ 100,00", "tone": "primary"}],
            "columns": [{"key": "data", "label": "Data"}, {"key": "valor", "label": "Valor"}],
            "rows": [{"data": "2026-06-07", "valor": "100.00", "valor_label": "R$ 100,00"}],
            "dossier_income_statement": {
                "title": "Demonstração de Resultados 01",
                "company_name": "Empresa Teste",
                "generated_at": "07/06/2026 10:00",
                "filters": [{"label": "Período", "value": "2026-06-01 até 2026-06-30"}],
                "hierarchy_rows": [
                    {
                        "codigo": "3.1.01",
                        "descricao": "Receitas",
                        "level": 0,
                        "liquidacao_label": "R$ 100,00",
                        "liquidacao": 100.0,
                        "competencia_label": "R$ 999,00",
                        "vencimento_label": "R$ 888,00",
                    },
                    {
                        "codigo": "4.1.01",
                        "descricao": "Despesas",
                        "level": 0,
                        "liquidacao_label": "-R$ 40,00",
                        "liquidacao": -40.0,
                        "competencia_label": "R$ 777,00",
                        "vencimento_label": "R$ 666,00",
                    },
                ],
            },
            "dossier_documents": [
                {
                    "source_label": "Baixa",
                    "document_name": "comprovante-01.pdf",
                    "settlement_date": "2026-06-07",
                    "counterparty": "Fornecedor Teste",
                    "chart_account": "3.1.01 - Receitas",
                    "amount": "R$ 100,00",
                    "attachment": {"url": "/uploads/comprovante-01.pdf", "content_type": "application/pdf"},
                },
                {
                    "source_label": "Título financeiro",
                    "document_name": "comprovante-02.jpg",
                    "settlement_date": "2026-06-07",
                    "counterparty": "Fornecedor Teste 2",
                    "chart_account": "4.1.01 - Despesas",
                    "amount": "R$ 40,00",
                    "attachment": {"url": "/uploads/comprovante-02.jpg", "content_type": "image/jpeg"},
                },
                {
                    "source_label": "Lançamento",
                    "document_name": "comprovante-03.png",
                    "settlement_date": "2026-06-07",
                    "counterparty": "Fornecedor Teste 3",
                    "chart_account": "4.1.01 - Despesas",
                    "amount": "R$ 30,00",
                    "attachment": {"url": "/uploads/comprovante-03.png", "content_type": "image/png"},
                },
                {
                    "source_label": "Baixa",
                    "document_name": "comprovante-04.pdf",
                    "settlement_date": "2026-06-07",
                    "counterparty": "Fornecedor Teste 4",
                    "chart_account": "4.1.01 - Despesas",
                    "amount": "R$ 20,00",
                    "attachment": {"url": "/uploads/comprovante-04.pdf", "content_type": "application/pdf"},
                },
            ],
            "dossier_document_count": 4,
        }
    )

    reader = PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) == 3

    first_width = float(reader.pages[0].mediabox.width)
    first_height = float(reader.pages[0].mediabox.height)
    second_width = float(reader.pages[1].mediabox.width)
    second_height = float(reader.pages[1].mediabox.height)
    last_width = float(reader.pages[-1].mediabox.width)
    last_height = float(reader.pages[-1].mediabox.height)

    assert first_height > first_width
    assert second_height > second_width
    assert last_width > last_height

    dre_text = reader.pages[1].extract_text() or ""
    assert "Demonstração de Resultados" in dre_text
    assert "Face de liquidação" in dre_text
    assert "R$ 100,00" in dre_text
    assert "Resultado" in dre_text
    assert "R$ 60,00" in dre_text
    assert "R$ 999,00" not in dre_text
    assert "R$ 888,00" not in dre_text
    assert "R$ 777,00" not in dre_text
    assert "R$ 666,00" not in dre_text

    receipts_text = reader.pages[-1].extract_text() or ""
    assert "Lote 1" in receipts_text
    assert "1-4 de 4" in receipts_text
    assert "comprovante-01.pdf" in receipts_text
    assert "comprovante-02.jpg" in receipts_text
    assert "comprovante-03.png" in receipts_text
    assert "comprovante-04.pdf" in receipts_text


def test_cash_flow_projected_titles_route_returns_json(monkeypatch):
    app = _build_app()
    captured = {}
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
                "code": "cash_flow",
                "slug": "fluxo-caixa",
                "label": "Fluxo de Caixa",
                "description": "Fluxo gerencial.",
            },
            None,
        ),
    )

    def _fake_build_cash_flow_title_preview(**kwargs):
        captured.update(kwargs)
        return (
            {
                "titles": [
                    {
                        "id": 11,
                        "history": "Parcela abril",
                        "type": "Saída",
                        "title_amount": "R$ 1.200,00",
                        "open_amount": "R$ 1.200,00",
                        "counterparty": "Fornecedor Teste",
                        "number_installment": "NF-100 / 1",
                        "competence_date": "2026-04-01",
                        "due_date": "2026-04-15",
                        "projection_ref": "entry:11",
                        "selected": True,
                    }
                ],
                "summary": {"count": 1, "selected_count": 1, "total_open_amount_label": "R$ 1.200,00"},
            },
            None,
        )

    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "build_cash_flow_title_preview",
        _fake_build_cash_flow_title_preview,
    )

    client = app.test_client()
    response = client.get(
        "/financial/reports/fluxo-caixa/projected-titles"
        "?period_start=2026-04-01"
        "&period_end=2026-04-30"
        "&bank_account_ids=-1"
        "&bank_account_ids=3"
        "&enable_title_exclusions=true"
        "&excluded_projected_refs=entry:11"
        "&title_filter_search=fornecedor"
        "&title_filter_counterparty_id=9",
        follow_redirects=False,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["titles"][0]["id"] == 11
    assert captured["company_id"] == 7
    assert captured["filters"]["period_start"] == "2026-04-01"
    assert captured["filters"]["bank_account_ids"] == ["3"]
    assert captured["filters"]["excluded_projected_refs"] == ["entry:11"]
    assert "title_filter_search" not in captured["filters"]
    assert captured["selection_filters"]["search"] == "fornecedor"
    assert captured["selection_filters"]["counterparty_id"] == "9"


def test_cash_flow_report_view_renders_dedicated_layout():
    app = _build_app()
    company = SimpleNamespace(id=7, name="Empresa Teste")
    company.to_dict = lambda: {"id": 7, "name": "Empresa Teste"}
    report = {
        "report_type": "cash_flow",
        "report_slug": "fluxo-caixa",
        "title": "Fluxo de Caixa",
        "subtitle": "Fluxo gerencial.",
        "filters": [{"label": "Período", "value": "01/04/2026 até 30/04/2026"}],
        "summary_cards": [{"label": "Saldo inicial", "value": "R$ 1.000,00", "tone": "positive"}],
        "general_info": [{"label": "Periodicidade", "value": "Semanal"}],
        "bank_balance_reference_label": "21/04/2026",
        "bank_account_summary_rows": [
            {
                "description": "Inter Versus",
                "limit": "R$ 50.000,00",
                "limit_value": 50000.0,
                "balance": "R$ 1.500,00",
                "balance_value": 1500.0,
                "available_total": "R$ 51.500,00",
                "available_total_value": 51500.0,
            },
            {
                "description": "Efi Banco - Conta 01",
                "limit": "R$ 0,00",
                "limit_value": 0.0,
                "balance": "R$ -200,00",
                "balance_value": -200.0,
                "available_total": "R$ -200,00",
                "available_total_value": -200.0,
            },
        ],
        "bank_account_summary_totals": {
            "limit": "R$ 50.000,00",
            "limit_value": 50000.0,
            "balance": "R$ 1.300,00",
            "balance_value": 1300.0,
            "available_total": "R$ 51.300,00",
            "available_total_value": 51300.0,
        },
        "periodicity_label": "Semanal",
        "columns": [
            {"key": "periodo", "label": "Período"},
            {"key": "data_inicial", "label": "Data Inicial"},
            {"key": "data_final", "label": "Data Final"},
            {"key": "saldo_inicial", "label": "Saldo Inicial"},
            {"key": "entrada", "label": "Entrada"},
            {"key": "saida", "label": "Saída"},
            {"key": "saldo_final", "label": "Saldo Final"},
            {"key": "limite", "label": "Limite"},
            {"key": "disponivel_total_final", "label": "Disp. Total Final"},
        ],
        "rows": [
            {
                "periodo": "Semana 1",
                "data_inicial": "01/04/2026",
                "data_final": "07/04/2026",
                "saldo_inicial": "R$ 1.000,00",
                "entrada": "R$ 250,00",
                "saida": "R$ -100,00",
                "saldo_final": "R$ 900,00",
                "limite": "R$ 0,00",
                "disponivel_total_final": "R$ 900,00",
            }
        ],
        "selected_receivables": [
            {
                "id": 44,
                "type_code": "RCB",
                "title_amount": "R$ 1.250,00",
                "open_amount": "R$ 1.250,00",
                "counterparty": "001 - Cliente Teste 01",
                "due_date": "02/05/2026",
                "is_excluded": False,
            }
        ],
        "selected_receivables_totals": {
            "count": 1,
            "title_amount": "R$ 1.250,00",
            "open_amount": "R$ 1.250,00",
        },
        "selected_payables": [
            {
                "id": 45,
                "type_code": "PGT",
                "title_amount": "R$ -1.050,00",
                "open_amount": "R$ -1.050,00",
                "counterparty": "002 - Fornecedor Teste 02",
                "due_date": "02/05/2026",
                "is_excluded": False,
            }
        ],
        "selected_payables_totals": {
            "count": 1,
            "title_amount": "R$ -1.050,00",
            "open_amount": "R$ -1.050,00",
        },
        "generated_at": "21/04/2026 10:00",
    }

    with app.test_request_context("/financial/reports/fluxo-caixa/view?period_start=2026-04-01&period_end=2026-04-30"):
        report_macros = app.jinja_env.get_template(
            "modules/financial/partials/_report_workspace_macros.html"
        ).module
        html = render_template(
            "modules/financial/partials/report_view_cash_flow.html",
            company=company,
            company_id=company.id,
            report=report,
            report_macros=report_macros,
        )

    assert "Contas Correntes" in html
    assert "Empresa Teste" in html
    assert "Contas a Receber Selecionadas" in html
    assert "Contas a Pagar Selecionadas" in html
    assert "Disp. Total Final" in html
    assert "cashflow-bank-amount--positive" in html
    assert "cashflow-bank-amount--negative" in html
    assert "cashflow-amount--positive" in html
    assert "cashflow-amount--negative" in html
    assert "- 200,00" in html
    assert "1.250,00" in html
    assert "- 1.050,00" in html
    assert "R$ 1.250,00" not in html
    assert "R$ -1.050,00" not in html
    assert "Visão do período" not in html
    assert "Janela analisada" not in html
    assert "Periodicidade" not in html
    assert "Títulos financeiros em aberto" not in html


def test_bank_statement_filters_page_hides_redundant_operational_info():
    app = _build_app()
    company = SimpleNamespace(id=7, name="Empresa Teste")
    company.to_dict = lambda: {"id": 7, "name": "Empresa Teste"}
    report = {
        "report_type": "bank_statement",
        "report_slug": "extrato-bancario",
        "title": "Extrato Bancário",
        "subtitle": "Extrato gerencial.",
        "filters": [
            {"label": "Período", "value": "2026-03-01 até 2026-04-30"},
            {"label": "Conta bancária", "value": "003 - Caixinha Carol"},
            {"label": "Somente conciliados", "value": "Não"},
        ],
        "summary_cards": [
            {"label": "Saldo inicial", "value": "R$ 0,00", "tone": "neutral"},
            {"label": "Saídas", "value": "R$ 996,28", "tone": "negative"},
        ],
        "general_info": [
            {"label": "Janela analisada", "value": "2026-03-01 até 2026-04-30"},
            {"label": "Recorte", "value": "003 - Caixinha Carol"},
            {"label": "Movimentos", "value": "4"},
            {"label": "Somente conciliados", "value": "Não"},
        ],
        "rows": [],
        "generated_at": "30/04/2026 23:18",
    }

    with app.test_request_context("/financial/reports/extrato-bancario?period_start=2026-03-01&period_end=2026-04-30"):
        html = render_template(
            "modules/financial/partials/report_filters_bank_statement_page.html",
            company=company,
            company_id=company.id,
            report_definition={
                "slug": "extrato-bancario",
                "label": "Extrato Bancário",
                "description": "Extrato gerencial.",
            },
            report=report,
        )

    assert "Visão operacional" not in html
    assert "Janela analisada" not in html
    assert "Recorte" not in html
    assert "Movimentos" not in html


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


def test_income_statement_2_view_redirects_to_filters(monkeypatch):
    app = _build_app()
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)

    client = app.test_client()
    response = client.get(
        "/financial/reports/demonstrativo-resultados-02/view?competence_start=2026-04-01&competence_end=2026-04-19",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/financial/reports/demonstrativo-resultados-02?competence_start=2026-04-01&competence_end=2026-04-19"
    )


def test_income_statement_drilldown_route_returns_json(monkeypatch):
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
        "build_income_statement_drilldown",
        lambda **kwargs: (
            {
                "bucket": "competencia",
                "bucket_label": "Competência",
                "account_label": "4.01.001 - Receita teste",
                "total": 100.0,
                "total_label": "R$ 100,00",
                "item_count": 1,
                "items": [{"source_kind": "title", "source_code": "AG-000001", "amount_label": "R$ 100,00"}],
            },
            None,
        ),
    )

    client = app.test_client()
    response = client.get(
        "/financial/reports/demonstrativo-resultados/drilldown?bucket=competence&chart_account_id=11",
        follow_redirects=False,
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["bucket"] == "competencia"
    assert payload["account_label"] == "4.01.001 - Receita teste"
    assert payload["total"] == 100.0
    assert payload["item_count"] == 1


def test_income_statement_drilldown_route_strips_detail_params_from_filters(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(
        financial_reports_route,
        "get_active_company",
        lambda: SimpleNamespace(id=7, name="Empresa Teste"),
    )
    monkeypatch.setattr(financial_reports_route, "get_accessible_company_ids", lambda: [7])

    def _fake_build_income_statement_drilldown(**kwargs):
        captured.update(kwargs)
        return ({"bucket": "competencia", "bucket_label": "Competência", "account_label": "Teste", "total": 0.0, "total_label": "R$ 0,00", "item_count": 0, "items": []}, None)

    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "build_income_statement_drilldown",
        _fake_build_income_statement_drilldown,
    )

    client = app.test_client()
    response = client.get(
        "/financial/reports/demonstrativo-resultados/drilldown"
        "?bucket=competence"
        "&detail_chart_account_id=11"
        "&period_start=2026-04-01"
        "&period_end=2026-04-30"
        "&include_open=true"
        "&include_settled=true"
        "&include_receivable=true"
        "&include_payable=true"
        "&show_code=true"
        "&show_description=true",
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert captured["chart_account_id"] == 11
    assert captured["bucket"] == "competence"
    assert captured["filters"]["period_start"] == "2026-04-01"
    assert "bucket" not in captured["filters"]
    assert "detail_chart_account_id" not in captured["filters"]


def test_income_statement_drilldown_route_keeps_legacy_chart_account_param_out_of_filters(monkeypatch):
    app = _build_app()
    captured = {}
    monkeypatch.setattr(permission_utils, "has_permission", lambda company_id, resource, action: True)
    monkeypatch.setattr(
        financial_reports_route,
        "get_active_company",
        lambda: SimpleNamespace(id=7, name="Empresa Teste"),
    )
    monkeypatch.setattr(financial_reports_route, "get_accessible_company_ids", lambda: [7])

    def _fake_build_income_statement_drilldown(**kwargs):
        captured.update(kwargs)
        return ({"bucket": "competencia", "bucket_label": "Competência", "account_label": "Teste", "total": 0.0, "total_label": "R$ 0,00", "item_count": 0, "items": []}, None)

    monkeypatch.setattr(
        financial_reports_route.FinancialReportService,
        "build_income_statement_drilldown",
        _fake_build_income_statement_drilldown,
    )

    client = app.test_client()
    response = client.get(
        "/financial/reports/demonstrativo-resultados/drilldown"
        "?bucket=competence"
        "&chart_account_id=11"
        "&period_start=2026-04-01"
        "&period_end=2026-04-30"
        "&include_open=true"
        "&include_settled=true"
        "&include_receivable=true"
        "&include_payable=true"
        "&show_code=true"
        "&show_description=true",
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert captured["chart_account_id"] == 11
    assert "chart_account_id" not in captured["filters"]


def test_income_statement_filters_page_only_keeps_drilldown_on_analytical_rows(monkeypatch):
    app = _build_app()
    company = SimpleNamespace(id=7, name="Empresa Teste")
    company.to_dict = lambda: {"id": 7, "name": "Empresa Teste"}
    report_definition = {
        "code": "income_statement",
        "slug": "demonstrativo-resultados",
        "label": "Demonstração de Resultados 01",
        "description": "DRE contábil.",
        "filters": ("period",),
    }
    report = {
        "title": "Demonstração de Resultados 01",
        "subtitle": "DRE contábil.",
        "filters": [],
        "summary_cards": [],
        "general_info": [],
        "show_status_columns": False,
        "hierarchy_rows": [
            {
                "id": "dre-10",
                "parent_id": None,
                "chart_account_id": 10,
                "codigo": "3",
                "descricao": "Receitas",
                "account_label": "3 - Receitas",
                "level": 0,
                "row_type": "group",
                "is_leaf": False,
                "has_children": True,
                "competencia": 0.0,
                "competencia_label": "R$ 0,00",
                "vencimento": 0.0,
                "vencimento_label": "R$ 0,00",
                "liquidacao": 0.0,
                "liquidacao_label": "R$ 0,00",
                "aberto": 0.0,
                "aberto_label": "R$ 0,00",
                "baixado": 0.0,
                "baixado_label": "R$ 0,00",
            },
            {
                "id": "dre-11",
                "parent_id": "dre-10",
                "chart_account_id": 11,
                "codigo": "3.1.01.001",
                "descricao": "Receita teste",
                "account_label": "3.1.01.001 - Receita teste",
                "level": 1,
                "row_type": "account",
                "is_leaf": True,
                "has_children": False,
                "competencia": 100.0,
                "competencia_label": "R$ 100,00",
                "vencimento": 100.0,
                "vencimento_label": "R$ 100,00",
                "liquidacao": 100.0,
                "liquidacao_label": "R$ 100,00",
                "aberto": 0.0,
                "aberto_label": "R$ 0,00",
                "baixado": 100.0,
                "baixado_label": "R$ 100,00",
            },
        ],
        "totals": {
            "competence": 100.0,
            "competence_label": "R$ 100,00",
            "due": 100.0,
            "due_label": "R$ 100,00",
            "liquidation": 100.0,
            "liquidation_label": "R$ 100,00",
        },
    }

    with app.test_request_context(
        "/financial/reports/demonstrativo-resultados"
        "?period_start=2026-04-01"
        "&period_end=2026-04-30"
        "&include_open=true"
        "&include_settled=true"
        "&include_receivable=true"
        "&include_payable=true"
        "&show_code=true"
        "&show_description=true"
    ):
        html = render_template(
            "modules/financial/partials/report_filters_income_statement_page.html",
            company=company,
            company_id=company.id,
            report_definition=report_definition,
            report=report,
        )

    assert html.count("data-dre-detail-trigger") == 6
    assert 'data-chart-account-id="11"' in html
    assert 'data-chart-account-id="10"' not in html


def test_income_statement_sidebar_removes_budget_vs_actual_and_adds_column_toggles():
    app = _build_app()
    report_definition = {
        "code": "income_statement",
        "slug": "demonstrativo-resultados",
        "label": "Demonstração de Resultados 01",
        "description": "DRE contábil.",
    }
    options = SimpleNamespace(chart_accounts=[], cost_centers=[], projects=[])

    with app.test_request_context("/financial/reports/demonstrativo-resultados?company_id=7"):
        html = render_template(
            "modules/financial/partials/report_filters_income_statement_sidebar.html",
            company_id=7,
            default_period_start="2026-04-01",
            default_period_end="2026-04-30",
            filters={},
            options=options,
            report_definition=report_definition,
        )

    assert "Orçado x Realizado" not in html
    assert "include_budget_vs_actual" not in html
    assert 'name="show_competence_column"' in html
    assert 'name="show_due_column"' in html
    assert 'name="show_liquidation_column"' in html
    assert "Colunas principais" in html


def test_income_statement_filters_page_hides_unselected_primary_columns():
    app = _build_app()
    company = SimpleNamespace(id=7, name="Empresa Teste")
    company.to_dict = lambda: {"id": 7, "name": "Empresa Teste"}
    report_definition = {
        "code": "income_statement",
        "slug": "demonstrativo-resultados",
        "label": "Demonstração de Resultados 01",
        "description": "DRE contábil.",
        "filters": ("period",),
    }
    report = {
        "title": "Demonstração de Resultados 01",
        "subtitle": "DRE contábil.",
        "filters": [],
        "summary_cards": [],
        "general_info": [],
        "show_status_columns": False,
        "show_competence_column": False,
        "show_due_column": True,
        "show_liquidation_column": False,
        "hierarchy_rows": [
            {
                "id": "dre-11",
                "parent_id": None,
                "chart_account_id": 11,
                "codigo": "3.1.01.001",
                "descricao": "Receita teste",
                "account_label": "3.1.01.001 - Receita teste",
                "level": 0,
                "row_type": "account",
                "is_leaf": True,
                "has_children": False,
                "competencia": 100.0,
                "competencia_label": "R$ 100,00",
                "vencimento": 100.0,
                "vencimento_label": "R$ 100,00",
                "liquidacao": 100.0,
                "liquidacao_label": "R$ 100,00",
                "aberto": 0.0,
                "aberto_label": "R$ 0,00",
                "baixado": 100.0,
                "baixado_label": "R$ 100,00",
            }
        ],
        "totals": {
            "competence": 100.0,
            "competence_label": "R$ 100,00",
            "due": 100.0,
            "due_label": "R$ 100,00",
            "liquidation": 100.0,
            "liquidation_label": "R$ 100,00",
        },
    }

    with app.test_request_context(
        "/financial/reports/demonstrativo-resultados"
        "?period_start=2026-04-01"
        "&period_end=2026-04-30"
        "&show_competence_column=false"
        "&show_due_column=true"
        "&show_liquidation_column=false"
    ):
        html = render_template(
            "modules/financial/partials/report_filters_income_statement_page.html",
            company=company,
            company_id=company.id,
            report_definition=report_definition,
            report=report,
        )

    assert '<th class="col-value">Competência</th>' not in html
    assert '<th class="col-value">Vencimento</th>' in html
    assert '<th class="col-value">Liquidação</th>' not in html
    assert 'data-bucket="competence"' not in html
    assert 'data-bucket="due"' in html
    assert 'data-bucket="liquidation"' not in html
