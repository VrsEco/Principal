from types import SimpleNamespace

import services.financial_reconciliation_workspace_service as workspace_module
from services.financial_reconciliation_workspace_service import FinancialReconciliationWorkspaceService


class _Column:
    def __eq__(self, other):
        return ("eq", other)

    def is_(self, other):
        return ("is", other)

    def in_(self, values):
        return ("in", tuple(values))

    def asc(self):
        return self

    def desc(self):
        return self

    def between(self, start, end):
        return ("between", start, end)

    def __ge__(self, other):
        return ("ge", other)

    def __le__(self, other):
        return ("le", other)


class _RecordingQuery:
    def __init__(self):
        self.filters = []

    def filter(self, *args, **kwargs):
        self.filters.extend(args)
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return []


class _FakeDateExpr:
    def __init__(self, label):
        self.label = label

    def between(self, start, end):
        return ("between", self.label, start, end)

    def asc(self):
        return self

    def desc(self):
        return self


def test_load_open_titles_accepts_scheduled_entries(monkeypatch):
    query = _RecordingQuery()

    class _FakeFinancialEntry:
        company_id = _Column()
        deleted_at = _Column()
        entry_type = _Column()
        status = _Column()
        occurred_on = _Column()
        due_date = _Column()
        competence_date = _Column()
        movement_nature = _Column()
        id = _Column()

    _FakeFinancialEntry.query = query

    monkeypatch.setattr(workspace_module, "FinancialEntry", _FakeFinancialEntry)

    FinancialReconciliationWorkspaceService._load_open_titles(
        company_id=9,
        rows=[],
    )

    assert ("in", ("scheduled", "posted", "partially_settled")) in query.filters


def test_load_open_titles_skips_reference_window_when_due_date_filter_is_explicit(monkeypatch):
    query = _RecordingQuery()

    class _FakeFinancialEntry:
        company_id = _Column()
        deleted_at = _Column()
        entry_type = _Column()
        status = _Column()
        occurred_on = _FakeDateExpr("occurred_on")
        due_date = _Column()
        competence_date = _FakeDateExpr("competence_date")
        movement_nature = _Column()
        id = _Column()

    _FakeFinancialEntry.query = query

    monkeypatch.setattr(workspace_module, "FinancialEntry", _FakeFinancialEntry)
    monkeypatch.setattr(workspace_module, "db", SimpleNamespace(or_=lambda *args: ("or", args)))

    FinancialReconciliationWorkspaceService._load_open_titles(
        company_id=9,
        rows=[SimpleNamespace(occurred_on=None, due_date="2026-05-01", movement_nature="debit")],
        due_date_from="2026-01-01",
    )

    assert not any(
        isinstance(item, tuple) and item and item[0] == "or"
        for item in query.filters
    )
