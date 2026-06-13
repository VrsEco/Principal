import ast
import os
import sys
import types
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
    assert "create_financial_bank_transfer" in mcp.registered
    assert "preview_financial_bank_statement_repair" in mcp.registered
    assert "apply_financial_bank_statement_repair" in mcp.registered
    assert "list_financial_closings" in mcp.registered
    assert "create_financial_closing" in mcp.registered
    assert "resolve_financial_classification_answer" in mcp.registered
    assert len(mcp.registered) >= 73


def test_new_financial_mcp_capabilities_are_admin_or_analytics_only():
    from src.intelligence.tool_catalog import catalog

    capabilities = {
        item.name: item
        for item in catalog.iter_capabilities(domain="finance")
        if item.name
        in {
            "create_financial_bank_transfer",
            "preview_financial_bank_statement_repair",
            "apply_financial_bank_statement_repair",
        }
    }

    assert set(capabilities) == {
        "create_financial_bank_transfer",
        "preview_financial_bank_statement_repair",
        "apply_financial_bank_statement_repair",
    }
    assert "mcp_user" not in capabilities["create_financial_bank_transfer"].scopes
    assert "mcp_user" not in capabilities["apply_financial_bank_statement_repair"].scopes
    assert capabilities["create_financial_bank_transfer"].human_gate is True
    assert capabilities["apply_financial_bank_statement_repair"].human_gate is True
    assert "mcp_analytics" in capabilities["preview_financial_bank_statement_repair"].scopes


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


def test_create_financial_entry_serializes_inside_app_context(monkeypatch):
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)

    events = []

    class _FakeAppContext:
        def __enter__(self):
            events.append("enter_app_context")
            return self

        def __exit__(self, exc_type, exc, tb):
            events.append("exit_app_context")
            return False

    class _FakeApp:
        def app_context(self):
            return _FakeAppContext()

    fake_app_module = types.ModuleType("app")
    fake_app_module.create_app = lambda: _FakeApp()
    monkeypatch.setitem(sys.modules, "app", fake_app_module)

    class _FakeEntry:
        pass

    class _FakeFinancialService:
        @staticmethod
        def create_entry(*, payload):
            events.append(("create_entry", payload))
            return _FakeEntry(), None

        @staticmethod
        def serialize_entry(entry, *, include_children=True):
            events.append(("serialize_entry", include_children, isinstance(entry, _FakeEntry)))
            return {"id": 33, "company_id": 10, "entry_code": "LCT-000033"}

    fake_service_module = types.ModuleType("services.financial_service")
    fake_service_module.FinancialService = _FakeFinancialService
    monkeypatch.setitem(sys.modules, "services.financial_service", fake_service_module)

    response = mcp.registered["create_financial_entry"]({"company_id": 10, "entry_code": "LCT-000033"})

    assert response == {
        "success": True,
        "item": {"id": 33, "company_id": 10, "entry_code": "LCT-000033"},
    }
    assert events[0] == "enter_app_context"
    assert events[2] == ("serialize_entry", True, True)
    assert events[3] == "exit_app_context"
    payload = events[1][1]
    assert events[1][0] == "create_entry"
    assert payload["company_id"] == 10
    assert payload["entry_code"] == "LCT-000033"
    assert payload["created_by_agent"] == "web"
    assert payload["metadata_json"]["audit"]["actor"]["agent"] == "web"
    assert payload["metadata_json"]["audit"]["channel"] == "web"


def test_create_financial_schedule_attaches_agent_audit_context(monkeypatch):
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)

    captured = {}

    class _FakeAppContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeApp:
        def app_context(self):
            return _FakeAppContext()

    fake_app_module = types.ModuleType("app")
    fake_app_module.create_app = lambda: _FakeApp()
    monkeypatch.setitem(sys.modules, "app", fake_app_module)

    class _FakeFinancialScheduleService:
        @staticmethod
        def create_schedule(*, payload):
            captured.update(payload)
            return {"id": 63, "company_id": payload["company_id"]}, None

    fake_service_module = types.ModuleType("services.financial_schedule_service")
    fake_service_module.FinancialScheduleService = _FakeFinancialScheduleService
    monkeypatch.setitem(sys.modules, "services.financial_schedule_service", fake_service_module)
    monkeypatch.setenv("APP32_MCP_CHANNEL", "claude_code")
    monkeypatch.setenv("APP32_MCP_USER_ID", "3")
    monkeypatch.delenv("APP32_MCP_CLIENT", raising=False)
    monkeypatch.delenv("APP32_MCP_THREAD_ID", raising=False)

    response = mcp.registered["create_financial_schedule"]({"company_id": 10, "schedule_code": "SCH-001"})

    assert response == {"success": True, "item": {"id": 63, "company_id": 10}}
    assert captured["created_by_agent"] == "claude_code"
    assert captured["created_by_user_id"] == 3
    assert captured["metadata_json"]["audit"]["actor"]["agent"] == "claude_code"
    assert captured["metadata_json"]["audit"]["channel"] == "claude_code"


def test_create_financial_schedule_resolves_employee_by_user_and_company(monkeypatch):
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)

    captured = {}

    class _FakeAppContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _FakeApp:
        def app_context(self):
            return _FakeAppContext()

    fake_app_module = types.ModuleType("app")
    fake_app_module.create_app = lambda: _FakeApp()
    monkeypatch.setitem(sys.modules, "app", fake_app_module)

    class _FakeFinancialScheduleService:
        @staticmethod
        def create_schedule(*, payload):
            captured.update(payload)
            return {"id": 68, "company_id": payload["company_id"]}, None

    fake_service_module = types.ModuleType("services.financial_schedule_service")
    fake_service_module.FinancialScheduleService = _FakeFinancialScheduleService
    monkeypatch.setitem(sys.modules, "services.financial_schedule_service", fake_service_module)

    class _FakeEmployeeQuery:
        @staticmethod
        def filter_by(**kwargs):
            class _FakeResult:
                @staticmethod
                def first():
                    assert kwargs == {"user_id": 3, "company_id": 10}
                    return types.SimpleNamespace(id=88)

            return _FakeResult()

    fake_employee_module = types.ModuleType("models.employee")
    fake_employee_module.Employee = types.SimpleNamespace(query=_FakeEmployeeQuery())
    monkeypatch.setitem(sys.modules, "models.employee", fake_employee_module)

    monkeypatch.setenv("APP32_MCP_CHANNEL", "claude_code")
    monkeypatch.setenv("APP32_MCP_USER_ID", "3")
    monkeypatch.delenv("APP32_MCP_THREAD_ID", raising=False)
    monkeypatch.delenv("APP32_MCP_CLIENT", raising=False)

    response = mcp.registered["create_financial_schedule"]({"company_id": 10, "schedule_code": "SCH-EMP-001"})

    assert response == {"success": True, "item": {"id": 68, "company_id": 10}}
    assert captured["created_by_user_id"] == 3
    assert captured["created_by_employee_id"] == 88
    assert captured["metadata_json"]["audit"]["actor"]["employee_id"] == 88
