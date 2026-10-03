"""Read-only diagnostic harness; in-memory doubles, no real application or DB."""
import ast
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, has_app_context

from services.financial_reconciliation_diagnostic_service import FinancialReconciliationDiagnosticService as Service
from src.core.mcp_financial_tools import register_financial_mcp_tools
from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy
from src.intelligence.tooling.capabilities import infer_tool_capability

NAMES = (
    "list_financial_reconciliation_batches",
    "get_financial_reconciliation_batch",
    "get_financial_reconciliation_settlement",
)


@pytest.fixture
def imports(monkeypatch):
    data = {
        "batch": {"id": 12, "company_id": 9, "batch_code": "REC-TEST"},
        "rows": [{"id": 9577}, {"id": 9581}, {"id": 9584}],
        "matches": [
            {"id": 1, "import_row_id": 9577, "financial_entry_id": 2673,
             "match_status": "confirmed", "metadata_json": {"financial_settlement_id": 2752}},
            {"id": 2, "import_row_id": 9577, "financial_entry_id": 100,
             "match_status": "suggested", "metadata_json": {}},
            {"id": 3, "import_row_id": 9577, "financial_entry_id": 101,
             "match_status": "rejected", "metadata_json": {"reconciliation_cancelled": True}},
            {"id": 4, "import_row_id": 9581, "financial_entry_id": 2615,
             "match_status": "confirmed", "metadata_json": {"financial_settlement_id": 2684}},
            {"id": 5, "import_row_id": 9581, "financial_entry_id": 102,
             "match_status": "confirmed", "metadata_json": {"financial_settlement_id": 200}},
        ],
        "suggestions": [{"id": 8, "import_row_id": 9577}, {"id": 9, "import_row_id": 9584}],
    }
    calls = []
    def list_batches(**kwargs):
        calls.append(kwargs)
        return [data["batch"]], None
    def get_batch(**kwargs):
        calls.append(kwargs)
        return data, None
    stub = SimpleNamespace(list_import_batches=list_batches, get_import_batch=get_batch)
    monkeypatch.setitem(sys.modules, "services.financial_import_service", SimpleNamespace(FinancialImportService=stub))
    return data, calls, stub


@pytest.mark.parametrize("company_id", [1, 8, 10, None, True, "9", 9.0, -9])
def test_rejects_other_tenants_before_repository_access(company_id, imports):
    for result, error in (
        Service.list_batches(company_id=company_id),
        Service.get_batch(company_id=company_id, batch_id=12),
        Service.get_settlement(company_id=company_id, settlement_id=2752),
    ):
        assert result is None and error
    assert imports[1] == []


@pytest.mark.parametrize("invalid_id", [0, -1, True, "12", 12.0, None])
def test_rejects_invalid_object_ids(invalid_id, imports):
    assert Service.get_batch(company_id=9, batch_id=invalid_id)[1]
    assert Service.get_settlement(company_id=9, settlement_id=invalid_id)[1]
    assert imports[1] == []


def test_batch_listing_supplies_explicit_tenant_scope(imports):
    result, error = Service.list_batches(company_id=9)
    assert error is None
    assert result == {"items": [imports[0]["batch"]], "count": 1}
    assert imports[1] == [{"company_id": 9, "allowed_company_ids": (9,)}]


def test_batch_filter_preserves_suggestions_confirmed_rejected_and_1_to_many(imports):
    original = copy.deepcopy(imports[0])
    result, error = Service.get_batch(company_id=9, batch_id=12, row_ids=[9577, 9581])
    assert error is None
    assert result["matches"] == original["matches"]
    assert result["suggestions"] == [original["suggestions"][0]]
    assert [row["id"] for row in result["rows"]] == [9577, 9581]
    assert imports[0] == original
    assert imports[1] == [{"company_id": 9, "batch_id": 12, "allowed_company_ids": (9,)}]


def test_unfiltered_batch_preserves_all_persisted_fields(imports):
    result, error = Service.get_batch(company_id=9, batch_id=12)
    assert error is None and result == imports[0]


def test_row_outside_batch_fails_without_revealing_destination(imports):
    result, error = Service.get_batch(company_id=9, batch_id=12, row_ids=[999])
    assert result is None and error


@pytest.mark.parametrize("row_ids", [[], [0], [True], ["9577"], "9577", list(range(1, 102))])
def test_invalid_row_filter_does_not_query(row_ids, imports):
    assert Service.get_batch(company_id=9, batch_id=12, row_ids=row_ids)[1]
    assert imports[1] == []


def test_import_service_errors_propagate(imports):
    imports[2].get_import_batch = lambda **kwargs: (None, "Lote não encontrado")
    assert Service.get_batch(company_id=9, batch_id=12) == (None, "Lote não encontrado")
    imports[2].list_import_batches = lambda **kwargs: (None, "Escopo negado")
    assert Service.list_batches(company_id=9) == (None, "Escopo negado")


@pytest.mark.parametrize("found", [True, False])
def test_settlement_query_and_inverse_metadata(monkeypatch, found):
    predicates = []
    class Column:
        def __init__(self, name): self.name = name
        def __eq__(self, value): return (self.name, value)
        def is_(self, value): return (self.name, value)
    item = SimpleNamespace(id=2752)
    class Query:
        def filter(self, *values): predicates.extend(values); return self
        def first(self): return item if found else None
    model = SimpleNamespace(id=Column("id"), company_id=Column("company_id"),
                            deleted_at=Column("deleted_at"), query=Query())
    serialized = {"id": 2752, "company_id": 9, "financial_entry_id": 2673,
                  "metadata_json": {"import_batch_id": 12, "import_row_id": 9577,
                                    "reconciliation_match_id": 1}}
    def serialize(value, *, include_components):
        assert value is item and include_components and has_app_context()
        return serialized
    monkeypatch.setitem(sys.modules, "models.financial", SimpleNamespace(FinancialSettlement=model))
    monkeypatch.setitem(sys.modules, "services.financial_service", SimpleNamespace(
        FinancialService=SimpleNamespace(serialize_settlement=serialize)))
    with Flask(__name__).app_context():
        result, error = Service.get_settlement(company_id=9, settlement_id=2752)
    assert predicates == [("id", 2752), ("company_id", 9), ("deleted_at", None)]
    assert (result == {"item": serialized} and error is None) if found else (result is None and error)


