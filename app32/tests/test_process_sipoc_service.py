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


def test_validate_snapshot_for_publish_requires_boundaries_and_lanes(monkeypatch):
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

    errors = process_sipoc_service.validate_snapshot_for_publish(snapshot)

    assert "Preencha o início do processo." in errors
    assert "Preencha o fim do processo." in errors
    assert "Cadastre ao menos 1 fornecedor." in errors
    assert "Cadastre ao menos 1 entrada." in errors
    assert "Cadastre pelo menos 3 macroetapas no processo." in errors
    assert "Cadastre ao menos 1 saída." in errors
    assert "Cadastre ao menos 1 cliente." in errors


def test_validate_snapshot_for_publish_accepts_valid_minimum_structure(monkeypatch):
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

    errors = process_sipoc_service.validate_snapshot_for_publish(snapshot)

    assert errors == []


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
