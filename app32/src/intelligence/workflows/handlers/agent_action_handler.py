from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentActionOperationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class AgentActionOperationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class AgentActionOperationExecutionHandler:
    def __init__(
        self,
        *,
        load_action_by_id: Callable[[int], Any],
        load_latest_pending_action: Callable[[int, Optional[int]], Any],
        find_backlog_link_by_action_id: Callable[[Optional[int]], Any],
        load_task_by_id: Callable[[int], Any],
        execute_backlog_human_gate_operation: Callable[..., Any],
        user_can_access_company: Callable[[int, int], bool],
    ):
        self._load_action_by_id = load_action_by_id
        self._load_latest_pending_action = load_latest_pending_action
        self._find_backlog_link_by_action_id = find_backlog_link_by_action_id
        self._load_task_by_id = load_task_by_id
        self._execute_backlog_human_gate_operation = execute_backlog_human_gate_operation
        self._user_can_access_company = user_can_access_company

    def execute(self, request: AgentActionOperationRequest) -> AgentActionOperationResult:
        payload = dict(request.payload or {})
        operation = str(
            payload.get("agent_action_operation")
            or payload.get("operation")
            or ""
        ).strip().lower()
        if operation not in {"approve", "reject", "revalidate"}:
            return AgentActionOperationResult(
                response_text="Nao identifiquei a operacao desejada. Use aprovar, rejeitar ou revalidar."
            )

        raw_action_id = payload.get("agent_action_id") or payload.get("approval_request_id")
        action = None
        if raw_action_id is not None and str(raw_action_id).strip().isdigit():
            action = self._load_action_by_id(int(str(raw_action_id).strip()))
        if action is None:
            action = self._load_latest_pending_action(request.user_id, request.active_company_id)
        if action is None:
            return AgentActionOperationResult(
                response_text="Nao encontrei solicitacao pendente para operar. Informe o ID/ticket da aprovacao."
            )

        company_id = getattr(action, "company_id", None)
        if (
            request.active_company_id
            and company_id
            and company_id != request.active_company_id
            and not self._user_can_access_company(request.user_id, int(company_id))
        ):
            return AgentActionOperationResult(
                response_text="A solicitacao encontrada esta fora do contexto da empresa ativa."
            )

        link = self._find_backlog_link_by_action_id(getattr(action, "id", None))
        task = self._load_task_by_id(getattr(link, "project_task_id", None)) if link is not None else None
        if task is None:
            return AgentActionOperationResult(
                response_text=(
                    f"Encontrei a solicitacao #{getattr(action, 'id', 'N/A')}, mas ela nao possui card operacional vinculado. "
                    "Sincronize o backlog antes de operar."
                )
            )

        feedback = str(payload.get("feedback") or "").strip() or None
        outcome = self._execute_backlog_human_gate_operation(
            task=task,
            operation=operation,
            actor_user_id=request.user_id,
            actor_name=str(payload.get("actor_name") or "Sapiens").strip() or "Sapiens",
            feedback=feedback,
        )
        return AgentActionOperationResult(
            response_text=str(getattr(outcome, "message", None) or "Operacao executada.")
        )
