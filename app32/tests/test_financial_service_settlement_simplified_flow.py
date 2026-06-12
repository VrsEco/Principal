import io
import os
import sys
from datetime import date
from decimal import Decimal

from flask import Flask
from werkzeug.datastructures import FileStorage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_service as financial_module
import services.financial_bordero_service as bordero_module
from services.financial_service import FinancialService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def like(self, other):
        return ("like", other)

    def in_(self, other):
        return ("in", other)

    def desc(self):
        return self

    def asc(self):
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

    def all(self):
        if isinstance(self._result, list):
            return list(self._result)
        return [] if self._result is None else [self._result]


class _SequenceQueryStub(_QueryStub):
    def __init__(self, results):
        self._results = list(results)

    def first(self):
        if self._results:
            return self._results.pop(0)
        return None

    def all(self):
        if self._results:
            result = self._results.pop(0)
            return list(result) if isinstance(result, list) else ([] if result is None else [result])
        return []


def test_create_settlement_generates_code_when_not_informed(monkeypatch):
    captured = {}

    class _FakeEntry:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

        def __init__(self):
            self.original_amount = Decimal("500.00")
            self.status = "posted"

    class _FakeSettlement:
        company_id = _Column()
        settlement_code = _Column()
        deleted_at = _Column()
        id = _Column()
        principal_amount = _Column()
        financial_entry_id = _Column()
        settlement_status = _Column()
        query = _SequenceQueryStub([[type("PreviousSettlement", (), {"settlement_code": "LIQ-000014", "id": 14})()], None])

        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            self.id = 501
            self.__dict__.update(kwargs)

    entry = _FakeEntry()
    entry_query = _QueryStub(entry)

    monkeypatch.setattr(financial_module, "FinancialEntry", type("FinancialEntryStub", (), {
        "id": _Column(),
        "company_id": _Column(),
        "deleted_at": _Column(),
        "query": entry_query,
    }))
    monkeypatch.setattr(financial_module, "FinancialSettlement", _FakeSettlement)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialCatalogService, "validate_reference_ids", lambda **kwargs: None)
    monkeypatch.setattr(
        financial_module.db.session,
        "query",
        lambda *args, **kwargs: type("AggQuery", (), {"filter": lambda self, *a, **k: self, "scalar": lambda self: Decimal("0")})(),
    )
    monkeypatch.setattr(financial_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(financial_module.db.session, "flush", lambda: captured.setdefault("flushed", True))
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_entry", lambda **kwargs: None)

    settlement, error = FinancialService.create_settlement(
        payload={
            "company_id": 7,
            "financial_entry_id": 99,
            "settlement_type": "manual",
            "settlement_date": date(2026, 3, 29),
            "bank_account_id": 3,
            "principal_amount": Decimal("120.00"),
            "notes": "Baixa simplificada",
            "metadata_json": {
                "history": "Baixa simplificada",
                "payment_method_id": 8,
                "payment_method_label": "PIX",
            },
        },
        allowed_company_ids=[7],
    )

    assert error is None
    assert settlement is not None
    assert captured["kwargs"]["settlement_code"] == "BX-000015"
    assert captured["kwargs"]["metadata_json"]["history"] == "Baixa simplificada"
    assert captured["committed"] is True
    assert entry.status == "partially_settled"


def test_generate_settlement_code_does_not_reuse_soft_deleted_code(monkeypatch):
    captured_filters = []

    class _CaptureQuery:
        def filter(self, *args, **kwargs):
            captured_filters.extend(args)
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return [
                type("DeletedSettlement", (), {"settlement_code": "LIQ-000016", "id": 16})(),
                type("ActiveSettlement", (), {"settlement_code": "BX-000015", "id": 15})(),
            ]

    class _FakeSettlement:
        company_id = _Column()
        settlement_code = _Column()
        deleted_at = _Column()
        id = _Column()
        query = _CaptureQuery()

    monkeypatch.setattr(financial_module, "FinancialSettlement", _FakeSettlement)

    assert FinancialService._generate_settlement_code(7) == "BX-000017"
    assert ("is", None) not in captured_filters


def test_create_settlement_regenerates_duplicate_auto_code(monkeypatch):
    captured = {}

    class _FakeEntry:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

        def __init__(self):
            self.original_amount = Decimal("500.00")
            self.status = "posted"

    class _FakeSettlement:
        company_id = _Column()
        settlement_code = _Column()
        deleted_at = _Column()
        id = _Column()
        principal_amount = _Column()
        financial_entry_id = _Column()
        settlement_status = _Column()
        query = _SequenceQueryStub([type("ExistingSettlement", (), {"id": 16, "settlement_code": "LIQ-000016"})(), None])

        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            self.id = 777
            self.__dict__.update(kwargs)

    entry = _FakeEntry()
    monkeypatch.setattr(
        financial_module,
        "FinancialEntry",
        type("FinancialEntryStub", (), {
            "id": _Column(),
            "company_id": _Column(),
            "deleted_at": _Column(),
            "query": _QueryStub(entry),
        }),
    )
    monkeypatch.setattr(financial_module, "FinancialSettlement", _FakeSettlement)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialCatalogService, "validate_reference_ids", lambda **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialService, "_generate_settlement_code", lambda company_id: "BX-000017")
    monkeypatch.setattr(
        financial_module.db.session,
        "query",
        lambda *args, **kwargs: type("AggQuery", (), {"filter": lambda self, *a, **k: self, "scalar": lambda self: Decimal("0")})(),
    )
    monkeypatch.setattr(financial_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(financial_module.db.session, "flush", lambda: captured.setdefault("flushed", True))
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_entry", lambda **kwargs: None)

    settlement, error = FinancialService.create_settlement(
        payload={
            "company_id": 7,
            "financial_entry_id": 99,
            "settlement_code": "LIQ-000016",
            "settlement_type": "manual",
            "settlement_date": date(2026, 4, 20),
            "principal_amount": Decimal("100.00"),
            "bank_account_id": 3,
            "notes": "Baixa regenerada",
            "metadata_json": {"history": "Baixa regenerada"},
        },
        allowed_company_ids=[7],
    )

    assert error is None
    assert settlement is not None
    assert captured["kwargs"]["settlement_code"] == "BX-000017"


def test_create_settlement_adds_financial_title_snapshot(monkeypatch):
    captured = {}

    class _FakeEntry:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

        def __init__(self):
            self.id = 99
            self.company_id = 7
            self.original_amount = Decimal("475.00")
            self.status = "posted"
            self.financial_schedule_id = 77

    class _FakeSchedule:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(type("Schedule", (), {
            "id": 77,
            "company_id": 7,
            "schedule_code": "TIT-077",
            "status": "active",
            "entry_type": "payable",
            "movement_nature": "debit",
            "description": "Título teste",
            "name": "Título teste",
            "template_amount": Decimal("500.00"),
            "metadata_json": {"discount_amount_override": "25"},
            "competence_date": date(2026, 3, 5),
            "start_date": date(2026, 3, 5),
            "first_due_date": date(2026, 3, 22),
            "next_due_date": date(2026, 3, 22),
        })())

    class _FakeSettlement:
        company_id = _Column()
        settlement_code = _Column()
        deleted_at = _Column()
        id = _Column()
        principal_amount = _Column()
        financial_entry_id = _Column()
        settlement_status = _Column()
        query = _SequenceQueryStub([[type("PreviousSettlement", (), {"settlement_code": "LIQ-000020", "id": 20})()], None])

        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            self.__dict__.update(kwargs)

    class _FakeTitleCalculationLog:
        def __init__(self, **kwargs):
            captured["log_kwargs"] = kwargs
            self.__dict__.update(kwargs)

    entry = _FakeEntry()
    monkeypatch.setattr(financial_module, "FinancialTitleCalculationLog", _FakeTitleCalculationLog)
    monkeypatch.setattr(
        financial_module.FinancialTitleBalanceService,
        "calculate_for_schedule",
        lambda **kwargs: {
            "principal_settled": 100.0,
            "principal_open": 400.0,
            "adjustments_open": 0.0,
            "discounts_open": 25.0,
            "total_open": 375.0,
        },
    )
    monkeypatch.setattr(financial_module, "FinancialEntry", type("FinancialEntryStub", (), {
        "id": _Column(),
        "company_id": _Column(),
        "deleted_at": _Column(),
        "query": _QueryStub(entry),
    }))
    monkeypatch.setattr(financial_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(financial_module, "FinancialSettlement", _FakeSettlement)
    monkeypatch.setattr(
        financial_module,
        "FinancialEntryAllocation",
        type(
            "FinancialEntryAllocationStub",
            (),
            {
                "company_id": _Column(),
                "financial_entry_id": _Column(),
                "deleted_at": _Column(),
                "id": _Column(),
                "query": _QueryStub([
                    type("AllocationA", (), {"to_dict": lambda self: {"id": 1, "chart_account_id": 501, "cost_center_id": 601, "allocation_type": "amount", "allocated_amount": 300.0, "percentage": None, "notes": "Principal A", "metadata_json": {}}})(),
                    type("AllocationB", (), {"to_dict": lambda self: {"id": 2, "chart_account_id": 502, "cost_center_id": 602, "allocation_type": "amount", "allocated_amount": 175.0, "percentage": None, "notes": "Principal B", "metadata_json": {}}})(),
                ]),
            },
        ),
    )
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialCatalogService, "validate_reference_ids", lambda **kwargs: None)
    monkeypatch.setattr(
        financial_module.db.session,
        "query",
        lambda *args, **kwargs: type("AggQuery", (), {"filter": lambda self, *a, **k: self, "scalar": lambda self: Decimal("100")})(),
    )
    monkeypatch.setattr(financial_module.db.session, "add", lambda obj: captured.setdefault("added", obj))
    monkeypatch.setattr(financial_module.db.session, "flush", lambda: captured.setdefault("flushed", True))
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_entry", lambda **kwargs: None)

    settlement, error = FinancialService.create_settlement(
        payload={
            "company_id": 7,
            "financial_entry_id": 99,
            "settlement_type": "manual",
            "settlement_date": date(2026, 3, 29),
            "principal_amount": Decimal("120.00"),
            "bank_account_id": 3,
            "notes": "Baixa com trilha auditável",
            "created_by_user_id": 19,
            "created_by_employee_id": 27,
            "created_by_agent": "app32",
            "metadata_json": {
                "history": "Liquidação realizada via fluxo assistido",
                "payment_method_id": 8,
                "payment_method_label": "PIX",
                "attachments": [
                    {"id": "att-1", "name": "comprovante.pdf", "content_type": "application/pdf", "size": 2048}
                ],
                "audit": {"actor": {"user_name": "Fabiano Diretor"}, "channel": "app32-web"},
            },
        },
        allowed_company_ids=[7],
    )

    assert error is None
    assert settlement is not None
    snapshot = captured["kwargs"]["metadata_json"]["financial_title_snapshot"]
    assert snapshot["contract_version"] == "financial_title_memory_v2"
    assert snapshot["financial_schedule_id"] == 77
    assert snapshot["updated_amount"] == 475.0
    assert snapshot["settled_principal_before"] == 100.0
    assert snapshot["settled_principal_current"] == 120.0
    assert snapshot["settled_principal_after"] == 220.0
    assert snapshot["open_principal_after"] == 280.0
    assert snapshot["before"]["principal"] == 400.0
    assert snapshot["before"]["financial_correction"] == 0.0
    assert snapshot["before"]["discount"] == 25.0
    assert snapshot["before"]["gross_amount"] == 375.0
    assert snapshot["before"]["principal_open"] == 400.0
    assert snapshot["before"]["total_open"] == 375.0
    assert snapshot["before"]["editable_open"]["principal"] == 400.0
    assert snapshot["before"]["editable_open"]["discount"] == 25.0
    assert snapshot["before"]["editable_rules"]["principal_max"] == 400.0
    assert snapshot["current"]["principal"] == 120.0
    assert snapshot["current"]["principal_settled"] == 120.0
    assert snapshot["current"]["financial_correction"] == 0.0
    assert snapshot["current"]["discount"] == 0.0
    assert snapshot["current"]["gross_amount"] == 120.0
    assert snapshot["after"]["principal"] == 280.0
    assert snapshot["after"]["financial_correction"] == 0.0
    assert snapshot["after"]["discount"] == 25.0
    assert snapshot["after"]["gross_amount"] == 255.0
    assert snapshot["after"]["principal_open"] == 280.0
    assert snapshot["after"]["editable_open"]["principal"] == 280.0
    assert snapshot["after"]["editable_open"]["discount"] == 25.0
    assert snapshot["after"]["editable_open"]["total_open"] == 255.0
    assert snapshot["after"]["editable_open"]["gross_amount"] == 255.0
    assert snapshot["after"]["total_open"] == 255.0
    assert snapshot["after"]["operational_state"]["code"] == "partial"
    assert settlement.metadata_json["settlement_allocation_breakdown"]["principal"]["total_allocated_amount"] == 120.0
    assert settlement.metadata_json["settlement_allocation_breakdown"]["principal"]["items"][0]["chart_account_id"] == 501
    assert settlement.metadata_json["settlement_allocation_breakdown"]["principal"]["items"][1]["settled_allocated_amount"] == 44.21
    assert captured["flushed"] is True
    assert captured["log_kwargs"]["financial_schedule_id"] == 77
    assert captured["log_kwargs"]["financial_entry_id"] == 99
    assert captured["log_kwargs"]["event_type"] == "settlement_posted"
    assert captured["log_kwargs"]["updated_amount"] == Decimal("475.0")
    assert captured["log_kwargs"]["principal_before"] == Decimal("400.00")
    assert captured["log_kwargs"]["principal_settled_now"] == Decimal("120.00")
    assert captured["log_kwargs"]["principal_after"] == Decimal("280.00")
    assert captured["log_kwargs"]["adjustments_open_before"] == Decimal("0.00")
    assert captured["log_kwargs"]["total_due_before"] == Decimal("375.00")
    assert captured["log_kwargs"]["total_due_after"] == Decimal("255.00")
    assert captured["log_kwargs"]["snapshot_json"]["financial_schedule_id"] == 77
    assert captured["log_kwargs"]["metadata_json"]["ledger_version"] == "financial_title_memory_v2"
    assert captured["log_kwargs"]["metadata_json"]["memory_contract_version"] == "financial_title_memory_v2"
    assert captured["log_kwargs"]["metadata_json"]["actor"] == {
        "user_id": 19,
        "employee_id": 27,
        "agent": "app32",
        "user_name": "Fabiano Diretor",
        "channel": "app32-web",
    }
    assert captured["log_kwargs"]["metadata_json"]["evidence"]["bank_account_id"] == 3
    assert captured["log_kwargs"]["metadata_json"]["evidence"]["history"] == "Liquidação realizada via fluxo assistido"
    assert captured["log_kwargs"]["metadata_json"]["evidence"]["payment_method"] == {"id": 8, "label": "PIX"}
    assert captured["log_kwargs"]["metadata_json"]["evidence"]["attachments_count"] == 1
    assert captured["log_kwargs"]["metadata_json"]["component_summary"]["principal"] == 120.0
    assert captured["log_kwargs"]["metadata_json"]["component_summary"]["gross_amount"] == 120.0
    assert captured["log_kwargs"]["metadata_json"]["component_summary"]["count"] == 1
    assert captured["log_kwargs"]["metadata_json"]["editable_before"]["principal"] == 400.0
    assert captured["log_kwargs"]["metadata_json"]["editable_after"]["principal"] == 280.0
    assert captured["log_kwargs"]["metadata_json"]["editable_rules"]["principal_max"] == 400.0
    assert captured["log_kwargs"]["metadata_json"]["tenant_scope"]["company_id"] == 7
    assert captured["log_kwargs"]["metadata_json"]["tenant_scope"]["financial_schedule_id"] == 77
    assert captured["log_kwargs"]["metadata_json"]["tenant_scope"]["scope_consistent"] is True


def test_build_title_settlement_snapshot_keeps_after_principal_and_correction_split(monkeypatch):
    schedule = type(
        "Schedule",
        (),
        {
            "id": 88,
            "company_id": 7,
            "schedule_code": "TIT-088",
            "status": "active",
            "entry_type": "payable",
            "movement_nature": "debit",
            "description": "Título com correção aberta",
            "name": "Título com correção aberta",
            "template_amount": Decimal("2500.00"),
            "metadata_json": {},
            "competence_date": date(2026, 4, 1),
            "start_date": date(2026, 4, 1),
            "first_due_date": date(2026, 4, 30),
            "next_due_date": date(2026, 4, 30),
        },
    )()
    monkeypatch.setattr(
        financial_module,
        "FinancialSchedule",
        type(
            "FinancialScheduleStub",
            (),
            {
                "id": _Column(),
                "company_id": _Column(),
                "deleted_at": _Column(),
                "query": _QueryStub(schedule),
            },
        ),
    )
    monkeypatch.setattr(
        financial_module.FinancialTitleAmountService,
        "calculate",
        lambda **kwargs: {
            "template_amount": 2500.0,
            "correction_amount": 300.0,
            "discount_amount": 0.0,
            "updated_amount": 2800.0,
        },
    )
    monkeypatch.setattr(
        financial_module.FinancialTitleBalanceService,
        "calculate_for_schedule",
        lambda **kwargs: {
            "principal_amount": 2500.0,
            "principal_settled": 300.0,
            "principal_open": 2200.0,
            "adjustments_open": 300.0,
            "discounts_open": 0.0,
            "total_open": 2500.0,
            "adjustments_settled": 0.0,
            "discounts_applied": 0.0,
        },
    )

    entry = type("Entry", (), {"company_id": 7, "financial_schedule_id": 88})()
    settlement_data = type(
        "SettlementData",
        (),
        {
            "company_id": 7,
            "settlement_date": date(2026, 5, 10),
            "principal_amount": Decimal("200.00"),
            "interest_amount": Decimal("0.00"),
            "penalty_amount": Decimal("0.00"),
            "discount_amount": Decimal("0.00"),
            "fee_amount": Decimal("0.00"),
            "other_adjustments_amount": Decimal("0.00"),
            "gross_amount": Decimal("200.00"),
            "net_amount": Decimal("200.00"),
            "settlement_components": [],
        },
    )()

    snapshot = FinancialService._build_title_settlement_snapshot(
        entry=entry,
        settlement_data=settlement_data,
        total_liquidated_before=Decimal("300.00"),
    )

    assert snapshot is not None
    assert snapshot["before"]["principal"] == 2200.0
    assert snapshot["before"]["financial_correction"] == 300.0
    assert snapshot["before"]["discount"] == 0.0
    assert snapshot["before"]["gross_amount"] == 2500.0
    assert snapshot["current"]["principal"] == 200.0
    assert snapshot["current"]["financial_correction"] == 0.0
    assert snapshot["current"]["discount"] == 0.0
    assert snapshot["current"]["gross_amount"] == 200.0
    assert snapshot["after"]["principal"] == 2000.0
    assert snapshot["after"]["financial_correction"] == 300.0
    assert snapshot["after"]["discount"] == 0.0
    assert snapshot["after"]["gross_amount"] == 2300.0
    assert snapshot["after"]["total_open"] == 2300.0
    assert snapshot["after"]["editable_open"]["principal"] == 2000.0
    assert snapshot["after"]["editable_open"]["financial_correction"] == 300.0
    assert snapshot["after"]["editable_open"]["gross_amount"] == 2300.0
    assert snapshot["after"]["editable_open"]["total_open"] == 2300.0


def test_delete_settlement_hides_previous_memory_event_and_registers_exclusion_log(monkeypatch):
    captured = {"added": []}

    settlement = type(
        "Settlement",
        (),
        {
            "id": 31,
            "company_id": 7,
            "financial_entry_id": 99,
            "settlement_code": "BX-000031",
            "settlement_date": date(2026, 4, 20),
            "reconciliation_status": None,
            "deleted_at": None,
            "settlement_status": "posted",
            "metadata_json": {},
        },
    )()
    entry = type(
        "Entry",
        (),
        {
            "id": 99,
            "company_id": 7,
            "deleted_at": None,
            "financial_schedule_id": 77,
            "entry_code": "LAN-099",
            "status": "partially_settled",
            "original_amount": Decimal("7500.00"),
            "metadata_json": {"schedule_template_amount": 7500.0},
        },
    )()
    schedule = type(
        "Schedule",
        (),
        {
            "id": 77,
            "company_id": 7,
            "deleted_at": None,
            "schedule_code": "TIT-077",
            "status": "active",
            "entry_type": "payable",
            "movement_nature": "debit",
            "description": "Título teste",
            "name": "Título teste",
            "template_amount": Decimal("7500.00"),
            "metadata_json": {},
            "competence_date": date(2026, 1, 31),
            "start_date": date(2026, 1, 31),
            "first_due_date": date(2026, 2, 28),
            "next_due_date": date(2026, 2, 28),
        },
    )()
    components = [
        type(
            "ComponentPrincipal",
            (),
            {
                "id": 1,
                "company_id": 7,
                "financial_settlement_id": 31,
                "financial_schedule_id": 77,
                "component_type": "principal",
                "amount": Decimal("2000.00"),
                "competence_date": date(2026, 1, 31),
                "due_date": date(2026, 2, 28),
                "source": "user",
                "origin_adjustment_id": None,
                "metadata_json": {},
            },
        )(),
        type(
            "ComponentInterest",
            (),
            {
                "id": 2,
                "company_id": 7,
                "financial_settlement_id": 31,
                "financial_schedule_id": 77,
                "component_type": "interest",
                "amount": Decimal("100.00"),
                "competence_date": date(2026, 4, 20),
                "due_date": date(2026, 4, 20),
                "source": "user",
                "origin_adjustment_id": 901,
                "metadata_json": {},
            },
        )(),
    ]
    adjustment = type(
        "Adjustment",
        (),
        {
            "id": 901,
            "company_id": 7,
            "deleted_at": None,
            "generated_amount": Decimal("100.00"),
            "settled_amount": Decimal("100.00"),
            "open_amount": Decimal("0.00"),
            "status": "settled",
        },
    )()
    hidden_log = type(
        "CalcLog",
        (),
        {
            "id": 701,
            "event_type": "settlement_posted",
            "metadata_json": {"source": "create_settlement"},
        },
    )()

    monkeypatch.setattr(
        financial_module,
        "FinancialSettlement",
        type("FinancialSettlementStub", (), {"id": _Column(), "company_id": _Column(), "deleted_at": _Column(), "settlement_status": _Column(), "principal_amount": _Column(), "financial_entry_id": _Column(), "query": _QueryStub(settlement)}),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialSettlementComponent",
        type("FinancialSettlementComponentStub", (), {"company_id": _Column(), "financial_settlement_id": _Column(), "query": _QueryStub(components)}),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialEntry",
        type("FinancialEntryStub", (), {"id": _Column(), "company_id": _Column(), "deleted_at": _Column(), "query": _QueryStub(entry)}),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialSchedule",
        type("FinancialScheduleStub", (), {"id": _Column(), "company_id": _Column(), "deleted_at": _Column(), "query": _QueryStub(schedule)}),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialTitleAdjustment",
        type("FinancialTitleAdjustmentStub", (), {"id": _Column(), "company_id": _Column(), "deleted_at": _Column(), "query": _QueryStub(adjustment)}),
    )

    class _FakeCalculationLog:
        company_id = _Column()
        financial_schedule_id = _Column()
        financial_settlement_id = _Column()
        id = _Column()
        query = _QueryStub([hidden_log])

        def __init__(self, **kwargs):
            captured["added"].append(kwargs)
            self.__dict__.update(kwargs)

    monkeypatch.setattr(financial_module, "FinancialTitleCalculationLog", _FakeCalculationLog)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    balance_snapshots = [
        {
            "principal_amount": 7500.0,
            "principal_settled": 2000.0,
            "principal_open": 5500.0,
            "adjustments_open": 100.0,
            "discounts_open": 0.0,
            "total_open": 5600.0,
            "adjustments_settled": 100.0,
            "discounts_applied": 0.0,
            "settlement_state": "partial",
            "operational_state": "partial",
            "operational_state_label": "Parcial",
            "include_in_accounting_reports": True,
            "include_in_projected_reports": False,
            "editable_open": {"principal": 5500.0, "financial_correction": 100.0, "discount": 0.0, "gross_amount": 5600.0, "total_open": 5600.0},
            "editable_rules": {"principal_max": 5500.0},
        },
        {
            "principal_amount": 7500.0,
            "principal_settled": 0.0,
            "principal_open": 7500.0,
            "adjustments_open": 100.0,
            "discounts_open": 0.0,
            "total_open": 7600.0,
            "adjustments_settled": 0.0,
            "discounts_applied": 0.0,
            "settlement_state": "open",
            "operational_state": "open",
            "operational_state_label": "Em aberto",
            "include_in_accounting_reports": True,
            "include_in_projected_reports": True,
            "editable_open": {"principal": 7500.0, "financial_correction": 100.0, "discount": 0.0, "gross_amount": 7600.0, "total_open": 7600.0},
            "editable_rules": {"principal_max": 7500.0},
        },
    ]
    monkeypatch.setattr(
        financial_module.FinancialTitleBalanceService,
        "calculate_for_schedule",
        lambda **kwargs: balance_snapshots.pop(0),
    )
    monkeypatch.setattr(
        financial_module.db.session,
        "query",
        lambda *args, **kwargs: type("AggQuery", (), {"filter": lambda self, *a, **k: self, "scalar": lambda self: Decimal("0")})(),
    )
    monkeypatch.setattr(financial_module.db.session, "add", lambda obj: captured["added"].append(obj))
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))

    result, error = FinancialService.delete_settlement(
        settlement_id=31,
        company_id=7,
        allowed_company_ids=[7],
    )

    assert error is None
    assert result["id"] == 31
    assert settlement.deleted_at is not None
    assert hidden_log.metadata_json["hidden_from_memory"] is True
    assert hidden_log.metadata_json["hidden_reason"] == "settlement_deleted"
    created_log = next(item for item in captured["added"] if isinstance(item, dict))
    assert created_log["event_type"] == "settlement_deleted"
    assert created_log["snapshot_json"]["after"]["principal"] == 7500.0
    assert created_log["snapshot_json"]["after"]["financial_correction"] == 100.0
    assert created_log["snapshot_json"]["after"]["gross_amount"] == 7600.0
    assert created_log["metadata_json"]["hidden_superseded_log_ids"] == [701]
    assert entry.status == "posted"


