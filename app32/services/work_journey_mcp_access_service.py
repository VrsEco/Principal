from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models import Employee
from services.work_journey_base import WorkJourneyError
from src.core.mcp_runtime import MCPExecutionContext, resolve_mcp_execution_context


_PRIVILEGED_ROLES = {"admin", "administrator", "administrador", "client", "cliente"}


@dataclass(frozen=True)
class WorkJourneyMcpActorScope:
    company_id: int
    employee_ids: tuple[int, ...]
    execution_context: MCPExecutionContext
    privileged: bool


def is_privileged_work_journey_role(role: str | None) -> bool:
    return str(role or "").strip().lower() in _PRIVILEGED_ROLES


def resolve_actor_scope(
    *,
    company_id: int | None,
    employee_id: int | None = None,
    include_all: bool = False,
    department: str | None = None,
    payload: dict[str, Any] | None = None,
) -> WorkJourneyMcpActorScope:
    execution_context = resolve_mcp_execution_context(payload or {})
    resolved_company_id = _resolve_company_id(company_id, execution_context)
    privileged = is_privileged_work_journey_role(execution_context.role)

    query = Employee.query.filter_by(company_id=resolved_company_id, status="active")
    if department:
        query = query.filter(Employee.department == department)

    if employee_id is not None:
        employee = query.filter(Employee.id == int(employee_id)).first()
        if not employee:
            raise WorkJourneyError("Colaborador não encontrado para a empresa informada.")
        _ensure_employee_visible(int(employee.id), execution_context, privileged)
        return WorkJourneyMcpActorScope(
            company_id=resolved_company_id,
            employee_ids=(int(employee.id),),
            execution_context=execution_context,
            privileged=privileged,
        )

    if not privileged:
        if execution_context.employee_id is None:
            raise WorkJourneyError("Sessão MCP sem colaborador vinculado para a operação solicitada.")
        employee = query.filter(Employee.id == int(execution_context.employee_id)).first()
        if not employee:
            raise WorkJourneyError("Colaborador da sessão não encontrado para a empresa ativa.")
        return WorkJourneyMcpActorScope(
            company_id=resolved_company_id,
            employee_ids=(int(employee.id),),
            execution_context=execution_context,
            privileged=False,
        )

    if include_all or department:
        employee_ids = tuple(int(row.id) for row in query.order_by(Employee.name.asc()).all())
    elif execution_context.employee_id is not None:
        employee_ids = (int(execution_context.employee_id),)
    else:
        employee_ids = tuple(int(row.id) for row in query.order_by(Employee.name.asc()).all())

    return WorkJourneyMcpActorScope(
        company_id=resolved_company_id,
        employee_ids=employee_ids,
        execution_context=execution_context,
        privileged=privileged,
    )


def ensure_employee_mutation_allowed(
    *,
    company_id: int | None,
    employee_id: int,
    payload: dict[str, Any] | None = None,
) -> tuple[int, MCPExecutionContext]:
    execution_context = resolve_mcp_execution_context(payload or {})
    resolved_company_id = _resolve_company_id(company_id, execution_context)
    privileged = is_privileged_work_journey_role(execution_context.role)
    _ensure_employee_visible(int(employee_id), execution_context, privileged)
    employee = Employee.query.filter_by(
        company_id=resolved_company_id,
        id=int(employee_id),
        status="active",
    ).first()
    if not employee:
        raise WorkJourneyError("Colaborador não encontrado para a empresa informada.")
    return resolved_company_id, execution_context


def _resolve_company_id(company_id: int | None, execution_context: MCPExecutionContext) -> int:
    resolved_company_id = int(company_id or execution_context.company_id or 0)
    if resolved_company_id <= 0:
        raise WorkJourneyError("company_id obrigatório para a operação MCP.")
    accessible = {int(item) for item in (execution_context.accessible_company_ids or ()) if int(item) > 0}
    if accessible and resolved_company_id not in accessible:
        raise WorkJourneyError("A empresa solicitada não está acessível para a sessão MCP atual.")
    return resolved_company_id


def _ensure_employee_visible(employee_id: int, execution_context: MCPExecutionContext, privileged: bool) -> None:
    if privileged:
        return
    if execution_context.employee_id is None:
        raise WorkJourneyError("Sessão MCP sem colaborador vinculado para a operação solicitada.")
    if int(execution_context.employee_id) != int(employee_id):
        raise WorkJourneyError("Esta sessão MCP só pode acessar o próprio colaborador.")
