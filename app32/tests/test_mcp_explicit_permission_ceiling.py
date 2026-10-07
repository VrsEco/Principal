"""MCP grant ceilings constrain administrators without changing ordinary RBAC.

Use the protected reconciliation runner. Identity/grant lookups, application
bootstrap and audit persistence are declared doubles; runtime and policy are real.
"""

from contextlib import nullcontext
from types import ModuleType, SimpleNamespace
import sys

import pytest

from services.principal_authorization_service import PrincipalAuthorizationDecision
import src.core.mcp_runtime as runtime
from src.intelligence.security.tenant_rbac import (
    PrincipalContext,
    resolve_identity_context,
    validate_permission,
)
from src.intelligence.tooling.capabilities import infer_tool_capability


_MISSING = object()


@pytest.fixture
def grant_runtime(monkeypatch):
    """Supply trusted identity and a real decision over an in-memory raw grant."""
    state = SimpleNamespace(
        role="administrador",
        permissions={},
        full_app32=True,
        grant_calls=[],
        identity_calls=[],
        audits=[],
        callback_calls=[],
        approval_flow_attempts=0,
        principal=SimpleNamespace(id=71, user_id=44),
        grant=SimpleNamespace(id=90, principal_id=71, company_id=9,
                              role="administrador", mcp_permissions=["financial.view"]),
        allowed=True,
        reason="ok",
    )

    class GrantService:
        def resolve_for_company(self, *, principal_id, company_id):
            assert (principal_id, company_id) == (71, 9)
            state.grant_calls.append((principal_id, company_id))
            return PrincipalAuthorizationDecision(
                allowed=state.allowed,
                company_id=company_id,
                reason=state.reason,
                principal=state.principal,
                grant=state.grant,
            )

    def identity_lookup(*, user_id, company_id):
        assert (user_id, company_id) == (44, 9)
        state.identity_calls.append((user_id, company_id))
        return {
            "company_id": company_id,
            "employee_id": 23,
            "role": state.role,
            "permissions": state.permissions,
            "has_full_app32_permissions": state.full_app32,
            "accessible_company_ids": [company_id],
        }

    monkeypatch.setattr(runtime, "_principal_grant_gate_enabled", lambda: True)
    monkeypatch.setattr(runtime, "get_http_request_context", lambda: {
        "user_id": 44,
        "principal_id": 71,
        "company_id": 9,
        "surface": "analytics",
        "transport": "streamable_http",
        "channel": "mcp_http",
        "thread_id": "synthetic-ceiling-unit",
        "auth_method": "oauth_oidc_bearer",
        "token_scopes": ["mcp:access", "mcp:user", "mcp:analytics", "mcp:finance"],
        "subject_type": "USER",
        "mcp_enabled": True,
        "training_completed": True,
    })
    monkeypatch.setattr(runtime, "resolve_runtime_identity", identity_lookup)
    monkeypatch.setattr(
        "services.principal_authorization_service.principal_authorization_service",
        GrantService(),
    )
    monkeypatch.setattr(runtime, "_emit_mcp_policy_audit",
                        lambda *args, **kwargs: state.audits.append((args, kwargs)))
    original_approval_check = runtime._policy_requires_persisted_approval

    def forbid_approval_flow(decision):
        if original_approval_check(decision):
            state.approval_flow_attempts += 1
            raise AssertionError("Read-only ceiling tests must never enter an approval flow")
        return False

    monkeypatch.setattr(runtime, "_policy_requires_persisted_approval", forbid_approval_flow)
    app_module = ModuleType("app")
    app_module.create_app = lambda: SimpleNamespace(app_context=nullcontext)
    monkeypatch.setitem(sys.modules, "app", app_module)
    return state


def _set_ceiling(state, raw):
    if raw is _MISSING:
        del state.grant.mcp_permissions
    else:
        state.grant.mcp_permissions = raw


def _permission(context, required, *, domain="finance", action="read"):
    return validate_permission(
        resolve_identity_context(context), domain=domain, action=action,
        required_permissions=required,
    )


def _wrapped_tool(monkeypatch, state, name, surface):
    capability = infer_tool_capability(SimpleNamespace(name=name, description="unit double"))
    catalog_module = ModuleType("src.intelligence.tool_catalog")
    catalog_module.catalog = SimpleNamespace(
        get_tool_capability=lambda tool_name: capability if tool_name == name else None,
    )
    monkeypatch.setitem(sys.modules, catalog_module.__name__, catalog_module)

    def callback(company_id: int):
        state.callback_calls.append((name, company_id))
        return {"tool": name, "company_id": company_id}

    callback.__app32_tool_name__ = name
    return runtime.wrap_mcp_callable(callback, policy_surface=surface), capability


