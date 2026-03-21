from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any, Callable, Dict, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .approval_utils import DEFAULT_WORKFLOW_APPROVAL_TTL_HOURS, is_workflow_approval_expired
from .direct_execution import DirectExecutionRequest, DirectExecutionResult

logger = logging.getLogger(__name__)


class WorkflowApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: int
    reused_existing: bool = False
    approval_key: Optional[str] = None
    action_key: Optional[str] = None
    object_code: Optional[str] = None
    resume_payload: Dict[str, Any] = Field(default_factory=dict)


class WorkflowApprovalPolicyGuard:
    def __init__(
        self,
        *,
        sensitive_action_keys: Optional[Sequence[str]] = None,
        approval_channels: Optional[Sequence[str]] = None,
        create_approval_request: Optional[Callable[[DirectExecutionRequest, Dict[str, Any]], WorkflowApprovalRequest]] = None,
        approval_ttl_hours: int = DEFAULT_WORKFLOW_APPROVAL_TTL_HOURS,
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
        self._approval_ttl_hours = max(int(approval_ttl_hours or DEFAULT_WORKFLOW_APPROVAL_TTL_HOURS), 1)

    def evaluate(self, request: DirectExecutionRequest) -> Optional[DirectExecutionResult]:
        action_key = str(request.action_key or "").strip().lower()
        channel = str(request.channel or "web").strip().lower()
        if action_key not in self._sensitive_action_keys:
            return None
        if channel not in self._approval_channels:
            return None
        if request.active_company_id is None:
            return DirectExecutionResult(
                executed=True,
                response_text=(
                    "Esta ação sensível exige empresa ativa definida antes da execução. "
                    "Selecione a empresa e tente novamente."
                ),
                metadata={
                    "workflow_approval": {
                        "required": True,
                        "status": "missing_company_context",
                        "action_key": action_key,
                        "channel": channel,
                    }
                },
            )

        context = self._build_context(request)
        approval = self._create_approval_request(request, context)
        reuse_text = "já existente" if approval.reused_existing else "registrada"
        metadata = self._build_metadata(request, context, approval)
        return DirectExecutionResult(
            executed=True,
            response_text=(
                f"⚠️ Esta ação exige aprovação humana antes da execução. "
                f"Solicitação #{approval.approval_id} {reuse_text} para {context['object_label']}. "
                "Após a aprovação, a execução poderá ser retomada com segurança."
            ),
            metadata=metadata,
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
        resume_payload = {
            "action_key": action_key,
            "payload": payload,
            "active_company_id": request.active_company_id,
            "user_id": request.user_id,
            "channel": request.channel,
        }
        return {
            "action_key": action_key,
            "object_code": str(object_code),
            "object_label": object_label,
            "approval_key": approval_key,
            "payload": payload,
            "resume_payload": resume_payload,
        }

    def _build_metadata(
        self,
        request: DirectExecutionRequest,
        context: Dict[str, Any],
        approval: WorkflowApprovalRequest,
    ) -> Dict[str, Any]:
        approval_key = approval.approval_key or context["approval_key"]
        resume_payload = approval.resume_payload or context["resume_payload"]
        return {
            "workflow_approval": {
                "required": True,
                "status": "pending",
                "approval_request_id": approval.approval_id,
                "reused_existing": approval.reused_existing,
                "approval_key": approval_key,
                "action_key": approval.action_key or context["action_key"],
                "object_code": approval.object_code or context["object_code"],
                "channel": request.channel,
                "resume_payload": resume_payload,
            }
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
        resume_payload = context["resume_payload"]

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
            if is_workflow_approval_expired(pending):
                continue
            if payload.get("approval_key") == approval_key and payload.get("action_key") == action_key:
                return WorkflowApprovalRequest(
                    approval_id=pending.id,
                    reused_existing=True,
                    approval_key=approval_key,
                    action_key=action_key,
                    object_code=context["object_code"],
                    resume_payload=payload.get("resume_payload") or resume_payload,
                )

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
                "approval_status": "pending",
                "approval_expires_at": (datetime.utcnow() + timedelta(hours=self._approval_ttl_hours)).isoformat(),
                "action_key": action_key,
                "channel": request.channel,
                "object_code": context["object_code"],
                "request_payload": context["payload"],
                "resume_payload": resume_payload,
                "created_via": "workflow_policy_guard",
            },
            company_id=company_id,
            user_id=request.user_id,
            created_at=datetime.utcnow(),
        )
        db.session.add(action)
        db.session.commit()
        try:
            from services.agent_action_backlog_service import ensure_backlog_task_for_action

            ensure_backlog_task_for_action(action, autocommit=True)
        except Exception as exc:
            logger.exception(
                "Falha ao espelhar workflow approval #%s no backlog AA.J.31: %s",
                action.id,
                exc,
            )
        return WorkflowApprovalRequest(
            approval_id=action.id,
            reused_existing=False,
            approval_key=approval_key,
            action_key=action_key,
            object_code=context["object_code"],
            resume_payload=resume_payload,
        )
