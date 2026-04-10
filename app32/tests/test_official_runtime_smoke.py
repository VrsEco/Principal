from contextlib import contextmanager

from langgraph.checkpoint.memory import MemorySaver

from src.intelligence import execution
from src.intelligence.menu_engine import MenuInterceptResult
from src.intelligence.runtime_classification import describe_runtime_topology
from src.intelligence.tool_context import active_company_id_ctx, active_user_id_ctx
from src.intelligence.tool_catalog import catalog, tools
from src.intelligence.work_agents import graph as work_agents_graph


def test_official_runtime_topology_smoke_points_to_supported_chain():
    topology = describe_runtime_topology()

    assert topology["official"]["entrypoint"] == "src.intelligence.execution.run_agent_with_context"
    assert topology["official"]["menu_router"] == "src.intelligence.menu_engine.handle_menu_message"
    assert topology["official"]["work_agent_graph"] == "src.intelligence.work_agents.graph.create_work_agent_workflow"
    assert topology["official"]["tool_catalog"] == "src.intelligence.tool_catalog.catalog"
    assert all(component["allowed_for_new_work"] for component in topology["official"]["components"])
    assert all(not component["allowed_for_new_work"] for component in topology["legacy"]["components"])


def test_work_agent_graph_smoke_compiles_expected_nodes_without_llm_call():
    graph = work_agents_graph.create_work_agent_workflow(checkpointer=MemorySaver())
    runtime_graph = graph.get_graph()

    assert hasattr(graph, "invoke")
    assert {
        "__start__",
        "supervisor",
        "strategist",
        "business_architect",
        "operations",
        "finance",
        "auditor",
        "sapiens",
        "engineering",
        "tools",
        "__end__",
    } <= set(runtime_graph.nodes)
    assert work_agents_graph.tools == tools
    assert catalog.get_langchain_tools() == tools


def test_run_agent_with_context_smoke_menu_intercept_bypasses_llm_graph(monkeypatch):
    captured_usage = {}

    monkeypatch.setattr(execution, "_audit_execution_event", lambda **kwargs: {})
    monkeypatch.setattr(execution, "set_sapiens_context", lambda **kwargs: "token")
    monkeypatch.setattr(execution, "reset_sapiens_context", lambda token: None)
    monkeypatch.setattr(execution, "set_legacy_tool_context", lambda **kwargs: "legacy")
    monkeypatch.setattr(execution, "reset_legacy_tool_context", lambda token: None)
    monkeypatch.setattr(
        execution,
        "_capture_workflow_usage_from_execution",
        lambda **kwargs: captured_usage.update(kwargs),
    )
    monkeypatch.setattr(
        execution,
        "handle_menu_message",
        lambda **kwargs: MenuInterceptResult(
            handled=True,
            response_text="Menu interceptado com segurança.",
            metadata={"menu_engine": {"intercept_stage": "smoke"}},
        ),
    )
    monkeypatch.setattr(
        execution,
        "create_work_agent_workflow",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("graph should not be invoked")),
    )

    response = execution.run_agent_with_context(
        user_id=101,
        user_msg="menu",
        channel="web",
        thread_id="smoke-menu",
        company_id=202,
    )

    assert response["messages"] == [("ai", "Menu interceptado com segurança.")]
    assert response["next_node"] == "sapiens"
    assert response["menu_metadata"]["execution_context"]["menu_intercepted"] is True
    assert response["menu_metadata"]["execution_context"]["company_id"] == 202
    assert captured_usage["thread_id"] == "smoke-menu"


def test_run_agent_with_context_smoke_graph_path_sets_context_and_uses_official_graph(monkeypatch):
    captured = {}

    monkeypatch.setattr(execution, "_audit_execution_event", lambda **kwargs: {})
    monkeypatch.setattr(
        execution,
        "handle_menu_message",
        lambda **kwargs: MenuInterceptResult(handled=False, metadata={"workflow_discovery": {"route": "smoke"}}),
    )
    monkeypatch.setattr(execution, "_capture_workflow_usage_from_execution", lambda **kwargs: None)
    monkeypatch.setattr(execution, "_capture_workflow_gap_from_execution", lambda **kwargs: None)

    @contextmanager
    def fake_checkpointer():
        yield object()

    class FakeOfficialGraph:
        def invoke(self, inputs, config=None):
            captured["inputs"] = dict(inputs)
            captured["config"] = dict(config or {})
            captured["ctx_user"] = active_user_id_ctx.get()
            captured["ctx_company"] = active_company_id_ctx.get()
            return {"messages": [("ai", "runtime oficial ok")]}

    monkeypatch.setattr(execution, "get_checkpointer", fake_checkpointer)
    monkeypatch.setattr(execution, "create_work_agent_workflow", lambda checkpointer: FakeOfficialGraph())

    response = execution.run_agent_with_context(
        user_id=303,
        user_msg="teste runtime oficial",
        channel="whatsapp",
        thread_prefix="wa",
        thread_id="smoke-graph",
        company_id=404,
    )

    assert response["messages"] == [("ai", "runtime oficial ok")]
    assert captured["inputs"] == {
        "messages": [("user", "teste runtime oficial")],
        "user_id": 303,
        "company_id": 404,
    }
    assert captured["config"]["configurable"]["thread_id"] == "smoke-graph"
    assert captured["ctx_user"] == 303
    assert captured["ctx_company"] == 404
    assert active_user_id_ctx.get() is None
    assert active_company_id_ctx.get() is None


def test_run_agent_with_context_smoke_blocks_without_tenant_before_menu_or_graph(monkeypatch):
    monkeypatch.setattr(execution, "_audit_execution_event", lambda **kwargs: {})
    monkeypatch.setattr(execution, "_capture_workflow_usage_from_execution", lambda **kwargs: None)
    monkeypatch.setattr(
        execution,
        "handle_menu_message",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("menu should not be called")),
    )
    monkeypatch.setattr(
        execution,
        "create_work_agent_workflow",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("graph should not be called")),
    )

    response = execution.run_agent_with_context(
        user_id=505,
        user_msg="teste sem empresa",
        channel="web",
        thread_id="smoke-denied",
        company_id=None,
    )

    assert response["next_node"] == "sapiens"
    assert "contexto de empresa nao foi validado" in response["messages"][0][1]
    assert response["menu_metadata"]["ai_security"]["tenant_allowed"] is False
