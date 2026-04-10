from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import src.core.mcp_surface_registry as registry


@dataclass
class _FakeTool:
    name: str
    description: str
    result: object

    def invoke(self, payload):
        return {"tool": self.name, "payload": payload, "result": self.result}


@dataclass
class _Capability:
    name: str
    domain: str
    description: str
    scopes: list[str]
    risk: str
    permissions: list[str]
    human_gate: bool
    human_gate_reason: str | None
    tags: list[str]

    def to_dict(self):
        return {
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "scopes": list(self.scopes),
            "risk": self.risk,
            "permissions": list(self.permissions),
            "human_gate": self.human_gate,
            "human_gate_reason": self.human_gate_reason,
            "tags": list(self.tags),
        }


class _FakeMCP:
    def __init__(self):
        self.registered: dict[str, dict[str, object]] = {}

    def tool(self, name=None, description=None):
        def decorator(fn):
            tool_name = name or fn.__name__
            self.registered[tool_name] = {
                "description": description,
                "callable": fn,
            }
            return fn

        return decorator


class _FakeCatalog:
    def __init__(self):
        self.langchain_tools = (
            _FakeTool("process_read", "Lê processos", "process-ok"),
            _FakeTool("plan_read", "Lê estratégia", "plan-ok"),
            _FakeTool("company_diag", "Diagnóstico administrativo", "diag-ok"),
            _FakeTool("analytics_query", "Consulta analítica", "analytics-ok"),
            _FakeTool("ops_escalate", "Escala operação", "ops-ok"),
        )
        self.mcp_registrars = (self._register_shared_tools,)

    def get_langchain_tools(self):
        return list(self.langchain_tools)

    def get_capability_manifest(self, *, scope=None, domain=None, include_tools=True):
        allowed = self._filter_tools(scope=scope, domain=domain)
        manifest = {
            "summary": {"capabilities": len(allowed)},
            "domains": {},
            "scopes": {},
        }
        if include_tools:
            manifest["tools"] = [tool.to_dict() for tool in allowed]
        return manifest

    def _filter_tools(self, *, scope=None, domain=None):
        scope_values = None
        if scope is not None:
            if isinstance(scope, tuple):
                scope_values = set(scope)
            elif isinstance(scope, list):
                scope_values = set(scope)
            else:
                scope_values = {scope}

        result = []
        for tool in self._capabilities():
            if scope_values is not None and not scope_values.intersection(tool["scopes"]):
                continue
            if domain is not None and tool["domain"] != domain:
                continue
            result.append(_Capability(**tool))
        return result

    def _capabilities(self):
        return [
            {
                "name": "process_read",
                "domain": "processes",
                "description": "Lê processos",
                "scopes": ["mcp_user"],
                "risk": "low",
                "permissions": [],
                "human_gate": False,
                "human_gate_reason": None,
                "tags": [],
            },
            {
                "name": "plan_read",
                "domain": "strategy",
                "description": "Lê estratégia",
                "scopes": ["mcp_user", "mcp_admin"],
                "risk": "low",
                "permissions": [],
                "human_gate": False,
                "human_gate_reason": None,
                "tags": [],
            },
            {
                "name": "company_diag",
                "domain": "governance",
                "description": "Diagnóstico administrativo",
                "scopes": ["mcp_admin"],
                "risk": "high",
                "permissions": [],
                "human_gate": True,
                "human_gate_reason": "admin",
                "tags": [],
            },
            {
                "name": "analytics_query",
                "domain": "analytics",
                "description": "Consulta analítica",
                "scopes": ["mcp_analytics"],
                "risk": "high",
                "permissions": [],
                "human_gate": True,
                "human_gate_reason": "analytics",
                "tags": [],
            },
            {
                "name": "ops_escalate",
                "domain": "operations",
                "description": "Escala operação",
                "scopes": ["mcp_ops"],
                "risk": "medium",
                "permissions": [],
                "human_gate": False,
                "human_gate_reason": None,
                "tags": [],
            },
        ]

    def _register_shared_tools(self, mcp):
        @mcp.tool(name="shared_surface_tool", description="Ferramenta compartilhada")
        def shared_surface_tool():
            return {"success": True}