def test_tools_reuse_existing_context_without_booting_real_app(monkeypatch, imports):
    registered = {}
    class MCP:
        def tool(self, **kwargs):
            def register(fn): registered[fn.__name__] = fn; return fn
            return register
    register_financial_mcp_tools(MCP(), include_diagnostic_reads=True)
    def forbidden(): raise AssertionError("Real app factory must not run")
    monkeypatch.setitem(sys.modules, "app", SimpleNamespace(create_app=forbidden))
    with Flask(__name__).app_context():
        assert registered[NAMES[0]](9)["success"] is True
        result = registered[NAMES[1]](9, 12, [9577])
        assert result["success"] and len(result["matches"]) == 3
        assert registered[NAMES[2]](8, 2752)["success"] is False


@pytest.mark.parametrize("name", NAMES)
def test_explicit_capability_is_analytics_read_only(name):
    capability = infer_tool_capability(SimpleNamespace(name=name, description="diagnostic"))
    assert capability.scopes == ("mcp_analytics",)
    assert capability.domain == "finance" and capability.risk.value == "low"
    assert capability.permissions == ("financial.view",)
    assert capability.required_context == ("user", "company")
    assert "mutation" not in capability.tags


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("case", ["allowed", "no_permission", "no_scope", "other_tenant", "no_user"])
def test_canonical_policy_is_not_bypassed(name, case):
    capability = infer_tool_capability(SimpleNamespace(name=name, description="diagnostic"))
    identity = {"user_id": 3, "company_id": 9, "role": "cliente",
                "permissions": ("financial.view",), "accessible_company_ids": (9,),
                "issuer": "https://id.example.test", "subject": "test-user",
                "auth_method": "oauth_oidc_bearer", "token_scopes": ("mcp:access", "mcp:analytics")}
    if case == "no_permission": identity["permissions"] = ()
    if case == "no_scope": identity["token_scopes"] = ("mcp:access", "mcp:user")
    if case == "no_user": identity["user_id"] = None
    decision = evaluate_tool_policy(identity, ToolPolicyRequest(
        tool_name=name, surface="analytics", domain=capability.domain, action="read",
        risk="low", requested_company_id=8 if case == "other_tenant" else 9,
        accessible_company_ids=(9,), required_permissions=capability.permissions,
        required_context=capability.required_context))
    assert decision.allowed is (case == "allowed")


def test_diagnostic_service_contains_no_mutation_or_app_bootstrap():
    source = Path(__file__).parents[1] / "services/financial_reconciliation_diagnostic_service.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    calls = [node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
             for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert not {"commit", "flush", "rollback", "add", "delete", "create_app", "review_match",
                "create_settlement", "learn_from_confirmed_row"}.intersection(calls)


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("invalid", [True, "9", 9.0])
def test_mcp_schema_rejects_coerced_tenant_ids(name, invalid):
    from pydantic import ValidationError, validate_call
    registered = {}
    class MCP:
        def tool(self, **kwargs):
            def register(fn): registered[fn.__name__] = fn; return fn
            return register
    register_financial_mcp_tools(MCP(), include_diagnostic_reads=True)
    checked = validate_call(registered[name])
    args = (invalid,) if name == NAMES[0] else (invalid, 12)
    with pytest.raises(ValidationError):
        checked(*args)


def test_full_registry_publishes_diagnostic_reads_only_in_analytics(monkeypatch):
    import asyncio
    import src.core.mcp_surface_registry as registry
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda permission: False)
    monkeypatch.setitem(sys.modules, "app", SimpleNamespace(create_app=lambda: Flask(__name__)))
    analytics = registry.build_oauth_analytics_finance_mcp_server()
    user = registry.build_oauth_user_mcp_server()
    unified = registry.build_oauth_unified_mcp_server()
    names = lambda server: {tool.name for tool in asyncio.run(server.list_tools())}
    assert set(NAMES).issubset(names(analytics))
    assert not set(NAMES).intersection(names(user))
    assert not set(NAMES).intersection(names(unified))
    for name in NAMES:
        capability = registry.catalog.get_tool_capability(name)
        assert capability.scopes == ("mcp_analytics",)
    assert "review_financial_reconciliation_match" not in names(analytics)

@pytest.mark.parametrize("surface", ["user", "admin", "ops", "finance", None])
def test_shared_registrar_cannot_expose_diagnostic_reads_on_other_surfaces(surface):
    import src.core.mcp_surface_registry as registry
    registered = {}
    class MCP:
        def tool(self, **kwargs):
            def register(fn): registered[fn.__name__] = fn; return fn
            return register
    registry._register_shared_registrars(MCP(), tool_names=set(NAMES), policy_surface=surface)
    assert not set(NAMES).intersection(registered)


def test_legacy_registrar_does_not_publish_diagnostic_tools_by_default():
    registered = {}
    class MCP:
        def tool(self, **kwargs):
            def register(fn): registered[fn.__name__] = fn; return fn
            return register
    register_financial_mcp_tools(MCP())
    assert not set(NAMES).intersection(registered)
