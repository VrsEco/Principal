import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services import process_modeling_publication_service as service  # noqa: E402
from src.core import mcp_process_flow_tools  # noqa: E402
from src.intelligence.tooling.capabilities import (  # noqa: E402
    _PRESET_CAPABILITIES,
    infer_tool_action,
)


class FakeMcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.tools[kwargs.get("name") or func.__name__] = func
            return func

        return decorator


def test_publication_requires_explicit_human_gate_before_database_access():
    with pytest.raises(service.ProcessModelingPublicationError, match="aprovação humana explícita"):
        service.publish_approved_process_modeling_package(
            company_id=8,
            process_id=150,
            package={},
            human_gate_confirmed=False,
        )


def test_mcp_publication_tool_forwards_tenant_process_and_gate(monkeypatch):
    captured = {}

    def fake_publish(**kwargs):
        captured.update(kwargs)
        return {"company_id": kwargs["company_id"], "process_id": kwargs["process_id"]}

    monkeypatch.setattr(mcp_process_flow_tools, "publish_approved_process_modeling_package", fake_publish)
    mcp = FakeMcp()
    mcp_process_flow_tools.register_process_flow_tools(mcp)

    result = mcp.tools["publish_approved_process_modeling_package_tool"](
        company_id=8,
        process_id=150,
        package={"artifacts": []},
        human_gate_confirmed=True,
    )

    assert result == {"ok": True, "company_id": 8, "process_id": 150}
    assert captured == {
        "company_id": 8,
        "process_id": 150,
        "package": {"artifacts": []},
        "human_gate_confirmed": True,
    }


def test_publication_tool_is_high_risk_tenant_safe_and_human_gated():
    capability = _PRESET_CAPABILITIES["publish_approved_process_modeling_package_tool"]

    assert capability["domain"] == "processes"
    assert capability["human_gate"] is True
    assert "tenant_safe" in capability["tags"]
    assert "company" in capability["required_context"]
    assert capability["scopes"] == ("mcp_admin",)
    assert infer_tool_action("publish_approved_process_modeling_package_tool", "processes") == "update"


def test_mcp_readback_tool_forwards_tenant_and_read_options(monkeypatch):
    captured = {}

    def fake_get(**kwargs):
        captured.update(kwargs)
        return {"company_id": kwargs["company_id"], "process_id": kwargs["process_id"]}

    monkeypatch.setattr(mcp_process_flow_tools, "get_process_modeling_package", fake_get)
    mcp = FakeMcp()
    mcp_process_flow_tools.register_process_flow_tools(mcp)

    result = mcp.tools["get_process_modeling_package_tool"](
        company_id=8,
        process_id=150,
        diagram_status="draft",
        include_bpmn_xml=False,
    )

    assert result == {"ok": True, "package": {"company_id": 8, "process_id": 150}}
    assert captured == {
        "company_id": 8,
        "process_id": 150,
        "diagram_status": "draft",
        "include_bpmn_xml": False,
    }


def test_process_modeling_read_and_analysis_use_tenant_safe_read_permission():
    readback = _PRESET_CAPABILITIES["get_process_modeling_package_tool"]
    analysis = _PRESET_CAPABILITIES["analyze_process_flow_copilot_tool"]

    assert set(readback["scopes"]) == {"mcp_user", "mcp_admin"}
    assert readback["permissions"] == ("process.read",)
    assert readback["required_context"] == ("company",)
    assert analysis["permissions"] == ("process.read",)


def test_instruction_bundle_resolver_remains_in_operational_self_service_domain():
    resolver = _PRESET_CAPABILITIES["resolve_app32_instruction_bundle_tool"]

    assert resolver["domain"] == "identity_self_service"
    assert resolver["permissions"] == ("identity_self_service.read",)
    assert "mcp_user" in resolver["scopes"]


def test_process_lookup_always_filters_by_company_id(monkeypatch):
    captured = {}

    class QueryStub:
        def filter_by(self, **kwargs):
            captured.update(kwargs)
            return self

        def first(self):
            return None

    monkeypatch.setattr(service, "Process", type("ProcessStub", (), {"query": QueryStub()}))

    with pytest.raises(service.ProcessModelingPublicationError, match="tenant"):
        service._process(8, 150)

    assert captured == {"id": 150, "company_id": 8}


def test_new_pop_is_initialized_with_required_fields_before_flush(monkeypatch):
    process = type("ProcessStub", (), {"company_id": 8, "id": 150})()
    created = {}

    class QueryStub:
        def filter_by(self, **kwargs):
            return self

        def first(self):
            return None

    class RoutineStub:
        query = QueryStub()

        def __init__(self, **kwargs):
            created.update(kwargs)

    monkeypatch.setattr(service, "ProcessRoutine", RoutineStub)
    monkeypatch.setattr(service.db.session, "add", lambda row: None)

    def verify_before_flush():
        assert created["name"] == "POP Limpeza"
        assert created["bpmn_element_id"] == "Activity_04"

    monkeypatch.setattr(service.db.session, "flush", verify_before_flush)

    with pytest.raises(AttributeError):
        service._publish_pop(
            process,
            {
                "code": "AW.C.2.2.6.POP.01",
                "name": "POP Limpeza",
                "primary_bpmn_element_id": "Activity_04",
                "activity_ids": ["Activity_04"],
                "steps": [{"name": "Preparar"}],
            },
        )
