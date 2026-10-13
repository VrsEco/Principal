"""Coortes de ESCRITA do mcp-versus (sub-onda 2A): desligadas por padrão, por assunto, com o contrato como porta."""
from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

import src.core.mcp_surface_registry as registry
import src.core.mcp_write_cohorts as cohorts
from src.core.mcp_cohort_contract import probe_registered_tools
from src.core.mcp_gate_policy import requires_persisted_approval
from src.core.mcp_mutation_contract import audit_mutation_tool
from src.intelligence.tool_catalog import catalog

BASELINE = Path(__file__).parent / "data" / "mcp_mutation_violations_baseline.json"
USER = SimpleNamespace(scopes=("mcp:access", "mcp:user", "mcp:finance"))
EXPECTED = {
    "projects": {"create_project", "update_project", "update_project_task_secure"},
    "operations": {"request_engineering_suggestion", "request_new_app32_integration"},
    "meetings": {"log_meeting_discussion"},
    "processes": {
        "create_process_bpmn_activity_tool",
        "create_process_pop_step_for_bpmn_tool",
        "draft_process_pop_step_description_tool",
        "attach_process_pop_step_static_image_tool",
        "update_process_instance",
    },
    "routine": {
        "create_work_calendar_event_tool",
        "create_work_journey_absence_request_tool",
        "create_work_journey_manual_task_tool",
        "create_work_journey_transfer_request_tool",
        "delete_work_calendar_event_tool",
        "generate_work_journey_agenda_tool",
        "lock_work_journey_agenda_tool",
        "move_work_journey_agenda_item_tool",
        "save_routine_journey_binding_tool",
        "save_work_journey_block_tool",
        "save_work_journey_rule_tool",
        "unlock_work_journey_agenda_tool",
        "update_work_calendar_event_tool",
        "update_work_journey_item_tool",
    },
    "strategy": {
        "correct_plan_global_okrs_tool",
        "create_and_link_plan_global_okrs_tool",
        "create_area_key_result",
        "create_area_okr",
        "create_global_key_result",
        "create_global_okr",
        "create_sector_okr_structure_tool",
        "create_single_plan_driver_tool",
        "review_strategy_maturation_item_tool",
        "sync_plan_participants_tool",
        "update_plan_section",
        "upsert_indicator_line_of_sight_tool",
        "upsert_organizational_identity_tool",
        "upsert_process_strategic_profile_tool",
        "upsert_process_strategy_alignment_link_tool",
        "upsert_process_strategy_profile_tool",
        "upsert_strategy_identity_tool",
    },
    "commercial": {
        "add_commercial_contract_item",
        "close_commercial_contract",
        "create_commercial_contract",
        "create_commercial_issuer",
        "toggle_commercial_catalog_structure_item",
        "toggle_commercial_customer_portfolio",
        "toggle_commercial_product_service",
        "update_commercial_catalog_structure_item",
        "update_commercial_contract_general",
        "update_commercial_contract_item",
        "update_commercial_customer",
        "update_commercial_customer_portfolio",
        "update_commercial_issuer",
        "update_commercial_offer_contract",
        "update_commercial_product_service",
    },
    "admin_ops": {
        "approve_work_journey_absence_request_tool",
        "approve_work_journey_transfer_request_tool",
        "delete_indicator_line_of_sight_tool",
        "delete_process_strategy_alignment_link_tool",
        "delete_work_journey_block_tool",
        "delete_work_journey_manual_task_tool",
        "delete_work_journey_rule_tool",
    },
    "deletions": {
        "delete_project",
        "delete_project_task_secure",
        "restore_project_task_secure",
        "delete_meeting_secure",
    },
    "finance_setup": {
        "create_financial_catalog_item",
        "create_financial_classification_rule",
        "create_financial_automation_rule",
        "create_financial_budget_version",
        "create_financial_budget_line",
        "create_financial_budget_contract",
        "create_financial_budget_document",
        "create_financial_budget_document_schedules",
        "import_financial_budget_matrix",
        "upsert_financial_budget_matrix",
        "upsert_financial_domain_enablement",
        "generate_financial_report",
    },
    "finance_ledger": {
        "create_financial_direct_entry",
        "create_financial_bordero",
        "create_financial_bordero_settlement",
        "create_financial_entry_from_bank_reconciliation_row",
        "match_financial_bank_reconciliation_row",
        "reconcile_financial_import_batch",
        "create_financial_import_batch",
        "create_financial_ingestion_record",
        "replace_financial_allocations",
        "create_financial_schedule",
        "generate_due_financial_schedules",
    },
}
ALL = set().union(*EXPECTED.values())


