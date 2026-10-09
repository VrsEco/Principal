import ast
import os
import sys
import types
from pathlib import Path

from src.core.mcp_financial_tools import register_financial_mcp_tools

import pytest
from contextlib import nullcontext


@pytest.fixture(autouse=True)
def isolated_financial_tool_runtime(monkeypatch):
    """Wrappers unitários nunca devem iniciar Flask, scheduler ou banco real."""
    fake_app = types.ModuleType("app")
    fake_app.create_app = lambda: types.SimpleNamespace(app_context=lambda: nullcontext())
    monkeypatch.setitem(sys.modules, "app", fake_app)
    import psycopg2

    def deny_database(*args, **kwargs):
        raise AssertionError("Teste unitário tentou conectar a um banco real")

    monkeypatch.setattr(psycopg2, "connect", deny_database)




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
    assert "create_financial_settlement" in mcp.registered
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

    response = mcp.registered["create_financial_entry"](10, {"entry_code": "LCT-000033"})

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


def test_create_financial_entry_rejects_payload_company_different_from_explicit_tenant():
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)

    response = mcp.registered["create_financial_entry"](
        10,
        {"company_id": 11, "entry_code": "LCT-TENANT-MISMATCH"},
    )

    assert response == {
        "success": False,
        "error": "company_id do payload diverge do tenant da requisição",
    }


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


def test_get_financial_payables_due_summary_uses_due_dates_and_open_balance(monkeypatch):
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)

    class _FakeFinancialService:
        @staticmethod
        def list_entries(**kwargs):
            assert kwargs["company_id"] == 1
            assert kwargs["entry_type"] == "payable"
            assert kwargs["due_date_from"].isoformat() == "2026-07-20"
            assert kwargs["due_date_to"].isoformat() == "2026-07-26"
            return [
                {"id": 1, "entry_code": "PAG-1", "due_date": "2026-07-21", "counterparty_name": "Fornecedor A", "description": "Compra", "status": "posted", "original_amount": 1000, "settled_principal_amount": 250},
                {"id": 2, "entry_code": "PAG-2", "due_date": "2026-07-22", "counterparty_name": "Fornecedor B", "description": "Serviço", "status": "settled", "original_amount": 500, "settled_principal_amount": 500},
                {"id": 3, "entry_code": "PAG-3", "due_date": "2026-07-23", "counterparty_name": "Fornecedor C", "description": "Contrato", "status": "scheduled", "original_amount": 200, "settled_principal_amount": 0},
            ], None

    fake_service_module = types.ModuleType("services.financial_service")
    fake_service_module.FinancialService = _FakeFinancialService
    monkeypatch.setitem(sys.modules, "services.financial_service", fake_service_module)

    response = mcp.registered["get_financial_payables_due_summary"](
        company_id=1,
        due_date_from="2026-07-20",
        due_date_to="2026-07-26",
    )

    assert response["success"] is True
    assert response["title_count"] == 2
    assert response["total_open_amount"] == 950.0
    assert [item["id"] for item in response["items"]] == [1, 3]


def test_list_financial_entries_accepts_due_date_filters(monkeypatch):
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)
    captured = {}

    class _FakeFinancialService:
        @staticmethod
        def list_entries(**kwargs):
            captured.update(kwargs)
            return [], None

    fake_service_module = types.ModuleType("services.financial_service")
    fake_service_module.FinancialService = _FakeFinancialService
    monkeypatch.setitem(sys.modules, "services.financial_service", fake_service_module)

    response = mcp.registered["list_financial_entries"](
        company_id=1,
        entry_type="receivable",
        due_date_from="2026-07-20",
        due_date_to="2026-07-26",
    )

    assert response == {"success": True, "items": [], "count": 0}
    assert captured["company_id"] == 1
    assert captured["entry_type"] == "receivable"
    assert captured["due_date_from"].isoformat() == "2026-07-20"
    assert captured["due_date_to"].isoformat() == "2026-07-26"


def test_create_financial_entry_rejects_settled_status_without_settlement():
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)

    response = mcp.registered["create_financial_entry"](
        10,
        {"company_id": 10, "entry_code": "LCT-000034", "status": "settled"},
    )

    assert response["success"] is False
    assert "create_financial_settlement" in response["error"]


def test_create_financial_settlement_binds_payload_to_explicit_tenant(monkeypatch):
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)

    response = mcp.registered["create_financial_settlement"](
        10,
        {"company_id": 11, "financial_entry_id": 33},
    )

    assert response == {
        "success": False,
        "error": "company_id do payload diverge do tenant da requisição",
    }


