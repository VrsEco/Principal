from src.intelligence.tool_catalog import catalog


class _FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        if args and callable(args[0]) and not kwargs:
            func = args[0]
            self.tools[func.__name__] = func
            return func

        def decorator(func):
            name = kwargs.get("name", func.__name__)
            self.tools[name] = func
            return func

        return decorator


def test_register_mcp_tools_exposes_discovery_and_keeps_callable_contract():
    fake_mcp = _FakeMCP()

    catalog.register_mcp_tools(fake_mcp)

    assert "list_app32_capabilities" in fake_mcp.tools
    assert "describe_app32_analysis_catalog_tool" in fake_mcp.tools
    assert "get_incentive_indicators" in fake_mcp.tools
    assert "suspend_commercial_contract" in fake_mcp.tools
    assert "close_commercial_contract" in fake_mcp.tools
    assert "delete_commercial_contract" in fake_mcp.tools

    manifest = fake_mcp.tools["list_app32_capabilities"](scope="mcp_user", include_tools=False)
    analytics_manifest = fake_mcp.tools["list_app32_capabilities"](scope="mcp_analytics", include_tools=True)

    assert manifest["domains"]
    assert isinstance(manifest["domains"], dict)
    assert "get_plan_diagnostics_read_model" in {tool["name"] for tool in analytics_manifest["tools"]}
