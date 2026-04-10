from pathlib import Path

from src.core.mcp_surface_registry import get_surface_manifest
from src.intelligence.mcp_contracts import APP32_SURFACE_PLAYBOOKS_MANIFEST


RUNBOOK = Path(__file__).resolve().parents[1] / "docs" / "governance" / "mcp_user_admin_production_runbook.md"


def test_mcp_user_admin_runbook_exists_with_required_sections():
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "Runbook de Produção MCP User/Admin" in text
    assert "## 4. Checklist pré-release" in text
    assert "## 5. Smoke pós-deploy" in text
    assert "## 7. Critérios de congelamento de tool" in text
    assert "## 8. Rollback" in text
    assert "MCP_USER_ADMIN_RUNBOOK_SMOKE_OK True True" in text


def test_mcp_user_admin_runbook_references_canonical_sources():
    text = RUNBOOK.read_text(encoding="utf-8")

    for source in (
        "src.intelligence.tool_catalog.catalog",
        "src.core.mcp_surface_registry",
        "src.intelligence.mcp_contracts.profiles",
        "src.intelligence.mcp_contracts.playbooks",
        "src.intelligence.mcp_contracts.domain_playbooks",
        "src.intelligence.security.tool_policy",
        "src.intelligence.execution.run_agent_with_context",
    ):
        assert source in text


def test_mcp_user_admin_runtime_manifests_match_runbook_boundaries():
    user_manifest = get_surface_manifest("user")
    admin_manifest = get_surface_manifest("admin")
    user_playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface("user")
    admin_playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface("admin")

    assert "mcp_user" in user_manifest["summary"]["scopes"]
    assert "mcp_admin" in admin_manifest["summary"]["scopes"]
    assert user_playbook is not None
    assert admin_playbook is not None
    assert "finance" not in user_playbook.allowed_domains
    assert "finance" in admin_playbook.allowed_domains
    assert admin_playbook.default_scope == "explicit_company_id"


def test_mcp_user_admin_runbook_forbids_unsafe_shortcuts():
    text = RUNBOOK.read_text(encoding="utf-8").lower()

    assert "não usar sql livre" in text
    assert "não inferir `company_id`" in text
    assert "mutação financeira acessível pela surface `user`" in text
    assert "vazamento cross-tenant" in text
