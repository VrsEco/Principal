"""Coorte whatsapp_status: desligada por padrão, mesmas ferramentas do módulo, gates e escopo do conector comum."""

import pytest

from src.core.mcp_gate_policy import requires_persisted_approval
from src.core.mcp_read_cohorts import token_scope_for
from src.core.mcp_whatsapp_status_tools import STATUS_TOOL_NAMES
from src.core.mcp_write_cohorts import WRITE_COHORT_TOOL_NAMES, enabled_write_domains
from src.intelligence.tool_catalog import catalog

GATED = {
    "publish_whatsapp_status_art", "publish_whatsapp_status_kit", "publish_whatsapp_status_test",
    "resume_whatsapp_status_schedule", "confirm_whatsapp_status_mobile",
    "configure_whatsapp_status_account", "register_whatsapp_status_approved_bundle",
}


def test_the_cohort_is_exactly_the_status_module_tools():
    assert tuple(WRITE_COHORT_TOOL_NAMES["whatsapp_status"]) == tuple(STATUS_TOOL_NAMES)


def test_it_is_off_by_default(monkeypatch):
    monkeypatch.delenv("MCP_VERSUS_WRITE_DOMAINS", raising=False)
    assert "whatsapp_status" not in enabled_write_domains()
    monkeypatch.setenv("MCP_VERSUS_WRITE_DOMAINS", "projects,finance_setup")
    assert "whatsapp_status" not in enabled_write_domains()
    monkeypatch.setenv("MCP_VERSUS_WRITE_DOMAINS", "whatsapp_status")
    assert enabled_write_domains() == {"whatsapp_status"}


@pytest.mark.parametrize("name", STATUS_TOOL_NAMES)
def test_every_tool_is_reachable_by_the_common_connector_and_keeps_the_admin_surface(name):
    capability = catalog.get_tool_capability(name)
    assert token_scope_for(capability) == "mcp:user"
    assert "mcp_admin" in {getattr(s, "value", s) for s in capability.scopes}
    assert capability.permissions and all(p.startswith("whatsapp_status.") for p in capability.permissions)


@pytest.mark.parametrize("name", STATUS_TOOL_NAMES)
def test_persisted_approval_covers_publication_resume_check_and_account_binding_only(name):
    capability = catalog.get_tool_capability(name)
    assert requires_persisted_approval(name, capability) is (name in GATED)


def test_no_status_tool_takes_identity_confirmation_or_free_media():
    from src.core.mcp_mutation_contract import CONFIRM_PARAM, IDENTITY_PARAM
    from src.core.mcp_surface_registry import _tool_map  # noqa: F401 - garante o registro do catálogo

    import inspect
    from types import SimpleNamespace

    registered = {}
    from src.core.mcp_whatsapp_status_tools import register_whatsapp_status_tools

    class _Collector:
        def tool(self):
            return lambda fn: registered.setdefault(fn.__name__, fn)

    register_whatsapp_status_tools(_Collector())
    assert set(registered) == set(STATUS_TOOL_NAMES)
    for name, fn in registered.items():
        params = tuple(inspect.signature(fn).parameters)
        assert "company_id" in params
        assert not [p for p in params if IDENTITY_PARAM.match(p) or CONFIRM_PARAM.match(p)], name
        assert not {"url", "path", "media_url", "token", "api_key", "instance_id"} & set(params), name
