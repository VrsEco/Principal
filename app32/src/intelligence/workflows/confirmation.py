from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Set, Union

from pydantic import BaseModel, ConfigDict, Field

from .direct_execution import DirectExecutionResult
from .session import WorkflowSessionState

CONFIRMATION_ROUTE_CANCELLED = "cancelled"
CONFIRMATION_ROUTE_DIRECT_RESPONSE = "direct_response"
CONFIRMATION_ROUTE_EXECUTION_PROMPT = "execution_prompt"
CONFIRMATION_ROUTE_RECONFIRM = "reconfirm"


class ConfirmationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    response_text: Optional[str] = None
    override_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConfirmationCoordinator:
    def __init__(
        self,
        *,
        confirm_words: Set[str],
        cancel_words: Set[str],
        extract_fields_from_text: Callable[[str], Dict[str, str]],
        public_payload: Callable[[Dict[str, Any]], Dict[str, Any]],
        try_execute_direct_option: Callable[..., Union[Optional[str], DirectExecutionResult]],
        build_execution_prompt: Callable[[Any, Dict[str, Any], str], str],
        cancel_response_text: str = "Acao cancelada. Se quiser, digite 'menu' para escolher outra opcao.",
    ):
        self._confirm_words = {str(word or "").strip().lower() for word in confirm_words}
        self._cancel_words = {str(word or "").strip().lower() for word in cancel_words}
        self._extract_fields_from_text = extract_fields_from_text
        self._public_payload = public_payload
        self._try_execute_direct_option = try_execute_direct_option
        self._build_execution_prompt = build_execution_prompt
        self._cancel_response_text = cancel_response_text

    @staticmethod
    def _coerce_direct_execution_result(
        value: Union[Optional[str], DirectExecutionResult],
    ) -> Optional[DirectExecutionResult]:
        if value is None:
            return None
        if isinstance(value, DirectExecutionResult):
            return value
        return DirectExecutionResult(executed=True, response_text=str(value))

    def handle_reply(
        self,
        workflow_state: WorkflowSessionState,
        *,
        option: Any,
        text: str,
        lower: str,
    ) -> ConfirmationDecision:
        first_word = str(lower or "").split(" ")[0] if lower else ""
        payload = dict(workflow_state.payload or {})

        if first_word in self._confirm_words:
            direct_execution = self._try_execute_direct_option(
                option=option,
                payload=payload,
                company_id=workflow_state.company_id,
                user_id=workflow_state.user_id,
                channel=workflow_state.channel or "web",
            )
            direct_result = self._coerce_direct_execution_result(direct_execution)
            if direct_result is not None:
                return ConfirmationDecision(
                    route=CONFIRMATION_ROUTE_DIRECT_RESPONSE,
                    payload=self._public_payload(payload),
                    response_text=direct_result.response_text,
                    metadata=dict(direct_result.metadata or {}),
                )

            prompt = self._build_execution_prompt(
                option,
                self._public_payload(payload),
                workflow_state.last_user_message or text,
            )
            return ConfirmationDecision(
                route=CONFIRMATION_ROUTE_EXECUTION_PROMPT,
                payload=self._public_payload(payload),
                override_message=prompt,
            )

        if first_word in self._cancel_words:
            return ConfirmationDecision(
                route=CONFIRMATION_ROUTE_CANCELLED,
                payload=self._public_payload(payload),
                response_text=self._cancel_response_text,
            )

        updated = dict(payload)
        updated.update(self._extract_fields_from_text(text))
        return ConfirmationDecision(
            route=CONFIRMATION_ROUTE_RECONFIRM,
            payload=self._public_payload(updated),
        )
