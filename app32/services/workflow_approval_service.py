from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.intelligence.workflows.approval_utils import (
    DEFAULT_WORKFLOW_APPROVAL_TTL_HOURS,
    get_workflow_approval_expires_at,
    is_workflow_approval_expired,
)
from src.intelligence.workflows.direct_execution import DirectExecutionResult


def serialize_workflow_approval_action(action: Any, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    payload = dict(getattr(action, "payload", None) or {})
    resume_payload = dict(payload.get("resume_payload") or {})
    resume_result = dict(payload.get("resume_result") or {})
    expires_at = get_workflow_approval_expires_at(action)
    expired = is_workflow_approval_expired(action, now=now)
    return {
        "id": getattr(action, "id", None),
        "type": getattr(action, "type", None),
        "status": getattr(action, "status", None),
        "title": getattr(action, "title", None),
        "description": getattr(action, "description", None),
        "company_id": getattr(action, "company_id", None),
        "user_id": getattr(action, "user_id", None),
        "requesting_agent": getattr(action, "requesting_agent", None),
        "handling_agent": getattr(action, "handling_agent", None),
        "created_at": getattr(action, "created_at", None).isoformat() if getattr(action, "created_at", None) else None,
        "resolved_at": getattr(action, "resolved_at", None).isoformat() if getattr(action, "resolved_at", None) else None,
        "executed_at": getattr(action, "executed_at", None).isoformat() if getattr(action, "executed_at", None) else None,
        "approval": {
            "approval_status": payload.get("approval_status") or ("expired" if expired else getattr(action, "status", None)),
            "approval_key": payload.get("approval_key"),
            "action_key": payload.get("action_key") or resume_payload.get("action_key"),
            "channel": payload.get("channel") or resume_payload.get("channel"),
            "object_code": payload.get("object_code"),
            "request_payload": dict(payload.get("request_payload") or {}),
            "resume_payload": resume_payload,
            "resume_result": resume_result,
            "approved_by_user_id": payload.get("approved_by_user_id"),
            "approved_at": payload.get("approved_at"),
            "rejected_by_user_id": payload.get("rejected_by_user_id"),
            "rejected_at": payload.get("rejected_at"),
            "rejection_feedback": payload.get("rejection_feedback"),
            "created_via": payload.get("created_via"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "expired": expired,
            "expired_at": payload.get("expired_at"),
            "revalidated_at": payload.get("revalidated_at"),
            "revalidated_by_user_id": payload.get("revalidated_by_user_id"),
        },
    }



class WorkflowApprovalOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    message: str
    http_status: int = 200
    action_status: Optional[str] = None
    resume_payload: Dict[str, Any] = Field(default_factory=dict)
    resume_result: Dict[str, Any] = Field(default_factory=dict)
    audit_metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowApprovalService:
    def __init__(
        self,
        *,
        resume_executor: Callable[[Dict[str, Any]], DirectExecutionResult],
        now_factory: Callable[[], datetime] = datetime.utcnow,
        approval_ttl_hours: int = DEFAULT_WORKFLOW_APPROVAL_TTL_HOURS,
    ):
        self._resume_executor = resume_executor
        self._now_factory = now_factory
        self._approval_ttl_hours = max(int(approval_ttl_hours or DEFAULT_WORKFLOW_APPROVAL_TTL_HOURS), 1)

    def approve(
        self,
        *,
        action: Any,
        approver_user_id: int,
        approver_name: str,
        active_company_id: Optional[int],
    ) -> WorkflowApprovalOutcome:
        validation_error = self._validate_action(action, active_company_id)
        if validation_error is not None:
            return validation_error

        if getattr(action, "status", None) != "pending":
            return WorkflowApprovalOutcome(
                success=True,
                message=f"Ação já estava em status {getattr(action, 'status', 'desconhecido')}.",
                action_status=getattr(action, "status", None),
                audit_metadata=self._build_audit_metadata(action=action, event="already_processed"),
            )

        payload = dict(getattr(action, "payload", None) or {})
        resume_payload = dict(payload.get("resume_payload") or {})
        now = self._now_factory()
        approved_at = now.isoformat()

        resume_payload["approved_action_id"] = getattr(action, "id", None)
        resume_payload["approved_at"] = approved_at
        resume_payload["approved_by_user_id"] = approver_user_id
        resume_payload["approved_by_name"] = approver_name
        payload["resume_payload"] = resume_payload
        payload["approval_status"] = "approved"
        payload["approved_by_user_id"] = approver_user_id
        payload["approved_at"] = approved_at

        action.user_feedback = f"Aprovado por {approver_name}"
        action.resolved_at = now

        if not resume_payload.get("action_key"):
            action.payload = payload
            action.status = "approved"
            return WorkflowApprovalOutcome(
                success=True,
                message="Solicitação aprovada. Não havia payload de retomada para executar automaticamente.",
                action_status=action.status,
                resume_payload=resume_payload,
                audit_metadata=self._build_audit_metadata(
                    action=action,
                    event="approved_without_resume",
                    resume_payload=resume_payload,
                ),
            )

        resume_result = self._resume_executor(resume_payload)
        payload["resume_result"] = resume_result.model_dump()
        action.payload = payload

        if resume_result.executed:
            action.status = "executed"
            action.executed_at = now
            message = resume_result.response_text or "Solicitação aprovada e executada com sucesso."
            event = "approved_and_executed"
        else:
            action.status = "approved"
            message = resume_result.response_text or "Solicitação aprovada, mas a retomada não executou automaticamente."
            event = "approved_without_execution"

        return WorkflowApprovalOutcome(
            success=True,
            message=message,
            action_status=action.status,
            resume_payload=resume_payload,
            resume_result=resume_result.model_dump(),
            audit_metadata=self._build_audit_metadata(
                action=action,
                event=event,
                resume_payload=resume_payload,
                resume_result=resume_result.model_dump(),
            ),
        )

    def reject(
        self,
        *,
        action: Any,
        approver_user_id: int,
        approver_name: str,
        active_company_id: Optional[int],
        feedback: Optional[str] = None,
    ) -> WorkflowApprovalOutcome:
        validation_error = self._validate_action(action, active_company_id)
        if validation_error is not None:
            return validation_error

        if getattr(action, "status", None) != "pending":
            return WorkflowApprovalOutcome(
                success=True,
                message=f"Ação já estava em status {getattr(action, 'status', 'desconhecido')}.",
                action_status=getattr(action, "status", None),
                audit_metadata=self._build_audit_metadata(action=action, event="already_processed"),
            )

        now = self._now_factory()
        payload = dict(getattr(action, "payload", None) or {})
        payload["approval_status"] = "rejected"
        payload["rejected_by_user_id"] = approver_user_id
        payload["rejected_at"] = now.isoformat()
        if feedback:
            payload["rejection_feedback"] = feedback

        action.payload = payload
        action.status = "rejected"
        action.user_feedback = (
            f"Rejeitado por {approver_name}: {feedback}" if feedback else f"Rejeitado por {approver_name}"
        )
        action.resolved_at = now

        return WorkflowApprovalOutcome(
            success=True,
            message="Solicitação rejeitada. A execução automática não será retomada.",
            action_status=action.status,
            resume_payload=dict(payload.get("resume_payload") or {}),
            audit_metadata=self._build_audit_metadata(
                action=action,
                event="rejected",
                resume_payload=dict(payload.get("resume_payload") or {}),
                extra={"feedback": feedback or ""},
            ),
        )

    def revalidate(
        self,
        *,
        action: Any,
        approver_user_id: int,
        approver_name: str,
        active_company_id: Optional[int],
    ) -> WorkflowApprovalOutcome:
        base_error = self._validate_action_company_only(action, active_company_id)
        if base_error is not None:
            return base_error

        if getattr(action, "status", None) != "pending":
            return WorkflowApprovalOutcome(
                success=False,
                message="Somente approvals pendentes podem ser revalidados.",
                http_status=409,
                action_status=getattr(action, "status", None),
                audit_metadata=self._build_audit_metadata(action=action, event="revalidation_not_allowed"),
            )

        now = self._now_factory()
        payload = dict(getattr(action, "payload", None) or {})
        payload["approval_status"] = "pending"
        payload["revalidated_at"] = now.isoformat()
        payload["revalidated_by_user_id"] = approver_user_id
        payload["approval_expires_at"] = (now + timedelta(hours=self._approval_ttl_hours)).isoformat()
        payload.pop("expired_at", None)
        action.payload = payload
        action.user_feedback = f"Revalidado por {approver_name}"

        return WorkflowApprovalOutcome(
            success=True,
            message="Solicitação revalidada com sucesso. O prazo de aprovação foi renovado.",
            http_status=200,
            action_status=getattr(action, "status", None),
            resume_payload=dict(payload.get("resume_payload") or {}),
            audit_metadata=self._build_audit_metadata(
                action=action,
                event="revalidated",
                extra={"revalidated_by_user_id": approver_user_id},
            ),
        )

    def _validate_action_company_only(
        self,
        action: Any,
        active_company_id: Optional[int],
    ) -> Optional[WorkflowApprovalOutcome]:
        if action is None:
            return WorkflowApprovalOutcome(success=False, message="Ação não encontrada.", http_status=404)

        if active_company_id and getattr(action, "company_id", None) != active_company_id:
            return WorkflowApprovalOutcome(
                success=False,
                message="Ação não pertence à empresa ativa.",
                http_status=403,
            )
        return None

    def _validate_action(
        self,
        action: Any,
        active_company_id: Optional[int],
    ) -> Optional[WorkflowApprovalOutcome]:
        base_error = self._validate_action_company_only(action, active_company_id)
        if base_error is not None:
            return base_error

        now = self._now_factory()
        if is_workflow_approval_expired(action, now=now):
            payload = dict(getattr(action, "payload", None) or {})
            payload["approval_status"] = "expired"
            payload.setdefault("expired_at", now.isoformat())
            action.payload = payload
            return WorkflowApprovalOutcome(
                success=False,
                message="A solicitação de aprovação expirou e precisa ser revalidada antes da execução.",
                http_status=409,
                action_status=getattr(action, "status", None),
                resume_payload=dict(payload.get("resume_payload") or {}),
                audit_metadata=self._build_audit_metadata(action=action, event="expired"),
            )
        return None

    def _build_audit_metadata(
        self,
        *,
        action: Any,
        event: str,
        resume_payload: Optional[Dict[str, Any]] = None,
        resume_result: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = dict(getattr(action, "payload", None) or {})
        metadata = {
            "workflow_approval": {
                "event": event,
                "action_id": getattr(action, "id", None),
                "action_status": getattr(action, "status", None),
                "approval_status": payload.get("approval_status"),
                "action_key": payload.get("action_key") or (resume_payload or {}).get("action_key"),
                "resume_payload": resume_payload or dict(payload.get("resume_payload") or {}),
                "resume_result": resume_result or dict(payload.get("resume_result") or {}),
            }
        }
        if extra:
            metadata["workflow_approval"].update(extra)
        return metadata
