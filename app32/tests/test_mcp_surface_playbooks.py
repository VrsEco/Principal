import pytest
from pydantic import ValidationError

from src.core.mcp_surface_playbook_tools import register_surface_playbook_tools
from src.intelligence.mcp_contracts import (
    APP32_CRUD_CONTRACTS_MANIFEST,
    APP32_SURFACE_PLAYBOOKS_MANIFEST,
    SurfacePlaybook,
)


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


def test_surface_playbooks_cover_all_surfaces():
    surfaces = {playbook.surface for playbook in APP32_SURFACE_PLAYBOOKS_MANIFEST.playbooks}
    assert surfaces == {"user", "admin", "analytics", "ops"}


def test_describe_surface_playbook_returns_expected_surface_contract():
    mcp = _FakeMCP()
    register_surface_playbook_tools(mcp)
    tool = mcp.registered["describe_app32_surface_playbooks_tool"]

    for surface in ("user", "admin", "analytics", "ops"):
        payload = tool(surface)
        assert payload["success"] is True
        assert payload["meta"]["operation"] == "surface_playbooks.describe"
        assert payload["data"]["surface"] == surface


def test_surface_playbook_rejects_invalid_surface():
    mcp = _FakeMCP()
    register_surface_playbook_tools(mcp)
    tool = mcp.registered["describe_app32_surface_playbooks_tool"]

    payload = tool("invalid")

    assert payload["success"] is False
    assert payload["error"]["code"] == "surface_playbook_not_found"


def test_surface_contract_rules_and_crud_coherence():
    user_playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface("user")
    analytics_playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface("analytics")
    admin_playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface("admin")
    ops_playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface("ops")

    assert user_playbook is not None
    assert analytics_playbook is not None
    assert admin_playbook is not None
    assert ops_playbook is not None

    assert "finance" not in user_playbook.allowed_domains
    assert any("nunca mutar dados" in item.lower() for item in analytics_playbook.forbidden_actions)
    assert any("gate humano" in rule.rule.lower() or "confirmação humana" in rule.rule.lower() for rule in admin_playbook.interaction_rules)
    assert "finance" not in ops_playbook.allowed_domains

    crud_domains = {contract.domain for contract in APP32_CRUD_CONTRACTS_MANIFEST.domains}
    allowed_non_crud_domains = {"governance", "analytics", "operations", "workload", "identity_self_service", "identity_admin"}
    assert set(user_playbook.allowed_domains).issubset(crud_domains | allowed_non_crud_domains)
    assert set(admin_playbook.allowed_domains).issubset(crud_domains | allowed_non_crud_domains)


def test_surface_playbook_forbids_extra_fields():
    with pytest.raises(ValidationError):
        SurfacePlaybook(
            surface="analytics",
            title="Analytics",
            objective="Playbook analítico seguro.",
            actor_roles=["administrador"],
            allowed_domains=["analytics"],
            discovery_tools=["list_analytics_app32_capabilities"],
            startup_checklist=["Definir tenant", "Validar leitura"],
            interaction_rules=[
                {"rule": "Executar apenas leitura.", "rationale": "Evita mutação."},
                {"rule": "Respeitar tenant.", "rationale": "Evita cross-tenant."},
            ],
            forbidden_actions=["Nunca mutar dados operacionais ou financeiros."],
            example_flows=[{"title": "Ler diagnóstico", "steps": ["Descobrir", "Ler"]}],
            unexpected="blocked",  # type: ignore[arg-type]
        )
