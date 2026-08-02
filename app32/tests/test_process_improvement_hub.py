from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import src.core.mcp_process_improvement_tools as tools_module
import src.core.mcp_surface_registry as registry
from src.core.mcp_runtime import MCPExecutionContext


ROOT = Path(__file__).resolve().parents[1]


class DummyMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, name=None):
        def decorator(function):
            self.tools[name or function.__name__] = function
            return function

        return decorator


def test_improvement_hub_replaces_technical_form_with_short_intake():
    template = (ROOT / "templates" / "modules" / "processes" / "bpms_analysis.html").read_text(encoding="utf-8")

    assert "Central de Melhorias e Diagnósticos" in template
    assert "problem_statement" in template
    assert "expected_result" in template
    assert "Enviar para o Squad Cliente" in template
    assert "improvement-flow" in template
    assert "improvement-type-grid" in template
    assert "improvement-history" in template
    assert "AS-IS" not in template
    assert "requires_architect" not in template


def test_improvement_request_route_uses_tenant_scoped_service():
    routes = (ROOT / "api" / "routes" / "processes.py").read_text(encoding="utf-8")

    assert "/companies/<int:company_id>/bpms-analysis/request" in routes
    assert "create_improvement_request(" in routes
    assert "company_id=company_id" in routes


def test_process_improvement_mcp_tools_require_human_gate_for_write(monkeypatch):
    mcp = DummyMCP()
    tools_module.register_process_improvement_tools(mcp)

    assert {
        "list_process_improvement_requests_tool",
        "get_process_improvement_analysis_context_tool",
        "submit_process_improvement_analysis_tool",
    }.issubset(mcp.tools)

    monkeypatch.setattr(tools_module, "get_http_actor_role", lambda: "cliente")
    monkeypatch.setattr(tools_module, "get_http_request_context", lambda: {"user_id": 77, "company_id": 9})
    monkeypatch.setattr(
        tools_module,
        "submit_squad_analysis",
        lambda **kwargs: SimpleNamespace(to_dict=lambda: {"id": kwargs["analysis_id"], "status": "ready"}),
    )

    denied = mcp.tools["submit_process_improvement_analysis_tool"](
        company_id=9,
        analysis_id=12,
        payload={"diagnosis": "Diagnóstico", "recommendations": "Recomendação"},
    )
    allowed = mcp.tools["submit_process_improvement_analysis_tool"](
        company_id=9,
        analysis_id=12,
        payload={"diagnosis": "Diagnóstico", "recommendations": "Recomendação"},
        human_gate_confirmed=True,
    )

    assert denied["error"]["code"] == "process_improvement_forbidden"
    assert allowed["data"] == {"id": 12, "status": "ready"}
    assert allowed["meta"]["company_id"] == 9
    assert allowed["meta"]["human_gate_required"] is True


def test_process_improvement_tools_are_registered_and_tenant_scoped():
    catalog = (ROOT / "src" / "intelligence" / "tool_catalog.py").read_text(encoding="utf-8")
    capabilities = (ROOT / "src" / "intelligence" / "tooling" / "capabilities.py").read_text(encoding="utf-8")
    service = (ROOT / "services" / "process_bpms_analysis_service.py").read_text(encoding="utf-8")

    assert "register_process_improvement_tools" in catalog
    assert '"submit_process_improvement_analysis_tool"' in capabilities
    assert "get_bpms_analysis(company_id, analysis_id)" in service
    assert "Process.query.filter_by(company_id=company_id" in service


def test_process_improvement_tools_are_visible_to_squad_cliente_user_surface(monkeypatch):
    monkeypatch.setattr(
        registry,
        "resolve_mcp_execution_context",
        lambda payload=None: MCPExecutionContext(
            user_id=77,
            company_id=9,
            employee_id=None,
            role="administrador",
            channel="claude_remote",
            thread_id=None,
            accessible_company_ids=(9,),
            permissions=("processes.ai_assistant.view", "processes.ai_assistant.execute"),
            metadata={
                "surface": "user",
                "runtime_profile": "squad_cliente",
                "actor_type": "client_agent",
                "mcp_enabled": True,
                "training_completed": True,
            },
        ),
    )

    manifest = registry.get_surface_manifest("user", domain="processes", include_tools=True)
    names = {item["name"] for item in manifest["tools"]}

    assert "list_process_improvement_requests_tool" in names
    assert "get_process_improvement_analysis_context_tool" in names
    assert "submit_process_improvement_analysis_tool" in names
