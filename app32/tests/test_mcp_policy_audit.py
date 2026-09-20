from types import SimpleNamespace

import pytest

from src.core.mcp_runtime import _emit_mcp_policy_audit
from src.intelligence.security.tool_policy import ToolPolicyRequest
from src.intelligence.audit import AIExecutionAuditPersistenceError


@pytest.mark.parametrize("action,allowed,required", [
    ("read", True, False), ("update", True, True), ("delete", True, True),
    ("create", False, False),
])
def test_policy_audit_has_server_identity_and_requires_durable_mutations(monkeypatch, action, allowed, required):
    captured = {}
    def emit(record, *, require_persistence):
        captured.update(record=record, required=require_persistence)
    monkeypatch.setattr("src.intelligence.audit.emit_ai_execution_audit_event", emit)
    source = {
        "principal_id": 71, "company_id": 9, "user_id": 3, "client_id": "codex",
        "auth_method": "oauth", "token_scopes": ["mcp:access", "mcp:admin"],
        "subject": "do-not-log", "correlation_id": "trace-1",
    }
    request = ToolPolicyRequest(tool_name="update_project", surface="admin", action=action,
                                domain="projects", requested_company_id=9,
                                metadata={"approved_human_gate_request_id": 321})
    _emit_mcp_policy_audit(source, request, {"description": "PRIVATE_PAYLOAD"}, allowed=allowed, reason="ok")
    record = captured["record"]
    assert captured["required"] is required
    assert record.company_id == 9
    assert record.trace_id == "trace-1"
    assert record.metadata["principal_id"] == 71
    assert record.metadata["approval_request_id"] == 321
    assert len(record.metadata["payload_digest"]) == 64
    assert "PRIVATE_PAYLOAD" not in str(record.metadata)
    assert "do-not-log" not in str(record.metadata)


def test_mutation_policy_audit_denies_execution_without_durable_storage(monkeypatch):
    monkeypatch.setattr("src.intelligence.audit.has_app_context", lambda: False)
    request = ToolPolicyRequest(tool_name="update_project", surface="admin", action="update",
                                domain="projects", requested_company_id=9)
    with pytest.raises(AIExecutionAuditPersistenceError):
        _emit_mcp_policy_audit({"principal_id": 71, "user_id": 3}, request, {}, allowed=True, reason="ok")


def test_runtime_never_calls_mutation_when_policy_audit_cannot_persist(monkeypatch):
    import sys
    from contextlib import nullcontext
    from src.core.mcp_runtime import wrap_mcp_callable

    monkeypatch.setitem(sys.modules, "app", SimpleNamespace(
        create_app=lambda: SimpleNamespace(app_context=nullcontext),
    ))
    capability = SimpleNamespace(domain="projects", risk=SimpleNamespace(value="medium"),
                                  permissions=(), required_context=())
    monkeypatch.setitem(sys.modules, "src.intelligence.tool_catalog", SimpleNamespace(
        catalog=SimpleNamespace(get_tool_capability=lambda name: capability),
    ))
    context = SimpleNamespace(user_id=3, principal_id=71, company_id=9, employee_id=23,
                              role="administrador", channel="mcp", thread_id=None,
                              permissions=(), accessible_company_ids=(9,), metadata={"surface": "admin"})
    monkeypatch.setattr("src.core.mcp_runtime.resolve_mcp_execution_context", lambda payload: context)
    monkeypatch.setattr("src.core.mcp_runtime.evaluate_tool_policy",
                        lambda *args: SimpleNamespace(allowed=True, reason="ok"))
    monkeypatch.setattr("src.core.mcp_runtime.require_tool_policy", lambda *args: None)
    monkeypatch.setattr("src.intelligence.audit.has_app_context", lambda: False)
    calls = []
    def update_project(**kwargs):
        calls.append(kwargs)
    with pytest.raises(AIExecutionAuditPersistenceError):
        wrap_mcp_callable(update_project)(company_id=9)
    assert calls == []
