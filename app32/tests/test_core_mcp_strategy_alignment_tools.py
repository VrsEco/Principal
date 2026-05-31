from src.core.mcp_strategy_alignment_tools import register_strategy_alignment_tools
from src.intelligence.mcp_contracts import APP32_ALLOWED_ANALYSIS_CATALOG


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


def test_strategy_alignment_tools_register_and_return_envelopes(monkeypatch):
    mcp = _FakeMCP()
    monkeypatch.setattr(
        "src.core.mcp_strategy_alignment_tools.StrategyAlignmentN1Service.get_identity",
        staticmethod(lambda company_id, status="confirmed": {"company_id": company_id, "mission": "Salvar água", "status": status}),
    )
    monkeypatch.setattr(
        "src.core.mcp_strategy_alignment_tools.StrategyAlignmentN1Service.upsert_identity",
        staticmethod(lambda company_id, payload, user_id=None: {"company_id": company_id, **payload}),
    )
    monkeypatch.setattr(
        "src.core.mcp_strategy_alignment_tools.StrategyAlignmentN1Service.run_alignment_analysis",
        staticmethod(lambda company_id: {"company_id": company_id, "analysis_id": "strategic_alignment_n1"}),
    )
    monkeypatch.setattr(
        "src.core.mcp_strategy_alignment_tools.StrategyAlignmentN1Service.list_maturation_backlog",
        staticmethod(lambda company_id, **kwargs: {"company_id": company_id, "items": [], "summary": {"backlog_open": 0}}),
    )
    monkeypatch.setattr(
        "src.core.mcp_strategy_alignment_tools.StrategyAlignmentN1Service.review_maturation_item",
        staticmethod(lambda company_id, item_id, decision, reviewer_user_id=None, notes=None: {"reviewed": True, "decision": decision, "item_id": item_id}),
    )

    register_strategy_alignment_tools(mcp)

    expected_tools = {
        "get_strategy_identity_tool",
        "get_organizational_identity_tool",
        "upsert_strategy_identity_tool",
        "upsert_organizational_identity_tool",
        "get_process_strategy_profile_tool",
        "get_process_strategic_profile_tool",
        "upsert_process_strategy_profile_tool",
        "upsert_process_strategic_profile_tool",
        "list_process_strategy_alignment_links_tool",
        "upsert_process_strategy_alignment_link_tool",
        "delete_process_strategy_alignment_link_tool",
        "list_indicator_line_of_sight_tool",
        "upsert_indicator_line_of_sight_tool",
        "delete_indicator_line_of_sight_tool",
        "list_strategy_maturation_backlog_tool",
        "review_strategy_maturation_item_tool",
        "get_strategy_alignment_n1_readiness_tool",
        "get_strategic_alignment_n1_readiness_tool",
        "run_strategy_alignment_n1_analysis_tool",
        "analyze_strategic_alignment_n1_tool",
    }
    assert expected_tools.issubset(set(mcp.registered))

    read_response = mcp.registered["get_strategy_identity_tool"](company_id=1)
    write_response = mcp.registered["upsert_strategy_identity_tool"](
        company_id=1,
        payload={"mission": "Salvar água"},
    )
    analysis_response = mcp.registered["analyze_strategic_alignment_n1_tool"](company_id=1)
    backlog_response = mcp.registered["list_strategy_maturation_backlog_tool"](company_id=1, status="pending")
    review_response = mcp.registered["review_strategy_maturation_item_tool"](
        company_id=1,
        item_id=10,
        decision="hold",
        user_id=7,
    )

    assert read_response["success"] is True
    assert read_response["data"]["mission"] == "Salvar água"
    assert write_response["success"] is True
    assert write_response["meta"]["human_gate_required"] is True
    assert analysis_response["success"] is True
    assert analysis_response["meta"]["scope"] == "mcp_analytics"
    assert backlog_response["success"] is True
    assert review_response["meta"]["human_gate_required"] is True
    assert review_response["data"]["decision"] == "hold"


def test_strategy_alignment_analysis_catalog_contract_is_published():
    contract = APP32_ALLOWED_ANALYSIS_CATALOG.get_analysis("strategic_alignment_n1")

    assert contract is not None
    assert APP32_ALLOWED_ANALYSIS_CATALOG.get_analysis("strategy_alignment_n1") is contract
    assert contract.domain == "strategy"
    assert contract.status == "ready"
    assert contract.allowed_surfaces == ["analytics"]
    assert "analyze_strategic_alignment_n1_tool" in contract.capability_names
    assert "list_strategy_maturation_backlog_tool" in contract.capability_names
    assert "review_strategy_maturation_item_tool" in contract.capability_names
    assert "strategic.alignment_n1" in contract.required_read_models
    assert contract.cross_tenant_allowed is False
    assert contract.sql_freeform_allowed is False