def test_upload_and_delete_settlement_attachment_updates_metadata(tmp_path, monkeypatch):
    class _FakeSettlement:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

        def __init__(self):
            self.id = 33
            self.company_id = 5
            self.metadata_json = {}

    settlement = _FakeSettlement()
    settlement_query = _QueryStub(settlement)

    monkeypatch.setattr(financial_module, "FinancialSettlement", type("SettlementStub", (), {
        "id": _Column(),
        "company_id": _Column(),
        "deleted_at": _Column(),
        "query": settlement_query,
    }))
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: None)

    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = str(tmp_path)

    with app.app_context():
        attachment, error = FinancialService.upload_settlement_attachment(
            settlement_id=33,
            company_id=5,
            file=FileStorage(stream=io.BytesIO(b"arquivo"), filename="comprovante.pdf", content_type="application/pdf"),
            allowed_company_ids=[5],
        )

        assert error is None
        assert attachment is not None
        assert len(settlement.metadata_json["attachments"]) == 1
        saved_file = settlement.metadata_json["attachments"][0]["stored_name"]
        saved_path = tmp_path / "financial_settlements" / "5" / "33" / saved_file
        assert saved_path.exists()

        removed, delete_error = FinancialService.delete_settlement_attachment(
            settlement_id=33,
            company_id=5,
            attachment_id=attachment["id"],
            allowed_company_ids=[5],
        )

        assert delete_error is None
        assert removed["id"] == attachment["id"]
        assert settlement.metadata_json["attachments"] == []
        assert not saved_path.exists()