def test_user_surface_exposes_only_user_scope_manifest_and_no_admin_diagnostics(monkeypatch):
    fake_catalog = _FakeCatalog()
    monkeypatch.setattr(registry, "catalog", fake_catalog)

    mcp = _FakeMCP()
    registry.register_user_mcp_tools(mcp)

    assert "process_read" in mcp.registered
    assert "plan_read" in mcp.registered
    assert "company_diag" not in mcp.registered
    assert "analytics_query" not in mcp.registered
    assert "ops_escalate" not in mcp.registered
    assert "get_system_health" not in mcp.registered
    assert "get_database_schema" not in mcp.registered
    assert "list_user_app32_capabilities" in mcp.registered

    manifest = mcp.registered["list_user_app32_capabilities"]["callable"]()
    tool_names = {tool["name"] for tool in manifest["tools"]}
    assert "process_read" in tool_names
    assert "plan_read" in tool_names
    assert "company_diag" not in tool_names
    assert "analytics_query" not in tool_names
    assert "ops_escalate" not in tool_names
    assert all("mcp_user" in tool["scopes"] for tool in manifest["tools"])


def test_admin_surface_exposes_only_admin_scope_and_diagnostics(monkeypatch):
    fake_catalog = _FakeCatalog()
    monkeypatch.setattr(registry, "catalog", fake_catalog)

    mcp = _FakeMCP()
    registry.register_admin_mcp_tools(mcp)

    assert "process_read" not in mcp.registered
    assert "plan_read" in mcp.registered
    assert "company_diag" in mcp.registered
    assert "analytics_query" not in mcp.registered
    assert "ops_escalate" not in mcp.registered
    assert "shared_surface_tool" in mcp.registered
    assert "list_admin_app32_capabilities" in mcp.registered
    assert "get_system_health" in mcp.registered
    assert "get_database_schema" in mcp.registered

    manifest = mcp.registered["list_admin_app32_capabilities"]["callable"]()
    tool_names = {tool["name"] for tool in manifest["tools"]}
    assert "process_read" not in tool_names
    assert "plan_read" in tool_names
    assert "company_diag" in tool_names
    assert "analytics_query" not in tool_names
    assert "ops_escalate" not in tool_names
    assert any("mcp_admin" in tool["scopes"] for tool in manifest["tools"])


def test_analytics_and_ops_surfaces_are_separated(monkeypatch):
    fake_catalog = _FakeCatalog()
    monkeypatch.setattr(registry, "catalog", fake_catalog)

    analytics_mcp = _FakeMCP()
    ops_mcp = _FakeMCP()

    registry.register_analytics_mcp_tools(analytics_mcp)
    registry.register_ops_mcp_tools(ops_mcp)

    assert "analytics_query" in analytics_mcp.registered
    assert "ops_escalate" not in analytics_mcp.registered
    assert "list_analytics_app32_capabilities" in analytics_mcp.registered
    analytics_manifest = analytics_mcp.registered["list_analytics_app32_capabilities"]["callable"]()
    assert {tool["name"] for tool in analytics_manifest["tools"]} == {"analytics_query"}

    assert "ops_escalate" in ops_mcp.registered
    assert "analytics_query" not in ops_mcp.registered
    assert "list_ops_app32_capabilities" in ops_mcp.registered
    ops_manifest = ops_mcp.registered["list_ops_app32_capabilities"]["callable"]()
    assert {tool["name"] for tool in ops_manifest["tools"]} == {"ops_escalate"}


def test_surface_scope_filter_is_explicit_and_safe():
    assert registry.get_surface_scope_filter("user") == ("mcp_user",)
    assert registry.get_surface_scope_filter("analytics") == ("mcp_analytics",)
    assert registry.get_surface_scope_filter("ops") == ("mcp_ops",)
    assert registry.get_surface_scope_filter("admin") == ("mcp_admin",)
