import os
import sys
from datetime import date, datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_schedule_service as schedule_module
from services.financial_schedule_service import FinancialScheduleService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)


class _QueryStub:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
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
            self.activity_id = None
            self.process_instance_id = None
            self.routine_id = None
            self.template_amount = Decimal("1000.00")

    schedule = _FakeSchedule()
    _FakeSchedule.query = _QueryStub(schedule)

    monkeypatch.setattr(schedule_module, "FinancialSchedule", _FakeSchedule)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_links", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_validate_schedule_allocations", lambda **kwargs: None)
    monkeypatch.setattr(schedule_module.FinancialScheduleService, "_serialize_schedule", lambda schedule, **kwargs: schedule.__dict__)
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