def test_create_financial_settlement_attaches_mcp_audit_context(monkeypatch):
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

    class _FakeSettlement:
        def to_dict(self):
            return {"id": 91, "financial_entry_id": 33}

    class _FakeFinancialService:
        @staticmethod
        def create_settlement(*, payload):
            captured.update(payload)
            return _FakeSettlement(), None

        @staticmethod
        def serialize_settlement(item):
            return item.to_dict()

    fake_service_module = types.ModuleType("services.financial_service")
    fake_service_module.FinancialService = _FakeFinancialService
    monkeypatch.setitem(sys.modules, "services.financial_service", fake_service_module)

    response = mcp.registered["create_financial_settlement"](
        10,
        {"financial_entry_id": 33, "settlement_code": "SET-000033", "bank_account_id": 8},
    )

    assert response == {"success": True, "item": {"id": 91, "financial_entry_id": 33}}
    assert captured["company_id"] == 10
    assert captured["metadata_json"]["audit"]["channel"] == "web"


def test_create_financial_settlement_requires_bank_account():
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)

    response = mcp.registered["create_financial_settlement"](
        10,
        {"financial_entry_id": 33, "settlement_code": "SET-000033"},
    )

    assert response == {
        "success": False,
        "error": "bank_account_id é obrigatório para registrar uma baixa bancária vinculada.",
    }


def _install_create_entry_fakes(monkeypatch, *, gate_metadata, approval_action):
    """Instala fakes para exercitar create_financial_entry sem banco."""
    from datetime import datetime

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

    class _FakeFinancialService:
        @staticmethod
        def create_entry(*, payload):
            captured["payload"] = payload
            return object(), None

        @staticmethod
        def serialize_entry(entry, *, include_children=True):
            return {"id": 1}

    fake_service_module = types.ModuleType("services.financial_service")
    fake_service_module.FinancialService = _FakeFinancialService
    monkeypatch.setitem(sys.modules, "services.financial_service", fake_service_module)

    class _FakeQuery:
        def filter_by(self, **kwargs):
            captured["agent_action_filter"] = kwargs
            return self

        def first(self):
            return approval_action

    class _FakeAgentAction:
        query = _FakeQuery()

    fake_agent_action_module = types.ModuleType("models.agent_action")
    fake_agent_action_module.AgentAction = _FakeAgentAction
    monkeypatch.setitem(sys.modules, "models.agent_action", fake_agent_action_module)

    fake_context = types.SimpleNamespace(
        user_id=14, company_id=10, employee_id=None, channel="mcp_http", thread_id=None, metadata=gate_metadata
    )
    monkeypatch.setattr("src.intelligence.tool_context.get_sapiens_context", lambda: fake_context)
    return captured, datetime


def test_create_financial_entry_posts_entry_when_human_approval_was_consumed(monkeypatch):
    from datetime import datetime

    approved_at = datetime(2026, 10, 9, 14, 26, 49)
    action = types.SimpleNamespace(
        id=909,
        status="executed",
        resolved_at=approved_at,
        payload={"approved_by_user_id": 14},
    )
    captured, _ = _install_create_entry_fakes(
        monkeypatch,
        gate_metadata={"approved_human_gate_request_id": 909},
        approval_action=action,
    )
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)

    response = mcp.registered["create_financial_entry"](
        10,
        {
            "entry_code": "LCT-1",
            # Tentativa de forjar aprovação pelo cliente deve ser ignorada.
            "approved_by_user_id": 999,
            "approved_at": "2000-01-01T00:00:00",
        },
    )

    assert response["success"] is True
    payload = captured["payload"]
    assert payload["status"] == "posted"
    assert payload["review_status"] == "approved"
    assert payload["approved_by_user_id"] == 14
    assert payload["approved_at"] == approved_at
    assert payload["metadata_json"]["human_approval_request_id"] == 909
    assert captured["agent_action_filter"]["company_id"] == 10


def test_create_financial_entry_stays_draft_without_human_approval(monkeypatch):
    captured, _ = _install_create_entry_fakes(
        monkeypatch,
        gate_metadata={},
        approval_action=None,
    )
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)

    response = mcp.registered["create_financial_entry"](
        10,
        {"entry_code": "LCT-2", "approved_by_user_id": 999},
    )

    assert response["success"] is True
    payload = captured["payload"]
    assert "status" not in payload
    assert "review_status" not in payload
    assert "approved_by_user_id" not in payload
    assert "approved_at" not in payload
    assert "agent_action_filter" not in captured


def test_create_financial_entry_ignores_approval_from_other_company_or_unapproved_status(monkeypatch):
    action = types.SimpleNamespace(id=5, status="pending", resolved_at=None, payload={"approved_by_user_id": 14})
    captured, _ = _install_create_entry_fakes(
        monkeypatch,
        gate_metadata={"approved_human_gate_request_id": 5},
        approval_action=action,
    )
    mcp = _FakeMCP()
    register_financial_mcp_tools(mcp)

    mcp.registered["create_financial_entry"](10, {"entry_code": "LCT-3"})

    assert "status" not in captured["payload"]
    assert "approved_by_user_id" not in captured["payload"]