def test_delete_settlement_rejects_direct_entry_link(monkeypatch):
    schedule = type(
        "Schedule",
        (),
        {
            "id": 44,
            "company_id": 7,
            "schedule_code": "TIT-44",
            "metadata_json": {"direct_entry": True},
            "next_due_date": None,
            "first_due_date": date(2026, 6, 1),
            "start_date": None,
        },
    )()
    entry = type(
        "Entry",
        (),
        {"id": 21, "company_id": 7, "financial_schedule_id": 44, "deleted_at": None, "metadata_json": {"direct_entry": True}},
    )()
    settlement = type(
        "Settlement",
        (),
        {"id": 31, "company_id": 7, "deleted_at": None, "financial_entry_id": 21, "reconciliation_status": "pending"},
    )()

    monkeypatch.setattr(
        financial_module,
        "FinancialSettlement",
        type(
            "SettlementStub",
            (),
            {
                "id": _Column(),
                "company_id": _Column(),
                "deleted_at": _Column(),
                "query": _QueryStub(settlement),
            },
        ),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialEntry",
        type(
            "EntryStub",
            (),
            {
                "id": _Column(),
                "company_id": _Column(),
                "deleted_at": _Column(),
                "query": _QueryStub(entry),
            },
        ),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialSchedule",
        type(
            "ScheduleStub",
            (),
            {
                "id": _Column(),
                "company_id": _Column(),
                "deleted_at": _Column(),
                "query": _QueryStub(schedule),
            },
        ),
    )
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)

    result, error = FinancialService.delete_settlement(
        settlement_id=31,
        company_id=7,
        allowed_company_ids=[7],
    )

    assert result is None
    assert "Lançamento rápido" in error


