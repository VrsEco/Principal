import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.security import (
    PermissionDeniedError,
    PrincipalContext,
    TenantScopeError,
    prepare_enforcement,
    require_company_scope,
    require_permission,
    resolve_identity_context,
    validate_company_id,
    validate_permission,
)


def test_resolve_identity_context_normalizes_mapping_payload():
    principal = resolve_identity_context(
        {
            "user_id": "7",
            "company_id": "12",
            "employee_id": 44,
            "role": "Administrator",
            "channel": "whatsapp",
            "thread_id": "wa_7_abc",
            "permissions": ["finance.read", "  reports.export "],
            "metadata": {"origin": "mcp"},
        }
    )

    assert isinstance(principal, PrincipalContext)
    assert principal.user_id == 7
    assert principal.company_id == 12
    assert principal.employee_id == 44
    assert principal.role == "administrador"
    assert principal.channel == "whatsapp"
    assert principal.thread_id == "wa_7_abc"
    assert principal.permissions == frozenset({"finance.read", "reports.export"})
    assert principal.metadata == {"origin": "mcp"}


def test_resolve_identity_context_accepts_object_source_and_overrides():
    principal = resolve_identity_context(
        SimpleNamespace(user_id="9", company_id=33, role="collaborator", channel="web"),
        role="client",
        company_id="41",
    )

    assert principal.user_id == 9
    assert principal.company_id == 41
    assert principal.role == "cliente"
    assert principal.channel == "web"


def test_validate_company_id_allows_matching_company_and_sets_resolution():
    principal = PrincipalContext(user_id=1, company_id=12, role="colaborador")

    decision = validate_company_id(principal, 12)

    assert decision.allowed is True
    assert decision.resolved_company_id == 12
    assert "requested_matches_principal" in decision.checks


def test_validate_company_id_blocks_mismatch_without_accessible_list():
    principal = PrincipalContext(user_id=1, company_id=12, role="colaborador")

    decision = validate_company_id(principal, 99)

    assert decision.allowed is False
    assert decision.resolved_company_id == 12
    assert "requested_company_mismatch" in decision.checks


def test_validate_company_id_allows_admin_when_company_in_accessible_list():
    principal = PrincipalContext(user_id=1, company_id=None, role="administrador")

    decision = validate_company_id(principal, 99, accessible_company_ids=[11, "99"])

    assert decision.allowed is True
    assert decision.resolved_company_id == 99
    assert "admin_accessible_company_match" in decision.checks


def test_validate_permission_enforces_role_matrix_by_domain_and_action():
    collaborator = PrincipalContext(user_id=2, company_id=12, role="colaborador")
    client = PrincipalContext(user_id=3, company_id=12, role="cliente")
    admin = PrincipalContext(user_id=4, company_id=12, role="administrador")

    collaborator_read = validate_permission(collaborator, domain="routine", action="read")
    collaborator_delete = validate_permission(collaborator, domain="finance", action="delete")
    client_delete = validate_permission(client, domain="routine", action="delete")
    admin_delete = validate_permission(admin, domain="finance", action="delete")

    assert collaborator_read.allowed is True
    assert collaborator_delete.allowed is False
    assert client_delete.allowed is False
    assert admin_delete.allowed is True


def test_validate_permission_blocks_finance_for_non_admin_profiles_by_profile_contract():
    collaborator = PrincipalContext(user_id=2, company_id=12, role="colaborador")
    client = PrincipalContext(user_id=3, company_id=12, role="cliente")

    collaborator_read = validate_permission(collaborator, domain="finance", action="read")
    client_read = validate_permission(client, domain="finance", action="discover")

    assert collaborator_read.allowed is False
    assert client_read.allowed is False
    assert "domain_forbidden_by_profile_contract" in collaborator_read.checks
    assert "domain_forbidden_by_profile_contract" in client_read.checks


def test_validate_permission_supports_projects_meetings_and_canonical_actions():
    collaborator = PrincipalContext(user_id=5, company_id=12, role="colaborador")
    admin_tecnico = PrincipalContext(user_id=6, company_id=12, role="admin_tecnico")

    project_discover = validate_permission(collaborator, domain="projects", action="discover")
    meeting_search = validate_permission(collaborator, domain="meetings", action="search")
    operations_audit = validate_permission(admin_tecnico, domain="operations", action="audit")

    assert project_discover.allowed is True
    assert meeting_search.allowed is True
    assert operations_audit.allowed is True


def test_validate_permission_supports_workload_only_for_admin_profiles():
    collaborator = PrincipalContext(user_id=6, company_id=12, role="colaborador")
    admin = PrincipalContext(user_id=7, company_id=12, role="administrador")
    admin_tecnico = PrincipalContext(user_id=8, company_id=12, role="admin_tecnico")

    collaborator_workload = validate_permission(collaborator, domain="workload", action="read")
    admin_workload = validate_permission(admin, domain="workload", action="analyze")
    admin_tecnico_workload = validate_permission(admin_tecnico, domain="workload", action="audit")

    assert collaborator_workload.allowed is False
    assert admin_workload.allowed is True
    assert admin_tecnico_workload.allowed is True


def test_validate_permission_blocks_legacy_diagnostics_for_colaborador():
    collaborator = PrincipalContext(user_id=7, company_id=12, role="colaborador")
    admin_tecnico = PrincipalContext(user_id=8, company_id=12, role="admin_tecnico")

    collaborator_read = validate_permission(collaborator, domain="diagnostics", action="read")
    admin_read = validate_permission(admin_tecnico, domain="diagnostics", action="read")

    assert collaborator_read.allowed is False
    assert admin_read.allowed is True


def test_validate_permission_supports_identity_split_and_blocks_unknown_domain_even_for_admin():
    collaborator = PrincipalContext(user_id=9, company_id=12, role="colaborador")
    admin = PrincipalContext(user_id=9, company_id=12, role="administrador")

    self_service = validate_permission(collaborator, domain="identity_self_service", action="update")
    admin_identity = validate_permission(admin, domain="identity_admin", action="read")
    decision = validate_permission(admin, domain="identity_legacy", action="read")

    assert self_service.allowed is True
    assert admin_identity.allowed is True
    assert decision.allowed is False
    assert "unknown_domain_rejected" in decision.checks


def test_prepare_enforcement_combines_tenant_and_permission_checks():
    plan = prepare_enforcement(
        {"user_id": 7, "company_id": 12, "role": "collaborator"},
        requested_company_id="12",
        domain="routine",
        action="update",
    )

    assert plan.allowed is True
    assert plan.reason == "ok"
    assert plan.tenant.allowed is True
    assert plan.permission.allowed is True


def test_require_company_scope_raises_for_cross_tenant_access():
    try:
        require_company_scope(
            {"user_id": 7, "company_id": 12, "role": "collaborator"},
            requested_company_id=99,
        )
    except TenantScopeError as exc:
        assert exc.decision.allowed is False
        assert exc.decision.requested_company_id == 99
    else:
        raise AssertionError("TenantScopeError deveria ter sido lançado")


def test_require_permission_raises_for_sensitive_operation_without_role():
    try:
        require_permission(
            {"user_id": 7, "company_id": 12, "role": "client"},
            domain="finance",
            action="delete",
        )
    except PermissionDeniedError as exc:
        assert exc.decision.allowed is False
        assert exc.decision.domain == "finance"
        assert exc.decision.action == "delete"
    else:
        raise AssertionError("PermissionDeniedError deveria ter sido lançado")
