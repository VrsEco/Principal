from types import ModuleType, SimpleNamespace
import sys

import pytest

from src.core.mcp_internal_audit_tools import register_internal_audit_mcp_tools
from src.intelligence.security.tenant_rbac import validate_permission, resolve_identity_context
from src.intelligence.taxonomy import CANONICAL_TOOL_DOMAINS
from src.intelligence.tooling.capabilities import ToolScope, build_capability_index


class _FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorate(func):
            self.tools[kwargs.get("name") or func.__name__] = func
            return func
        if args and callable(args[0]):
            return decorate(args[0])
        return decorate


def _service_module(monkeypatch):
    calls = []

    class Service:
        @staticmethod
        def summary(company_id):
            calls.append(("summary", company_id))
            return {"open_points_count": 2}

        @staticmethod
        def list_points(company_id, status=None):
            calls.append(("points", company_id, status))
            return [{"company_id": company_id, "id": index} for index in range(130)]

        @staticmethod
        def list_findings(company_id, status=None):
            calls.append(("findings", company_id, status))
            return [{"company_id": company_id, "id": index} for index in range(3)]

    module = ModuleType("services.internal_audit_service")
    module.InternalAuditService = Service
    monkeypatch.setitem(sys.modules, "services.internal_audit_service", module)
    return calls


def test_internal_audit_mcp_reads_are_tenant_scoped_and_bounded(monkeypatch):
    calls = _service_module(monkeypatch)
    mcp = _FakeMCP()
    register_internal_audit_mcp_tools(mcp)

    assert mcp.tools["get_internal_audit_summary"](9) == {
        "company_id": 9,
        "summary": {"open_points_count": 2},
    }
    points = mcp.tools["list_internal_audit_points"](9, status="open", limit=100)
    assert points["company_id"] == 9
    assert points["returned"] == 100
    assert len(points["items"]) == 100
    assert all(item["company_id"] == 9 for item in points["items"])
    findings = mcp.tools["list_internal_audit_findings"](9, status="open", limit=50)
    assert findings["returned"] == 3
    assert calls == [("summary", 9), ("points", 9, "open"), ("findings", 9, "open")]


@pytest.mark.parametrize("limit", [0, 101, True, "10"])
def test_internal_audit_mcp_rejects_unbounded_or_invalid_limit(monkeypatch, limit):
    _service_module(monkeypatch)
    mcp = _FakeMCP()
    register_internal_audit_mcp_tools(mcp)
    with pytest.raises(ValueError):
        mcp.tools["list_internal_audit_points"](9, limit=limit)


def test_audit_domain_capabilities_are_analytics_admin_and_role_checked():
    names = {
        "get_internal_audit_summary",
        "list_internal_audit_points",
        "list_internal_audit_findings",
    }
    assert "audit" in CANONICAL_TOOL_DOMAINS
    registry = build_capability_index([SimpleNamespace(name=name, description=name) for name in names])
    for name in names:
        capability = registry[name]
        assert capability.domain == "audit"
        assert set(capability.scopes) == {ToolScope.MCP_ANALYTICS.value, ToolScope.MCP_ADMIN.value}
        assert capability.required_context == ("company",)

    admin = resolve_identity_context({"role": "administrador"})
    client = resolve_identity_context({"role": "cliente"})
    assert validate_permission(admin, domain="audit", action="read").allowed is True
    assert validate_permission(client, domain="audit", action="read").allowed is False
