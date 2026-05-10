from __future__ import annotations

from types import SimpleNamespace

from schemas.process import macro_process_schema
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


def test_create_process_area_blocks_explicit_foreign_company(monkeypatch) -> None:
    monkeypatch.setattr(process_ops, "get_active_company_id", lambda: 12)

    result = process_ops.create_process_area(name="Gestão", company_id=13)

    assert "não pertence ao contexto" in result


def test_tools_process_wrappers_delegate_to_domain(monkeypatch) -> None:
    called = {}

    def _fake_list(*, company_id=None):
        called["company_id"] = company_id
        return "ok"

    monkeypatch.setattr(tools_module.process_ops_domain, "list_process_hierarchy", _fake_list)

    assert tools_module.list_process_hierarchy.func(company_id=12) == "ok"
    assert called == {"company_id": 12}


def test_tools_process_mutation_wrappers_forward_company_id(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        tools_module.process_ops_domain,
        "create_process_area",
        lambda **kwargs: calls.append(("area", kwargs)) or "area-ok",
    )
    monkeypatch.setattr(
        tools_module.process_ops_domain,
        "create_macro_process",
        lambda **kwargs: calls.append(("macro", kwargs)) or "macro-ok",
    )
    monkeypatch.setattr(
        tools_module.process_ops_domain,
        "update_macro_process",
        lambda **kwargs: calls.append(("macro-update", kwargs)) or "macro-update-ok",
    )
    monkeypatch.setattr(
        tools_module.process_ops_domain,
        "create_process",
        lambda **kwargs: calls.append(("process", kwargs)) or "process-ok",
    )

    assert tools_module.create_process_area.func("Gestão", company_id=12) == "area-ok"
    assert tools_module.create_macro_process.func(10, "Planejamento", company_id=12, responsible="Fabiano") == "macro-ok"
    assert (
        tools_module.update_macro_process.func(
            33,
            responsible="Fabiano",
            description="Atualizado via MCP",
            order_index=5,
            company_id=12,
        )
        == "macro-update-ok"
    )
    assert tools_module.create_process.func(20, "Diagnóstico", company_id=12) == "process-ok"

    assert calls == [
        ("area", {"name": "Gestão", "description": None, "code": None, "company_id": 12}),
        (
            "macro",
            {
                "area_id": 10,
                "name": "Planejamento",
                "description": None,
                "order_index": 1,
                "company_id": 12,
                "responsible": "Fabiano",
            },
        ),
        (
            "macro-update",
            {
                "macro_id": 33,
                "name": None,
                "responsible": "Fabiano",
                "description": "Atualizado via MCP",
                "order_index": 5,
                "area_id": None,
                "company_id": 12,
            },
        ),
        (
            "process",
            {
                "macro_id": 20,
                "name": "Diagnóstico",
                "description": None,
                "responsible": None,
                "order_index": 1,
                "company_id": 12,
            },
        ),
    ]


def test_update_macro_process_blocks_foreign_company(monkeypatch) -> None:
    monkeypatch.setattr(process_ops, "get_active_company_id", lambda: 12)

    result = process_ops.update_macro_process(44, description="X", company_id=13)

    assert "não pertence ao contexto" in result


def test_update_macro_process_updates_owner_from_responsible(monkeypatch) -> None:
    macro = SimpleNamespace(
        id=44,
        company_id=12,
        area_id=5,
        order_index=2,
        code="AY.C.1.2",
        name="Financeiro",
        owner="Antigo",
        description="Anterior",
    )
    macro_query = _FakeQuery(macro)
    committed = {"ok": False}

    monkeypatch.setattr(process_ops, "get_active_company_id", lambda: 12)
    monkeypatch.setattr("models.process.MacroProcess", SimpleNamespace(query=macro_query))
    monkeypatch.setattr(process_ops, "_normalize_macro_owner_payload", lambda **kwargs: ("Fabiano", None))
    monkeypatch.setattr(process_ops, "_build_scope_reconciliation", lambda company_id: f"tenant {company_id}")
    monkeypatch.setattr("api.resources.process.generate_macro_code", lambda area_id, sequence: f"AY.C.{area_id}.{sequence}")
    monkeypatch.setattr(process_ops.db.session, "commit", lambda: committed.__setitem__("ok", True))
    monkeypatch.setattr(process_ops.db.session, "rollback", lambda: None)

    result = process_ops.update_macro_process(
        44,
        responsible="Fabiano",
        description="Novo texto",
        order_index=7,
        company_id=12,
    )

    assert committed["ok"] is True
    assert macro.owner == "Fabiano"
    assert macro.description == "Novo texto"
    assert macro.order_index == 7
    assert macro.code == "AY.C.5.7"
    assert "atualizado com sucesso" in result


def test_macro_process_schema_exposes_responsible_alias() -> None:
    payload = macro_process_schema.dump(
        SimpleNamespace(
            id=1,
            company_id=12,
            area_id=5,
            code="AY.C.1.2",
            name="Financeiro",
            owner="Fabiano",
            description="Macro",
            order_index=2,
            created_at=None,
            updated_at=None,
            area=None,
        )
    )

    assert payload["owner"] == "Fabiano"
    assert payload["responsible"] == "Fabiano"
