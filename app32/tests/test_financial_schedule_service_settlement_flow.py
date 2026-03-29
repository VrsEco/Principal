import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_schedule_service as schedule_module
from services.financial_schedule_service import FinancialScheduleService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def in_(self, other):
        return ("in", other)


class _QueryStub:
    def __init__(self, first_result=None, all_result=None):
        self._first_result = first_result
        self._all_result = list(all_result or [])

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_result

    def all(self):
        return list(self._all_result)

    def update(self, *args, **kwargs):
        return None


def test_create_settlement_from_schedule_forwards_entry_and_external_reference(monkeypatch):
    schedule = type("Schedule", (), {"id": 15, "company_id": 9})()

    class _FakeScheduleModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(first_result=schedule)

    captured = {}

    monkeypatch.setattr(schedule_module, "FinancialSchedule", _FakeScheduleModel)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        schedule_module.FinancialScheduleService,
        "create_entry_from_schedule",
        lambda **kwargs: ({"entry": {"id": 88}, "created": True}, None),
    )

    def _fake_create_settlement(*, payload, allowed_company_ids=None):
        captured["payload"] = payload
        return type("Settlement", (), {"to_dict": lambda self: {"id": 901, "financial_entry_id": 88}})(), None

    monkeypatch.setattr(schedule_module.FinancialService, "create_settlement", _fake_create_settlement)
    monkeypatch.setattr(
        schedule_module,
        "FinancialEntry",
        type(
            "FinancialEntryModel",
            (),
            {
                "id": _Column(),
                "company_id": _Column(),
                "deleted_at": _Column(),
                "query": _QueryStub(first_result=type("Entry", (), {"id": 88})()),
            },
        ),
    )
    monkeypatch.setattr(schedule_module.FinancialService, "serialize_entry", lambda entry: {"id": entry.id})

    result, error = FinancialScheduleService.create_settlement_from_schedule(
        schedule_id=15,
        company_id=9,
        payload={"settlement_type": "manual", "settlement_date": "2026-03-29", "principal_amount": 10},
        allowed_company_ids=[9],
    )

    assert error is None
    assert result == {
        "entry": {"id": 88},
        "settlement": {"id": 901, "financial_entry_id": 88},
        "created_entry": True,
    }
    assert captured["payload"]["financial_entry_id"] == 88
    assert captured["payload"]["external_reference"] == "financial_schedule:15"


def test_delete_schedule_soft_deletes_generated_entries_without_settlements(monkeypatch):
    schedule = type("Schedule", (), {"id": 21, "company_id": 9, "deleted_at": None})()
    linked_entry = type(
        "Entry",
        (),
        {"id": 31, "metadata_json": {"generated_from_schedule": True}, "deleted_at": None},
    )()

    class _FakeScheduleModel:
        id = _Column()
        company_id = _Column()
        deleted_at = _Column()
        query = _QueryStub(first_result=schedule)

    class _FakeEntryModel:
        company_id = _Column()
        external_reference = _Column()
        deleted_at = _Column()
        id = _Column()
        query = _QueryStub(all_result=[linked_entry])

    class _FakeSettlementModel:
        company_id = _Column()
        financial_entry_id = _Column()
        deleted_at = _Column()
        settlement_status = _Column()
        query = _QueryStub(first_result=None)

    updates = {}

    class _FakeAllocationModel:
        company_id = _Column()
        financial_entry_id = _Column()
        deleted_at = _Column()
        query = _QueryStub()

    monkeypatch.setattr(schedule_module, "FinancialSchedule", _FakeScheduleModel)
    monkeypatch.setattr(schedule_module, "FinancialEntry", _FakeEntryModel)
    monkeypatch.setattr(schedule_module, "FinancialSettlement", _FakeSettlementModel)
    monkeypatch.setattr(schedule_module, "FinancialEntryAllocation", _FakeAllocationModel)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(schedule_module.db.session, "commit", lambda: updates.setdefault("committed", True))
    monkeypatch.setattr(schedule_module.db.session, "rollback", lambda: updates.setdefault("rollback", True))
    monkeypatch.setattr(
        schedule_module.FinancialEntryAllocation.query,
        "update",
        lambda values, synchronize_session=False: updates.setdefault("allocation_deleted_at", values["deleted_at"]),
    )

    import services.financial_bordero_service as bordero_module

    monkeypatch.setattr(bordero_module.FinancialBorderoService, "get_active_bordero_for_schedule", lambda **kwargs: None)

    result, error = FinancialScheduleService.delete_schedule(
        schedule_id=21,
        company_id=9,
        allowed_company_ids=[9],
    )

    assert error is None
    assert result == {"message": "Agendamento removido com sucesso.", "id": 21}
    assert isinstance(schedule.deleted_at, datetime)
    assert isinstance(linked_entry.deleted_at, datetime)
    assert updates["committed"] is True
    assert isinstance(updates["allocation_deleted_at"], datetime)
