import os
import sys
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_schedule_service as schedule_module
import services.financial_bordero_service as bordero_module
from services.financial_schedule_service import FinancialScheduleService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def like(self, other):
        return ("like", other)

    def desc(self):
        return self


class _QueryStub:
    def __init__(self, result=None, all_result=None):
        self._result = result
        self._all_result = list(all_result or [])

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._result

    def all(self):
        return list(self._all_result)


class _Today2026_04_01:
    @staticmethod
    def today():
        return date(2026, 4, 1)


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
    monkeypatch.setattr(
        schedule_module.FinancialBudgetSchedulePolicy,
        "validate_document_schedule_amount",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_has_active_settlements", lambda **kwargs: False)
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
            "competence_date": date(2026, 3, 21),
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
    assert captured["kwargs"]["competence_date"] == date(2026, 3, 21)
    allocation = captured["kwargs"]["metadata_json"]["allocations"][0]
    assert allocation["allocated_amount"] == 1000.0
    assert allocation["competence_date"] == "2026-03-22"
    assert captured["kwargs"]["budget_line_id"] == 12
    assert captured["kwargs"]["budget_contract_id"] == 34
    assert captured["kwargs"]["budget_document_id"] == 56
    assert captured["kwargs"]["metadata_json"]["budget_line_id"] == 12
    assert captured["kwargs"]["metadata_json"]["budget_contract_id"] == 34
    assert captured["kwargs"]["metadata_json"]["budget_document_id"] == 56


def test_create_schedule_uses_flush_when_auto_commit_is_disabled(monkeypatch):
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
        lambda **kwargs: ({"budget_line_id": None, "budget_contract_id": None, "budget_document_id": None}, None),
    )
    monkeypatch.setattr(
        schedule_module.FinancialBudgetSchedulePolicy,
        "validate_document_schedule_amount",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_has_active_settlements", lambda **kwargs: False)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_serialize_schedule", lambda schedule, **kwargs: schedule.__dict__)
    monkeypatch.setattr(schedule_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(schedule_module.db.session, "flush", lambda: captured.setdefault("flushed", True))
    monkeypatch.setattr(schedule_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(schedule_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))

    result, error = FinancialScheduleService.create_schedule(
        payload={
            "company_id": 9,
            "schedule_code": "SCH-002",
            "name": "Condomínio",
            "entry_type": "payable",
            "movement_nature": "debit",
            "origin_type": "manual",
            "status": "draft",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": date(2026, 3, 22),
            "first_due_date": date(2026, 3, 22),
            "description": "Teste flush",
            "template_amount": Decimal("300.00"),
            "currency_code": "BRL",
            "metadata_json": {
                "allocations": [
                    {
                        "allocation_type": "amount",
                        "allocated_amount": Decimal("300.00"),
                        "chart_account_id": 1,
                        "cost_center_id": 2,
                    }
                ]
            },
        },
        allowed_company_ids=[9],
        auto_commit=False,
    )

    assert error is None
    assert result is not None
    assert captured["flushed"] is True
    assert "committed" not in captured


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
    monkeypatch.setattr(
        schedule_module.FinancialBudgetSchedulePolicy,
        "validate_document_schedule_amount",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_has_active_settlements", lambda **kwargs: False)
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


def test_update_schedule_uses_flush_when_auto_commit_is_disabled(monkeypatch):
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
            self.metadata_json = {
                "allocations": [
                    {
                        "allocation_type": "amount",
                        "allocated_amount": 200.0,
                        "chart_account_id": 1,
                        "cost_center_id": 2,
                    }
                ]
            }
            self.bank_account_id = None
            self.counterparty_id = None
            self.chart_account_id = 1
            self.cost_center_id = 2
            self.budget_line_id = None
            self.budget_contract_id = None
            self.budget_document_id = None
            self.activity_id = None
            self.process_instance_id = None
            self.routine_id = None
            self.template_amount = Decimal("200.00")
            self.schedule_code = "SCH-003"

    schedule = _FakeSchedule()
    _FakeSchedule.query = _QueryStub(schedule)
    captured = {}

    monkeypatch.setattr(schedule_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        schedule_module.FinancialService,
        "_resolve_budget_links",
        lambda **kwargs: ({"budget_line_id": None, "budget_contract_id": None, "budget_document_id": None}, None),
    )
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_has_active_settlements", lambda **kwargs: False)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_serialize_schedule", lambda schedule, **kwargs: schedule.__dict__)
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_schedule", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.db.session, "flush", lambda: captured.setdefault("flushed", True))
    monkeypatch.setattr(schedule_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(schedule_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))

    result, error = FinancialScheduleService.update_schedule(
        schedule_id=1,
        company_id=9,
        payload={
            "description": "Atualizado sem commit interno",
            "metadata_json": {
                "allocations": [
                    {
                        "allocation_type": "amount",
                        "allocated_amount": Decimal("200.00"),
                        "chart_account_id": 1,
                        "cost_center_id": 2,
                    }
                ]
            },
        },
        allowed_company_ids=[9],
        auto_commit=False,
    )

    assert error is None
    assert result is not None
    assert captured["flushed"] is True
    assert "committed" not in captured


def test_build_budget_document_schedule_payload_preserves_budget_hierarchy_without_operational_links():
    counterparty = type("Counterparty", (), {"id": 91, "name": "Fornecedor XPTO"})()
    version = type("Version", (), {"code": "AA.O.2026.CAPEX.1"})()
    line = type(
        "Line",
        (),
        {
            "id": 10,
            "budget_version_id": 1,
            "version": version,
            "line_code": "AA.O.2026.CAPEX.1.2",
            "movement_nature": "debit",
            "chart_account_id": 301,
            "cost_center_id": 401,
            "activity_id": 501,
            "process_instance_id": 601,
            "routine_id": 701,
            "metadata_json": {},
        },
    )()
    contract = type(
        "Contract",
        (),
        {
            "id": 20,
            "contract_code": "AA.O.2026.CAPEX.1.2.3",
            "name": "Contrato Infra",
            "notes": "Notas contrato",
            "counterparty": None,
            "metadata_json": {},
        },
    )()
    document = type(
        "Document",
        (),
        {
            "id": 30,
            "document_code": "AA.O.2026.CAPEX.1.2.3.4",
            "title": "NF Infra",
            "document_number": "NF-123",
            "notes": "Notas NF",
            "counterparty": counterparty,
            "metadata_json": {},
        },
    )()

    payload = FinancialScheduleService.build_budget_document_schedule_payload(
        company_id=9,
        document=document,
        contract=contract,
        line=line,
        label="Parcela 1/2",
        amount=Decimal("250.00"),
        due_date=date(2026, 4, 30),
        competence_date=date(2026, 4, 30),
        notes=None,
        status="active",
        auto_post=False,
        default_suggestions={"domain_type": "process", "domain_source_id": 77, "domain_label": "Proc. XPTO"},
        default_correction_index_id=12,
        domain_type="process",
        domain_source_id=77,
        domain_label="Proc. XPTO",
    )

    assert payload["budget_line_id"] == 10
    assert payload["budget_contract_id"] == 20
    assert payload["budget_document_id"] == 30
    assert payload["entry_type"] == "payable"
    assert payload["movement_nature"] == "debit"
    assert payload["competence_date"] == date(2026, 4, 30)
    assert payload["counterparty_id"] == 91
    assert "activity_id" not in payload
    assert "process_instance_id" not in payload
    assert "routine_id" not in payload
    assert payload["metadata_json"]["budget_schedule_source"] == "financial_budget_workspace"
    assert payload["metadata_json"]["budget_document_id"] == 30
    assert payload["metadata_json"]["budget_document_code"] == "AA.O.2026.CAPEX.1.2.3.4"
    assert payload["metadata_json"]["document_number"] == "NF-123"
    allocation = payload["metadata_json"]["allocations"][0]
    assert allocation["chart_account_id"] == 301
    assert allocation["cost_center_id"] == 401
    assert allocation["budget_line_id"] == 10
    assert allocation["budget_contract_id"] == 20
    assert allocation["budget_document_id"] == 30


def test_build_budget_document_schedule_payload_adds_adjustment_allocations_for_past_due_items(monkeypatch):
    counterparty = type("Counterparty", (), {"id": 91, "name": "Fornecedor XPTO"})()
    version = type("Version", (), {"code": "AA.O.2026.CAPEX.1"})()
    line = type(
        "Line",
        (),
        {
            "id": 10,
            "budget_version_id": 1,
            "version": version,
            "line_code": "AA.O.2026.CAPEX.1.2",
            "movement_nature": "debit",
            "chart_account_id": 301,
            "cost_center_id": 401,
            "metadata_json": {},
        },
    )()
    contract = type(
        "Contract",
        (),
        {
            "id": 20,
            "contract_code": "AA.O.2026.CAPEX.1.2.3",
            "name": "Contrato Infra",
            "notes": "Notas contrato",
            "counterparty": None,
            "metadata_json": {},
        },
    )()
    document = type(
        "Document",
        (),
        {
            "id": 30,
            "document_code": "AA.O.2026.CAPEX.1.2.3.4",
            "title": "NF Infra",
            "document_number": "NF-123",
            "notes": "Notas NF",
            "counterparty": counterparty,
            "metadata_json": {},
        },
    )()

    class _FakeCorrectionIndex:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        is_active = _Column()
        query = _QueryStub(type("Correction", (), {"metadata_json": {"penalty_rate": 10, "chart_account_id": 777}})())

    class _FakeDiscountRule:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        is_active = _Column()
        query = _QueryStub(type("Discount", (), {"metadata_json": {"discount_type": "percentage", "value": 5, "chart_account_id": 888}})())

    monkeypatch.setattr(schedule_module, "FinancialCorrectionIndex", _FakeCorrectionIndex)
    monkeypatch.setattr(schedule_module, "FinancialDiscountRule", _FakeDiscountRule)
    monkeypatch.setattr(schedule_module, "date", _Today2026_04_01)

    payload = FinancialScheduleService.build_budget_document_schedule_payload(
        company_id=9,
        document=document,
        contract=contract,
        line=line,
        label="Parcela vencida",
        amount=Decimal("250.00"),
        due_date=date(2026, 3, 10),
        competence_date=date(2026, 3, 10),
        notes=None,
        status="active",
        auto_post=False,
        default_suggestions={"discount_rule_id": 21},
        default_correction_index_id=12,
        domain_type="process",
        domain_source_id=77,
        domain_label="Proc. XPTO",
    )

    allocations = payload["metadata_json"]["allocations"]
    assert len(allocations) == 3

    base_allocation, correction_allocation, discount_allocation = allocations
    assert base_allocation["allocated_amount"] == 250.0
    assert base_allocation["chart_account_id"] == 301
    assert base_allocation["budget_document_id"] == 30

    assert correction_allocation["allocated_amount"] == 25.0
    assert correction_allocation["chart_account_id"] == 777
    assert correction_allocation["cost_center_id"] == 401
    assert correction_allocation["budget_document_id"] is None
    assert correction_allocation["metadata_json"]["adjustment_kind"] == "correction"
    assert correction_allocation["metadata_json"]["adjustment_label"] == "Correção Financeira"

    assert discount_allocation["allocated_amount"] == -12.5
    assert discount_allocation["chart_account_id"] == 888
    assert discount_allocation["cost_center_id"] == 401
    assert discount_allocation["budget_document_id"] is None
    assert discount_allocation["metadata_json"]["adjustment_kind"] == "discount"
    assert discount_allocation["metadata_json"]["adjustment_label"] == "Desconto"

    allocated_total = sum(Decimal(str(item["allocated_amount"])) for item in allocations)
    assert allocated_total == Decimal("262.5")


def test_build_entry_payload_propagates_budget_links():
    class _Schedule:
        company_id = 9
        id = 77
        schedule_code = "SCH-077"
        competence_date = date(2026, 3, 5)
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
        metadata_json = {"document_number": "NF-123", "discount_amount_override": "25"}

    payload = FinancialScheduleService._build_entry_payload(
        schedule=_Schedule(),
        entry_code="ENT-001",
    )

    assert payload["budget_line_id"] == 10
    assert payload["budget_contract_id"] == 20
    assert payload["budget_document_id"] == 30
    assert payload["competence_date"] == date(2026, 3, 5)
    assert payload["due_date"] == date(2026, 3, 22)
    assert payload["financial_schedule_id"] == 77
    assert payload["external_reference"] == "financial_schedule:77"
    assert payload["original_amount"] == Decimal("475.0")
    assert payload["metadata_json"]["schedule_discount_amount"] == 25.0
    assert payload["metadata_json"]["budget_line_id"] == 10
    assert payload["metadata_json"]["budget_contract_id"] == 20
    assert payload["metadata_json"]["budget_document_id"] == 30


def test_update_schedule_accepts_same_schedule_code_in_payload(monkeypatch):
    import services.financial_schedule_service as schedule_module
    import services.financial_bordero_service as bordero_module

    class _Column:
        def __eq__(self, other):
            return self

        def is_(self, other):
            return self

    class _Query:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return schedule

    class _Schedule:
        query = _Query()
        id = 1
        company_id = 9
        schedule_code = "SCH-077"
        entry_type = "payable"
        movement_nature = "debit"
        start_date = date(2026, 3, 20)
        end_date = None
        first_due_date = date(2026, 3, 25)
        next_due_date = date(2026, 3, 25)
        template_amount = Decimal("100.00")
        bank_account_id = None
        counterparty_id = 2
        chart_account_id = 3
        cost_center_id = 4
        budget_line_id = None
        budget_contract_id = None
        budget_document_id = None
        activity_id = None
        process_instance_id = None
        routine_id = None
        metadata_json = {}
        deleted_at = _Column()

    schedule = _Schedule()
    monkeypatch.setattr(schedule_module, "FinancialSchedule", _Schedule)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialService, "_resolve_budget_links", lambda **kwargs: ({}, None))
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_has_active_settlements", lambda **kwargs: False)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_serialize_schedule", lambda schedule, **kwargs: schedule.__dict__)
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_schedule", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.db.session, "commit", lambda: None)
    monkeypatch.setattr(schedule_module.db.session, "rollback", lambda: None)

    result, error = schedule_module.FinancialScheduleService.update_schedule(
        schedule_id=1,
        company_id=9,
        payload={
            "schedule_code": "SCH-077",
            "description": "Conta atualizada",
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    assert schedule.schedule_code == "SCH-077"
    assert schedule.description == "Conta atualizada"


def test_update_schedule_rejects_schedule_code_change(monkeypatch):
    import services.financial_schedule_service as schedule_module
    import services.financial_bordero_service as bordero_module

    class _Column:
        def __eq__(self, other):
            return self

        def is_(self, other):
            return self

    class _Query:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return schedule

    class _Schedule:
        query = _Query()
        id = 1
        company_id = 9
        schedule_code = "SCH-077"
        entry_type = "payable"
        movement_nature = "debit"
        start_date = date(2026, 3, 20)
        end_date = None
        first_due_date = date(2026, 3, 25)
        next_due_date = date(2026, 3, 25)
        template_amount = Decimal("100.00")
        bank_account_id = None
        counterparty_id = 2
        chart_account_id = 3
        cost_center_id = 4
        budget_line_id = None
        budget_contract_id = None
        budget_document_id = None
        activity_id = None
        process_instance_id = None
        routine_id = None
        metadata_json = {}
        deleted_at = _Column()

    schedule = _Schedule()
    monkeypatch.setattr(schedule_module, "FinancialSchedule", _Schedule)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_has_active_settlements", lambda **kwargs: False)
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_schedule", lambda **kwargs: None)

    result, error = schedule_module.FinancialScheduleService.update_schedule(
        schedule_id=1,
        company_id=9,
        payload={"schedule_code": "SCH-999"},
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "O código do Título Financeiro não pode ser alterado após a criação."


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


def test_generate_schedule_code_considers_soft_deleted_history(monkeypatch):
    class _LastSchedule:
        id = 10
        schedule_code = "AG-000010"

    class _FakeSchedule:
        company_id = _Column()
        schedule_code = _Column()
        id = _Column()
        query = _QueryStub(_LastSchedule())

    monkeypatch.setattr(schedule_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(
        schedule_module.FinancialScheduleService,
        "_find_schedule_by_code",
        lambda **kwargs: None,
    )

    generated = schedule_module.FinancialScheduleService._generate_schedule_code(9)

    assert generated == "AG-000011"


def test_create_schedule_rejects_duplicate_code_even_if_existing_row_is_soft_deleted(monkeypatch):
    class _ExistingSchedule:
        id = 99

    class _FakeSchedule:
        company_id = _Column()
        schedule_code = _Column()
        query = _QueryStub(_ExistingSchedule())

    monkeypatch.setattr(schedule_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        schedule_module.FinancialService,
        "_resolve_budget_links",
        lambda **kwargs: ({}, None),
    )
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)

    result, error = schedule_module.FinancialScheduleService.create_schedule(
        payload={
            "company_id": 9,
            "schedule_code": "AG-000010",
            "name": "Teste duplicado",
            "entry_type": "receivable",
            "movement_nature": "credit",
            "origin_type": "manual",
            "status": "active",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": date(2026, 3, 1),
            "first_due_date": date(2026, 3, 10),
            "description": "Teste duplicado",
            "template_amount": Decimal("2500.00"),
            "currency_code": "BRL",
            "metadata_json": {},
        },
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "Já existe agendamento com código AG-000010 para esta empresa."


def test_create_schedule_blocks_when_budget_document_exceeds_capacity(monkeypatch):
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        schedule_module.FinancialService,
        "_resolve_budget_links",
        lambda **kwargs: (
            {
                "budget_line_id": 10,
                "budget_contract_id": 20,
                "budget_document_id": 30,
            },
            None,
        ),
    )
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(
        schedule_module.FinancialBudgetSchedulePolicy,
        "validate_document_schedule_amount",
        lambda **kwargs: "A soma das parcelas ultrapassa o valor executado da NF/equivalente.",
    )
    add_state = {"called": False}
    monkeypatch.setattr(schedule_module.db.session, "add", lambda obj: add_state.__setitem__("called", True))

    result, error = FinancialScheduleService.create_schedule(
        payload={
            "company_id": 9,
            "schedule_code": "AG-OVER",
            "name": "Agendamento acima do saldo",
            "entry_type": "receivable",
            "movement_nature": "credit",
            "origin_type": "manual",
            "status": "active",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": date(2026, 4, 1),
            "first_due_date": date(2026, 4, 20),
            "description": "Agendamento acima do saldo",
            "template_amount": Decimal("3000.00"),
            "currency_code": "BRL",
            "metadata_json": {"allocations": [{"chart_account_id": 3, "cost_center_id": 8, "allocation_type": "amount", "allocated_amount": Decimal("3000.00")}]},
        },
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "A soma das parcelas ultrapassa o valor executado da NF/equivalente."
    assert add_state["called"] is False


def test_create_schedule_retries_auto_generated_code_after_unique_violation(monkeypatch):
    captured = {"codes": []}

    class _FakeSchedule:
        company_id = _Column()
        schedule_code = _Column()
        query = _QueryStub(None)

        def __init__(self, **kwargs):
            captured["codes"].append(kwargs["schedule_code"])
            self.__dict__.update(kwargs)

    class _OrigDiag:
        constraint_name = "uq_financial_schedules_company_code"

    class _Orig:
        diag = _OrigDiag()

    commit_attempts = {"count": 0}

    def _commit():
        commit_attempts["count"] += 1
        if commit_attempts["count"] == 1:
            raise IntegrityError("INSERT", {}, _Orig())

    def _rollback():
        captured["rollback"] = captured.get("rollback", 0) + 1

    generated_codes = iter(["AG-000010", "AG-000011", "AG-000011"])

    monkeypatch.setattr(schedule_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        schedule_module.FinancialService,
        "_resolve_budget_links",
        lambda **kwargs: ({}, None),
    )
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_serialize_schedule", lambda schedule, **kwargs: schedule.__dict__)
    monkeypatch.setattr(
        schedule_module.FinancialScheduleService,
        "_generate_schedule_code",
        lambda company_id: next(generated_codes),
    )
    monkeypatch.setattr(
        schedule_module.FinancialScheduleService,
        "_find_schedule_by_code",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(schedule_module.db.session, "add", lambda obj: captured.setdefault("added", []).append(obj))
    monkeypatch.setattr(schedule_module.db.session, "commit", _commit)
    monkeypatch.setattr(schedule_module.db.session, "rollback", _rollback)

    result, error = schedule_module.FinancialScheduleService.create_schedule(
        payload={
            "company_id": 9,
            "name": "Teste retry",
            "entry_type": "receivable",
            "movement_nature": "credit",
            "origin_type": "manual",
            "status": "active",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": date(2026, 3, 1),
            "first_due_date": date(2026, 3, 10),
            "description": "Teste retry",
            "template_amount": Decimal("2500.00"),
            "currency_code": "BRL",
            "metadata_json": {},
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    assert result["schedule_code"] == "AG-000011"
    assert captured["codes"] == ["AG-000010", "AG-000011"]
    assert commit_attempts["count"] == 2


def test_update_schedule_blocks_when_budget_document_exceeds_capacity(monkeypatch):
    class _Schedule:
        id = 40
        company_id = 9
        schedule_code = "AG-040"
        entry_type = "receivable"
        movement_nature = "credit"
        start_date = date(2026, 4, 1)
        end_date = None
        first_due_date = date(2026, 4, 20)
        next_due_date = date(2026, 4, 20)
        template_amount = Decimal("2500.00")
        bank_account_id = None
        counterparty_id = 2
        chart_account_id = 3
        cost_center_id = 8
        budget_line_id = 10
        budget_contract_id = 20
        budget_document_id = 30
        activity_id = None
        process_instance_id = None
        routine_id = None
        metadata_json = {"allocations": [{"chart_account_id": 3, "cost_center_id": 8, "allocation_type": "amount", "allocated_amount": Decimal("2500.00")}]}
        deleted_at = _Column()

    class _FakeSchedule:
        query = _QueryStub(_Schedule())
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

    monkeypatch.setattr(schedule_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_has_active_settlements", lambda **kwargs: False)
    monkeypatch.setattr(
        schedule_module.FinancialService,
        "_resolve_budget_links",
        lambda **kwargs: (
            {
                "budget_line_id": 10,
                "budget_contract_id": 20,
                "budget_document_id": 30,
            },
            None,
        ),
    )
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_schedule", lambda **kwargs: None)
    monkeypatch.setattr(
        schedule_module.FinancialBudgetSchedulePolicy,
        "validate_document_schedule_amount",
        lambda **kwargs: "A soma das parcelas ultrapassa o valor executado da NF/equivalente.",
    )
    monkeypatch.setattr(schedule_module.db.session, "commit", lambda: (_ for _ in ()).throw(AssertionError("não deveria commitar")))

    result, error = FinancialScheduleService.update_schedule(
        schedule_id=40,
        company_id=9,
        payload={
            "template_amount": Decimal("3000.00"),
            "description": "Tentativa acima do saldo",
        },
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "A soma das parcelas ultrapassa o valor executado da NF/equivalente."


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

    class _FakeCorrectionIndex:
        company_id = _Column()
        deleted_at = _Column()
        is_active = _Column()
        updated_at = _Column()
        id = _Column()
        query = _QueryStub(all_result=[])

    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(schedule_module, "FinancialCostCenter", _FakeCostCenter)
    monkeypatch.setattr(schedule_module, "FinancialDomainEnablement", _FakeEnablement)
    monkeypatch.setattr(schedule_module, "FinancialBudgetDocument", _FakeBudgetDocument)
    monkeypatch.setattr(schedule_module, "FinancialBudgetContract", _FakeBudgetContract)
    monkeypatch.setattr(schedule_module, "FinancialBudgetLine", _FakeBudgetLine)
    monkeypatch.setattr(schedule_module, "FinancialBudgetVersion", _FakeBudgetVersion)
    monkeypatch.setattr(schedule_module, "FinancialCorrectionIndex", _FakeCorrectionIndex)
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
        due_date=None,
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


def test_validate_schedule_allocations_accepts_adjustment_rows_matching_updated_amount(monkeypatch):
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
        query = _SequentialQuery(
            [
                type("Center", (), {"id": 8})(),
                None,
                type("Center", (), {"id": 8})(),
                None,
                type("Center", (), {"id": 8})(),
                None,
            ]
        )

    monkeypatch.setattr(schedule_module, "FinancialChartAccount", _FakeChartAccount)
    monkeypatch.setattr(schedule_module, "FinancialCostCenter", _FakeCostCenter)
    monkeypatch.setattr(schedule_module.FinancialService, "_resolve_budget_links", lambda **kwargs: ({}, None))
    monkeypatch.setattr(
        schedule_module.FinancialScheduleService,
        "_calculate_schedule_adjustments",
        lambda **kwargs: {
            "template_amount": 250.0,
            "correction_amount": 25.0,
            "discount_amount": 12.5,
            "updated_amount": 262.5,
        },
    )

    error = FinancialScheduleService._validate_schedule_allocations(
        company_id=9,
        template_amount=Decimal("250.00"),
        due_date=date(2026, 3, 10),
        metadata_json={
            "allocations": [
                {
                    "chart_account_id": 301,
                    "cost_center_id": 8,
                    "allocation_type": "amount",
                    "allocated_amount": Decimal("250.00"),
                    "metadata_json": {"adjustment_kind": None},
                },
                {
                    "chart_account_id": 777,
                    "cost_center_id": 8,
                    "allocation_type": "amount",
                    "allocated_amount": Decimal("25.00"),
                    "metadata_json": {"adjustment_kind": "correction"},
                },
                {
                    "chart_account_id": 888,
                    "cost_center_id": 8,
                    "allocation_type": "amount",
                    "allocated_amount": Decimal("-12.50"),
                    "metadata_json": {"adjustment_kind": "discount"},
                },
            ]
        },
    )

    assert error is None


def test_normalize_schedule_allocations_backfills_adjustment_rows_for_legacy_principal_only_payload(monkeypatch):
    monkeypatch.setattr(
        schedule_module.FinancialScheduleService,
        "_calculate_schedule_adjustments",
        lambda **kwargs: {
            "template_amount": 500000.0,
            "correction_amount": 12483.33,
            "discount_amount": 0.0,
            "updated_amount": 512483.33,
        },
    )
    monkeypatch.setattr(
        schedule_module.FinancialScheduleService,
        "_resolve_adjustment_chart_account_id",
        lambda **kwargs: 777,
    )

    allocations = FinancialScheduleService._normalize_schedule_allocations(
        company_id=9,
        template_amount=Decimal("500000.00"),
        due_date=date(2026, 4, 21),
        metadata_json={
            "correction_index_id": 12,
            "allocations": [
                {
                    "chart_account_id": 301,
                    "cost_center_id": 8,
                    "allocation_type": "amount",
                    "allocated_amount": Decimal("500000.00"),
                    "metadata_json": {"adjustment_kind": None},
                }
            ],
        },
        fallback_chart_account_id=301,
        fallback_cost_center_id=8,
    )

    assert len(allocations) == 2
    assert allocations[0]["allocated_amount"] == Decimal("500000.00")
    assert allocations[1]["chart_account_id"] == 777
    assert allocations[1]["cost_center_id"] == 8
    assert allocations[1]["allocated_amount"] == 12483.33
    assert allocations[1]["metadata_json"]["adjustment_kind"] == "correction"
    allocated_total = sum(Decimal(str(item["allocated_amount"])) for item in allocations)
    assert allocated_total == Decimal("512483.33")


def test_create_schedule_normalizes_legacy_adjustment_gap_before_validation_and_persist(monkeypatch):
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
        lambda **kwargs: ({"budget_line_id": None, "budget_contract_id": None, "budget_document_id": None}, None),
    )
    monkeypatch.setattr(
        schedule_module.FinancialBudgetSchedulePolicy,
        "validate_document_schedule_amount",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(
        schedule_module.FinancialScheduleService,
        "_validate_schedule_allocations",
        lambda **kwargs: captured.setdefault("validated_metadata", kwargs["metadata_json"]) and None,
    )
    monkeypatch.setattr(
        schedule_module.FinancialScheduleService,
        "_calculate_schedule_adjustments",
        lambda **kwargs: {
            "template_amount": 500000.0,
            "correction_amount": 12483.33,
            "discount_amount": 0.0,
            "updated_amount": 512483.33,
        },
    )
    monkeypatch.setattr(
        schedule_module.FinancialScheduleService,
        "_resolve_adjustment_chart_account_id",
        lambda **kwargs: 777,
    )
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_serialize_schedule", lambda schedule, **kwargs: schedule.__dict__)
    monkeypatch.setattr(schedule_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(schedule_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(schedule_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))

    result, error = FinancialScheduleService.create_schedule(
        payload={
            "company_id": 9,
            "schedule_code": "SCH-ADJ-001",
            "name": "Título legado",
            "entry_type": "payable",
            "movement_nature": "debit",
            "origin_type": "manual",
            "status": "active",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": date(2026, 4, 1),
            "competence_date": date(2026, 4, 1),
            "first_due_date": date(2026, 4, 10),
            "next_due_date": date(2026, 4, 10),
            "description": "Título com correção pendente",
            "template_amount": Decimal("500000.00"),
            "currency_code": "BRL",
            "chart_account_id": 301,
            "cost_center_id": 8,
            "metadata_json": {
                "correction_index_id": 12,
                "allocations": [
                    {
                        "chart_account_id": 301,
                        "cost_center_id": 8,
                        "allocation_type": "amount",
                        "allocated_amount": Decimal("500000.00"),
                        "metadata_json": {"adjustment_kind": None},
                    }
                ],
            },
        },
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    assert len(captured["validated_metadata"]["allocations"]) == 2
    persisted_allocations = captured["kwargs"]["metadata_json"]["allocations"]
    assert len(persisted_allocations) == 2
    assert persisted_allocations[1]["chart_account_id"] == 777
    assert persisted_allocations[1]["allocated_amount"] == 12483.33