def _server(monkeypatch, env):
    if env is None:
        monkeypatch.delenv("MCP_VERSUS_WRITE_DOMAINS", raising=False)
    else:
        monkeypatch.setenv("MCP_VERSUS_WRITE_DOMAINS", env)
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: True)
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: USER)
    server = registry.build_oauth_unified_mcp_server()
    listed = {tool.name for tool in asyncio.run(server.list_tools())}
    registered = {tool.name for tool in asyncio.run(FastMCP.list_tools(server))}
    return server, listed, registered


def test_cohort_content_is_exactly_the_approved_set():
    assert {k: set(v) for k, v in cohorts.WRITE_COHORT_TOOL_NAMES.items()} == EXPECTED
    assert len(cohorts.all_write_cohort_names()) == len(ALL) == 91


@pytest.mark.parametrize("value", [None, "", "none", "NONE", "  "])
def test_off_by_default_and_by_none(monkeypatch, value):
    _, listed, registered = _server(monkeypatch, value)
    assert ALL.isdisjoint(listed) and ALL.isdisjoint(registered), "desligada: não listar nem registrar"


@pytest.mark.parametrize("subject", sorted(EXPECTED))
def test_each_subject_turns_on_alone(monkeypatch, subject):
    _, listed, registered = _server(monkeypatch, subject)
    assert EXPECTED[subject] <= listed and EXPECTED[subject] <= registered
    other = ALL - EXPECTED[subject]
    assert other.isdisjoint(listed) and other.isdisjoint(registered)


def test_all_subjects_on_lists_everything_and_changes_nothing_else(monkeypatch):
    _, off, _ = _server(monkeypatch, None)
    _, on, _ = _server(monkeypatch, "projects,operations,meetings,processes,routine,strategy,commercial,admin_ops,deletions,finance_setup,finance_ledger")
    assert on - off == ALL and off - on == set()


def test_still_requires_user_scope_and_per_tool_permission(monkeypatch):
    monkeypatch.setenv("MCP_VERSUS_WRITE_DOMAINS", "projects,operations,meetings,processes,routine,strategy,commercial,admin_ops,deletions,finance_setup,finance_ledger")
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: SimpleNamespace(scopes=("mcp:access",)))
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: True)
    server = registry.build_oauth_unified_mcp_server()
    assert ALL.isdisjoint({t.name for t in asyncio.run(server.list_tools())})
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: USER)
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: False)
    server = registry.build_oauth_unified_mcp_server()
    assert ALL.isdisjoint({t.name for t in asyncio.run(server.list_tools())})


def test_manifest_follows_the_flag_and_reports_the_enforced_gate(monkeypatch):
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: True)
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: USER)
    monkeypatch.delenv("MCP_VERSUS_WRITE_DOMAINS", raising=False)
    off = {t["name"] for t in registry.get_unified_manifest()["tools"]}
    monkeypatch.setenv("MCP_VERSUS_WRITE_DOMAINS", "projects,operations,meetings,processes,routine,strategy,commercial,admin_ops,deletions,finance_setup,finance_ledger")
    manifest = registry.get_unified_manifest()
    on = {t["name"]: t for t in manifest["tools"]}
    assert ALL.isdisjoint(off) and ALL <= set(on)
    assert all(on[name].get("human_gate") is (name in APPROVAL_IN_COHORTS) for name in ALL), "só excluir/encerrar exigem aprovação (D6)"


