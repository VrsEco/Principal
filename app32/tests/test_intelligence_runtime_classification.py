from src.intelligence.runtime_classification import (
    RUNTIME_COMPONENTS,
    RUNTIME_TOPOLOGY,
    describe_runtime_topology,
    list_legacy_graph_components,
    list_runtime_components,
)


def test_runtime_topology_marks_official_and_legacy_graphs():
    topology = describe_runtime_topology()

    assert topology["official"]["entrypoint"] == "src.intelligence.execution.run_agent_with_context"
    assert topology["official"]["work_agent_graph"] == "src.intelligence.work_agents.graph.create_work_agent_workflow"
    assert "src.intelligence.graph" in topology["legacy"]["graph_modules"]
    assert "execution -> menu_engine -> work_agents.graph" in topology["legacy"]["note"]
    assert RUNTIME_TOPOLOGY.official_tool_catalog == "src.intelligence.tool_catalog.catalog"


def test_runtime_components_separate_official_from_legacy_paths():
    official = list_runtime_components(status="official")
    legacy_graphs = list_legacy_graph_components()

    assert {component.module for component in official} >= {
        "src.intelligence.execution.run_agent_with_context",
        "src.intelligence.menu_engine.handle_menu_message",
        "src.intelligence.work_agents.graph.create_work_agent_workflow",
        "src.intelligence.tool_catalog.catalog",
    }
    assert {component.module for component in legacy_graphs} == {
        "src.intelligence.graph.create_agent_workflow",
        "src.intelligence.graphs.main_graph.create_main_graph",
    }
    assert all(component.allowed_for_new_work for component in official)
    assert all(not component.allowed_for_new_work for component in legacy_graphs)


def test_runtime_topology_export_includes_migration_actions():
    topology = describe_runtime_topology()

    legacy_components = topology["legacy"]["components"]
    compatibility_components = topology["compatibility"]["components"]

    assert legacy_components
    assert compatibility_components
    assert all(component["next_action"] for component in legacy_components)
    assert all(component["allowed_for_new_work"] is False for component in legacy_components)
    assert len(RUNTIME_COMPONENTS) >= 8
