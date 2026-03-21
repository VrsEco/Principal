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


class AgentActionListPendingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class AgentActionListPendingResult(BaseModel):
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


class AgentActionListPendingExecutionHandler:
    def __init__(
        self,
        *,
        resolve_company_ids_for_payload: Callable[[Dict[str, Any], Optional[int], int], tuple[list[int], str]],
        list_pending_actions: Callable[[list[int] | tuple[int, ...]], tuple[list[Any], list[dict[str, Any]]]],
    ):
        self._resolve_company_ids_for_payload = resolve_company_ids_for_payload
        self._list_pending_actions = list_pending_actions

    def execute(self, request: AgentActionListPendingRequest) -> AgentActionListPendingResult:
        payload = dict(request.payload or {})
        company_ids, label_or_error = self._resolve_company_ids_for_payload(
            payload,
            request.active_company_id,
            request.user_id,
        )
        if not company_ids:
            return AgentActionListPendingResult(
                response_text=label_or_error or "Nao consegui identificar o recorte de empresas para listar as solicitacoes."
            )

        limit_raw = payload.get("limite") or payload.get("limit") or payload.get("quantidade") or 20
        try:
            limit = max(1, min(int(limit_raw), 50))
        except (TypeError, ValueError):
            limit = 20

        actions, _suppressed = self._list_pending_actions(company_ids)
        if not actions:
            return AgentActionListPendingResult(
                response_text="Nao encontrei solicitacoes pendentes aguardando sua decisao no recorte atual."
            )

        visible = list(actions)[:limit]
        lines = [f"Encontrei {len(actions)} solicitacao(oes) pendente(s) aguardando decisao no recorte {label_or_error or 'atual'}."]
        lines.append("")
        lines.append("Principais itens:")
        for idx, action in enumerate(visible, start=1):
            action_id = getattr(action, "id", None)
            title = str(getattr(action, "title", None) or "Solicitacao sem titulo").strip()
            status = str(getattr(action, "status", None) or "pending").strip()
            action_type = str(getattr(action, "type", None) or "approval_request").strip()
            company_id = getattr(action, "company_id", None)
            lines.append(
                f"{idx}. #{action_id} | {title} | tipo={action_type} | status={status} | company_id={company_id}"
            )
        if len(actions) > len(visible):
            lines.append("")
            lines.append(f"...e mais {len(actions) - len(visible)} solicitacao(oes).")
        return AgentActionListPendingResult(response_text="\n".join(lines))
