from __future__ import annotations

import inspect

import src.core.mcp_consultive_assisted_analysis_tools as tools_module


class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorator(fn):
            self.registered[kwargs.get("name") or fn.__name__] = fn
            return fn
        return decorator


def _register(monkeypatch):
    mcp = _FakeMCP()
    monkeypatch.setattr(
        tools_module,
        "get_http_request_context",
        lambda: {
            "user_id": 22,
            "fallback_role": "cliente",
            "runtime_profile": "squad_cliente",
            "company_id": 9,
        },
    )
    monkeypatch.setattr(tools_module, "get_http_actor_role", lambda default=None: "cliente")
    tools_module.register_consultive_assisted_analysis_tools(mcp)
    return mcp.registered


def test_client_assisted_analysis_requires_explicit_gate_and_uses_authenticated_user(monkeypatch):
    registered = _register(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        tools_module.ConsultiveAssistedAnalysisService,
        "register_assisted_analysis",
        lambda **kwargs: captured.update(kwargs) or {"id": 101},
    )

    denied = registered["consultive_register_assisted_analysis"](
        company_id=9,
        front_key="identity",
        payload={"summary": "Diagnóstico confirmado"},
    )
    allowed = registered["consultive_register_assisted_analysis"](
        company_id=9,
        front_key="identity",
        payload={"summary": "Diagnóstico confirmado"},
        human_gate_confirmed=True,
    )

    assert denied["success"] is False
    assert denied["error"]["code"] == "consultive_assisted_analysis_forbidden"
    assert allowed["success"] is True
    assert captured["company_id"] == 9
    assert captured["user_id"] == 22


def test_assisted_analysis_exposes_and_merges_methodological_contract(monkeypatch):
    registered = _register(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        tools_module.ConsultiveAssistedAnalysisService,
        "register_assisted_analysis",
        lambda **kwargs: captured.update(kwargs) or {"id": 102},
    )

    result = registered["consultive_register_assisted_analysis"](
        company_id=9,
        front_key="identity",
        payload={
            "analysis_type": "technical_test",
            "diagnosis": "Diagnóstico confirmado",
            "benchmarks": "Benchmark documentado",
            "risks": "Riscos documentados",
            "recommendations": "Recomendações documentadas",
        },
        human_gate_confirmed=True,
        analysis_type="methodological",
        subphase_key="mission",
        human_evidence=["Entrevista confirmada pelo gestor"],
        internal_evidence=["MVV e processos lidos via MCP"],
    )

    assert result["success"] is True
    assert captured["payload"]["analysis_type"] == "methodological"
    assert captured["payload"]["subphase_key"] == "mission"
    assert captured["payload"]["human_evidence"] == ["Entrevista confirmada pelo gestor"]
    assert captured["payload"]["internal_evidence"] == ["MVV e processos lidos via MCP"]
    assert captured["payload"]["diagnosis"] == "Diagnóstico confirmado"


def test_client_can_validate_only_own_squad(monkeypatch):
    registered = _register(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        tools_module.ConsultiveAssistedAnalysisService,
        "register_squad_validation",
        lambda **kwargs: captured.update(kwargs) or {"id": 202},
    )

    denied = registered["consultive_register_squad_validation"](
        company_id=9,
        analysis_id=101,
        squad="versus",
        status="validated",
        human_gate_confirmed=True,
    )
    allowed = registered["consultive_register_squad_validation"](
        company_id=9,
        analysis_id=101,
        squad="client",
        status="validated",
        human_gate_confirmed=True,
    )

    assert denied["success"] is False
    assert denied["error"]["code"] == "consultive_assisted_analysis_forbidden"
    assert allowed["success"] is True
    assert captured["squad"] == "client"
    assert captured["user_id"] == 22


def test_authenticated_user_cannot_be_overridden(monkeypatch):
    registered = _register(monkeypatch)
    denied = registered["consultive_register_assisted_analysis"](
        company_id=9,
        front_key="identity",
        payload={"summary": "Diagnóstico confirmado"},
        human_gate_confirmed=True,
        user_id=999,
    )

    assert denied["success"] is False
    assert denied["error"]["code"] == "consultive_assisted_analysis_forbidden"


def test_gated_write_schemas_expose_explicit_confirmation(monkeypatch):
    registered = _register(monkeypatch)

    for tool_name in (
        "consultive_register_assisted_analysis",
        "consultive_register_squad_validation",
        "consultive_register_consultant_decision",
    ):
        signature = inspect.signature(registered[tool_name])
        assert signature.parameters["human_gate_confirmed"].default is False

    assisted_signature = inspect.signature(registered["consultive_register_assisted_analysis"])
    for field in (
        "analysis_type",
        "subphase_key",
        "human_evidence",
        "internal_evidence",
        "benchmark_not_applicable_reason",
    ):
        assert field in assisted_signature.parameters



def test_methodological_arguments_generate_explicit_json_schema(monkeypatch):
    from pydantic import TypeAdapter
    from typing import get_type_hints

    registered = _register(monkeypatch)
    hints = get_type_hints(registered["consultive_register_assisted_analysis"])

    analysis_schema = TypeAdapter(hints["analysis_type"]).json_schema()
    human_evidence_schema = TypeAdapter(hints["human_evidence"]).json_schema()
    internal_evidence_schema = TypeAdapter(hints["internal_evidence"]).json_schema()

    assert analysis_schema["anyOf"][0]["enum"] == ["methodological", "technical_test"]
    assert human_evidence_schema["anyOf"][0]["items"]["type"] == "string"
    assert internal_evidence_schema["anyOf"][0]["items"]["type"] == "string"
