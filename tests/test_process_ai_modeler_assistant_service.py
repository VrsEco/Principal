import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app32"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.process_ai_modeler_assistant_service import ProcessAIModelerAssistantService


def test_build_catalog_exposes_expected_defaults():
    catalog = ProcessAIModelerAssistantService.build_catalog()

    assert "task_operation_options" in catalog
    assert "gateway_operation_options" in catalog
    assert "human_review" in catalog["fallback_actions"]
    assert isinstance(catalog["tool_items"], list)


def test_suggest_gateway_uses_closed_routes_when_llm_fails(monkeypatch):
    class BrokenLLM:
        def invoke(self, _messages):
            raise RuntimeError("offline")

    class DummyExpert:
        def with_structured_output(self, _schema):
            return BrokenLLM()

    monkeypatch.setattr(
        "services.process_ai_modeler_assistant_service.llm_expert",
        DummyExpert(),
    )

    result = ProcessAIModelerAssistantService.suggest(
        {
            "semantic_type": "ai_gateway",
            "objective": "Decidir se arquiva ou envia para financeiro.",
            "next_candidates": [
                {"element_id": "Activity_Archive", "element_name": "Arquivar"},
                {"element_id": "Activity_Finance", "element_name": "Enviar Financeiro"},
            ],
        }
    )

    suggestion = result["suggestion"]
    assert suggestion["execution_mode"] == "ai_decision"
    assert suggestion["allowed_decisions"] == ["arquivar", "enviar_financeiro"]
    assert suggestion["decision_routes"]["arquivar"] == "Activity_Archive"
    assert suggestion["decision_routes"]["enviar_financeiro"] == "Activity_Finance"


def test_merge_normalizes_llm_decision_objects():
    merged = ProcessAIModelerAssistantService._merge_with_heuristic(
        {"execution_mode": "ai_decision"},
        {
            "execution_mode": "ai_decision",
            "allowed_decisions": [
                {"decision": "archive", "element_id": "Task_Archive"},
                {"decision": "human_review", "element_id": "Task_Review"},
            ],
        },
    )

    assert merged["allowed_decisions"] == ["archive", "human_review"]
    assert merged["decision_routes"] == {
        "archive": "Task_Archive",
        "human_review": "Task_Review",
    }
