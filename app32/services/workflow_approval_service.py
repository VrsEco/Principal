from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.intelligence.workflows.direct_execution import DirectExecutionResult


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
    ):
        self._resume_executor = resume_executor
        self._now_factory = now_factory

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

    def _validate_action(
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
