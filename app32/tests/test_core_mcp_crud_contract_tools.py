from src.core.mcp_crud_contract_tools import register_crud_contract_tools


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


def test_crud_contract_tool_describes_all_domains_and_single_domain():
    mcp = _FakeMCP()
    register_crud_contract_tools(mcp)

    tool = mcp.registered["describe_app32_crud_contracts_tool"]
    all_contracts = tool()
    finance_contract = tool("finance")
    invalid = tool("invalid")

    assert all_contracts["success"] is True
    assert all_contracts["meta"]["operation"] == "crud_contracts.describe"
    assert {domain["domain"] for domain in all_contracts["data"]["domains"]} == {
        "routine",
        "projects",
        "meetings",
        "finance",
        "strategy",
    }
    assert finance_contract["success"] is True
    assert finance_contract["data"]["domain"] == "finance"
    assert any(operation["human_gate_required"] for operation in finance_contract["data"]["operations"])
    assert invalid["success"] is False
    assert invalid["error"]["code"] == "crud_contract_not_found"
