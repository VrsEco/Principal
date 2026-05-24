import os
import sys
from datetime import date
from types import SimpleNamespace

from sqlalchemy import true

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import work_journey_sync


class _Expression:
    def __eq__(self, _value):
        return true()

    def __lt__(self, _value):
        return true()

    def between(self, _start, _end):
        return true()

    def in_(self, _values):
        return true()

    def isnot(self, _value):
        return true()


class _RelationshipExpression:
    def has(self, **_kwargs):
        return true()


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []

    def filter(self, *conditions):
        self.filters.extend(conditions)
        return self

    def all(self):
        return self.rows


def test_sync_project_tasks_reconciles_completed_link_with_canonical_code(monkeypatch):
    linked_items_query = _FakeQuery([SimpleNamespace(source_id=238)])
    source_tasks_query = _FakeQuery(
        [
            SimpleNamespace(
                id=238,
                employee_id=None,
                project_id=32,
                project=SimpleNamespace(code="AA.J.2", name="Comercial Versus"),
                code="AA.J.2.1",
                what="Wagner - Cliente de Imóveis",
                how=None,
                due_date=date(2026, 3, 19),
                estimated_hours=0,
                worked_hours=0,
                priority="normal",
                stage="completed",
                status="completed",
            )
        ]
    )
    captured = {}

    monkeypatch.setattr(
        work_journey_sync,
        "WorkJourneyItem",
        SimpleNamespace(
            query=linked_items_query,
            company_id=_Expression(),
            employee_id=_Expression(),
            item_type=_Expression(),
            source_id=_Expression(),
        ),
    )
    monkeypatch.setattr(
        work_journey_sync,
        "ProjectTask",
        SimpleNamespace(
            query=source_tasks_query,
            employee_id=_Expression(),
            project=_RelationshipExpression(),
            due_date=_Expression(),
            stage=_Expression(),
            id=_Expression(),
        ),
    )
    monkeypatch.setattr(work_journey_sync, "current_manual_assignment", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(work_journey_sync, "upsert_source_item", lambda **kwargs: captured.update(kwargs))

    work_journey_sync.sync_project_tasks(9, 23, date(2026, 5, 24), date(2026, 5, 30))

    assert captured["source_id"] == 238
    assert captured["employee_id"] == 23
    assert captured["status"] == "completed"
    assert captured["metadata"]["source_code"] == "AA.J.2.1"
    assert captured["metadata"]["project_code"] == "AA.J.2"
    assert captured["metadata"]["source_url"] == "/projects/32/manage?activity_id=238&from=work-journey"
