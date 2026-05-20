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
