from __future__ import annotations

import os
import inspect
from dataclasses import dataclass
from functools import wraps
from types import SimpleNamespace
from typing import Any, Callable, Mapping, get_type_hints

from src.intelligence.security.runtime_identity import resolve_runtime_identity
from src.intelligence.security.tool_policy import ToolPolicyRequest, require_tool_policy
from src.intelligence.tool_context import (
    reset_legacy_tool_context,
    reset_sapiens_context,
    set_legacy_tool_context,
    set_sapiens_context,
)
from src.intelligence.tooling.capabilities import infer_tool_action, infer_tool_capability
from src.core.mcp_http_auth import get_http_request_context


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _coerce_optional_int_list(value: Any) -> tuple[int, ...]:
    if isinstance(value, (list, tuple, set, frozenset)):
        normalized: list[int] = []
        for item in value:
            coerced = _coerce_optional_int(item)
            if coerced is not None and coerced not in normalized:
                normalized.append(coerced)
        return tuple(normalized)
    return ()


def extract_mcp_payload(args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    if kwargs:
        return dict(kwargs)
    if not args:
        return {}
    first = args[0]
    if isinstance(first, Mapping):
        return dict(first)
    return {}




def _resolve_requested_company_id(raw_payload: Mapping[str, Any], http_request_context: Mapping[str, Any]) -> tuple[int | None, str | None]:
    candidates = (
        (raw_payload.get("company_id"), "payload.company_id"),
        (raw_payload.get("active_company_id"), "payload.active_company_id"),
        (raw_payload.get("_selected_company_id"), "payload._selected_company_id"),
        (raw_payload.get("_summary_company_id"), "payload._summary_company_id"),
        (http_request_context.get("company_id"), "http.company_id"),
    )
    for value, source in candidates:
        normalized = _coerce_optional_int(value)
        if normalized is not None:
            return normalized, source
    return None, None

def _normalize_permissions(raw_permissions: Any) -> tuple[str, ...]:
    if raw_permissions is None:
        return ()
    if isinstance(raw_permissions, dict):
        normalized: list[str] = []
        for resource, actions in raw_permissions.items():
            resource_name = str(resource).strip().lower()
            if not resource_name:
                continue
            if resource_name not in normalized:
                normalized.append(resource_name)
            if isinstance(actions, str):
                action_values = [actions]
            elif isinstance(actions, (list, tuple, set, frozenset)):
                action_values = list(actions)
            elif isinstance(actions, bool):
                action_values = []
            elif actions:
                action_values = [actions]
            else:
                action_values = []
            for action in action_values:
                action_name = str(action).strip().lower()
                if not action_name:
                    continue
                permission_key = f"{resource_name}.{action_name}"
                if permission_key not in normalized:
                    normalized.append(permission_key)
        return tuple(normalized)
    if isinstance(raw_permissions, (list, tuple, set, frozenset)):
        return tuple(str(item).strip().lower() for item in raw_permissions if str(item).strip())
    return (str(raw_permissions).strip().lower(),) if str(raw_permissions).strip() else ()


@dataclass(frozen=True)
class MCPExecutionContext:
    user_id: int | None
    company_id: int | None
    employee_id: int | None
    role: str
    channel: str
    thread_id: str | None
    accessible_company_ids: tuple[int, ...]
    permissions: tuple[str, ...]
    metadata: dict[str, Any]


def resolve_mcp_execution_context(payload: Mapping[str, Any] | None = None) -> MCPExecutionContext:
    raw_payload = dict(payload or {})
    http_request_context = dict(get_http_request_context() or {})

    user_id = _coerce_optional_int(
        http_request_context.get("user_id")
        or os.environ.get("APP32_MCP_USER_ID")
        or os.environ.get("ACTIVE_USER_ID")
    )
    requested_company_id, requested_company_source = _resolve_requested_company_id(raw_payload, http_request_context)
    channel = (
        str(
            raw_payload.get("channel")
            or http_request_context.get("channel")
            or os.environ.get("APP32_MCP_CHANNEL")
            or "claude_code"
        )
        .strip()
        .lower()
    )
    thread_id = str(
        raw_payload.get("thread_id")
        or http_request_context.get("thread_id")
        or os.environ.get("APP32_MCP_THREAD_ID")
        or os.environ.get("APP32_MCP_SESSION_ID")
        or ""
    ).strip() or None

    runtime_identity: dict[str, Any] = {}
    if user_id:
        runtime_identity = resolve_runtime_identity(user_id=user_id, company_id=requested_company_id)

    http_accessible_company_ids = _coerce_optional_int_list(http_request_context.get("accessible_company_ids"))
    runtime_accessible_company_ids = tuple(
        int(company_id)
        for company_id in (runtime_identity.get("accessible_company_ids") or ())
        if _coerce_optional_int(company_id) is not None
    )
    accessible_company_ids = http_accessible_company_ids or runtime_accessible_company_ids
    disable_company_fallback = bool(http_request_context.get("disable_company_fallback"))
    resolved_company_id = requested_company_id
    if resolved_company_id is None and not disable_company_fallback:
        resolved_company_id = _coerce_optional_int(runtime_identity.get("company_id"))
    company_resolution_source = requested_company_source
    if resolved_company_id is None and len(accessible_company_ids) == 1:
        resolved_company_id = int(accessible_company_ids[0])
        company_resolution_source = "runtime_identity.single_accessible_company_id"
    fallback_role = str(
        http_request_context.get("fallback_role")
        or os.environ.get("APP32_MCP_FALLBACK_ROLE")
        or "colaborador"
    ).strip().lower()
    role = str(runtime_identity.get("role") or fallback_role).strip().lower() or "colaborador"
    permissions = _normalize_permissions(runtime_identity.get("permissions"))

    metadata = {
        "surface": str(
            http_request_context.get("surface") or os.environ.get("APP32_MCP_SURFACE") or "user"
        ).strip().lower(),
        "transport": str(http_request_context.get("transport") or "stdio").strip().lower(),
        "client": str(
            http_request_context.get("client") or os.environ.get("APP32_MCP_CLIENT") or "claude_code"
        ).strip().lower(),
        "company_resolution_source": company_resolution_source,
        "runtime_profile": str(http_request_context.get("runtime_profile") or "").strip().lower() or None,
        "actor_type": str(http_request_context.get("actor_type") or "").strip().lower() or None,
        "runtime_family": str(http_request_context.get("runtime_family") or "").strip().lower() or None,
        "runtime_family_label": str(http_request_context.get("runtime_family_label") or "").strip() or None,
        "harness_key": str(http_request_context.get("harness_key") or "").strip().lower() or None,
        "harness_label": str(http_request_context.get("harness_label") or "").strip() or None,
        "mcp_enabled": bool(http_request_context.get("mcp_enabled", True)),
        "training_completed": bool(http_request_context.get("training_completed", True)),
        "client_id": str(http_request_context.get("client_id") or "").strip() or None,
        "token_subject": str(http_request_context.get("token_subject") or "").strip() or None,
        "accessible_company_ids": list(accessible_company_ids),
        "multi_company": len(accessible_company_ids) > 1,
        "selection_required_for_mutations": len(accessible_company_ids) > 1 and resolved_company_id is None,
        "disable_company_fallback": disable_company_fallback or len(accessible_company_ids) > 1,
    }

    return MCPExecutionContext(
        user_id=user_id,
        company_id=resolved_company_id,
        employee_id=_coerce_optional_int(runtime_identity.get("employee_id")),
        role=role,
        channel=channel or "claude_code",
        thread_id=thread_id,
        accessible_company_ids=accessible_company_ids,
        permissions=permissions,
        metadata=metadata,
    )


def wrap_mcp_callable(callback: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(callback)
    def _wrapped(*args: Any, **kwargs: Any) -> Any:
        from app import create_app
        from src.intelligence.tool_catalog import catalog

        payload = extract_mcp_payload(args, kwargs)
        app = create_app()
        with app.app_context():
            execution_context = resolve_mcp_execution_context(payload)
            tool_name = str(
                getattr(callback, "__app32_tool_name__", None)
                or getattr(callback, "__name__", "unknown_tool")
            ).strip() or "unknown_tool"
            capability = catalog.get_tool_capability(tool_name)
            if capability is None and "financial" in tool_name.lower():
                capability = infer_tool_capability(
                    SimpleNamespace(
                        name=tool_name,
                        description=getattr(callback, "__doc__", "") or "",
                    )
                )
            if capability is not None:
                action = infer_tool_action(tool_name, getattr(capability, "domain", None))
                confirmed_mutation = bool(
                    payload.get("confirmed_mutation")
                    or payload.get("human_gate_confirmed")
                    or payload.get("approval_confirmed")
                    or not getattr(capability, "human_gate", False)
                )
                require_tool_policy(
                    {
                        "user_id": execution_context.user_id,
                        "company_id": execution_context.company_id,
                        "employee_id": execution_context.employee_id,
                        "role": execution_context.role,
                        "channel": execution_context.channel,
                        "thread_id": execution_context.thread_id,
                        "permissions": execution_context.permissions,
                        "metadata": dict(execution_context.metadata or {}),
                    },
                    ToolPolicyRequest(
                        tool_name=tool_name,
                        surface=str(execution_context.metadata.get("surface") or "user"),
                        domain=getattr(capability, "domain", None),
                        action=action,
                        risk=getattr(getattr(capability, "risk", None), "value", "medium"),
                        requested_company_id=execution_context.company_id,
                        accessible_company_ids=execution_context.accessible_company_ids,
                        required_permissions=tuple(getattr(capability, "permissions", ()) or ()),
                        confirmed_mutation=confirmed_mutation,
                        required_context=tuple(getattr(capability, "required_context", ()) or ()),
                        metadata=dict(execution_context.metadata or {}),
                    ),
                )
            sapiens_token = set_sapiens_context(
                user_id=execution_context.user_id,
                company_id=execution_context.company_id,
                employee_id=execution_context.employee_id,
                channel=execution_context.channel,
                thread_id=execution_context.thread_id,
                metadata=execution_context.metadata,
            )
            legacy_tokens = set_legacy_tool_context(
                user_id=execution_context.user_id,
                company_id=execution_context.company_id,
            )
            try:
                return callback(*args, **kwargs)
            finally:
                reset_legacy_tool_context(legacy_tokens)
                reset_sapiens_context(sapiens_token)

    try:
        original_signature = inspect.signature(callback)
        resolved_hints = get_type_hints(callback, globalns=getattr(callback, "__globals__", {}))
        resolved_parameters = [
            parameter.replace(
                annotation=resolved_hints.get(parameter.name, parameter.annotation),
            )
            for parameter in original_signature.parameters.values()
        ]
        _wrapped.__signature__ = original_signature.replace(  # type: ignore[attr-defined]
            parameters=resolved_parameters,
            return_annotation=resolved_hints.get("return", original_signature.return_annotation),
        )
        _wrapped.__annotations__ = {
            parameter.name: parameter.annotation
            for parameter in resolved_parameters
            if parameter.annotation is not inspect.Signature.empty
        }
        if original_signature.return_annotation is not inspect.Signature.empty:
            _wrapped.__annotations__["return"] = _wrapped.__signature__.return_annotation
    except Exception:
        pass

    return _wrapped
