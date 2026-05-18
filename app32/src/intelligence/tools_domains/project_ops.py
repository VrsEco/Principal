from __future__ import annotations

import logging
import os

from services.project_mcp_service import ProjectMCPService
from src.intelligence.security.mcp_mutation_guard import (
    evaluate_mutation_limit,
    record_mutation_success,
)
from src.intelligence.security.runtime_identity import resolve_runtime_identity
from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy
from src.intelligence.tooling.capabilities import TOOL_CONTEXT_COMPANY, TOOL_CONTEXT_USER
from src.intelligence.tools_support import get_active_company_id, get_active_user_id

logger = logging.getLogger(__name__)


def _current_surface() -> str:
    return str(os.environ.get("APP32_MCP_SURFACE") or "user").strip().lower()


def _build_mcp_principal(company_id: int | None) -> dict[str, object]:
    user_id = get_active_user_id()
    runtime_identity = (
        resolve_runtime_identity(user_id=int(user_id), company_id=company_id)
        if user_id
        else {}
    )
    permissions = runtime_identity.get("permissions") or ()
    if isinstance(permissions, dict):
        permissions = tuple(str(key).strip().lower() for key in permissions.keys() if str(key).strip())
    elif isinstance(permissions, (list, tuple, set, frozenset)):
        permissions = tuple(str(item).strip().lower() for item in permissions if str(item).strip())
    elif permissions:
        permissions = (str(permissions).strip().lower(),)
    else:
        permissions = ()

    return {
        "user_id": user_id,
        "company_id": runtime_identity.get("company_id") or company_id,
        "employee_id": runtime_identity.get("employee_id"),
        "role": runtime_identity.get("role") or str(os.environ.get("APP32_MCP_FALLBACK_ROLE") or "colaborador").strip().lower(),
        "channel": str(os.environ.get("APP32_MCP_CHANNEL") or "claude_code").strip().lower(),
        "thread_id": os.environ.get("APP32_MCP_THREAD_ID"),
        "permissions": permissions,
        "accessible_company_ids": tuple(runtime_identity.get("accessible_company_ids") or ()),
    }


def _authorize_project_mcp(
    *,
    tool_name: str,
    action: str,
    company_id: int | None,
    risk: str,
    confirmed_mutation: bool = False,
    required_permissions: tuple[str, ...] = (),
):
    principal = _build_mcp_principal(company_id)
    decision = evaluate_tool_policy(
        principal,
        ToolPolicyRequest(
            tool_name=tool_name,
            surface=_current_surface(),
            domain="projects",
            action=action,
            risk=risk,
            requested_company_id=company_id,
            accessible_company_ids=tuple(principal.get("accessible_company_ids") or ()),
            required_permissions=required_permissions,
            confirmed_mutation=confirmed_mutation,
            required_context=(TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
        ),
    )
    return principal, decision


def list_projects(
    company_id: int | None = None,
    status: str | None = None,
    include_deleted: bool = False,
    limit: int = 50,
):
    resolved_company_id = int(company_id or get_active_company_id() or 0) or None
    principal, decision = _authorize_project_mcp(
        tool_name="list_projects",
        action="read",
        company_id=resolved_company_id,
        risk="low",
        required_permissions=("project.read",),
    )
    if not decision.allowed:
        return {"success": False, "error": decision.reason, "policy": decision.to_audit_event()}

    payload, error = ProjectMCPService.list_projects(
        company_id=int(decision.resolved_company_id),
        status=status,
        include_deleted=bool(include_deleted),
        limit=limit,
    )
    if error:
        return {"success": False, "error": error}
    return {"success": True, "actor_user_id": principal.get("user_id"), **payload}


def create_project(
    name: str,
    company_id: int | None = None,
    description: str | None = None,
    responsible_name: str | None = None,
    start_date: str | None = None,
    due_date: str | None = None,
):
    resolved_company_id = int(company_id or get_active_company_id() or 0) or None
    principal, decision = _authorize_project_mcp(
        tool_name="create_project",
        action="create",
        company_id=resolved_company_id,
        risk="medium",
        required_permissions=("project.create",),
    )
    if not decision.allowed:
        return {"success": False, "error": decision.reason, "policy": decision.to_audit_event()}

    limit_decision = evaluate_mutation_limit(
        action="create",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return {"success": False, "error": limit_decision.reason, "limits": limit_decision.to_dict()}

    payload, error = ProjectMCPService.create_project(
        company_id=int(decision.resolved_company_id),
        name=name,
        description=description,
        responsible_name=responsible_name,
        start_date=start_date,
        due_date=due_date,
    )
    if error:
        return {"success": False, "error": error}

    project = (payload or {}).get("project") or {}
    record_mutation_success(
        action="create",
        company_id=int(decision.resolved_company_id),
        user_id=int(principal["user_id"]),
        tool_name="create_project",
        domain="projects",
        metadata={"project_id": project.get("id"), "project_code": project.get("code")},
    )
    return {"success": True, **(payload or {})}


def update_project(
    changes: dict,
    company_id: int | None = None,
    project_id: int | None = None,
    project_code: str | None = None,
):
    resolved_company_id = int(company_id or get_active_company_id() or 0) or None
    principal, decision = _authorize_project_mcp(
        tool_name="update_project",
        action="update",
        company_id=resolved_company_id,
        risk="medium",
        required_permissions=("project.update",),
    )
    if not decision.allowed:
        return {"success": False, "error": decision.reason, "policy": decision.to_audit_event()}

    limit_decision = evaluate_mutation_limit(
        action="update",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return {"success": False, "error": limit_decision.reason, "limits": limit_decision.to_dict()}

    payload, error = ProjectMCPService.update_project(
        company_id=int(decision.resolved_company_id),
        project_id=int(project_id) if project_id else None,
        project_code=project_code,
        changes=dict(changes or {}),
    )
    if error:
        return {"success": False, "error": error}

    project = (payload or {}).get("project") or {}
    record_mutation_success(
        action="update",
        company_id=int(decision.resolved_company_id),
        user_id=int(principal["user_id"]),
        tool_name="update_project",
        domain="projects",
        metadata={"project_id": project.get("id"), "project_code": project.get("code")},
    )
    return {"success": True, **(payload or {})}


def delete_project(
    reason: str,
    company_id: int | None = None,
    project_id: int | None = None,
    project_code: str | None = None,
    confirm: bool = False,
):
    resolved_company_id = int(company_id or get_active_company_id() or 0) or None
    principal, decision = _authorize_project_mcp(
        tool_name="delete_project",
        action="delete",
        company_id=resolved_company_id,
        risk="high",
        confirmed_mutation=bool(confirm),
        required_permissions=("project.delete",),
    )
    if not decision.allowed:
        return {"success": False, "error": decision.reason, "policy": decision.to_audit_event()}

    limit_decision = evaluate_mutation_limit(
        action="delete",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return {"success": False, "error": limit_decision.reason, "limits": limit_decision.to_dict()}

    payload, error = ProjectMCPService.soft_delete_project(
        company_id=int(decision.resolved_company_id),
        user_id=int(principal["user_id"]),
        reason=reason,
        project_id=int(project_id) if project_id else None,
        project_code=project_code,
    )
    if error:
        return {"success": False, "error": error}

    project = (payload or {}).get("project") or {}
    record_mutation_success(
        action="delete",
        company_id=int(decision.resolved_company_id),
        user_id=int(principal["user_id"]),
        tool_name="delete_project",
        domain="projects",
        metadata={"project_id": project.get("id"), "project_code": project.get("code")},
    )
    return {"success": True, **(payload or {})}
