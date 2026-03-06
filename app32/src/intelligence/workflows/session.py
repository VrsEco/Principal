from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkflowSessionState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: int
    company_id: Optional[int] = None
    channel: str = "web"
    thread_id: Optional[str] = None
    status: str = "idle"
    workflow_code: Optional[str] = None
    workflow_action_key: Optional[str] = None
    selected_option_id: Optional[int] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    missing_fields: List[Dict[str, Any]] = Field(default_factory=list)
    last_user_message: Optional[str] = None

    @classmethod
    def from_agent_menu_session(
        cls,
        session: Any,
        *,
        workflow_code: Optional[str] = None,
        workflow_action_key: Optional[str] = None,
    ) -> "WorkflowSessionState":
        selected_option = getattr(session, "selected_option", None)
        option_code = workflow_code or getattr(selected_option, "code", None)
        option_action_key = workflow_action_key or getattr(selected_option, "action_key", None)

        return cls(
            user_id=int(getattr(session, "user_id")),
            company_id=getattr(session, "company_id", None),
            channel=str(getattr(session, "channel", "web") or "web"),
            thread_id=getattr(session, "thread_id", None),
            status=str(getattr(session, "status", "idle") or "idle"),
            workflow_code=(str(option_code).strip() if option_code else None),
            workflow_action_key=(str(option_action_key).strip().lower() if option_action_key else None),
            selected_option_id=getattr(session, "selected_option_id", None),
            payload=dict(getattr(session, "collected_data", {}) or {}),
            missing_fields=list(getattr(session, "missing_fields", []) or []),
            last_user_message=getattr(session, "last_user_message", None),
        )

    def with_payload(self, payload: Dict[str, Any]) -> "WorkflowSessionState":
        return self.model_copy(update={"payload": dict(payload or {})})
