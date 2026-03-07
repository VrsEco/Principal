import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.agent_menu import AgentMenuOption
from src.intelligence.workflows import (
    WorkflowDefinition,
    WorkflowDiscoveryRequest,
    WorkflowDiscoveryResult,
    WorkflowMatch,
    build_explicit_workflow_trace,
    build_workflow_discovery_trace,
)


def test_build_workflow_discovery_trace_compacts_top_matches():
    workflow = WorkflowDefinition(
        code="3.5.4",
        title="Resumo Personalizado",
        action_key="summary.custom",
        keywords=["resumo personalizado"],
    )
    discovery = WorkflowDiscoveryResult(
        request=WorkflowDiscoveryRequest(text="resumo de 01/03/2026 a 05/03/2026"),
        matches=[
            WorkflowMatch(
                workflow=workflow,
                score=98,
                reasons=[
                    "semantic:data explicita",
                    "reranker:periodo customizado",
                    "semantic:resumo",
                    "lexical:personalizado",
                    "extra:motivo excedente",
                ],
            )
        ],
        telemetry={
            "strategy": "hybrid",
            "reranker_applied": True,
            "reranker_kind": "LLMWorkflowReranker",
            "merged_match_count": 4,
            "selected_code": workflow.code,
            "selected_action_key": workflow.action_key,
            "final_top_matches": [
                {
                    "code": workflow.code,
                    "action_key": workflow.action_key,
                    "score": 98,
                    "reasons": [
                        "semantic:data explicita",
                        "reranker:periodo customizado",
                        "semantic:resumo",
                        "lexical:personalizado",
                        "extra:motivo excedente",
                    ],
                }
            ],
        },
    )

    trace = build_workflow_discovery_trace(discovery)

    assert trace["strategy"] == "hybrid"
    assert trace["candidate_count"] == 4
    assert trace["selected_action_key"] == "summary.custom"
    assert trace["reranker_applied"] is True
    assert trace["reranker_kind"] == "LLMWorkflowReranker"
    assert len(trace["top_matches"]) == 1
    assert len(trace["top_matches"][0]["reasons"]) == 4


def test_build_explicit_workflow_trace_marks_explicit_selection():
    option = AgentMenuOption(
        code="1.4",
        title="Cadastrar Atividade de Projeto",
        action_key="project_task.create",
    )
    option.id = 14

    trace = build_explicit_workflow_trace(option, explicit_code="1.4")

    assert trace["strategy"] == "explicit_code"
    assert trace["explicit_code"] == "1.4"
    assert trace["selected_action_key"] == "project_task.create"
    assert trace["top_matches"][0]["reasons"] == ["explicit:code_match"]
