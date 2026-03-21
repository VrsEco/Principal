import os
import sys
from contextlib import contextmanager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence import execution
from src.intelligence.menu_engine import MenuInterceptResult
from src.intelligence.tool_context import active_company_id_ctx, active_user_id_ctx


def test_run_agent_with_context_returns_menu_metadata_on_intercept(monkeypatch):
    captured_usage = {}

    monkeypatch.setattr(execution, "set_sapiens_context", lambda **kwargs: "token")
    monkeypatch.setattr(execution, "reset_sapiens_context", lambda token: None)
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
            response_text="Resumo pronto",
            metadata={
                "menu_engine": {
                    "intercept_stage": "implicit_discovery_selected",
                    "selected_option_code": "3.5.2",
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
    assert response["menu_metadata"]["execution_context"]["channel"] == "web"
    assert response["menu_metadata"]["execution_context"]["thread_id"] == "web_3_sapiens"
    assert response["menu_metadata"]["execution_context"]["menu_intercepted"] is True
    assert response["menu_metadata"]["execution_context"]["company_id"] == 9
    assert response["menu_metadata"]["execution_context"]["execution_id"]
    assert captured_usage["user_id"] == 3
    assert captured_usage["company_id"] == 9
    assert captured_usage["menu_metadata"]["menu_engine"]["selected_option_code"] == "3.5.2"


def test_run_agent_with_context_uses_contextvars_without_process_env(monkeypatch):
    captured = {}

    monkeypatch.setattr(execution, "set_sapiens_context", lambda **kwargs: "token")
    monkeypatch.setattr(execution, "reset_sapiens_context", lambda token: None)
    monkeypatch.setattr(
        execution,
        "handle_menu_message",
        lambda **kwargs: MenuInterceptResult(handled=False, metadata={"workflow_discovery": {"strategy": "hybrid"}}),
    )

    @contextmanager
    def fake_checkpointer():
        yield object()

    class FakeGraph:
        def invoke(self, inputs, config=None):
            captured["ctx_user_inside"] = active_user_id_ctx.get()
            captured["ctx_company_inside"] = active_company_id_ctx.get()
            captured["inputs"] = inputs
            captured["config"] = config
            return {"messages": [("ai", "ok")], "menu_metadata": {"agent": {"selected": "sapiens"}}}

    captured_gap = {}
    captured_usage = {}

    monkeypatch.setattr(execution, "get_checkpointer", fake_checkpointer)
    monkeypatch.setattr(execution, "create_work_agent_workflow", lambda checkpointer: FakeGraph())
    monkeypatch.setattr(
        execution,
        "_capture_workflow_gap_from_execution",
        lambda **kwargs: captured_gap.update(kwargs),
    )
    monkeypatch.setattr(
        execution,
        "_capture_workflow_usage_from_execution",
        lambda **kwargs: captured_usage.update(kwargs),
    )

    os.environ.pop("ACTIVE_USER_ID", None)
    os.environ.pop("ACTIVE_COMPANY_ID", None)

    response = execution.run_agent_with_context(
        user_id=7,
        user_msg="teste",
        channel="whatsapp",
        thread_prefix="wa",
        thread_id="wa_7_x",
        company_id=11,
    )

    assert captured["ctx_user_inside"] == 7
    assert captured["ctx_company_inside"] == 11
    assert active_user_id_ctx.get() is None
    assert active_company_id_ctx.get() is None
    assert "ACTIVE_USER_ID" not in os.environ
    assert "ACTIVE_COMPANY_ID" not in os.environ
    assert response["menu_metadata"]["agent"]["selected"] == "sapiens"
    assert response["menu_metadata"]["workflow_discovery"]["strategy"] == "hybrid"
    assert response["menu_metadata"]["execution_context"] == {
        "execution_id": response["menu_metadata"]["execution_context"]["execution_id"],
        "user_id": 7,
        "company_id": 11,
        "channel": "whatsapp",
        "thread_id": "wa_7_x",
        "thread_prefix": "wa",
        "menu_intercepted": False,
    }
    assert captured_usage["user_id"] == 7
    assert captured_usage["company_id"] == 11
    assert captured_usage["channel"] == "whatsapp"
    assert captured_usage["thread_id"] == "wa_7_x"
    assert captured_usage["menu_metadata"]["workflow_discovery"]["strategy"] == "hybrid"
    assert captured_gap["user_id"] == 7
    assert captured_gap["company_id"] == 11
    assert captured_gap["channel"] == "whatsapp"
    assert captured_gap["thread_id"] == "wa_7_x"
    assert captured_gap["user_msg"] == "teste"
    assert captured_gap["response_text"] == "ok"
    assert captured_gap["menu_metadata"]["workflow_discovery"]["strategy"] == "hybrid"


def test_classify_workflow_gap_ignores_whatsapp_auto_reply_noise():
    should_capture, resolution_type = execution._classify_workflow_gap(
        user_msg="Ops! Mensagem automática de ausência. Como posso ajudar? Deixe sua mensagem.",
        response_text="Tudo bem, fico à disposição.",
        menu_metadata={"workflow_discovery": {"candidate_count": 0}},
    )

    assert should_capture is False
    assert resolution_type == execution.WORKFLOW_GAP_NOISE_IGNORED


def test_classify_workflow_gap_marks_ambiguous_operational_request():
    should_capture, resolution_type = execution._classify_workflow_gap(
        user_msg="Quais atividades em aberto da Ventana com responsável Márcio Simoes?",
        response_text="Encontrei mais de um fluxo possível.",
        menu_metadata={
            "workflow_discovery": {
                "candidate_count": 2,
                "confidence": {"route": "ambiguous"},
            }
        },
    )

    assert should_capture is True
    assert resolution_type == execution.WORKFLOW_GAP_AMBIGUOUS_NEEDS_CLARIFICATION


def test_classify_workflow_gap_marks_entity_resolution_failure():
    should_capture, resolution_type = execution._classify_workflow_gap(
        user_msg="Quais atividades em aberto da Ventana com responsável Márcio Simoes?",
        response_text="Nao encontrei empresa para 'Ventana'.",
        menu_metadata={"workflow_discovery": {"candidate_count": 1}},
    )

    assert should_capture is True
    assert resolution_type == execution.WORKFLOW_GAP_ENTITY_RESOLUTION_FAILED
