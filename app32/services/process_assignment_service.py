from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, or_

from models import db, Employee, ProcessExecutionAssignment, ProcessInstance, ProcessInstanceExecution, Role, Team
from models.team import TeamMember


ACTIVE_ASSIGNMENT_STATUSES = {"assigned", "claimed"}
ACTIONABLE_EXECUTION_MODES = {"human_task", "manual_external", "open_form", "open_app32_page"}


class ProcessAssignmentValidationError(ValueError):
    pass


def is_execution_actionable(execution: ProcessInstanceExecution) -> bool:
    if str(execution.status or "").lower() in {"completed", "failed", "skipped"}:
        return False
    if str(execution.execution_mode or "").lower() in ACTIONABLE_EXECUTION_MODES:
        return True
    metadata = dict(execution.metadata_json or {})
    return bool(
        str(execution.status or "").lower() == "waiting_human"
        or metadata.get("requires_human_gate")
        or metadata.get("fallback_required")
        or metadata.get("human_review_required")
    )


def extract_assignment_payload(payload: dict | None) -> dict | None:
    """Remove os campos de atribuicao antes da validacao do schema da execution."""
    if not isinstance(payload, dict):
        return None
    nested = payload.pop("assignment", None)
    if isinstance(nested, dict):
        return dict(nested)
    employee_id = payload.pop("assigned_employee_id", None)
    if employee_id is not None:
        return {"assignee_type": "employee", "employee_id": employee_id}
    return None


def ensure_execution_assignment(
    *,
    company_id: int,
    instance: ProcessInstance,
    execution: ProcessInstanceExecution,
    assignment_payload: dict | None = None,
    assigned_by_user_id: int | None = None,
) -> ProcessExecutionAssignment | None:
    if int(instance.company_id) != int(company_id) or int(execution.company_id) != int(company_id):
        raise ProcessAssignmentValidationError("Execucao fora do escopo da empresa.")
    if int(execution.process_instance_id) != int(instance.id):
        raise ProcessAssignmentValidationError("Execucao nao pertence a instancia informada.")

    active = _active_assignments(company_id, execution.id)
    if not is_execution_actionable(execution):
        _finish_assignments(active, completed=execution.status == "completed")
        return None
    if assignment_payload is None and active:
        return active[0]

    target = _resolve_target(company_id, instance, execution, assignment_payload)
    if not target:
        return None

    for current in active:
        if _same_target(current, target):
            return current
        current.status = "cancelled"
        db.session.add(current)

    assignment = ProcessExecutionAssignment(
        company_id=company_id,
        activity_execution_id=execution.id,
        assignee_type=target["assignee_type"],
        employee_id=target.get("employee_id"),
        team_id=target.get("team_id"),
        role_key=target.get("role_key"),
        status="assigned",
        source=target["source"],
        assigned_by_user_id=assigned_by_user_id,
    )
    db.session.add(assignment)
    db.session.flush()
    return assignment


def sync_execution_assignment_status(company_id: int, execution: ProcessInstanceExecution) -> None:
    active = _active_assignments(company_id, execution.id)
    if execution.status == "completed":
        _finish_assignments(active, completed=True)
    elif execution.status in {"failed", "skipped"}:
        _finish_assignments(active, completed=False)


def employee_assignment_execution_ids(company_id: int, employee_id: int) -> list[int]:
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id, status="active").first()
    if not employee:
        return []
    team_ids = [row.team_id for row in TeamMember.query.filter_by(employee_id=employee_id, left_at=None).all()]
    role_keys = []
    if employee.role:
        role_keys.extend([str(employee.role.id), str(employee.role.title or "").strip().lower()])
    rows = (
        ProcessExecutionAssignment.query.filter(
            ProcessExecutionAssignment.company_id == company_id,
            ProcessExecutionAssignment.status.in_(list(ACTIVE_ASSIGNMENT_STATUSES)),
            or_(
                and_(
                    ProcessExecutionAssignment.assignee_type == "employee",
                    ProcessExecutionAssignment.employee_id == employee_id,
                ),
                and_(
                    ProcessExecutionAssignment.assignee_type == "team",
                    ProcessExecutionAssignment.team_id.in_(team_ids or [-1]),
                ),
                and_(
                    ProcessExecutionAssignment.assignee_type == "role",
                    ProcessExecutionAssignment.role_key.in_(role_keys or ["__none__"]),
                ),
            ),
        )
        .all()
    )
    return [int(row.activity_execution_id) for row in rows]


def employee_has_assignment_for_instance(company_id: int, employee_id: int, instance_id: int) -> bool:
    execution_ids = employee_assignment_execution_ids(company_id, employee_id)
    if not execution_ids:
        return False
    return (
        ProcessInstanceExecution.query.filter(
            ProcessInstanceExecution.company_id == company_id,
            ProcessInstanceExecution.process_instance_id == instance_id,
            ProcessInstanceExecution.id.in_(execution_ids),
        ).first()
        is not None
    )


