from types import SimpleNamespace

from src.intelligence.workflows.handlers.agent_action_handler import (
    AgentActionListPendingExecutionHandler,
    AgentActionListPendingRequest,
    AgentActionOperationExecutionHandler,
    AgentActionOperationRequest,
)


def test_agent_action_operation_handler_approves_explicit_action_id():
    action = SimpleNamespace(id=331, company_id=9)
    task = SimpleNamespace(id=693)
    link = SimpleNamespace(project_task_id=693)
    captured = {}

    handler = AgentActionOperationExecutionHandler(
        load_action_by_id=lambda action_id: action if action_id == 331 else None,
        load_latest_pending_action=lambda user_id, active_company_id: None,
        find_backlog_link_by_action_id=lambda action_id: link if action_id == 331 else None,
        load_task_by_id=lambda task_id: task if task_id == 693 else None,
        execute_backlog_human_gate_operation=lambda **kwargs: captured.update(kwargs) or SimpleNamespace(message="Solicitação aprovada com sucesso."),
        user_can_access_company=lambda user_id, company_id: True,
    )

    result = handler.execute(
        AgentActionOperationRequest(
            payload={"agent_action_operation": "approve", "agent_action_id": "331"},
            active_company_id=9,
            user_id=7,
        )
    )

    assert result.response_text == "Solicitação aprovada com sucesso."
    assert captured["operation"] == "approve"
    assert captured["task"] is task


def test_agent_action_operation_handler_falls_back_to_latest_pending_action():
    action = SimpleNamespace(id=260, company_id=9)
    task = SimpleNamespace(id=260)
    link = SimpleNamespace(project_task_id=260)

    handler = AgentActionOperationExecutionHandler(
        load_action_by_id=lambda action_id: None,
        load_latest_pending_action=lambda user_id, active_company_id: action,
        find_backlog_link_by_action_id=lambda action_id: link if action_id == 260 else None,
        load_task_by_id=lambda task_id: task if task_id == 260 else None,
        execute_backlog_human_gate_operation=lambda **kwargs: SimpleNamespace(message="Solicitação aprovada com sucesso."),
        user_can_access_company=lambda user_id, company_id: True,
    )

    result = handler.execute(
        AgentActionOperationRequest(
            payload={"agent_action_operation": "approve"},
            active_company_id=9,
            user_id=7,
        )
    )

    assert result.response_text == "Solicitação aprovada com sucesso."


def test_agent_action_list_pending_handler_formats_top_items():
    actions = [
        SimpleNamespace(id=331, title="Adiamento Lucro Real", type="approval_request", status="pending", company_id=9),
        SimpleNamespace(id=334, title="Atividades da semana", type="workflow_approval_request", status="awaiting_approval", company_id=12),
    ]
    handler = AgentActionListPendingExecutionHandler(
        resolve_company_ids_for_payload=lambda payload, active_company_id, user_id: ([9, 12], "empresas vinculadas"),
        list_pending_actions=lambda company_ids: (actions, []),
    )

    result = handler.execute(
        AgentActionListPendingRequest(
            payload={"limite": "1"},
            active_company_id=None,
            user_id=7,
        )
    )

    assert "Encontrei 2 solicitacao(oes) pendente(s)" in result.response_text
    assert "#331 | Adiamento Lucro Real" in result.response_text
    assert "...e mais 1 solicitacao(oes)." in result.response_text