def test_delete_settlement_allows_bordero_child_even_when_title_originated_from_direct_entry(monkeypatch):
    captured = {"added": []}
    schedule = type(
        "Schedule",
        (),
        {
            "id": 44,
            "company_id": 7,
            "schedule_code": "TIT-44",
            "metadata_json": {"direct_entry": True},
            "next_due_date": None,
            "first_due_date": date(2026, 6, 1),
            "start_date": None,
        },
    )()
    entry = type(
        "Entry",
        (),
        {
            "id": 21,
            "company_id": 7,
            "financial_schedule_id": 44,
            "deleted_at": None,
            "metadata_json": {"direct_entry": True},
            "status": "settled",
        },
    )()
    settlement = type(
        "Settlement",
        (),
        {
            "id": 31,
            "company_id": 7,
            "deleted_at": None,
            "financial_entry_id": 21,
            "reconciliation_status": "pending",
            "settlement_date": date(2026, 6, 1),
            "metadata_json": {
                "reconcile_via_bordero": True,
                "bordero_id": 11,
                "bordero_settlement_id": 12,
            },
        },
    )()

    monkeypatch.setattr(
        financial_module,
        "FinancialSettlement",
        type(
            "SettlementStub",
            (),
            {
                "id": _Column(),
                "company_id": _Column(),
                "deleted_at": _Column(),
                "query": _QueryStub(settlement),
            },
        ),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialEntry",
        type(
            "EntryStub",
            (),
            {
                "id": _Column(),
                "company_id": _Column(),
                "deleted_at": _Column(),
                "query": _QueryStub(entry),
            },
        ),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialSchedule",
        type(
            "ScheduleStub",
            (),
            {
                "id": _Column(),
                "company_id": _Column(),
                "deleted_at": _Column(),
                "query": _QueryStub(schedule),
            },
        ),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialSettlementComponent",
        type(
            "ComponentStub",
            (),
            {
                "company_id": _Column(),
                "financial_settlement_id": _Column(),
                "query": _QueryStub([]),
            },
        ),
    )
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialService, "_hide_superseded_calculation_logs", lambda **kwargs: [])
    monkeypatch.setattr(financial_module.FinancialService, "_build_deleted_settlement_snapshot", lambda **kwargs: {})
    monkeypatch.setattr(financial_module.FinancialService, "_build_title_calculation_log_payload", lambda **kwargs: {})
    monkeypatch.setattr(financial_module.FinancialService, "_recalculate_entry_status", lambda **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialTitleBalanceService, "calculate_for_schedule", lambda **kwargs: {})
    monkeypatch.setattr(financial_module.db.session, "add", lambda obj: captured["added"].append(obj))
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: captured.setdefault("rolled_back", True))

    result, error = FinancialService.delete_settlement(
        settlement_id=31,
        company_id=7,
        allowed_company_ids=[7],
        allow_bordero_child_delete=True,
    )

    assert error is None
    assert result["id"] == 31
    assert settlement.deleted_at is not None
    assert captured["committed"] is True


