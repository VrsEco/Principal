from decimal import Decimal

import pytest

from schemas.financial_reports import FinancialManagementReportFiltersInput
from services.financial_report_service import FinancialReportService


def test_income_statement_2_management_merges_selected_months_forecast_and_budget(monkeypatch):
    calls = []

    def fake_base(company_id, filters, *, consolidated_by_period):
        calls.append(filters)
        if filters.show_due_column and not filters.show_competence_column and not filters.show_liquidation_column and not filters.include_settled:
            amount = Decimal("300")
            return {
                "hierarchy_rows": [
                    {
                        "id": "dre-10",
                        "parent_id": None,
                        "chart_account_id": 10,
                        "codigo": "3.01",
                        "descricao": "Receita",
                        "account_label": "3.01 - Receita",
                        "level": 0,
                        "row_type": "group",
                        "is_leaf": True,
                        "has_children": False,
                        "vencimento": amount,
                        "vencimento_label": "300,00",
                    }
                ],
                "totals": {"due": amount},
            }
        value_key = "liquidacao" if filters.show_liquidation_column else "competencia"
        amount = Decimal("100") if filters.period_start.month == 4 else Decimal("200")
        return {
            "hierarchy_rows": [
                {
                    "id": "dre-10",
                    "parent_id": None,
                    "chart_account_id": 10,
                    "codigo": "3.01",
                    "descricao": "Receita",
                    "account_label": "3.01 - Receita",
                    "level": 0,
                    "row_type": "group",
                    "is_leaf": True,
                    "has_children": False,
                    value_key: amount,
                    f"{value_key}_label": f"{int(amount)},00",
                }
            ],
            "totals": {"liquidation": amount, "competence": amount, "due": amount},
        }

    monkeypatch.setattr(FinancialReportService, "_build_income_statement_base", staticmethod(fake_base))
    monkeypatch.setattr(FinancialReportService, "_budget_values_by_account", staticmethod(lambda *args, **kwargs: {10: Decimal("50")}))
    monkeypatch.setattr(FinancialReportService, "_build_filter_labels", staticmethod(lambda *args, **kwargs: []))
    monkeypatch.setattr(
        FinancialReportService,
        "_liquidation_revenue_breakdown",
        staticmethod(lambda *args, **kwargs: [{"key": "current", "label": "Recebido no mês de vencimento", "values": {}}]),
    )
    monkeypatch.setattr(
        FinancialReportService,
        "_liquidation_projected_result",
        staticmethod(lambda *args, **kwargs: {"rows": [{"label": "( = ) Resultado Projetado do Período", "label_value": "0,00", "value": 0}]}),
    )

    filters = FinancialManagementReportFiltersInput(
        report_type="income_statement_2",
        period_start="2026-01-01",
        period_end="2026-04-30",
        income_statement_layout="management",
        dre_view="liquidation",
        realized_months=["2026-04", "2026-01"],
        show_budget_column=True,
        show_forecast_column=True,
    )

    payload = FinancialReportService._build_income_statement_2(company_id=1, filters=filters)

    assert payload["income_statement_layout"] == "management"
    assert [column["label"] for column in payload["columns"][:3]] == ["Conta contábil", "Orçado", "Previsto 05/2026"]
    assert [column["label"] for column in payload["monthly_columns"]] == ["04/2026", "01/2026"]
    assert payload["totals"]["budget_label"] == "50,00"
    assert payload["totals"]["forecast_label"] == "300,00"
    assert payload["totals"]["realized_labels"] == {
        "realized_2026_04": "100,00",
        "realized_2026_01": "200,00",
    }
    row = payload["hierarchy_rows"][0]
    assert row["budget_label"] == "50,00"
    assert row["forecast_label"] == "300,00"
    assert row["management_values"]["realized_2026_04"]["label"] == "100,00"
    assert row["management_values"]["realized_2026_01"]["label"] == "200,00"
    assert len(calls) == 3


def test_income_statement_2_management_pdf_includes_liquidation_notes(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    payload = {
        "report_type": "income_statement_2",
        "income_statement_layout": "management",
        "dre_view": "liquidation",
        "company_name": "Empresa Teste",
        "title": "DRE Gerencial 02",
        "subtitle": "Teste PDF",
        "show_budget_column": True,
        "show_forecast_column": True,
        "forecast_month": "2026-07-01",
        "monthly_columns": [
            {"key": "realized_2026_06", "label": "06/2026"},
            {"key": "realized_2026_05", "label": "05/2026"},
            {"key": "realized_2026_04", "label": "04/2026"},
        ],
        "hierarchy_rows": [
            {
                "id": "dre-1",
                "level": 0,
                "row_type": "group",
                "codigo": "3.01",
                "descricao": "Receita",
                "budget_value": "1000.00",
                "budget_label": "1.000,00",
                "forecast_value": "1200.00",
                "forecast_label": "1.200,00",
                "management_values": {
                    "realized_2026_06": {"value": "900", "label": "900,00"},
                    "realized_2026_05": {"value": "800", "label": "800,00"},
                    "realized_2026_04": {"value": "700", "label": "700,00"},
                },
            }
        ],
        "totals": {
            "budget": "1000.00",
            "budget_label": "1.000,00",
            "forecast": "1200.00",
            "forecast_label": "1.200,00",
            "realized": {"realized_2026_06": "900", "realized_2026_05": "800", "realized_2026_04": "700"},
            "realized_labels": {
                "realized_2026_06": "900,00",
                "realized_2026_05": "800,00",
                "realized_2026_04": "700,00",
            },
        },
        "revenue_liquidation_breakdown": [
            {
                "label": "Receita recebida do mês",
                "values": {
                    "realized_2026_06": {"value": "100", "label": "100,00"},
                    "realized_2026_05": {"value": "90", "label": "90,00"},
                    "realized_2026_04": {"value": "80", "label": "80,00"},
                },
            },
            {"label": "Receita recebida meses anteriores", "values": {}},
            {"label": "Receita recebida meses posteriores", "values": {}},
        ],
        "liquidation_projection": {
            "rows": [
                {"key": "open_receivable", "label": "( + ) Total de contas a receber em aberto", "value": "500", "label_value": "500,00"},
                {"key": "open_payable", "label": "( - ) Total de contas a pagar em aberto", "value": "200", "label_value": "200,00"},
                {"key": "projected_result", "label": "( = ) Resultado Projetado do Período", "value": "300", "label_value": "300,00"},
            ]
        },
    }

    pdf_path = tmp_path / "dre02.pdf"
    pdf_path.write_bytes(FinancialReportService.export_pdf(payload))

    text = "\n".join(page.extract_text() or "" for page in pypdf.PdfReader(str(pdf_path)).pages)

    assert "Notas explicativas da liquidação" in text
    assert "Receita recebida do mês" in text
    assert "Receita recebida meses anteriores" in text
    assert "Resultado Projetado do Período" in text
    assert "Orçado" in text
    assert "Previsto" in text
    assert "07/2026" in text
    assert "R$" not in text
