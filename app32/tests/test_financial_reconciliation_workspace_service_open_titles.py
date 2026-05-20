from datetime import date
from types import SimpleNamespace

import services.financial_reconciliation_workspace_service as workspace_module
from services.financial_reconciliation_workspace_service import FinancialReconciliationWorkspaceService


class _Column:
    def __init__(self, name):
        self.name = name

    def in_(self, values):
        return ("in", self.name, tuple(values))

    def is_(self, value):
        return ("is", self.name, value)

    def __ge__(self, value):
        return ("ge", self.name, value)

    def __le__(self, value):
        return ("le", self.name, value)

    def asc(self):
        return ("asc", self.name)

    def desc(self):
        return ("desc", self.name)


class _RecordingQuery:
    def __init__(self, items):
        self.items = items
        self.filters = []

    def filter(self, *criteria):
        self.filters.extend(criteria)
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.items)


def _install_entry_model(monkeypatch, query):
    class _FakeFinancialEntry:
        company_id = _Column("company_id")
        deleted_at = _Column("deleted_at")
        entry_type = _Column("entry_type")
        status = _Column("status")
        due_date = _Column("due_date")
        competence_date = _Column("competence_date")
        id = _Column("id")

    _FakeFinancialEntry.query = query
    monkeypatch.setattr(workspace_module, "FinancialEntry", _FakeFinancialEntry)


def test_load_open_titles_keeps_scheduled_entries_and_positive_remaining_balance(monkeypatch):
    scheduled_entry = SimpleNamespace(id=11, status="scheduled", remaining_marker="keep")
    zero_balance_entry = SimpleNamespace(id=12, status="posted", remaining_marker="drop")
    query = _RecordingQuery([scheduled_entry, zero_balance_entry])
    _install_entry_model(monkeypatch, query)
    monkeypatch.setattr(
        workspace_module.FinancialReconciliationWorkspaceService,
        "_entry_remaining_amount",
        lambda entry: 100 if entry.remaining_marker == "keep" else 0,
    )

    result = FinancialReconciliationWorkspaceService._load_open_titles(
        company_id=7,
        rows=[],
        due_date_from=date(2026, 5, 1),
        due_date_to=date(2026, 5, 31),
    )

    assert [item.id for item in result] == [11]
    assert ("in", "status", ("scheduled", "posted", "partially_settled")) in query.filters
    assert ("ge", "due_date", date(2026, 5, 1)) in query.filters
    assert ("le", "due_date", date(2026, 5, 31)) in query.filters


def test_load_open_titles_does_not_apply_row_date_or_nature_restrictions(monkeypatch):
    query = _RecordingQuery([SimpleNamespace(id=21, remaining_marker="keep")])
    _install_entry_model(monkeypatch, query)
    monkeypatch.setattr(
        workspace_module.FinancialReconciliationWorkspaceService,
        "_entry_remaining_amount",
        lambda entry: 50,
    )

    rows = [
        SimpleNamespace(occurred_on=date(2026, 5, 18), due_date=date(2026, 5, 20), movement_nature="debit"),
        SimpleNamespace(occurred_on=date(2026, 5, 19), due_date=None, movement_nature="credit"),
    ]

    FinancialReconciliationWorkspaceService._load_open_titles(
        company_id=1,
        rows=rows,
    )

    assert all(not (isinstance(item, tuple) and len(item) > 1 and item[1] == "movement_nature") for item in query.filters)
    assert all(date(2026, 5, 18) not in item for item in query.filters if isinstance(item, tuple))
    assert all(date(2026, 5, 19) not in item for item in query.filters if isinstance(item, tuple))
    assert all(date(2026, 5, 20) not in item for item in query.filters if isinstance(item, tuple))