@pytest.mark.parametrize("role", ["administrador", "administrador_tecnico", "administrator"])
def test_admin_exact_ceiling_allows_covered_read_and_denies_other_permission(grant_runtime, role):
    grant_runtime.role = role
    context = runtime.resolve_mcp_execution_context({"company_id": 9})

    assert context.metadata["principal_grant_enforced"] is True
    assert context.metadata["mcp_permission_ceiling"] == ("financial.view",)
    assert context.permissions == ("financial.view",)
    assert _permission(context, ("financial.view",)).allowed
    denied = _permission(context, ("financial.create",), action="create")
    assert not denied.allowed
    assert "mcp_permission_ceiling_denied" in denied.checks


@pytest.mark.parametrize("domain,action,required", [
    ("projects", "read", ("project.read",)),
    (None, None, ("financial.create",)),
    ("finance", "create", ("financial.view", "financial.create")),
    ("finance", "read", ()),
])
def test_restricted_admin_ceiling_precedes_role_matrix_and_missing_capability_permission(
    grant_runtime, domain, action, required,
):
    context = runtime.resolve_mcp_execution_context({"company_id": 9})
    denied = _permission(context, required, domain=domain, action=action)
    assert not denied.allowed
    assert "mcp_permission_ceiling_denied" in denied.checks


@pytest.mark.parametrize("role,covered_read_allowed", [
    ("administrador", False), ("colaborador", False),
])
def test_nonempty_disjoint_grant_keeps_active_ceiling_even_when_intersection_is_empty(
    grant_runtime, role, covered_read_allowed,
):
    grant_runtime.role = role
    grant_runtime.full_app32 = False
    grant_runtime.permissions = {"project": ["read"]}
    context = runtime.resolve_mcp_execution_context({"company_id": 9})
    assert context.permissions == ()
    assert context.metadata["mcp_permission_ceiling"] == ("financial.view",)
    assert not _permission(context, ("project.read",), domain="projects").allowed
    # An active restricted grant cannot restore an atom excluded by the live
    # APP32 intersection, even when the role matrix would otherwise allow it.
    assert _permission(context, ("financial.view",)).allowed is covered_read_allowed


@pytest.mark.parametrize("raw", [[], (), set(), frozenset(), None, _MISSING],
                         ids=["empty-list", "empty-tuple", "empty-set", "empty-frozenset", "none", "absent-field"])
def test_empty_or_legacy_absent_ceiling_preserves_admin_app32_access(grant_runtime, raw):
    _set_ceiling(grant_runtime, raw)
    context = runtime.resolve_mcp_execution_context({"company_id": 9})
    assert context.metadata["principal_grant_enforced"] is True
    assert context.metadata["mcp_permission_ceiling"] == ()
    assert "*" in context.permissions
    assert _permission(context, ("financial.create",), action="create").allowed


@pytest.mark.parametrize("raw", [
    False, 0, 3, {"financial": ["view"]}, "", " ", "financial.view,,project.read",
    [True], [None], [""], [" "], [["financial.view"]],
    ["financial.view", False], ["financial.*"], ["*", ""],
], ids=[
    "bool", "zero", "integer", "mapping", "empty-string", "whitespace-string", "empty-csv-item",
    "bool-item", "null-item", "empty-item", "whitespace-item", "nested-item",
    "mixed-invalid-item", "unsupported-domain-wildcard", "wildcard-and-empty-item",
])
def test_malformed_raw_ceiling_fails_closed_before_app32_identity_lookup(grant_runtime, raw):
    _set_ceiling(grant_runtime, raw)
    with pytest.raises(PermissionError, match="teto MCP.*inválido"):
        runtime.resolve_mcp_execution_context({"company_id": 9})
    assert grant_runtime.grant_calls == [(71, 9)]
    assert grant_runtime.identity_calls == []
    assert grant_runtime.callback_calls == []


def test_missing_enterprise_grant_denies_even_when_user_is_admin(grant_runtime, monkeypatch):
    grant_runtime.allowed = False
    grant_runtime.reason = "grant ausente"
    grant_runtime.grant = None
    wrapped, _ = _wrapped_tool(monkeypatch, grant_runtime,
                               "get_financial_reconciliation_context", "analytics")
    with pytest.raises(PermissionError, match="principal grant negado"):
        wrapped(company_id=9)
    assert grant_runtime.identity_calls == []
    assert grant_runtime.callback_calls == []


def test_legacy_csv_ceiling_is_exact_and_does_not_add_resource_permissions(grant_runtime):
    _set_ceiling(grant_runtime, " FINANCIAL.VIEW , project.read ")
    context = runtime.resolve_mcp_execution_context({"company_id": 9})
    assert context.permissions == ("financial.view", "project.read")
    assert context.metadata["mcp_permission_ceiling"] == ("financial.view", "project.read")
    assert _permission(context, ("project.read",), domain="projects").allowed
    assert not _permission(context, ("meeting.read",), domain="meetings").allowed