def test_delete_entry_whole_flow_soft_deletes_active_settlement(monkeypatch):
    schedule = type("Schedule", (), {"id": 44, "company_id": 7, "deleted_at": None, "metadata_json": {"direct_entry": True}})()
    entry = type(
        "Entry",
        (),
        {"id": 21, "company_id": 7, "financial_schedule_id": 44, "deleted_at": None, "metadata_json": {"generate_target": "entry"}},
    )()
    settlement = type(
        "Settlement",
        (),
        {"id": 31, "company_id": 7, "deleted_at": None, "financial_entry_id": 21, "reconciliation_status": "pending", "metadata_json": {}},
    )()

    monkeypatch.setattr(
        financial_module,
        "FinancialEntry",
        type(
            "EntryStub",
            (),
            {
                "id": _Column(),
                "company_id": _Column(),
                "deleted_at": _Column(),
                "query": _QueryStub(entry),
            },
        ),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialSchedule",
        type(
            "ScheduleStub",
            (),
            {
                "id": _Column(),
                "company_id": _Column(),
                "deleted_at": _Column(),
                "query": _QueryStub(schedule),
            },
        ),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialSettlement",
        type(
            "SettlementStub",
            (),
            {
                "company_id": _Column(),
                "financial_entry_id": _Column(),
                "deleted_at": _Column(),
                "settlement_status": _Column(),
                "query": _QueryStub([settlement]),
            },
        ),
    )
    monkeypatch.setattr(
        financial_module,
        "FinancialEntryAllocation",
        type(
            "AllocationStub",
            (),
            {
                "company_id": _Column(),
                "financial_entry_id": _Column(),
                "deleted_at": _Column(),
                "query": _QueryStub(None),
            },
        ),
    )
    captured = {}
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        financial_module.FinancialEntryAllocation.query,
        "update",
        lambda values, synchronize_session=False: captured.setdefault("allocation_deleted_at", values["deleted_at"]),
        raising=False,
    )
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))

    result, error = FinancialService.delete_entry(
        entry_id=21,
        company_id=7,
        allowed_company_ids=[7],
    )

    assert error is None
    assert result == {"message": "Lançamento financeiro removido com sucesso.", "id": 21}
    assert entry.deleted_at is not None
    assert schedule.deleted_at is not None
    assert settlement.deleted_at is not None
    assert settlement.metadata_json["deleted_via"] == "financial_service.delete_entry"
    assert captured["committed"] is True


