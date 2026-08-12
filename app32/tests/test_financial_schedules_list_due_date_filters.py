import os
import sys
from datetime import date
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_schedule_service as schedule_module
from services.financial_schedule_service import FinancialScheduleService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def __ge__(self, other):
        return ("ge", other)

    def __le__(self, other):
        return ("le", other)

    def is_(self, other):
        return ("is", other)

    def asc(self):
        return self

    def desc(self):
        return self


class _QueryStub:
    def __init__(self, items):
        self.items = list(items)
        self.conditions = []

    def filter(self, *conditions):
        self.conditions.extend(conditions)
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return list(self.items)


class _FinancialScheduleStub:
    company_id = _Column()
    deleted_at = _Column()
    status = _Column()
    next_due_date = _Column()
    id = _Column()


def test_list_schedules_applies_tenant_and_due_date_range(monkeypatch):
    query = _QueryStub([type("Schedule", (), {"id": 77})()])
    _FinancialScheduleStub.query = query

    monkeypatch.setattr(schedule_module, "FinancialSchedule", _FinancialScheduleStub)
    monkeypatch.setattr(schedule_module.FinancialService, "_ensure_company_scope", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        FinancialScheduleService,
        "_build_counterparty_name_lookup",
        lambda **_kwargs: {},
    )
    monkeypatch.setattr(
        FinancialScheduleService,
        "_serialize_schedule",
        lambda item, **_kwargs: {"id": item.id},
    )

    result, error = FinancialScheduleService.list_schedules(
        company_id=9,
        allowed_company_ids=[9],
        due_date_from=date(2026, 8, 1),
        due_date_to=date(2026, 8, 31),
    )

    assert error is None
    assert result == [{"id": 77}]
    assert ("eq", 9) in query.conditions
    assert ("is", None) in query.conditions
    assert ("ge", date(2026, 8, 1)) in query.conditions
    assert ("le", date(2026, 8, 31)) in query.conditions


def test_api_and_ui_expose_due_date_filter_contract():
    project_root = Path(__file__).resolve().parents[2]
    resource_source = (project_root / "app32" / "api" / "resources" / "financial.py").read_text(encoding="utf-8")
    ui_source = (project_root / "static" / "js" / "financial_schedules_list.js").read_text(encoding="utf-8")

    assert 'due_date_from=_get_optional_iso_date_arg("due_date_from")' in resource_source
    assert 'due_date_to=_get_optional_iso_date_arg("due_date_to")' in resource_source
    assert "restoreFiltersFromUrl()" in ui_source
    assert "applyCurrentMonthDueDateRange()" in ui_source
    assert "scheduleParams.set('due_date_from', dueDateFrom)" in ui_source
    assert "scheduleParams.set('due_date_to', dueDateTo)" in ui_source