def employee_can_execute_activity(
    company_id: int,
    employee_id: int,
    instance: ProcessInstance,
    activity_execution_id: int,
) -> bool:
    """Autoriza operação humana apenas no tenant e na atividade atribuída/dirigida."""
    if not instance or int(instance.company_id) != int(company_id):
        return False
    if employee_id in {
        instance.owner_employee_id,
        instance.responsible_id,
        instance.executor_id,
    }:
        return True
    return int(activity_execution_id) in employee_assignment_execution_ids(company_id, employee_id)


def assigned_employee_id(company_id: int, execution_id: int) -> int | None:
    row = (
        ProcessExecutionAssignment.query.filter_by(
            company_id=company_id,
            activity_execution_id=execution_id,
            assignee_type="employee",
        )
        .filter(ProcessExecutionAssignment.status.in_(list(ACTIVE_ASSIGNMENT_STATUSES)))
        .order_by(ProcessExecutionAssignment.assigned_at.desc(), ProcessExecutionAssignment.id.desc())
        .first()
    )
    return int(row.employee_id) if row and row.employee_id else None


def _active_assignments(company_id: int, execution_id: int) -> list[ProcessExecutionAssignment]:
    return (
        ProcessExecutionAssignment.query.filter(
            ProcessExecutionAssignment.company_id == company_id,
            ProcessExecutionAssignment.activity_execution_id == execution_id,
            ProcessExecutionAssignment.status.in_(list(ACTIVE_ASSIGNMENT_STATUSES)),
        )
        .order_by(ProcessExecutionAssignment.id.asc())
        .all()
    )


def _resolve_target(company_id, instance, execution, assignment_payload):
    if assignment_payload:
        assignee_type = str(assignment_payload.get("assignee_type") or "employee").strip().lower()
        if assignee_type == "employee":
            employee_id = _valid_employee_id(company_id, assignment_payload.get("employee_id"))
            if not employee_id:
                raise ProcessAssignmentValidationError("Colaborador atribuido invalido para esta empresa.")
            return {"assignee_type": "employee", "employee_id": employee_id, "source": "explicit"}
        if assignee_type == "team":
            team = Team.query.filter_by(id=assignment_payload.get("team_id"), company_id=company_id, is_active=True).first()
            if not team:
                raise ProcessAssignmentValidationError("Equipe atribuida invalida para esta empresa.")
            return {"assignee_type": "team", "team_id": team.id, "source": "explicit"}
        if assignee_type == "role":
            role = _resolve_role(company_id, assignment_payload.get("role_key"))
            if not role:
                raise ProcessAssignmentValidationError("Funcao atribuida invalida para esta empresa.")
            return {"assignee_type": "role", "role_key": str(role.id), "source": "explicit"}
        raise ProcessAssignmentValidationError("Tipo de atribuicao invalido.")

    metadata = dict(execution.metadata_json or {})
    candidates = [
        (metadata.get("responsible_employee_id"), "execution_metadata"),
        (metadata.get("executor_employee_id"), "execution_metadata"),
        (metadata.get("owner_employee_id"), "execution_metadata"),
        (metadata.get("employee_id"), "execution_metadata"),
        (instance.executor_id, "instance_fallback"),
        (instance.responsible_id, "instance_fallback"),
        (instance.owner_employee_id, "instance_fallback"),
    ]
    for candidate, source in candidates:
        employee_id = _valid_employee_id(company_id, candidate)
        if employee_id:
            return {"assignee_type": "employee", "employee_id": employee_id, "source": source}
    return None


def _valid_employee_id(company_id, candidate):
    try:
        candidate = int(candidate)
    except (TypeError, ValueError):
        return None
    employee = Employee.query.filter_by(id=candidate, company_id=company_id, status="active").first()
    return int(employee.id) if employee else None


def _resolve_role(company_id, role_key):
    if role_key is None:
        return None
    raw = str(role_key).strip()
    if raw.isdigit():
        return Role.query.filter_by(id=int(raw), company_id=company_id).first()
    return Role.query.filter(Role.company_id == company_id, func.lower(Role.title) == raw.lower()).first()


def _same_target(assignment, target):
    return (
        assignment.assignee_type == target["assignee_type"]
        and assignment.employee_id == target.get("employee_id")
        and assignment.team_id == target.get("team_id")
        and assignment.role_key == target.get("role_key")
    )


def _finish_assignments(assignments, *, completed):
    now = datetime.utcnow()
    for assignment in assignments:
        assignment.status = "completed" if completed else "cancelled"
        assignment.completed_at = now if completed else None
        db.session.add(assignment)