def test_wildcard_ceiling_preserves_existing_nonadmin_app32_permissions_without_elevation(grant_runtime):
    _set_ceiling(grant_runtime, ["*"])
    grant_runtime.role = "colaborador"
    grant_runtime.full_app32 = False
    grant_runtime.permissions = {"financial": ["view"]}
    context = runtime.resolve_mcp_execution_context({"company_id": 9})
    assert context.metadata["mcp_permission_ceiling"] == ("*",)
    assert "*" not in context.permissions
    assert "financial.create" not in context.permissions
    assert _permission(context, ("financial.view",)).allowed
    assert not _permission(context, ("financial.create",), action="create").allowed


def test_wildcard_ceiling_remains_compatible_with_full_admin_app32_permissions(grant_runtime):
    _set_ceiling(grant_runtime, ["*"])
    context = runtime.resolve_mcp_execution_context({"company_id": 9})
    assert context.metadata["mcp_permission_ceiling"] == ("*",)
    assert context.permissions == ("*",)
    assert _permission(context, ("financial.create",), action="create").allowed


@pytest.mark.parametrize("name,surface,resource", [
    ("get_financial_reconciliation_context", "analytics", "financial"),
    ("list_projects", "user", "project"),
    ("list_meetings", "user", "meeting"),
])
def test_shared_wrapper_denies_resource_only_ceiling_before_callback(
    grant_runtime, monkeypatch, name, surface, resource,
):
    _set_ceiling(grant_runtime, [resource])
    wrapped, capability = _wrapped_tool(monkeypatch, grant_runtime, name, surface)
    assert capability.permissions and capability.permissions != (resource,)
    with pytest.raises(PermissionError):
        wrapped(company_id=9)
    assert grant_runtime.callback_calls == []
    assert grant_runtime.audits
    assert grant_runtime.audits[-1][1]["allowed"] is False
    assert grant_runtime.approval_flow_attempts == 0


@pytest.mark.parametrize("name,surface,permission", [
    ("get_financial_reconciliation_context", "analytics", "financial.view"),
    ("list_projects", "user", "project.read"),
    ("list_meetings", "user", "meeting.read"),
])
def test_shared_wrapper_allows_exact_covered_capability_and_revalidates_changed_grant(
    grant_runtime, monkeypatch, name, surface, permission,
):
    _set_ceiling(grant_runtime, [permission])
    wrapped, capability = _wrapped_tool(monkeypatch, grant_runtime, name, surface)
    assert capability.permissions == (permission,)
    assert wrapped(company_id=9) == {"tool": name, "company_id": 9}
    _set_ceiling(grant_runtime, ["unrelated.read"])
    with pytest.raises(PermissionError):
        wrapped(company_id=9)
    assert grant_runtime.callback_calls == [(name, 9)]
    assert grant_runtime.grant_calls == [(71, 9), (71, 9)]
    assert grant_runtime.approval_flow_attempts == 0


def test_payload_cannot_remove_or_replace_the_trusted_grant_ceiling(grant_runtime):
    _set_ceiling(grant_runtime, ["project.read"])
    context = runtime.resolve_mcp_execution_context({
        "company_id": 9,
        "principal_grant_enforced": False,
        "mcp_permission_ceiling": ["*"],
        "permissions": ["*"],
        "metadata": {"principal_grant_enforced": False, "mcp_permission_ceiling": ["*"]},
    })
    assert context.metadata["principal_grant_enforced"] is True
    assert context.metadata["mcp_permission_ceiling"] == ("project.read",)
    assert not _permission(context, ("financial.view",)).allowed


def test_shared_wrapper_cannot_restore_project_permission_excluded_by_live_app32_rbac(
    grant_runtime, monkeypatch,
):
    _set_ceiling(grant_runtime, ["project.read"])
    grant_runtime.role = "colaborador"
    grant_runtime.full_app32 = False
    grant_runtime.permissions = {"financial": ["view"]}
    context = runtime.resolve_mcp_execution_context({"company_id": 9})
    assert context.permissions == ()
    assert context.metadata["mcp_permission_ceiling"] == ("project.read",)
    wrapped, capability = _wrapped_tool(monkeypatch, grant_runtime, "list_projects", "user")
    assert capability.permissions == ("project.read",)
    with pytest.raises(PermissionError):
        wrapped(company_id=9)
    assert grant_runtime.callback_calls == []
    assert grant_runtime.approval_flow_attempts == 0


@pytest.mark.parametrize("metadata", [None, {}, {
    "principal_grant_enforced": False, "mcp_permission_ceiling": ("project.read",),
}], ids=["ordinary-web", "ordinary-ia", "inactive-marker"])
def test_admin_rbac_outside_enforced_mcp_grant_keeps_existing_role_behavior(metadata):
    principal = PrincipalContext(user_id=44, company_id=9, role="administrador",
                                 channel="web", permissions=frozenset(), metadata=metadata)
    decision = validate_permission(principal, domain="finance", action="create",
                                   required_permissions=("financial.create",))
    assert decision.allowed
    assert "mcp_permission_ceiling_denied" not in decision.checks
