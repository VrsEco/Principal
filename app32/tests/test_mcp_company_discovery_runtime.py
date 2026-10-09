"""Descoberta de empresa no MCP OAuth: auto-seleção com grant único e tools de descoberta."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from services import principal_authorization_service as authorization
from src.core import mcp_runtime as runtime


def _grant(company_id, reason=None, principal_id=71, mcp_permissions=()):
    return SimpleNamespace(
        company_id=company_id,
        principal_id=principal_id,
        mcp_permissions=list(mcp_permissions),
        inactive_reason_at=lambda _now: reason,
    )


def _service(grants, principal_active=True):
    principal = SimpleNamespace(id=71, user_id=32, is_active=principal_active)
    return authorization.PrincipalAuthorizationService(
        now_provider=datetime.utcnow,
        principal_lookup=lambda pid: principal if pid == 71 else None,
        grant_lookup=lambda pid, cid: next((g for g in grants if g.company_id == cid), None),
        grants_lookup=lambda pid: [g for g in grants if g.principal_id == pid],
    )


def test_active_company_ids_excludes_revoked_expired_and_foreign_grants():
    service = _service([
        _grant(8),
        _grant(9, reason="inactive"),
        _grant(10, reason="expired"),
        _grant(11, principal_id=999),
    ])
    assert service.active_company_ids(principal_id=71) == (8,)


def test_active_company_ids_empty_for_inactive_principal():
    assert _service([_grant(8)], principal_active=False).active_company_ids(principal_id=71) == ()


@pytest.fixture
def oauth(monkeypatch):
    monkeypatch.setenv("APP32_MCP_USE_PRINCIPAL_GRANTS", "1")
    monkeypatch.setattr(runtime, "get_http_request_context", lambda: {
        "transport": "streamable_http", "principal_id": 71, "user_id": 32,
        "company_id": None, "surface": "user", "auth_method": "oauth_oidc_bearer",
    })
    monkeypatch.setattr(runtime, "resolve_runtime_identity", lambda **kw: {
        "company_id": kw["company_id"], "employee_id": 73, "role": "cliente",
        "permissions": {}, "has_full_app32_permissions": True,
        "accessible_company_ids": [8, 9],
    })

    def install(grants):
        service = _service(grants)
        monkeypatch.setattr(authorization, "principal_authorization_service", service)
        return service

    return install


def test_single_active_grant_is_auto_selected(oauth):
    oauth([_grant(8)])
    context = runtime.resolve_mcp_execution_context({})
    assert context.company_id == 8
    assert context.metadata["company_resolution_source"] == "principal_company_grant"
    assert context.metadata["principal_grant_enforced"] is True


def test_multiple_grants_still_require_company_for_regular_tools(oauth):
    oauth([_grant(8), _grant(9)])
    with pytest.raises(PermissionError, match="company_id obrigatório"):
        runtime.resolve_mcp_execution_context({})


def test_no_grant_still_denied_for_regular_tools(oauth):
    oauth([])
    with pytest.raises(PermissionError, match="company_id obrigatório"):
        runtime.resolve_mcp_execution_context({})


def test_discovery_tools_get_company_less_context_limited_to_active_grants(oauth):
    oauth([_grant(8), _grant(9), _grant(10, reason="inactive")])
    context = runtime.resolve_mcp_execution_context({}, allow_missing_company=True)
    assert context.company_id is None
    assert context.accessible_company_ids == (8, 9)
    assert context.user_id == 32
    assert context.metadata["selection_required_for_mutations"] is True
    assert context.metadata["company_resolution_source"] == "principal_company_discovery"


def test_discovery_never_lists_companies_without_app32_membership(oauth, monkeypatch):
    oauth([_grant(8), _grant(9)])
    monkeypatch.setattr(runtime, "resolve_runtime_identity", lambda **kw: {
        "company_id": None, "employee_id": None, "role": "colaborador",
        "permissions": {}, "accessible_company_ids": [9],
    })
    context = runtime.resolve_mcp_execution_context({}, allow_missing_company=True)
    assert context.accessible_company_ids == (9,)


def test_discovery_denied_for_inactive_principal(monkeypatch):
    monkeypatch.setenv("APP32_MCP_USE_PRINCIPAL_GRANTS", "1")
    monkeypatch.setattr(runtime, "get_http_request_context", lambda: {
        "transport": "streamable_http", "principal_id": 71, "user_id": 32,
        "surface": "user", "auth_method": "oauth_oidc_bearer",
    })
    monkeypatch.setattr(authorization, "principal_authorization_service", _service([_grant(8)], principal_active=False))
    with pytest.raises(PermissionError, match="principal grant negado"):
        runtime.resolve_mcp_execution_context({}, allow_missing_company=True)


def test_explicit_company_still_goes_through_grant_gate(oauth):
    oauth([_grant(8)])
    with pytest.raises(PermissionError, match="grant do principal para a empresa não encontrado"):
        runtime.resolve_mcp_execution_context({"company_id": 99})


def test_only_read_discovery_tools_are_exempt():
    # Fronteira de segurança: só leituras que descobrem a empresa ou agregam dados PESSOAIS sobre as
    # empresas com grant ativo (lista do servidor, cada empresa validada) podem rodar sem company_id.
    assert runtime.COMPANY_DISCOVERY_TOOLS == {
        "list_my_companies",
        "bootstrap_session_context",
        "list_my_work_all_companies",
    }


def test_every_exempt_tool_is_a_low_risk_read_without_human_gate():
    from src.intelligence.tool_catalog import catalog

    for name in runtime.COMPANY_DISCOVERY_TOOLS:
        capability = catalog.get_tool_capability(name)
        assert capability is not None, name
        assert getattr(capability.risk, "value", capability.risk) == "low", name
        assert capability.human_gate is False, name
        assert name.split("_")[0] in {"list", "bootstrap", "get"}, f"{name}: isento de empresa só se for leitura"


# ---- descoberta com teto de permissões no grant (caso Joseane, 2026-10-09) --------------------
# Teto real encontrado em produção: vocabulário do RBAC do APP32, sem `identity.read`.
CEILING = ("projects.view", "projects.create", "projects.edit", "processes.view", "financial.view", "financial.create", "financial.edit")


def _policy(context, tool_name):
    from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy
    from src.intelligence.tool_catalog import catalog
    from src.intelligence.tooling.capabilities import infer_tool_action

    capability = catalog.get_tool_capability(tool_name)
    source = {
        "principal_id": context.principal_id, "subject_type": "USER", "user_id": context.user_id,
        "company_id": context.company_id, "employee_id": context.employee_id, "role": context.role,
        "auth_method": "oauth_oidc_bearer", "token_scopes": ["mcp:access", "mcp:user"],
        "issuer": "https://id.example/realms/app32", "subject": "s", "client_id": "c",
        "permissions": context.permissions, "metadata": dict(context.metadata or {}),
    }
    request = ToolPolicyRequest(
        tool_name=tool_name, surface="user", domain=capability.domain,
        action=infer_tool_action(tool_name, capability.domain), risk="low",
        requested_company_id=context.company_id, accessible_company_ids=tuple(context.accessible_company_ids or ()),
        required_permissions=tuple(capability.permissions or ()), required_context=tuple(capability.required_context or ()),
        metadata=dict(context.metadata or {}),
    )
    return evaluate_tool_policy(source, request)


def test_discovery_tool_adds_its_baseline_permissions_when_the_grant_has_a_ceiling(oauth):
    oauth([_grant(8, mcp_permissions=CEILING)])
    context = runtime.resolve_mcp_execution_context({}, allow_missing_company=True)
    baseline = runtime._discovery_baseline_permissions()
    assert {"identity.read", "work.read_self"} <= set(baseline)
    assert context.company_id == 8, "grant único é selecionado automaticamente (é por isso que o teto valia)"
    assert set(baseline) <= set(context.permissions)
    assert set(CEILING) <= set(context.permissions)
    assert set(baseline) <= set(context.metadata["mcp_permission_ceiling"])


def test_discovery_baseline_does_not_leak_into_regular_tools(oauth):
    oauth([_grant(8, mcp_permissions=CEILING)])
    context = runtime.resolve_mcp_execution_context({})
    assert set(context.permissions) == set(CEILING), "ferramenta comum continua restrita exatamente ao teto"
    assert "identity.read" not in context.permissions
    assert "identity.read" not in context.metadata["mcp_permission_ceiling"]


def test_grant_without_a_ceiling_is_untouched_by_the_baseline(oauth):
    oauth([_grant(8)])
    context = runtime.resolve_mcp_execution_context({}, allow_missing_company=True)
    assert context.metadata["mcp_permission_ceiling"] == ()
    assert "identity.read" not in context.permissions or "*" in context.permissions


def test_policy_lets_a_ceilinged_user_discover_companies_but_still_blocks_business_data(oauth):
    oauth([_grant(8, mcp_permissions=CEILING)])
    discovery = runtime.resolve_mcp_execution_context({}, allow_missing_company=True)
    for tool in ("list_my_companies", "bootstrap_session_context", "list_my_work_all_companies"):
        decision = _policy(discovery, tool)
        assert decision.allowed is True, (tool, decision.reason)

    regular = runtime.resolve_mcp_execution_context({})
    denied = _policy(regular, "list_my_companies")
    assert denied.allowed is False and "teto MCP" in denied.reason, "sem a base de descoberta o teto bloqueia (regressão do caso)"
    business = _policy(regular, "list_projects")
    assert business.allowed is False and "teto MCP" in business.reason, "dados de negócio seguem limitados pelo teto"


def test_wildcard_ceiling_is_not_changed(oauth):
    oauth([_grant(8, mcp_permissions=("*",))])
    context = runtime.resolve_mcp_execution_context({}, allow_missing_company=True)
    assert tuple(context.metadata["mcp_permission_ceiling"]) == ("*",)
