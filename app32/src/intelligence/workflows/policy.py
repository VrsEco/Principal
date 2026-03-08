from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .direct_execution import DirectExecutionRequest


class WorkflowApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: int
    reused_existing: bool = False


class WorkflowApprovalPolicyGuard:
    def __init__(
        self,
        *,
        sensitive_action_keys: Optional[Sequence[str]] = None,
        approval_channels: Optional[Sequence[str]] = None,
        create_approval_request: Optional[Callable[[DirectExecutionRequest, Dict[str, Any]], WorkflowApprovalRequest]] = None,
    ):
        self._sensitive_action_keys = {
            str(item or "").strip().lower()
            for item in (sensitive_action_keys or (
                "project_task.complete",
                "process_instance.complete",
                "meeting.start",
            ))
            if str(item or "").strip()
        }
        self._approval_channels = {
            str(item or "").strip().lower()
            for item in (approval_channels or ("telegram", "whatsapp", "email"))
            if str(item or "").strip()
        }
        self._create_approval_request = create_approval_request or self._create_approval_request_in_db

    def evaluate(self, request: DirectExecutionRequest) -> Optional[str]:
        action_key = str(request.action_key or "").strip().lower()
        channel = str(request.channel or "web").strip().lower()
        if action_key not in self._sensitive_action_keys:
            return None
        if channel not in self._approval_channels:
            return None
        if request.active_company_id is None:
            return (
                "Esta ação sensível exige empresa ativa definida antes da execução. "
                "Selecione a empresa e tente novamente."
            )

        context = self._build_context(request)
        approval = self._create_approval_request(request, context)
        reuse_text = "já existente" if approval.reused_existing else "registrada"
        return (
            f"⚠️ Esta ação exige aprovação humana antes da execução. "
            f"Solicitação #{approval.approval_id} {reuse_text} para {context['object_label']}. "
            "Após a aprovação, a execução poderá ser retomada com segurança."
        )

    def _build_context(self, request: DirectExecutionRequest) -> Dict[str, Any]:
        action_key = str(request.action_key or "").strip().lower()
        payload = dict(request.payload or {})
        object_code = (
            payload.get("codigo_atividade")
            or payload.get("codigo_instancia")
            or payload.get("codigo_reuniao")
            or payload.get("meeting_code")
            or payload.get("id_reuniao")
            or payload.get("titulo")
            or payload.get("nome_atividade")
            or "item sensível"
        )
        object_label = {
            "project_task.complete": f"a conclusão da atividade {object_code}",
            "process_instance.complete": f"a conclusão da instância {object_code}",
            "meeting.start": f"o início da reunião {object_code}",
        }.get(action_key, f"a ação {action_key}")
        approval_key = f"{action_key}|{request.user_id}|{request.active_company_id}|{object_code}"
        return {
            "action_key": action_key,
            "object_code": str(object_code),
            "object_label": object_label,
            "approval_key": approval_key,
            "payload": payload,
        }

    def _create_approval_request_in_db(
        self,
        request: DirectExecutionRequest,
        context: Dict[str, Any],
    ) -> WorkflowApprovalRequest:
        from models import db
        from models.agent_action import AgentAction

        company_id = int(request.active_company_id)
        action_key = context["action_key"]
        approval_key = context["approval_key"]

        pending_actions = (
            AgentAction.query.filter_by(
                type="workflow_approval_request",
                status="pending",
                company_id=company_id,
                user_id=request.user_id,
            )
            .order_by(AgentAction.created_at.desc())
            .limit(20)
            .all()
        )
        for pending in pending_actions:
            payload = pending.payload or {}
            if payload.get("approval_key") == approval_key and payload.get("action_key") == action_key:
                return WorkflowApprovalRequest(approval_id=pending.id, reused_existing=True)

        action = AgentAction(
            type="workflow_approval_request",
            status="pending",
            requesting_agent="sapiens",
            handling_agent="operations",
            title=f"Aprovação necessária: {context['object_label']}",
            description=(
                f"Ação sensível solicitada via canal {request.channel}.\n"
                f"Usuário: {request.user_id}\n"
                f"Empresa: {company_id}\n"
                f"Ação: {action_key}\n"
                f"Objeto: {context['object_code']}\n"
                f"Payload: {context['payload']}"
            ),
            payload={
                "approval_key": approval_key,
                "action_key": action_key,
                "channel": request.channel,
                "object_code": context["object_code"],
                "request_payload": context["payload"],
                "created_via": "workflow_policy_guard",
            },
            company_id=company_id,
            user_id=request.user_id,
            created_at=datetime.utcnow(),
        )
        db.session.add(action)
        db.session.commit()
        return WorkflowApprovalRequest(approval_id=action.id, reused_existing=False)
