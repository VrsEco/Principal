import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services import process_sipoc_service


class _FakePublishedQuery:
    def __init__(self, row):
        self.row = row
        self.filter_by_kwargs = None
        self.order_by_args = ()

    def filter_by(self, **kwargs):
        self.filter_by_kwargs = kwargs
        return self

    def order_by(self, *args):
        self.order_by_args = args
        return self

    def first(self):
        return self.row


def test_snapshot_gaps_are_suggestions_and_do_not_block_publication(monkeypatch):
    snapshot = SimpleNamespace(start_boundary=None, end_boundary="", id=91)
    monkeypatch.setattr(
        process_sipoc_service,
        "snapshot_lane_counts",
        lambda current_snapshot: {
            "supplier": 0,
            "input": 0,
            "process": 2,
            "output": 0,
            "customer": 0,
        },
    )

    suggestions = process_sipoc_service.get_publication_suggestions(snapshot)

    assert process_sipoc_service.validate_snapshot_for_publish(snapshot) == []
    assert any("início do processo" in suggestion for suggestion in suggestions)
    assert any("3 ou mais atividades" in suggestion for suggestion in suggestions)


def test_valid_structure_does_not_generate_suggestions(monkeypatch):
    snapshot = SimpleNamespace(start_boundary="Recebimento da demanda", end_boundary="Entrega ao cliente", id=92)
    monkeypatch.setattr(
        process_sipoc_service,
        "snapshot_lane_counts",
        lambda current_snapshot: {
            "supplier": 1,
            "input": 1,
            "process": 3,
            "output": 1,
            "customer": 1,
        },
    )

    suggestions = process_sipoc_service.get_publication_suggestions(snapshot)

    assert suggestions == []


def test_build_book_sipoc_context_returns_latest_published_snapshot(monkeypatch):
    published_snapshot = SimpleNamespace(id=15, version=3)
    fake_query = _FakePublishedQuery(published_snapshot)

    monkeypatch.setattr(
        process_sipoc_service,
        "ProcessSipocSnapshot",
        SimpleNamespace(
            query=fake_query,
            version=SimpleNamespace(desc=lambda: ("desc", "version")),
            id=SimpleNamespace(desc=lambda: ("desc", "id")),
        ),
    )
    monkeypatch.setattr(
        process_sipoc_service,
        "serialize_snapshot",
        lambda snapshot: {"id": snapshot.id, "version": snapshot.version, "status": "published"},
    )

    payload = process_sipoc_service.build_book_sipoc_context(process_id=7, company_id=3)

    assert payload == {"id": 15, "version": 3, "status": "published"}
    assert fake_query.filter_by_kwargs == {"process_id": 7, "company_id": 3, "status": "published"}
    assert fake_query.order_by_args == (("desc", "version"), ("desc", "id"))