def test_create_settlement_rejects_zero_principal_amount(monkeypatch):
    class _FakeEntry:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

        def __init__(self):
            self.original_amount = Decimal("500.00")
            self.status = "posted"

    class _FakeSettlement:
        company_id = _Column()
        settlement_code = _Column()
        deleted_at = _Column()
        id = _Column()
        principal_amount = _Column()
        financial_entry_id = _Column()
        settlement_status = _Column()
        query = _SequenceQueryStub([None])

    entry = _FakeEntry()
    entry_query = _QueryStub(entry)

    monkeypatch.setattr(financial_module, "FinancialEntry", type("FinancialEntryStub", (), {
        "id": _Column(),
        "company_id": _Column(),
        "deleted_at": _Column(),
        "query": entry_query,
    }))
    monkeypatch.setattr(financial_module, "FinancialSettlement", _FakeSettlement)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialCatalogService, "validate_reference_ids", lambda **kwargs: None)
    monkeypatch.setattr(
        financial_module.db.session,
        "query",
        lambda *args, **kwargs: type("AggQuery", (), {"filter": lambda self, *a, **k: self, "scalar": lambda self: Decimal("0")})(),
    )
    monkeypatch.setattr(financial_module.db.session, "add", lambda obj: (_ for _ in ()).throw(AssertionError("não deveria persistir")))
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: (_ for _ in ()).throw(AssertionError("não deveria commitar")))
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_entry", lambda **kwargs: None)

    settlement, error = FinancialService.create_settlement(
        payload={
            "company_id": 7,
            "financial_entry_id": 99,
            "settlement_type": "manual",
            "settlement_date": date(2026, 3, 29),
            "bank_account_id": 3,
            "principal_amount": Decimal("0"),
            "notes": "Baixa zerada inválida",
            "metadata_json": {
                "history": "Baixa zerada inválida",
            },
        },
        allowed_company_ids=[7],
    )

    assert settlement is None
    assert error == "Baixa inválida: o valor da baixa deve ser maior que zero."
    assert entry.status == "posted"


