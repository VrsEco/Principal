import os
import sys
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import models
from models import financial_budget as financial_budget_models

if not hasattr(models, "FinancialBudgetCycle"):
    models.FinancialBudgetCycle = financial_budget_models.FinancialBudgetCycle

import services.financial_budget_workspace_service as workspace_module
from services.financial_budget_workspace_service import FinancialBudgetWorkspaceService


class _SimpleObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def to_dict(self):
        return dict(self.__dict__)


def test_workspace_consolidates_planned_contracted_executed_and_scheduled_totals(monkeypatch):
    version = _SimpleObj(id=1, company_id=9, code="AA.O.2026.CAPEX.1", name="CAPEX 2026", status="active")
    line = _SimpleObj(
        id=10,
        company_id=9,
        budget_version_id=1,
        line_code="AA.O.2026.CAPEX.1.2",
        line_name="Verba Infra",
        line_order=1,
        budget_view="competence",
        movement_nature="debit",
        planned_amount=Decimal("1000.00"),
        chart_account=None,
        cost_center=None,
        to_dict=lambda: {
            "id": 10,
            "company_id": 9,
            "budget_version_id": 1,
            "line_code": "AA.O.2026.CAPEX.1.2",
            "line_name": "Verba Infra",
            "line_order": 1,
            "budget_view": "competence",
            "movement_nature": "debit",
            "planned_amount": 1000.0,
            "metadata_json": {"full_code": "AA.O.2026.CAPEX.1.2"},
        },
    )
    contract_a = _SimpleObj(
        id=20,
        company_id=9,
        budget_line_id=10,
        contract_code="AA.O.2026.CAPEX.1.2.3",
        name="Contrato A",
        status="active",
        contract_amount=Decimal("200.00"),
        counterparty=None,
        to_dict=lambda: {
            "id": 20,
            "company_id": 9,
            "budget_line_id": 10,
            "contract_code": "AA.O.2026.CAPEX.1.2.3",
            "name": "Contrato A",
            "status": "active",
            "contract_amount": 200.0,
            "metadata_json": {"full_code": "AA.O.2026.CAPEX.1.2.3"},
        },
    )
    contract_b = _SimpleObj(
        id=21,
        company_id=9,
        budget_line_id=10,
        contract_code="AA.O.2026.CAPEX.1.2.4",
        name="Contrato B",
        status="active",
        contract_amount=Decimal("400.00"),
        counterparty=None,
        to_dict=lambda: {
            "id": 21,
            "company_id": 9,
            "budget_line_id": 10,
            "contract_code": "AA.O.2026.CAPEX.1.2.4",
            "name": "Contrato B",
            "status": "active",
            "contract_amount": 400.0,
            "metadata_json": {"full_code": "AA.O.2026.CAPEX.1.2.4"},
        },
    )
    document_a = _SimpleObj(
        id=30,
        company_id=9,
        budget_contract_id=20,
        document_code="AA.O.2026.CAPEX.1.2.3.4",
        title="NF 1",
        document_type="invoice",
        status="registered",
        document_amount=Decimal("150.00"),
        counterparty=None,
        to_dict=lambda: {
            "id": 30,
            "company_id": 9,
            "budget_contract_id": 20,
            "document_code": "AA.O.2026.CAPEX.1.2.3.4",
            "title": "NF 1",
            "document_type": "invoice",
            "status": "registered",
            "document_amount": 150.0,
            "metadata_json": {"full_code": "AA.O.2026.CAPEX.1.2.3.4"},
        },
    )
    document_b = _SimpleObj(
        id=31,
        company_id=9,
        budget_contract_id=21,
        document_code="AA.O.2026.CAPEX.1.2.4.5",
        title="NF 2",
        document_type="invoice",
        status="registered",
        document_amount=Decimal("300.00"),
        counterparty=None,
        to_dict=lambda: {
            "id": 31,
            "company_id": 9,
            "budget_contract_id": 21,
            "document_code": "AA.O.2026.CAPEX.1.2.4.5",
            "title": "NF 2",
            "document_type": "invoice",
            "status": "registered",
            "document_amount": 300.0,
            "metadata_json": {"full_code": "AA.O.2026.CAPEX.1.2.4.5"},
        },
    )
    schedule_a = _SimpleObj(
        id=40,
        company_id=9,
        budget_document_id=30,
        template_amount=Decimal("50.00"),
        movement_nature="debit",
        first_due_date=date(2026, 3, 10),
        to_dict=lambda: {
            "id": 40,
            "company_id": 9,
            "budget_document_id": 30,
            "template_amount": 50.0,
            "movement_nature": "debit",
            "first_due_date": "2026-03-10",
        },
    )
    schedule_b = _SimpleObj(
        id=41,
        company_id=9,
        budget_document_id=30,
        template_amount=Decimal("25.00"),
        movement_nature="debit",
        first_due_date=date(2026, 3, 20),
        to_dict=lambda: {
            "id": 41,
            "company_id": 9,
            "budget_document_id": 30,
            "template_amount": 25.0,
            "movement_nature": "debit",
            "first_due_date": "2026-03-20",
        },
    )
    schedule_c = _SimpleObj(
        id=42,
        company_id=9,
        budget_document_id=31,
        template_amount=Decimal("75.00"),
        movement_nature="debit",
        first_due_date=date(2026, 4, 1),
        to_dict=lambda: {
            "id": 42,
            "company_id": 9,
            "budget_document_id": 31,
            "template_amount": 75.0,
            "movement_nature": "debit",
            "first_due_date": "2026-04-01",
        },
    )

    monkeypatch.setattr(workspace_module.FinancialService, "get_signed_amount", lambda amount, movement_nature: float(amount or 0))
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_contracts_for_line", lambda **kwargs: [contract_a, contract_b])
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_documents_for_contract", lambda **kwargs: [document_a] if kwargs["contract_id"] == 20 else [document_b])
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_schedules_for_document", lambda **kwargs: [schedule_a, schedule_b] if kwargs["document_id"] == 30 else [schedule_c])

    line_payload = FinancialBudgetWorkspaceService._serialize_line(line)
    contract_payload = FinancialBudgetWorkspaceService._serialize_contract(contract_a)
    document_payload = FinancialBudgetWorkspaceService._serialize_document(document_a)
    version_summary = FinancialBudgetWorkspaceService._build_version_summary([line])

    assert line_payload["summary"]["planned_total"] == 1000.0
    assert line_payload["summary"]["contracted_total"] == 600.0
    assert line_payload["summary"]["executed_total"] == 450.0
    assert line_payload["summary"]["scheduled_total"] == 150.0
    assert line_payload["summary"]["available_to_contract"] == 400.0
    assert line_payload["summary"]["contracts_count"] == 2
    assert line_payload["summary"]["documents_count"] == 2
    assert line_payload["summary"]["schedules_count"] == 3

    assert contract_payload["summary"]["contract_amount"] == 200.0
    assert contract_payload["summary"]["executed_total"] == 150.0
    assert contract_payload["summary"]["scheduled_total"] == 75.0
    assert contract_payload["summary"]["available_to_execute"] == 50.0
    assert contract_payload["summary"]["documents_count"] == 1
    assert contract_payload["summary"]["schedules_count"] == 2

    assert document_payload["summary"]["document_amount"] == 150.0
    assert document_payload["summary"]["scheduled_total"] == 75.0
    assert document_payload["summary"]["available_to_schedule"] == 75.0
    assert document_payload["summary"]["schedules_count"] == 2

    assert version_summary["planned_total"] == 1000.0
    assert version_summary["contracted_total"] == 600.0
    assert version_summary["executed_total"] == 450.0
    assert version_summary["scheduled_total"] == 150.0
    assert version_summary["available_to_contract"] == 400.0
    assert version_summary["lines_count"] == 1
    assert version_summary["contracts_count"] == 2
    assert version_summary["documents_count"] == 2
    assert version_summary["schedules_count"] == 3


def test_execution_workspace_rejects_cross_tenant_and_invalid_child_selection(monkeypatch):
    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: "Empresa fora do escopo.")

    result, error = FinancialBudgetWorkspaceService.get_execution_workspace(
        company_id=9,
        version_id=1,
        allowed_company_ids=[10],
    )

    assert result is None
    assert error == "Empresa fora do escopo."

    version = _SimpleObj(id=1, company_id=9, code="AA.O.2026.CAPEX.1", name="CAPEX 2026", to_dict=lambda: {"id": 1, "company_id": 9})
    line = _SimpleObj(id=10, company_id=9, to_dict=lambda: {"id": 10, "company_id": 9})
    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(workspace_module.FinancialBudgetService, "list_versions", lambda *args, **kwargs: ([version.to_dict()], None))
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_get_version", lambda **kwargs: version)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_lines_for_version", lambda **kwargs: [line])
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_resolve_selected_line", lambda **kwargs: None)

    result, error = FinancialBudgetWorkspaceService.get_execution_workspace(
        company_id=9,
        version_id=1,
        line_id=99,
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "Verba orçamentária não encontrada para o orçamento selecionado."
