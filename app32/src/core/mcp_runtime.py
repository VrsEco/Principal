from __future__ import annotations

import os
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Mapping

from src.intelligence.security.runtime_identity import resolve_runtime_identity
from src.intelligence.tool_context import (
    reset_legacy_tool_context,
    reset_sapiens_context,
    set_legacy_tool_context,
    set_sapiens_context,
)
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


def extract_mcp_payload(args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> dict[str, Any]:
    if kwargs:
        return dict(kwargs)
    if not args:
        return {}
    first = args[0]
    if isinstance(first, Mapping):
        return dict(first)
    return {}


def _normalize_permissions(raw_permissions: Any) -> tuple[str, ...]:
    if raw_permissions is None:
        return ()
    if isinstance(raw_permissions, dict):
        return tuple(str(key).strip().lower() for key in raw_permissions.keys() if str(key).strip())
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
    env_company_id = _coerce_optional_int(
        http_request_context.get("company_id")
        or os.environ.get("APP32_MCP_COMPANY_ID")
        or os.environ.get("ACTIVE_COMPANY_ID")
    )
    requested_company_id = _coerce_optional_int(raw_payload.get("company_id")) or env_company_id
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

    resolved_company_id = _coerce_optional_int(runtime_identity.get("company_id")) or requested_company_id
    accessible_company_ids = tuple(
        int(company_id)
        for company_id in (runtime_identity.get("accessible_company_ids") or ())
        if _coerce_optional_int(company_id) is not None
    )
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

        payload = extract_mcp_payload(args, kwargs)
        execution_context = resolve_mcp_execution_context(payload)
        app = create_app()
        with app.app_context():
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

    return _wrapped