def test_create_settlement_persists_gross_amount_and_component_breakdown(monkeypatch):
    captured = {"added": []}

    class _FakeEntry:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()

        def __init__(self):
            self.id = 99
            self.company_id = 7
            self.original_amount = Decimal("500.00")
            self.status = "posted"
            self.financial_schedule_id = 77
            self.competence_date = date(2026, 4, 1)

    class _FakeSchedule:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(type("Schedule", (), {
            "id": 77,
            "company_id": 7,
            "schedule_code": "TIT-077",
            "status": "active",
            "entry_type": "payable",
            "movement_nature": "debit",
            "description": "Título teste",
            "name": "Título teste",
            "template_amount": Decimal("500.00"),
            "metadata_json": {},
            "competence_date": date(2026, 4, 1),
            "start_date": date(2026, 4, 1),
            "first_due_date": date(2026, 4, 10),
            "next_due_date": date(2026, 4, 10),
        })())

    class _FakeSettlement:
        company_id = _Column()
        settlement_code = _Column()
        deleted_at = _Column()
        id = _Column()
        principal_amount = _Column()
        financial_entry_id = _Column()
        settlement_status = _Column()
        query = _SequenceQueryStub([[type("PreviousSettlement", (), {"settlement_code": "LIQ-000030", "id": 30})()], None])

        def __init__(self, **kwargs):
            captured["settlement_kwargs"] = kwargs
            self.id = 601
            self.__dict__.update(kwargs)

    class _FakeSettlementComponent:
        def __init__(self, **kwargs):
            captured.setdefault("component_kwargs", []).append(kwargs)
            self.__dict__.update(kwargs)

    entry = _FakeEntry()
    monkeypatch.setattr(
        financial_module.FinancialTitleBalanceService,
        "calculate_for_schedule",
        lambda **kwargs: {
            "principal_settled": 0.0,
            "principal_open": 500.0,
            "adjustments_open": 0.0,
            "total_open": 500.0,
        },
    )
    monkeypatch.setattr(financial_module, "FinancialEntry", type("FinancialEntryStub", (), {
        "id": _Column(),
        "company_id": _Column(),
        "deleted_at": _Column(),
        "query": _QueryStub(entry),
    }))
    monkeypatch.setattr(financial_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(financial_module, "FinancialSettlement", _FakeSettlement)
    monkeypatch.setattr(financial_module, "FinancialSettlementComponent", _FakeSettlementComponent)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialCatalogService, "validate_reference_ids", lambda **kwargs: None)
    monkeypatch.setattr(
        financial_module.db.session,
        "query",
        lambda *args, **kwargs: type("AggQuery", (), {"filter": lambda self, *a, **k: self, "scalar": lambda self: Decimal("0")})(),
    )
    monkeypatch.setattr(financial_module.db.session, "add", lambda obj: captured["added"].append(obj))
    monkeypatch.setattr(financial_module.db.session, "flush", lambda: captured.setdefault("flushed", True))
    monkeypatch.setattr(financial_module.db.session, "commit", lambda: captured.setdefault("committed", True))
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: captured.setdefault("rollback", True))
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_entry", lambda **kwargs: None)

    settlement, error = FinancialService.create_settlement(
        payload={
            "company_id": 7,
            "financial_entry_id": 99,
            "settlement_type": "manual",
            "settlement_date": date(2026, 4, 20),
            "principal_amount": Decimal("200.00"),
            "interest_amount": Decimal("50.00"),
            "gross_amount": Decimal("250.00"),
            "settlement_components": [
                {
                    "component_type": "principal",
                    "amount": Decimal("200.00"),
                    "competence_date": date(2026, 4, 1),
                    "due_date": date(2026, 4, 10),
                    "source": "user",
                },
                {
                    "component_type": "interest",
                    "amount": Decimal("50.00"),
                    "competence_date": date(2026, 4, 20),
                    "due_date": date(2026, 4, 20),
                    "source": "user",
                },
            ],
        },
        allowed_company_ids=[7],
    )

    assert error is None
    assert settlement is not None
    assert captured["settlement_kwargs"]["gross_amount"] == Decimal("250.00")
    assert len(captured["component_kwargs"]) == 2
    assert captured["component_kwargs"][0]["financial_settlement_id"] == 601
    assert captured["component_kwargs"][0]["component_type"] == "principal"
    assert captured["component_kwargs"][1]["component_type"] == "interest"
    assert captured["committed"] is True


def test_build_schedule_component_allocation_breakdown_for_financial_correction():
    schedule = type(
        "Schedule",
        (),
        {
            "id": 77,
            "metadata_json": {
                "allocations": [
                    {
                        "chart_account_id": 701,
                        "cost_center_id": 801,
                        "allocation_type": "amount",
                        "allocated_amount": 24.3,
                        "percentage": None,
                        "notes": "Correcao A",
                        "metadata_json": {"adjustment_kind": "correction"},
                    },
                    {
                        "chart_account_id": 702,
                        "cost_center_id": 802,
                        "allocation_type": "amount",
                        "allocated_amount": 10.7,
                        "percentage": None,
                        "notes": "Correcao B",
                        "metadata_json": {"adjustment_kind": "correction"},
                    },
                ]
            },
        },
    )()
    settlement = type("Settlement", (), {"settlement_date": date(2026, 4, 20)})()

    result = FinancialService._build_schedule_component_allocation_breakdown(
        schedule=schedule,
        settlement=settlement,
        component_kind="financial_correction",
        component_amount=35.0,
    )

    assert result["component_kind"] == "financial_correction"
    assert result["basis_schedule_id"] == 77
    assert result["total_allocated_amount"] == 35.0
    assert result["items"][0]["chart_account_id"] == 701
    assert result["items"][0]["competence_date"] == "2026-04-20"
    assert result["items"][0]["due_date"] == "2026-04-20"
    assert result["items"][1]["settled_allocated_amount"] == 10.7
    assert result["items"][0]["metadata_json"]["component_kind"] == "financial_correction"


