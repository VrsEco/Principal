import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services import macro_process_sipoc_service


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
    snapshot = SimpleNamespace(start_boundary=None, end_boundary="", id=201)
    monkeypatch.setattr(
        macro_process_sipoc_service,
        "snapshot_lane_counts",
        lambda current_snapshot: {
            "supplier": 0,
            "input": 0,
            "process": 2,
            "output": 0,
            "customer": 0,
        },
    )

    errors = macro_process_sipoc_service.validate_snapshot_for_publish(snapshot)

    assert "Preencha o início do macroprocesso." in errors
    assert "Preencha o fim do macroprocesso." in errors
    assert "Cadastre pelo menos 3 processos filhos ou grandes etapas no macroprocesso." in errors


def test_default_title_uses_macro_code_when_available():
    macro = SimpleNamespace(code="MP.01", name="Gestão Comercial")
    title = macro_process_sipoc_service._default_title(macro)
    assert title == "SIPOC - MP.01 - Gestão Comercial"
