from src.core.mcp_analysis_catalog_tools import register_analysis_catalog_tools
from src.intelligence.mcp_contracts import APP32_ALLOWED_ANALYSIS_CATALOG


class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.registered[kwargs.get("name") or func.__name__] = func
            return func

        if args and callable(args[0]):
            return decorator(args[0])
        return decorator


def test_allowed_analysis_catalog_is_tenant_safe_and_blocks_sql_freeform():
    assert APP32_ALLOWED_ANALYSIS_CATALOG.analyses

    for analysis in APP32_ALLOWED_ANALYSIS_CATALOG.analyses:
        assert analysis.requires_explicit_company_id is True
        assert analysis.cross_tenant_allowed is False
        assert analysis.sql_freeform_allowed is False
        assert "sql livre" in {item.lower() for item in analysis.forbidden_patterns}


def test_finance_analyses_are_restricted_to_admin_profiles_and_analytics_surface():
    finance_analyses = [item for item in APP32_ALLOWED_ANALYSIS_CATALOG.analyses if item.domain == "finance"]

    assert finance_analyses
    for analysis in finance_analyses:
        assert set(analysis.allowed_profiles) == {"administrador", "admin_tecnico"}
        assert analysis.allowed_surfaces == ["analytics"]
        assert analysis.human_gate_required is True


def test_analysis_catalog_tool_returns_manifest_and_single_contract():
    mcp = _FakeMCP()
    register_analysis_catalog_tools(mcp)
    tool = mcp.registered["describe_app32_analysis_catalog_tool"]

    manifest = tool()
    single = tool("strategy_plan_diagnostics")
    invalid = tool("foo")

    assert manifest["success"] is True
    assert len(manifest["data"]["analyses"]) >= 4
    assert single["success"] is True
    assert single["data"]["analysis_id"] == "strategy_plan_diagnostics"
    assert invalid["success"] is False
    assert invalid["error"]["code"] == "analysis_catalog_not_found"