# ---- o contrato de mutações é a porta de entrada ------------------------------------------------
def test_every_cohort_tool_passes_the_mutation_contract_and_is_not_in_the_baseline():
    probes = probe_registered_tools()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    for name in sorted(ALL):
        problems = audit_mutation_tool(name, capability=catalog.get_tool_capability(name), probe=probes.get(name))
        assert not problems, f"{name}: {[(v.code, v.detail) for v in problems]}"
        assert name not in baseline, f"{name} está na linha de base de violações"


APPROVAL_IN_COHORTS = {
    "delete_work_calendar_event_tool", "close_commercial_contract", *EXPECTED["admin_ops"],
    # financeiras que lançam ou baixam valor (APPROVAL_TOOLS)
    "create_financial_direct_entry", "create_financial_bordero_settlement",
    "create_financial_entry_from_bank_reconciliation_row", "match_financial_bank_reconciliation_row",
    "reconcile_financial_import_batch", "replace_financial_allocations", "generate_due_financial_schedules",
    # exclusões e restauração (verbo delete ou risco alto com gate)
    *EXPECTED["deletions"],
}


def test_only_the_expected_cohort_tools_need_approval_under_d6():
    needing = {name for name in ALL if requires_persisted_approval(name, catalog.get_tool_capability(name))}
    assert needing == APPROVAL_IN_COHORTS, "criar e editar não exigem aprovação; excluir/encerrar exigem (D6)"


# ---- parâmetro do cliente oculto só no MCP ------------------------------------------------------
def test_requester_name_is_hidden_in_mcp_but_kept_for_the_chat(monkeypatch):
    server, _, _ = _server(monkeypatch, "operations")
    mcp_params = set(server._tool_manager.get_tool("request_engineering_suggestion").parameters["properties"])
    assert "requester_name" not in mcp_params and "company_id" in mcp_params

    chat_tool = next(t for t in catalog.get_langchain_tools() if t.name == "request_engineering_suggestion")
    assert "requester_name" in inspect.signature(chat_tool.func).parameters, "o chat segue com a assinatura original"


def test_hidden_parameter_adapter_injects_the_fixed_value_and_drops_the_schema_entry():
    from src.core.mcp_param_hiding import HIDDEN_CLIENT_PARAMETERS, adapt_for_mcp

    seen = {}

    def original(title: str, requester_name: str = "x", company_id: int = 0):
        seen.update(title=title, requester_name=requester_name, company_id=company_id)

    HIDDEN_CLIENT_PARAMETERS["__probe__"] = {"requester_name": None}
    try:
        adapted = adapt_for_mcp("__probe__", original)
        assert list(inspect.signature(adapted).parameters) == ["title", "company_id"]
        adapted(title="t", company_id=3)
        assert seen == {"title": "t", "requester_name": None, "company_id": 3}
    finally:
        HIDDEN_CLIENT_PARAMETERS.pop("__probe__", None)
    assert adapt_for_mcp("outra", original) is original


def test_hidden_parameter_is_also_removed_from_the_mcp_description():
    from src.core.mcp_param_hiding import description_for_mcp

    description = "Registra uma sugestão.\n:param title: Título.\n:param requester_name: Opcional.\n:param urgency: low, medium."
    cleaned = description_for_mcp("request_engineering_suggestion", description)
    assert "requester_name" not in cleaned and ":param title:" in cleaned and ":param urgency:" in cleaned
    assert description_for_mcp("outra", description) == description


def test_registered_engineering_suggestion_description_does_not_mention_the_hidden_parameter(monkeypatch):
    server, _, _ = _server(monkeypatch, "operations")
    tool = server._tool_manager.get_tool("request_engineering_suggestion")
    assert "requester_name" not in (tool.description or "")


