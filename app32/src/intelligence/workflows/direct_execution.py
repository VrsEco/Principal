from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Type

from pydantic import BaseModel, ConfigDict, Field


class DirectExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_key: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int
    channel: str = "web"


class DirectExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    executed: bool = False
    response_text: Optional[str] = None


DirectExecutionHandler = Callable[[DirectExecutionRequest], Optional[str]]
DirectExecutionExtraFieldsBuilder = Callable[[DirectExecutionRequest], Dict[str, Any]]
DirectExecutionPolicyGuard = Callable[[DirectExecutionRequest], Optional[str]]


class DirectExecutionDispatcher:
    def __init__(self, handlers: Dict[str, DirectExecutionHandler], policy_guard: Optional[DirectExecutionPolicyGuard] = None):
        self._handlers = {
            self._normalize_action_key(action_key): handler
            for action_key, handler in (handlers or {}).items()
            if self._normalize_action_key(action_key) and handler is not None
        }
        self._policy_guard = policy_guard

    def execute(self, request: DirectExecutionRequest) -> DirectExecutionResult:
        action_key = self._normalize_action_key(request.action_key)
        if not action_key:
            return DirectExecutionResult(executed=False)

        handler = self._handlers.get(action_key)
        if handler is None:
            return DirectExecutionResult(executed=False)

        if self._policy_guard is not None:
            policy_response = self._policy_guard(request)
            if policy_response is not None:
                return DirectExecutionResult(executed=True, response_text=str(policy_response))

        response_text = handler(request)
        if response_text is None:
            return DirectExecutionResult(executed=False)

        return DirectExecutionResult(
            executed=True,
            response_text=str(response_text),
        )

    @staticmethod
    def _normalize_action_key(value: Optional[str]) -> str:
        return str(value or "").strip().lower()


def build_direct_execution_request(
    request: DirectExecutionRequest,
    request_model: Type[BaseModel],
    *,
    action_override: Optional[str] = None,
    extra_fields_builder: Optional[DirectExecutionExtraFieldsBuilder] = None,
) -> BaseModel:
    model_fields = getattr(request_model, "model_fields", {})
    request_kwargs: Dict[str, Any] = {}

    if "action" in model_fields:
        request_kwargs["action"] = action_override or str(request.action_key or "").strip().lower()
    if "payload" in model_fields:
        request_kwargs["payload"] = dict(request.payload or {})
    if "active_company_id" in model_fields:
        request_kwargs["active_company_id"] = request.active_company_id
    if "user_id" in model_fields:
        request_kwargs["user_id"] = request.user_id
    if "channel" in model_fields:
        request_kwargs["channel"] = request.channel or "web"

    if extra_fields_builder is not None:
        request_kwargs.update(dict(extra_fields_builder(request) or {}))

    return request_model(**request_kwargs)


def build_handler_executor(
    *,
    handler_factory: Callable[[], Any],
    request_model: Type[BaseModel],
    response_attr: str = "response_text",
    action_override: Optional[str] = None,
    extra_fields_builder: Optional[DirectExecutionExtraFieldsBuilder] = None,
) -> DirectExecutionHandler:
    def _execute(request: DirectExecutionRequest) -> Optional[str]:
        handler = handler_factory()
        request_payload = build_direct_execution_request(
            request,
            request_model,
            action_override=action_override,
            extra_fields_builder=extra_fields_builder,
        )
        result = handler.execute(request_payload)
        response_value = getattr(result, response_attr, None)
        if response_value is None:
            return None
        return str(response_value)

    return _execute
