from src.intelligence.security.cross_tenant_matrix import (
    CROSS_TENANT_DOMAIN_MATRIX,
    REQUIRED_ASSERTS,
    REQUIRED_PROFILES,
    REQUIRED_SURFACES,
    domains_requiring_analytics_guard,
    domains_requiring_mutation_isolation,
    get_cross_tenant_domain_requirement,
)


def test_cross_tenant_matrix_covers_core_ai_mcp_domains() -> None:
    domains = {item.domain for item in CROSS_TENANT_DOMAIN_MATRIX}

    assert {"routine", "process", "project", "meeting", "strategy", "finance", "admin", "analytics", "diagnostics"}.issubset(domains)
    assert REQUIRED_PROFILES == ("colaborador", "cliente", "administrador", "administrador_tecnico")
    assert REQUIRED_SURFACES == ("user", "admin", "analytics", "ops")


def test_finance_domain_has_full_strict_requirements() -> None:
    finance = get_cross_tenant_domain_requirement("finance")

    assert finance.requires_read_isolation is True
    assert finance.requires_mutation_isolation is True
    assert finance.requires_surface_rbac is True
    assert finance.requires_analytics_guard is True
    assert set(REQUIRED_ASSERTS).issubset(set(finance.minimum_asserts))


def test_admin_and_analytics_have_expected_surface_constraints() -> None:
    admin = get_cross_tenant_domain_requirement("admin")
    analytics = get_cross_tenant_domain_requirement("analytics")

    assert admin.requires_analytics_guard is False
    assert "surface_denies_admin_domain_to_user" in admin.minimum_asserts
    assert analytics.requires_mutation_isolation is False
    assert "analytics_surface_is_read_only" in analytics.minimum_asserts


def test_domain_groups_for_next_backlog() -> None:
    assert "project" in domains_requiring_mutation_isolation()
    assert "finance" in domains_requiring_mutation_isolation()
    assert "analytics" in domains_requiring_analytics_guard()
    assert "strategy" in domains_requiring_analytics_guard()