def test_integration_request_declares_its_accepted_values_in_the_schema(monkeypatch):
    server, _, _ = _server(monkeypatch, "operations")
    props = server._tool_manager.get_tool("request_new_app32_integration").parameters["properties"]
    assert set(props["integration_mode"]["enum"]) == {"consume", "provide", "bidirectional"}
    assert set(props["technical_channel"]["enum"]) == {"api", "mcp", "api_mcp"}
    assert set(props["urgency"]["enum"]) == {"low", "medium", "high", "critical"}
    assert set(props["compliance_level"]["enum"]) == {"internal", "restricted", "sensitive"}


LEGACY_CHAT_TOOLS = {
    "update_user_contacts", "create_project_task", "delete_project_task", "complete_task", "log_work_hours",
    "request_deadline_extension", "escalate_technical_issue", "search_organizational_knowledge",
    "describe_app32_domain_playbooks_tool", "describe_app32_surface_playbooks_tool",
}


def test_legacy_chat_tools_never_enter_a_write_or_read_cohort():
    """As legadas do chat (sem company_id de primeiro nível, com identidade do cliente ou sem variante segura) não se publicam."""
    import src.core.mcp_read_cohorts as read_cohorts

    cohort_names = set(cohorts.all_write_cohort_names()) | set(read_cohorts.all_read_cohort_names())
    assert LEGACY_CHAT_TOOLS.isdisjoint(cohort_names), sorted(LEGACY_CHAT_TOOLS & cohort_names)


# ---- coortes financeiras: escopo mcp:finance e surface finance -------------------------------------
FINANCE_TOOLS = EXPECTED["finance_setup"] | EXPECTED["finance_ledger"]


def test_finance_cohorts_need_the_finance_scope_and_never_appear_for_user_only(monkeypatch):
    monkeypatch.setenv("MCP_VERSUS_WRITE_DOMAINS", "finance_setup,finance_ledger")
    monkeypatch.setattr(registry, "_has_authenticated_mcp_permission", lambda _p: True)
    monkeypatch.setattr(
        "src.core.mcp_http_auth.get_http_request_identity", lambda: SimpleNamespace(scopes=("mcp:access", "mcp:user"))
    )
    listed = {t.name for t in asyncio.run(registry.build_oauth_unified_mcp_server().list_tools())}
    assert FINANCE_TOOLS.isdisjoint(listed), "mutação financeira não vai pela surface user"
    monkeypatch.setattr("src.core.mcp_http_auth.get_http_request_identity", lambda: USER)
    listed = {t.name for t in asyncio.run(registry.build_oauth_unified_mcp_server().list_tools())}
    assert FINANCE_TOOLS <= listed


def test_finance_cohort_tools_run_under_the_finance_policy_surface(monkeypatch):
    seen = {}
    real = registry._register_tool

    def spy(mcp, tool, *, policy_surface=None, **kwargs):
        seen[tool.name] = policy_surface
        return real(mcp, tool, policy_surface=policy_surface, **kwargs)

    monkeypatch.setattr(registry, "_register_tool", spy)
    shared = {}
    real_shared = registry._register_shared_registrars

    def spy_shared(mcp, *, tool_names=None, policy_surface=None, **kwargs):
        for name in tool_names or ():
            shared[name] = policy_surface
        return real_shared(mcp, tool_names=tool_names, policy_surface=policy_surface, **kwargs)

    monkeypatch.setattr(registry, "_register_shared_registrars", spy_shared)
    _server(monkeypatch, "finance_setup,finance_ledger")
    placed = {**seen, **shared}
    assert FINANCE_TOOLS <= set(placed)
    assert {placed[name] for name in FINANCE_TOOLS} == {"finance"}


def test_finance_subjects_are_a_subset_of_the_cohorts_and_leave_out_the_known_gaps():
    assert set(cohorts.finance_cohort_names()) == FINANCE_TOOLS
    for excluded in ("create_financial_closing", "create_financial_entry", "create_financial_settlement",
                     "generate_commercial_billing_batch", "upsert_commercial_contract_fiscal_terms"):
        assert excluded not in FINANCE_TOOLS
