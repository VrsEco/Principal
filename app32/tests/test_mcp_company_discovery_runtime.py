"""Descoberta de empresa no MCP OAuth: auto-seleção com grant único e tools de descoberta."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from services import principal_authorization_service as authorization
from src.core import mcp_runtime as runtime


def _grant(company_id, reason=None, principal_id=71):
    return SimpleNamespace(
        company_id=company_id,
        principal_id=principal_id,
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
    assert runtime.COMPANY_DISCOVERY_TOOLS == {"list_my_companies", "bootstrap_session_context"}
