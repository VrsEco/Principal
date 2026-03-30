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


class _QueryStub:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class _ColumnStub:
    def __eq__(self, other):
        return self

    def is_(self, other):
        return self


class _Today2026_04_01:
    @staticmethod
    def today():
        return date(2026, 4, 1)


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


def test_execution_workspace_falls_back_to_first_document_schedule_when_requested_id_is_missing(monkeypatch):
    version = _SimpleObj(
        id=1,
        company_id=9,
        code="AA.O.1",
        name="Opex 2026",
        metadata_json={},
        period_start=date(2026, 1, 1),
        to_dict=lambda: {"id": 1, "company_id": 9, "metadata_json": {}, "period_start": "2026-01-01"},
    )
    line = _SimpleObj(
        id=10,
        company_id=9,
        budget_version_id=1,
        line_code="AA.O.1.1",
        line_name="Receitas Janeiro 2026",
        movement_nature="credit",
        planned_amount=Decimal("100.00"),
        chart_account=None,
        cost_center=None,
        metadata_json={},
        to_dict=lambda: {"id": 10, "company_id": 9, "budget_version_id": 1},
    )
    contract = _SimpleObj(
        id=20,
        company_id=9,
        budget_line_id=10,
        contract_code="AA.O.1.1.1",
        name="Contrato 01",
        status="active",
        contract_amount=Decimal("80.00"),
        counterparty=None,
        metadata_json={},
        to_dict=lambda: {"id": 20, "company_id": 9, "budget_line_id": 10},
    )
    document = _SimpleObj(
        id=30,
        company_id=9,
        budget_contract_id=20,
        document_code="AA.O.1.1.1.1",
        title="Nota 01",
        document_type="invoice",
        status="registered",
        document_amount=Decimal("80.00"),
        counterparty=None,
        metadata_json={},
        to_dict=lambda: {"id": 30, "company_id": 9, "budget_contract_id": 20},
    )
    schedule = _SimpleObj(
        id=40,
        company_id=9,
        budget_document_id=30,
        template_amount=Decimal("80.00"),
        movement_nature="credit",
        first_due_date=date(2026, 4, 10),
        to_dict=lambda: {
            "id": 40,
            "company_id": 9,
            "budget_document_id": 30,
            "template_amount": 80.0,
            "movement_nature": "credit",
            "first_due_date": "2026-04-10",
        },
    )

    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(workspace_module.FinancialBudgetService, "list_versions", lambda *args, **kwargs: ([version.to_dict()], None))
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_get_version", lambda **kwargs: version)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_lines_for_version", lambda **kwargs: [line])
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_resolve_selected_line", lambda **kwargs: line)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_contracts_for_line", lambda **kwargs: [contract])
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_resolve_selected_contract", lambda **kwargs: contract)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_documents_for_contract", lambda **kwargs: [document])
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_resolve_selected_document", lambda **kwargs: document)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_schedules_for_document", lambda **kwargs: [schedule])

    result, error = FinancialBudgetWorkspaceService.get_execution_workspace(
        company_id=9,
        version_id=1,
        line_id=10,
        contract_id=20,
        document_id=30,
        schedule_id=999,
        allowed_company_ids=[9],
    )

    assert error is None
    assert result["selected_document_id"] == 30
    assert result["selected_schedule_id"] == 40
    assert result["selected_schedule"]["id"] == 40
    assert result["schedules"][0]["id"] == 40


