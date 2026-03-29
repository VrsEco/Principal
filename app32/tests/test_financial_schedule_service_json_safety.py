import os
import sys
from datetime import date, datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_schedule_service as schedule_module
import services.financial_bordero_service as bordero_module
from services.financial_schedule_service import FinancialScheduleService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def desc(self):
        return self


class _QueryStub:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


def test_sanitize_json_converts_decimal_date_datetime_and_sequences():
    payload = {
        "amount": Decimal("250.90"),
        "due_date": date(2026, 3, 22),
        "created_at": datetime(2026, 3, 22, 19, 30, 0),
        "items": {Decimal("10.50"), date(2026, 3, 23)},
        "nested": [{"discount": Decimal("5.25")}],
    }

    sanitized = FinancialScheduleService._sanitize_json(payload)

    assert sanitized["amount"] == 250.9
    assert sanitized["due_date"] == "2026-03-22"
    assert sanitized["created_at"] == "2026-03-22T19:30:00"
    assert sorted(sanitized["items"], key=str) == [10.5, "2026-03-23"]
    assert sanitized["nested"][0]["discount"] == 5.25


def test_create_schedule_sanitizes_metadata_json_before_insert(monkeypatch):
    captured = {}

    class _FakeSchedule:
        company_id = _Column()
        schedule_code = _Column()
        deleted_at = _Column()
        query = _QueryStub(None)

        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            self.__dict__.update(kwargs)

    monkeypatch.setattr(schedule_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        schedule_module.FinancialService,
        "_resolve_budget_links",
        lambda **kwargs: (
            {
                "budget_line_id": 12,
                "budget_contract_id": 34,
                "budget_document_id": 56,
            },
            None,
        ),
    )
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_serialize_schedule", lambda schedule, **kwargs: schedule.__dict__)
    monkeypatch.setattr(schedule_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(schedule_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(schedule_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))

    result, error = FinancialScheduleService.create_schedule(
        payload={
            "company_id": 9,
            "schedule_code": "SCH-001",
            "name": "Aluguel",
            "entry_type": "payable",
            "movement_nature": "debit",
            "origin_type": "manual",
            "status": "draft",
            "frequency": "monthly",
            "interval_value": 1,
            "start_date": date(2026, 3, 22),
            "first_due_date": date(2026, 3, 22),
            "description": "Teste Lcto Rapido",
            "template_amount": Decimal("1000.00"),
            "currency_code": "BRL",
            "metadata_json": {
                "allocations": [
                    {
                        "allocation_type": "fixed",
                        "allocated_amount": Decimal("1000.00"),
                        "competence_date": date(2026, 3, 22),
                    }
                ]
            },
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    assert captured["committed"] is True
    allocation = captured["kwargs"]["metadata_json"]["allocations"][0]
    assert allocation["allocated_amount"] == 1000.0
    assert allocation["competence_date"] == "2026-03-22"
    assert captured["kwargs"]["budget_line_id"] == 12
    assert captured["kwargs"]["budget_contract_id"] == 34
    assert captured["kwargs"]["budget_document_id"] == 56
    assert captured["kwargs"]["metadata_json"]["budget_line_id"] == 12
    assert captured["kwargs"]["metadata_json"]["budget_contract_id"] == 34
    assert captured["kwargs"]["metadata_json"]["budget_document_id"] == 56


def test_update_schedule_sanitizes_metadata_json_before_persist(monkeypatch):
    class _FakeSchedule:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(None)

        def __init__(self):
            self.company_id = 9
            self.entry_type = "payable"
            self.movement_nature = "debit"
            self.start_date = date(2026, 3, 22)
            self.end_date = None
            self.first_due_date = date(2026, 3, 22)
            self.next_due_date = date(2026, 3, 22)
            self.metadata_json = {}
            self.bank_account_id = None
            self.counterparty_id = None
            self.chart_account_id = None
            self.cost_center_id = None
            self.budget_line_id = None
            self.budget_contract_id = None
            self.budget_document_id = None
            self.activity_id = None
            self.process_instance_id = None
            self.routine_id = None
            self.template_amount = Decimal("1000.00")

    schedule = _FakeSchedule()
    _FakeSchedule.query = _QueryStub(schedule)

    monkeypatch.setattr(schedule_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        schedule_module.FinancialService,
        "_resolve_budget_links",
        lambda **kwargs: (
            {
                "budget_line_id": 90,
                "budget_contract_id": 91,
                "budget_document_id": 92,
            },
            None,
        ),
    )
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_serialize_schedule", lambda schedule, **kwargs: schedule.__dict__)
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_schedule", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.db.session, "commit", lambda: None)
    monkeypatch.setattr(schedule_module.db.session, "rollback", lambda: None)

    result, error = FinancialScheduleService.update_schedule(
        schedule_id=1,
        company_id=9,
        payload={
            "metadata_json": {
                "allocations": [
                    {
                        "allocation_type": "percentage",
                        "percentage": Decimal("50.00"),
                        "generated_at": datetime(2026, 3, 22, 20, 0, 0),
                    }
                ]
            }
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    allocation = schedule.metadata_json["allocations"][0]
    assert allocation["percentage"] == 50.0
    assert allocation["generated_at"] == "2026-03-22T20:00:00"
    assert schedule.budget_line_id == 90
    assert schedule.budget_contract_id == 91
    assert schedule.budget_document_id == 92
    assert schedule.metadata_json["budget_line_id"] == 90
    assert schedule.metadata_json["budget_contract_id"] == 91
    assert schedule.metadata_json["budget_document_id"] == 92


def test_build_entry_payload_propagates_budget_links():
    class _Schedule:
        company_id = 9
        id = 77
        schedule_code = "SCH-077"
        next_due_date = date(2026, 3, 22)
        first_due_date = date(2026, 3, 22)
        auto_post = False
        entry_type = "payable"
        movement_nature = "debit"
        origin_type = "manual"
        description = "Conta teste"
        memo = "memo"
        frequency = "one_time"
        document_number_prefix = "DOC"
        template_amount = Decimal("500.00")
        currency_code = "BRL"
        bank_account_id = 1
        counterparty_id = 2
        chart_account_id = 3
        cost_center_id = 4
        budget_line_id = 10
        budget_contract_id = 20
        budget_document_id = 30
        activity_id = None
        process_instance_id = None
        routine_id = None
        created_by_user_id = 5
        created_by_employee_id = 6
        created_by_agent = "agent"
        notes = "notes"
        metadata_json = {"document_number": "NF-123"}

    payload = FinancialScheduleService._build_entry_payload(
        schedule=_Schedule(),
        entry_code="ENT-001",
    )

    assert payload["budget_line_id"] == 10
    assert payload["budget_contract_id"] == 20
    assert payload["budget_document_id"] == 30
    assert payload["metadata_json"]["budget_line_id"] == 10
    assert payload["metadata_json"]["budget_contract_id"] == 20
    assert payload["metadata_json"]["budget_document_id"] == 30


def test_create_schedule_returns_friendly_date_validation_message():
    result, error = FinancialScheduleService.create_schedule(
        payload={
            "company_id": 9,
            "schedule_code": "SCH-002",
            "name": "Pagamento inválido",
            "entry_type": "payable",
            "movement_nature": "debit",
            "origin_type": "manual",
            "status": "draft",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": date(2026, 3, 29),
            "first_due_date": date(2026, 3, 28),
            "description": "Teste data inválida",
            "template_amount": Decimal("100.00"),
            "currency_code": "BRL",
            "metadata_json": {},
        },
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == (
        "Payload inválido para criação do agendamento: "
        "o vencimento não pode ser anterior à competência."
    )


def test_derive_budget_links_from_allocations_returns_unique_chain_only():
    unique_links = FinancialScheduleService._derive_budget_links_from_allocations(
        metadata_json={
            "allocations": [
                {"budget_line_id": 11, "budget_contract_id": 22, "budget_document_id": 33},
                {"budget_line_id": 11, "budget_contract_id": 22, "budget_document_id": 33},
            ]
        }
    )
    mixed_links = FinancialScheduleService._derive_budget_links_from_allocations(
        metadata_json={
            "allocations": [
                {"budget_line_id": 11, "budget_contract_id": 22, "budget_document_id": 33},
                {"budget_line_id": 12, "budget_contract_id": 23, "budget_document_id": 34},
            ]
        }
    )

    assert unique_links == {
        "budget_line_id": 11,
        "budget_contract_id": 22,
        "budget_document_id": 33,
    }
    assert mixed_links == {
        "budget_line_id": None,
        "budget_contract_id": None,
        "budget_document_id": None,
    }


def test_list_default_suggestions_returns_cost_center_domain_and_budget_chain(monkeypatch):
    class _FakeCostCenter:
        company_id = _Column()
        deleted_at = _Column()
        is_active = _Column()
        is_default_suggestion = _Column()
        updated_at = _Column()
        id = _Column()
        query = _QueryStub(type("Center", (), {"id": 7, "code": "1.01", "name": "Administrativo"})())

    class _FakeEnablement:
        company_id = _Column()
        deleted_at = _Column()
        is_enabled = _Column()
        is_default_suggestion = _Column()
        updated_at = _Column()
        id = _Column()
        source_id = _Column()
        domain_type = _Column()
        query = _QueryStub(type("Enablement", (), {"source_id": 21, "domain_type": "project"})())

    document = type("Document", (), {"id": 44, "title": "NF padrão", "budget_contract_id": 33})()
    contract = type("Contract", (), {"id": 33, "budget_line_id": 22})()
    line = type("Line", (), {"id": 22, "budget_version_id": 11})()
    version = type("Version", (), {"id": 11})()

    class _FakeBudgetDocument:
        company_id = _Column()
        deleted_at = _Column()
        is_default_suggestion = _Column()
        updated_at = _Column()
        id = _Column()
        query = _QueryStub(document)

    class _FakeBudgetContract:
        company_id = _Column()
        deleted_at = _Column()
        id = _Column()
        query = _QueryStub(contract)

    class _FakeBudgetLine:
        company_id = _Column()
        deleted_at = _Column()
        id = _Column()
        query = _QueryStub(line)

    class _FakeBudgetVersion:
        company_id = _Column()
        deleted_at = _Column()
        id = _Column()
        query = _QueryStub(version)

    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(schedule_module, "FinancialCostCenter", _FakeCostCenter)
    monkeypatch.setattr(schedule_module, "FinancialDomainEnablement", _FakeEnablement)
    monkeypatch.setattr(schedule_module, "FinancialBudgetDocument", _FakeBudgetDocument)
    monkeypatch.setattr(schedule_module, "FinancialBudgetContract", _FakeBudgetContract)
    monkeypatch.setattr(schedule_module, "FinancialBudgetLine", _FakeBudgetLine)
    monkeypatch.setattr(schedule_module, "FinancialBudgetVersion", _FakeBudgetVersion)
    monkeypatch.setattr(
        schedule_module.FinancialDomainEnablementService,
        "list_items",
        lambda **kwargs: (
            {
                "items": [
                    {
                        "domain_type": "project",
                        "source_id": 21,
                        "display_label": "AA.J.21 - Projeto Padrão",
                    }
                ]
            },
            None,
        ),
    )

    result, error = FinancialScheduleService.list_default_suggestions(company_id=9, allowed_company_ids=[9])

    assert error is None
    assert result == {
        "cost_center_id": 7,
        "cost_center_label": "1.01 - Administrativo",
        "domain_type": "project",
        "domain_source_id": 21,
        "domain_label": "AA.J.21 - Projeto Padrão",
        "budget_version_id": 11,
        "budget_line_id": 22,
        "budget_contract_id": 33,
        "budget_document_id": 44,
        "budget_document_label": "NF padrão",
    }


def test_validate_schedule_allocations_accepts_amount_mode_total_match(monkeypatch):
    class _FakeChartAccount:
        company_id = _Column()
        deleted_at = _Column()
        id = _Column()
        accepts_posting = True
        query = _QueryStub(type("Chart", (), {"accepts_posting": True})())

    class _SequentialQuery:
        def __init__(self, responses):
            self._responses = list(responses)

        def filter(self, *args, **kwargs):
            return self

        def first(self):
            if self._responses:
                return self._responses.pop(0)
            return None

    class _FakeCostCenter:
        company_id = _Column()
        deleted_at = _Column()
        id = _Column()
        parent_id = _Column()
        query = _SequentialQuery([type("Center", (), {"id": 8})(), None])

    monkeypatch.setattr(schedule_module, "FinancialChartAccount", _FakeChartAccount)
    monkeypatch.setattr(schedule_module, "FinancialCostCenter", _FakeCostCenter)
    monkeypatch.setattr(schedule_module.FinancialService, "_resolve_budget_links", lambda **kwargs: ({}, None))

    error = FinancialScheduleService._validate_schedule_allocations(
        company_id=9,
        template_amount=Decimal("1500.00"),
        metadata_json={
            "allocations": [
                {
                    "chart_account_id": 3,
                    "cost_center_id": 8,
                    "allocation_type": "amount",
                    "allocated_amount": Decimal("1500.00"),
                }
            ]
        },
    )

    assert error is None
