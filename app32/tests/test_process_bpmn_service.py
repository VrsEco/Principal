from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services import process_bpmn_service


class _FakeDiagramQuery:
    def filter_by(self, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return None

    def filter(self, *_args, **_kwargs):
        return self

    def update(self, *_args, **_kwargs):
        return 0


class _FakeComparable:
    def __eq__(self, other):
        return other

    def desc(self):
        return self


class _FakeNoAutoflush:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self):
        self.added: list[object] = []
        self.committed = False
        self.flushed = False
        self.no_autoflush = _FakeNoAutoflush()

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def flush(self):
        self.flushed = True
        if self.added and getattr(self.added[-1], "id", None) is None:
            self.added[-1].id = 321

    def query(self, _field):
        session = self

        class _FakeCompanyQuery:
            def filter(self, *_args, **_kwargs):
                return self

            def scalar(self):
                if session.added:
                    diagram = session.added[-1]
                    if getattr(diagram, "bpmn_xml", None) is None:
                        raise AssertionError("autoflush inseguro: bpmn_xml ainda estava nulo antes da query da empresa")
                    if getattr(diagram, "name", None) is None:
                        raise AssertionError("autoflush inseguro: name ainda estava nulo antes da query da empresa")
                return "Empresa Teste"

        return _FakeCompanyQuery()


class _FakeDiagram:
    query = _FakeDiagramQuery()
    id = _FakeComparable()
    updated_at = _FakeComparable()
    version = _FakeComparable()

    def __init__(self, **kwargs):
        self.id = None
        self.company_id = kwargs.get("company_id")
        self.process_id = kwargs.get("process_id")
        self.version = kwargs.get("version")
        self.created_by_user_id = kwargs.get("created_by_user_id")
        self.status = kwargs.get("status")
        self.name = kwargs.get("name")
        self.bpmn_xml = kwargs.get("bpmn_xml")
        self.svg_snapshot = kwargs.get("svg_snapshot")
        self.png_snapshot = kwargs.get("png_snapshot")
        self.metadata_json = kwargs.get("metadata_json")
        self.updated_by_user_id = kwargs.get("updated_by_user_id")
        self.updated_at = kwargs.get("updated_at")
        self.published_at = kwargs.get("published_at")


def test_upsert_process_bpmn_diagram_sets_required_fields_before_company_lookup(monkeypatch):
    fake_session = _FakeSession()

    monkeypatch.setattr(process_bpmn_service, "ProcessBpmnDiagram", _FakeDiagram)
    monkeypatch.setattr(process_bpmn_service, "_next_version", lambda process_id, company_id: 1)
    monkeypatch.setattr(process_bpmn_service, "sync_bpmn_participant_metadata", lambda *args, **kwargs: "<bpmn:definitions id='synced' />")
    monkeypatch.setattr(
        process_bpmn_service,
        "db",
        SimpleNamespace(session=fake_session),
    )
    monkeypatch.setattr(
        process_bpmn_service,
        "Company",
        SimpleNamespace(name="name", id=_FakeComparable()),
    )

    process = SimpleNamespace(id=526, company_id=10, code="M1.C.2.1.1", name="Tráfego Pago")
    payload = {
        "status": "draft",
        "name": "Tráfego Pago",
        "bpmn_xml": "<bpmn:definitions xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL' id='Defs_1' />",
        "svg_snapshot": None,
        "metadata_json": {"source": "test"},
    }

    saved = process_bpmn_service.upsert_process_bpmn_diagram(
        process=process,
        payload=payload,
        user_id=9,
    )

    assert fake_session.committed is True
    assert saved.company_id == 10
    assert saved.process_id == 526
    assert saved.name == "Tráfego Pago"
    assert saved.bpmn_xml == "<bpmn:definitions id='synced' />"


def test_upsert_new_published_diagram_flushes_before_archiving_previous_versions(monkeypatch):
    fake_session = _FakeSession()

    monkeypatch.setattr(process_bpmn_service, "ProcessBpmnDiagram", _FakeDiagram)
    monkeypatch.setattr(process_bpmn_service, "_next_version", lambda process_id, company_id: 2)
    monkeypatch.setattr(
        process_bpmn_service,
        "sync_bpmn_participant_metadata",
        lambda xml, **_kwargs: xml,
    )
    monkeypatch.setattr(process_bpmn_service, "db", SimpleNamespace(session=fake_session))
    monkeypatch.setattr(
        process_bpmn_service,
        "Company",
        SimpleNamespace(name="name", id=_FakeComparable()),
    )

    process = SimpleNamespace(id=2, company_id=9, code="AA.C.1.1.2", name="Identidade Organizacional")
    saved = process_bpmn_service.upsert_process_bpmn_diagram(
        process=process,
        payload={
            "status": "published",
            "name": process.name,
            "bpmn_xml": "<bpmn:definitions xmlns:bpmn='http://www.omg.org/spec/BPMN/20100524/MODEL' id='Defs_2' />",
            "metadata_json": {},
        },
        user_id=3,
    )

    assert fake_session.flushed is True
    assert saved.id == 321
    assert saved.status == "published"
    assert fake_session.committed is True