def test_create_document_schedules_aligns_payload_with_schedule_form_defaults(monkeypatch):
    version = _SimpleObj(id=1, code="AA.O.1")
    line = _SimpleObj(
        id=10,
        company_id=9,
        budget_version_id=1,
        line_code="AA.O.1.1",
        movement_nature="debit",
        chart_account_id=101,
        cost_center_id=202,
        activity_id=303,
        process_instance_id=404,
        routine_id=505,
        metadata_json={
            "domain_type": "project",
            "domain_source_id": 77,
            "domain_label": "Projeto Âncora",
        },
        version=version,
    )
    counterparty = _SimpleObj(id=900, name="Fornecedor Estratégico")
    contract = _SimpleObj(
        id=20,
        company_id=9,
        budget_line_id=10,
        contract_code="AA.O.1.1.1",
        name="Contrato 01",
        counterparty=counterparty,
        metadata_json={},
    )
    document = _SimpleObj(
        id=30,
        company_id=9,
        budget_contract_id=20,
        document_code="AA.O.1.1.1.1",
        title="Nota 01",
        document_number="NF-0001",
        document_amount=Decimal("50.00"),
        counterparty=None,
        notes="Observação da NF",
        metadata_json={},
    )

    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_get_document", lambda **kwargs: document)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_get_contract", lambda **kwargs: contract)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_get_line", lambda **kwargs: line)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_schedules_for_document", lambda **kwargs: [])
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_refresh_document_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_serialize_document", lambda item: {"id": item.id})
    monkeypatch.setattr(
        workspace_module.FinancialBudgetSchedulePolicy,
        "get_document_capacity",
        lambda **kwargs: (
            {
                "document": document,
                "scheduled_total": Decimal("0.00"),
                "document_total": Decimal("50.00"),
                "available_to_schedule": Decimal("50.00"),
            },
            None,
        ),
    )
    monkeypatch.setattr(
        workspace_module.FinancialScheduleService,
        "list_default_suggestions",
        lambda **kwargs: ({"payable_correction_index_id": 88}, None),
    )
    monkeypatch.setattr(workspace_module, "date", _Today2026_04_01)
    monkeypatch.setattr(workspace_module.db.session, "commit", lambda: None)
    monkeypatch.setattr(workspace_module.db.session, "rollback", lambda: None)

    captured = {}

    def _fake_create_schedule(*, payload, allowed_company_ids=None, auto_commit=True):
        captured["payload"] = payload
        captured["auto_commit"] = auto_commit
        return {"id": 555, "name": payload["name"]}, None

    monkeypatch.setattr(workspace_module.FinancialScheduleService, "create_schedule", _fake_create_schedule)

    result, error = FinancialBudgetWorkspaceService.create_document_schedules(
        company_id=9,
        document_id=30,
        payload={
            "company_id": 9,
            "installments": [
                {
                    "due_date": date(2026, 4, 10),
                    "competence_date": date(2026, 4, 1),
                    "amount": Decimal("50.00"),
                    "label": "Parcela única",
                }
            ],
            "notes": "Gerado pelo workspace",
            "auto_post": False,
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result["created_schedules"][0]["id"] == 555
    assert captured["auto_commit"] is False
    payload = captured["payload"]
    assert payload["budget_document_id"] == 30
    assert payload["name"] == "Parcela única"
    assert payload["start_date"] == date(2026, 4, 1)
    assert payload["chart_account_id"] == 101
    assert payload["cost_center_id"] == 202
    assert payload["metadata_json"]["competence_mode"] == "keep_first_competence"
    assert payload["metadata_json"]["correction_index_id"] == 88
    assert payload["metadata_json"]["discount_rule_id"] is None
    assert payload["metadata_json"]["discount_amount_override"] == 0
    assert payload["metadata_json"]["repeat_count"] == 1
    assert payload["metadata_json"]["attachments"] == []
    assert payload["metadata_json"]["counterparty_name"] == "Fornecedor Estratégico"
    allocation = payload["metadata_json"]["allocations"][0]
    assert allocation["allocation_type"] == "amount"
    assert allocation["allocated_amount"] == 50.0
    assert allocation["domain_value"] == "project:77"
    assert allocation["notes"] == "Parcela única | Nota 01"


def test_update_document_schedule_rebuilds_payload_with_document_inheritance(monkeypatch):
    version = _SimpleObj(id=1, code="AA.O.1")
    line = _SimpleObj(
        id=10,
        company_id=9,
        budget_version_id=1,
        line_code="AA.O.1.1",
        movement_nature="credit",
        chart_account_id=101,
        cost_center_id=202,
        activity_id=303,
        process_instance_id=404,
        routine_id=505,
        metadata_json={
            "domain_type": "project",
            "domain_source_id": 77,
            "domain_label": "Projeto Norte",
        },
        version=version,
    )
    counterparty = _SimpleObj(id=900, name="Cliente Premium")
    contract = _SimpleObj(
        id=20,
        company_id=9,
        budget_line_id=10,
        contract_code="AA.O.1.1.1",
        name="Contrato 01",
        counterparty=counterparty,
        metadata_json={},
    )
    document = _SimpleObj(
        id=30,
        company_id=9,
        budget_contract_id=20,
        document_code="AA.O.1.1.1.1",
        title="Nota 01",
        document_number="NF-0001",
        document_amount=Decimal("120.00"),
        counterparty=None,
        notes="Observação da NF",
        metadata_json={},
    )
    schedule = _SimpleObj(
        id=40,
        company_id=9,
        budget_document_id=30,
        schedule_code="AG-000001",
        name="Parcela antiga",
        status="active",
        origin_type="manual",
        movement_nature="credit",
        entry_type="receivable",
        template_amount=Decimal("20.00"),
        first_due_date=date(2026, 4, 10),
        next_due_date=date(2026, 4, 10),
        start_date=date(2026, 4, 10),
        auto_post=False,
        notes="Observação antiga",
        memo="Memo antigo",
        document_number_prefix="NF-0001",
        chart_account_id=101,
        cost_center_id=202,
        activity_id=303,
        process_instance_id=404,
        routine_id=505,
        counterparty_id=900,
        metadata_json={"discount_rule_id": 901},
    )

    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        workspace_module.FinancialBudgetWorkspaceService,
        "_get_document_schedule_context",
        lambda **kwargs: (
            {
                "document": document,
                "contract": contract,
                "line": line,
                "entry_type": "receivable",
                "counterparty": counterparty,
                "default_suggestions": {"receivable_correction_index_id": 88},
                "default_correction_index_id": 88,
                "line_metadata": dict(line.metadata_json),
                "contract_metadata": {},
                "document_metadata": {},
                "domain_type": "project",
                "domain_source_id": 77,
                "domain_label": "Projeto Norte",
            },
            None,
        ),
    )
    monkeypatch.setattr(
        workspace_module,
        "FinancialSchedule",
        type(
            "FakeFinancialSchedule",
            (),
            {
                "query": _QueryStub(schedule),
                "id": _ColumnStub(),
                "company_id": _ColumnStub(),
                "budget_document_id": _ColumnStub(),
                "deleted_at": _ColumnStub(),
            },
        ),
    )
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_has_generated_entries", lambda **kwargs: False)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_schedules_for_document", lambda **kwargs: [schedule])
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_refresh_document_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_serialize_document", lambda item: {"id": item.id})
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_serialize_schedule", lambda item: {"id": item.id, "name": item.name})
    monkeypatch.setattr(
        workspace_module.FinancialBudgetSchedulePolicy,
        "validate_document_schedule_amount",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        workspace_module.FinancialScheduleService,
        "_calculate_schedule_adjustments",
        lambda **kwargs: {
            "template_amount": float(kwargs["template_amount"]),
            "correction_amount": 0.0,
            "discount_amount": 0.0,
            "updated_amount": float(kwargs["template_amount"]),
        },
    )
    monkeypatch.setattr(workspace_module, "date", _Today2026_04_01)
    monkeypatch.setattr(workspace_module.db.session, "commit", lambda: None)
    monkeypatch.setattr(workspace_module.db.session, "rollback", lambda: None)

    captured = {}

    def _fake_update_schedule(*, schedule_id, company_id, payload, allowed_company_ids=None, auto_commit=True):
        captured["schedule_id"] = schedule_id
        captured["payload"] = payload
        captured["auto_commit"] = auto_commit
        schedule.name = payload["name"]
        schedule.status = payload["status"]
        schedule.template_amount = payload["template_amount"]
        schedule.start_date = payload["start_date"]
        schedule.first_due_date = payload["first_due_date"]
        schedule.next_due_date = payload["next_due_date"]
        schedule.notes = payload["notes"]
        schedule.metadata_json = payload["metadata_json"]
        return {"id": schedule_id}, None

    monkeypatch.setattr(workspace_module.FinancialScheduleService, "update_schedule", _fake_update_schedule)

    result, error = FinancialBudgetWorkspaceService.update_document_schedule(
        company_id=9,
        document_id=30,
        schedule_id=40,
        payload={
            "label": "Parcela renegociada",
            "amount": Decimal("45.00"),
            "due_date": date(2026, 5, 10),
            "competence_date": date(2026, 5, 1),
            "status": "paused",
            "notes": "Renegociação maio",
            "auto_post": False,
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result["id"] == 40
    assert captured["auto_commit"] is False
    payload = captured["payload"]
    assert captured["schedule_id"] == 40
    assert payload["budget_document_id"] == 30
    assert payload["name"] == "Parcela renegociada"
    assert payload["status"] == "paused"
    assert payload["template_amount"] == Decimal("45.00")
    assert payload["start_date"] == date(2026, 5, 1)
    assert payload["first_due_date"] == date(2026, 5, 10)
    assert payload["chart_account_id"] == 101
    assert payload["cost_center_id"] == 202
    assert payload["counterparty_id"] == 900
    assert payload["metadata_json"]["competence_mode"] == "keep_first_competence"
    assert payload["metadata_json"]["correction_index_id"] == 88
    assert payload["metadata_json"]["discount_rule_id"] == 901
    allocation = payload["metadata_json"]["allocations"][0]
    assert allocation["allocated_amount"] == 45.0
    assert allocation["domain_value"] == "project:77"
    assert allocation["notes"] == "Parcela renegociada | Nota 01"


def test_update_document_schedule_blocks_items_with_generated_entries(monkeypatch):
    document = _SimpleObj(id=30, company_id=9, document_amount=Decimal("120.00"))
    schedule = _SimpleObj(id=40, company_id=9, budget_document_id=30)

    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        workspace_module.FinancialBudgetWorkspaceService,
        "_get_document_schedule_context",
        lambda **kwargs: (
            {
                "document": document,
                "contract": _SimpleObj(id=20),
                "line": _SimpleObj(id=10),
            },
            None,
        ),
    )
    monkeypatch.setattr(
        workspace_module,
        "FinancialSchedule",
        type(
            "FakeFinancialSchedule",
            (),
            {
                "query": _QueryStub(schedule),
                "id": _ColumnStub(),
                "company_id": _ColumnStub(),
                "budget_document_id": _ColumnStub(),
                "deleted_at": _ColumnStub(),
            },
        ),
    )
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_has_generated_entries", lambda **kwargs: True)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_schedules_for_document", lambda **kwargs: [schedule])

    result, error = FinancialBudgetWorkspaceService.update_document_schedule(
        company_id=9,
        document_id=30,
        schedule_id=40,
        payload={
            "label": "Parcela bloqueada",
            "amount": Decimal("10.00"),
            "due_date": date(2026, 5, 10),
        },
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "Este agendamento já possui baixa/lançamento financeiro vinculado e não pode ser editado por aqui."


def test_create_document_schedules_uses_outer_transaction_and_rolls_back_batch(monkeypatch):
    document = _SimpleObj(id=30, company_id=9, document_amount=Decimal("300.00"))
    rollback_state = {"called": False}
    commit_state = {"called": False}
    create_calls = []

    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        workspace_module.FinancialBudgetWorkspaceService,
        "_get_document_schedule_context",
        lambda **kwargs: (
            {
                "document": document,
                "contract": _SimpleObj(id=20),
                "line": _SimpleObj(id=10),
            },
            None,
        ),
    )
    monkeypatch.setattr(
        workspace_module.FinancialBudgetWorkspaceService,
        "_list_schedules_for_document",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        workspace_module.FinancialBudgetWorkspaceService,
        "_build_document_schedule_payload",
        lambda **kwargs: {"template_amount": kwargs["amount"]},
    )
    monkeypatch.setattr(
        workspace_module.FinancialBudgetSchedulePolicy,
        "get_document_capacity",
        lambda **kwargs: (
            {
                "document": document,
                "scheduled_total": Decimal("0.00"),
                "document_total": Decimal("300.00"),
                "available_to_schedule": Decimal("300.00"),
            },
            None,
        ),
    )

    def _fake_create_schedule(*, payload, allowed_company_ids=None, auto_commit=True):
        create_calls.append(auto_commit)
        if len(create_calls) == 2:
            return None, "falha controlada"
        return {"id": len(create_calls), "template_amount": float(payload["template_amount"])}, None

    monkeypatch.setattr(workspace_module.FinancialScheduleService, "create_schedule", _fake_create_schedule)
    monkeypatch.setattr(workspace_module.db.session, "rollback", lambda: rollback_state.__setitem__("called", True))
    monkeypatch.setattr(workspace_module.db.session, "commit", lambda: commit_state.__setitem__("called", True))

    result, error = FinancialBudgetWorkspaceService.create_document_schedules(
        company_id=9,
        document_id=30,
        payload={
            "installments": [
                {"due_date": date(2026, 4, 10), "amount": Decimal("100.00"), "label": "Parcela 1"},
                {"due_date": date(2026, 5, 10), "amount": Decimal("100.00"), "label": "Parcela 2"},
            ]
        },
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "falha controlada"
    assert create_calls == [False, False]
    assert rollback_state["called"] is True
    assert commit_state["called"] is False


def test_create_document_schedules_allows_past_due_installment_with_correction_index(monkeypatch):
    document = _SimpleObj(id=30, company_id=9, document_amount=Decimal("100.00"))
    captured = {"create_called": False}

    monkeypatch.setattr(workspace_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        workspace_module.FinancialBudgetWorkspaceService,
        "_get_document_schedule_context",
        lambda **kwargs: (
            {
                "document": document,
                "contract": _SimpleObj(id=20),
                "line": _SimpleObj(id=10),
                "default_correction_index_id": 88,
            },
            None,
        ),
    )
    monkeypatch.setattr(
        workspace_module.FinancialBudgetSchedulePolicy,
        "get_document_capacity",
        lambda **kwargs: (
            {
                "document": document,
                "scheduled_total": Decimal("0.00"),
                "document_total": Decimal("100.00"),
                "available_to_schedule": Decimal("100.00"),
            },
            None,
        ),
    )
    monkeypatch.setattr(
        workspace_module.FinancialBudgetWorkspaceService,
        "_build_document_schedule_payload",
        lambda **kwargs: {
            "company_id": 9,
            "budget_document_id": document.id,
            "name": kwargs["label"],
            "entry_type": "receivable",
            "movement_nature": "credit",
            "origin_type": "manual",
            "status": "active",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": kwargs["competence_date"],
            "first_due_date": kwargs["due_date"],
            "next_due_date": kwargs["due_date"],
            "description": "Parcela 1 | NF teste",
            "template_amount": kwargs["amount"],
            "chart_account_id": 101,
            "cost_center_id": 202,
            "counterparty_id": 900,
            "metadata_json": {
                "allocations": [
                    {
                        "chart_account_id": 101,
                        "cost_center_id": 202,
                        "allocation_type": "amount",
                        "allocated_amount": 50.0,
                    }
                ]
            },
        },
    )
    monkeypatch.setattr(
        workspace_module.FinancialScheduleService,
        "create_schedule",
        lambda **kwargs: (captured.__setitem__("create_called", True) or {"id": 501, "name": "Parcela 1"}, None),
    )
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_refresh_document_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_list_schedules_for_document", lambda **kwargs: [])
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_serialize_document", lambda item: {"id": item.id})
    monkeypatch.setattr(workspace_module.FinancialBudgetWorkspaceService, "_serialize_schedule", lambda item: {"id": item.id})
    monkeypatch.setattr(workspace_module.db.session, "commit", lambda: None)
    monkeypatch.setattr(workspace_module.db.session, "rollback", lambda: None)

    result, error = FinancialBudgetWorkspaceService.create_document_schedules(
        company_id=9,
        document_id=30,
        payload={
            "installments": [
                {
                    "due_date": date(2026, 3, 10),
                    "competence_date": date(2026, 3, 1),
                    "amount": Decimal("50.00"),
                    "label": "Parcela 1",
                }
            ]
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result["created_schedules"][0]["id"] == 501
    assert captured["create_called"] is True
