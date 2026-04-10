from __future__ import annotations

from types import SimpleNamespace

from src.intelligence import tools as tools_module
from src.intelligence.tools_domains import process_ops


class _FakeQuery:
    def __init__(self, value=None):
        self.value = value
        self.last_filter_kwargs = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        return self

    def first(self):
        return self.value

    def all(self):
        return self.value or []


def test_create_macro_process_blocks_area_from_other_company(monkeypatch) -> None:
    area_query = _FakeQuery(None)
    monkeypatch.setattr(process_ops, "get_active_company_id", lambda: 12)
    monkeypatch.setattr("models.process.ProcessArea", SimpleNamespace(query=area_query))
    monkeypatch.setattr(process_ops.db.session, "rollback", lambda: None)

    result = process_ops.create_macro_process(area_id=99, name="Atendimento")

    assert "Área de processo não encontrada" in result
    assert area_query.last_filter_kwargs == {"id": 99, "company_id": 12}


def test_create_process_blocks_macro_from_other_company(monkeypatch) -> None:
    macro_query = _FakeQuery(None)
    monkeypatch.setattr(process_ops, "get_active_company_id", lambda: 12)
    monkeypatch.setattr("models.process.MacroProcess", SimpleNamespace(query=macro_query))
    monkeypatch.setattr(process_ops.db.session, "rollback", lambda: None)

    result = process_ops.create_process(macro_id=77, name="Executar")

    assert "Macroprocesso não encontrado" in result
    assert macro_query.last_filter_kwargs == {"id": 77, "company_id": 12}


def test_list_process_hierarchy_blocks_explicit_foreign_company(monkeypatch) -> None:
    monkeypatch.setattr(process_ops, "get_active_company_id", lambda: 12)

    result = process_ops.list_process_hierarchy(company_id=13)

    assert "não pertence ao contexto" in result


def test_tools_process_wrappers_delegate_to_domain(monkeypatch) -> None:
    called = {}

    def _fake_list(*, company_id=None):
        called["company_id"] = company_id
        return "ok"

    monkeypatch.setattr(tools_module.process_ops_domain, "list_process_hierarchy", _fake_list)

    assert tools_module.list_process_hierarchy.func(company_id=12) == "ok"
    assert called == {"company_id": 12}
