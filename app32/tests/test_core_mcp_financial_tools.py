import ast
from pathlib import Path

from src.core.mcp_financial_tools import register_financial_mcp_tools


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


def test_register_financial_mcp_tools_registers_complete_financial_surface():
    mcp = _FakeMCP()

    register_financial_mcp_tools(mcp)

    assert "list_financial_catalog_items" in mcp.registered
    assert "create_financial_catalog_item" in mcp.registered
    assert "create_financial_entry" in mcp.registered
    assert "match_financial_bank_reconciliation_row" in mcp.registered
    assert "list_financial_closings" in mcp.registered
    assert "create_financial_closing" in mcp.registered
    assert "resolve_financial_classification_answer" in mcp.registered
    assert len(mcp.registered) >= 70


def test_legacy_mcp_server_delegates_financial_surface_to_dedicated_module():
    source_path = Path(__file__).resolve().parents[1] / "src" / "core" / "mcp_server.py"
    module = ast.parse(source_path.read_text(encoding="utf-8"))

    function_names = {
        node.name for node in ast.walk(module) if isinstance(node, ast.FunctionDef)
    }

    assert "register_financial_mcp_tools" not in function_names
    assert "list_financial_catalog_items" not in function_names
    assert "create_financial_entry" not in function_names
    assert "register_financial_mcp_tools(mcp)" in source_path.read_text(encoding="utf-8")
