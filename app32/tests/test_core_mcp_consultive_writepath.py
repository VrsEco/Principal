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
