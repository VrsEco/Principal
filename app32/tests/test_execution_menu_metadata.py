import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence import execution
from src.intelligence.menu_engine import MenuInterceptResult


def test_run_agent_with_context_returns_menu_metadata_on_intercept(monkeypatch):
    monkeypatch.setattr(execution, "set_sapiens_context", lambda **kwargs: "token")
    monkeypatch.setattr(execution, "reset_sapiens_context", lambda token: None)
    monkeypatch.setattr(
        execution,
        "handle_menu_message",
        lambda **kwargs: MenuInterceptResult(
            handled=True,
            response_text="Resumo pronto",
            metadata={
                "menu_engine": {
                    "intercept_stage": "implicit_discovery_selected",
                    "selected_action_key": "summary.week",
                },
                "workflow_discovery": {
                    "strategy": "hybrid",
                    "selected_action_key": "summary.week",
                },
            },
        ),
    )

    response = execution.run_agent_with_context(
        user_id=3,
        user_msg="quero o resumo da semana",
        channel="web",
        thread_id="web_3_sapiens",
        company_id=9,
    )

    assert response["messages"] == [("ai", "Resumo pronto")]
    assert response["next_node"] == "sapiens"
    assert response["menu_metadata"]["menu_engine"]["intercept_stage"] == "implicit_discovery_selected"
    assert response["menu_metadata"]["workflow_discovery"]["selected_action_key"] == "summary.week"