def test_build_schedule_component_allocation_breakdown_uses_selected_correction_index(monkeypatch):
    schedule = type(
        "Schedule",
        (),
        {
            "id": 77,
            "company_id": 9,
            "cost_center_id": 801,
            "metadata_json": {},
        },
    )()
    settlement = type("Settlement", (), {"settlement_date": date(2026, 4, 20)})()
    correction = type("Correction", (), {"metadata_json": {"chart_account_id": 701}})()

    class _CorrectionIndexModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(correction)

    monkeypatch.setattr(financial_module, "FinancialCorrectionIndex", _CorrectionIndexModel)

    result = FinancialService._build_schedule_component_allocation_breakdown(
        schedule=schedule,
        settlement=settlement,
        component_kind="financial_correction",
        component_payloads=[
            {
                "component_type": "manual_adjustment",
                "amount": 35.0,
                "metadata_json": {"correction_index_id": 44},
            }
        ],
    )

    assert result["items"][0]["chart_account_id"] == 701
    assert result["items"][0]["cost_center_id"] == 801
    assert result["items"][0]["metadata_json"]["correction_index_id"] == 44


def test_build_schedule_component_allocation_breakdown_for_discount():
    schedule = type(
        "Schedule",
        (),
        {
            "id": 77,
            "metadata_json": {
                "allocations": [
                    {
                        "chart_account_id": 901,
                        "cost_center_id": 951,
                        "allocation_type": "amount",
                        "allocated_amount": -15.0,
                        "percentage": None,
                        "notes": "Desconto A",
                        "metadata_json": {"adjustment_kind": "discount"},
                    },
                    {
                        "chart_account_id": 902,
                        "cost_center_id": 952,
                        "allocation_type": "amount",
                        "allocated_amount": -5.0,
                        "percentage": None,
                        "notes": "Desconto B",
                        "metadata_json": {"adjustment_kind": "discount"},
                    },
                ]
            },
        },
    )()
    settlement = type("Settlement", (), {"settlement_date": date(2026, 4, 20)})()

    result = FinancialService._build_schedule_component_allocation_breakdown(
        schedule=schedule,
        settlement=settlement,
        component_kind="discount",
        component_amount=20.0,
    )

    assert result["component_kind"] == "discount"
    assert result["total_allocated_amount"] == 20.0
    assert result["items"][0]["chart_account_id"] == 901
    assert result["items"][0]["competence_date"] == "2026-04-20"
    assert result["items"][0]["metadata_json"]["component_kind"] == "discount"
    assert result["items"][1]["settled_allocated_amount"] == 5.0


def test_build_principal_allocation_breakdown_ignores_adjustment_rows(monkeypatch):
    monkeypatch.setattr(
        financial_module,
        "FinancialEntryAllocation",
        type(
            "FinancialEntryAllocationStub",
            (),
            {
                "company_id": _Column(),
                "financial_entry_id": _Column(),
                "deleted_at": _Column(),
                "id": _Column(),
                "query": _QueryStub(
                    [
                        type("AllocationPrincipalA", (), {"to_dict": lambda self: {"id": 1, "chart_account_id": 501, "cost_center_id": 601, "allocation_type": "amount", "allocated_amount": 180.0, "metadata_json": {}}})(),
                        type("AllocationCorrection", (), {"to_dict": lambda self: {"id": 2, "chart_account_id": 999, "cost_center_id": 699, "allocation_type": "amount", "allocated_amount": 50.0, "metadata_json": {"adjustment_kind": "correction"}}})(),
                        type("AllocationPrincipalB", (), {"to_dict": lambda self: {"id": 3, "chart_account_id": 502, "cost_center_id": 602, "allocation_type": "amount", "allocated_amount": 120.0, "metadata_json": {}}})(),
                    ]
                ),
            },
        ),
    )

    entry = type(
        "Entry",
        (),
        {
            "company_id": 7,
            "id": 99,
            "original_amount": Decimal("350.00"),
            "metadata_json": {"schedule_template_amount": 300.0},
        },
    )()
    settlement = type("Settlement", (), {"principal_amount": Decimal("120.00")})()

    result = FinancialService._build_principal_allocation_breakdown(
        entry=entry,
        settlement=settlement,
    )

    assert result["basis_entry_amount"] == 300.0
    assert result["total_allocated_amount"] == 120.0
    assert len(result["items"]) == 2
    assert result["items"][0]["chart_account_id"] == 501
    assert result["items"][0]["settled_allocated_amount"] == 72.0
    assert result["items"][1]["chart_account_id"] == 502
    assert result["items"][1]["settled_allocated_amount"] == 48.0


def test_create_settlement_uses_schedule_template_amount_as_principal_limit(monkeypatch):
    class _FakeEntry:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        financial_schedule_id = 77

        def __init__(self):
            self.original_amount = Decimal("350.00")
            self.status = "posted"
            self.company_id = 7
            self.metadata_json = {"schedule_template_amount": 300.0}

    class _FakeSchedule:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(type("Schedule", (), {"id": 77, "company_id": 7, "template_amount": Decimal("300.00"), "metadata_json": {}, "cost_center_id": None, "chart_account_id": 501})())

    class _FakeSettlement:
        company_id = _Column()
        settlement_code = _Column()
        id = _Column()
        principal_amount = _Column()
        financial_entry_id = _Column()
        deleted_at = _Column()
        settlement_status = _Column()
        query = _QueryStub(None)

    entry = _FakeEntry()
    entry_query = _QueryStub(entry)

    monkeypatch.setattr(financial_module, "FinancialEntry", type("FinancialEntryStub", (), {
        "id": _Column(),
        "company_id": _Column(),
        "deleted_at": _Column(),
        "query": entry_query,
    }))
    monkeypatch.setattr(financial_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(financial_module, "FinancialSettlement", _FakeSettlement)
    monkeypatch.setattr(financial_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(financial_module.FinancialCatalogService, "validate_reference_ids", lambda **kwargs: None)
    monkeypatch.setattr(
        financial_module.db.session,
        "query",
        lambda *args, **kwargs: type("AggQuery", (), {"filter": lambda self, *a, **k: self, "scalar": lambda self: Decimal("250.00")})(),
    )
    monkeypatch.setattr(financial_module.db.session, "rollback", lambda: None)
    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_entry", lambda **kwargs: None)

    settlement, error = FinancialService.create_settlement(
        payload={
            "company_id": 7,
            "financial_entry_id": 99,
            "settlement_type": "manual",
            "settlement_date": date(2026, 4, 20),
            "principal_amount": Decimal("60.00"),
            "gross_amount": Decimal("60.00"),
            "net_amount": Decimal("60.00"),
        },
        allowed_company_ids=[7],
    )

    assert settlement is None
    assert "valor principal do lançamento" in error

