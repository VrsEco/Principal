from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, or_

from models import db
from models.employee import Employee
from models.process import ProcessInstance
from models.project import Project, ProjectTask
from services.plan_service import PlanService
from src.intelligence.mcp_contracts import build_analytics_ai_envelope


def _ensure_accessible_company(company_id: int, accessible_company_ids: list[int] | tuple[int, ...] | set[int] | None = None) -> int:
    try:
        normalized_company_id = int(company_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("company_id inválido para read model analítico.") from exc

    if normalized_company_id <= 0:
        raise ValueError("company_id inválido para read model analítico.")

    if accessible_company_ids is not None:
        allowed = {int(item) for item in accessible_company_ids if item is not None}
        if normalized_company_id not in allowed:
            raise PermissionError("company_id solicitado não pertence ao escopo analítico permitido.")

    return normalized_company_id


def _to_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return float(value or 0)


class AnalyticsReadModelService:
    """Read models whitelisted para analytics MCP, sempre tenant-safe."""

    @staticmethod
    def get_plan_diagnostics_read_model(
        *,
        company_id: int,
        plan_id: int,
        accessible_company_ids: list[int] | tuple[int, ...] | set[int] | None = None,
    ) -> dict[str, Any]:
        company_id = _ensure_accessible_company(company_id, accessible_company_ids)
        data = PlanService.get_plan_dashboard_data(plan_id, company_id)
        if not data:
            raise ValueError("Plano não encontrado para a empresa informada.")

        sections = data.get("sections") or []
        delayed_sections = [section for section in sections if section.get("status") == "pending"]
        in_progress_sections = [section for section in sections if section.get("status") == "in_progress"]

        envelope = build_analytics_ai_envelope(
            analysis_id="strategy_plan_diagnostics",
            read_model="strategy.plan_diagnostics",
            company_id=company_id,
            filters={"company_id": company_id, "plan_id": plan_id},
            summary=data.get("stats") or {},
            rows=sections,
            dimensions={"plan": data.get("plan") or {}},
            signals={
                "pending_sections": len(delayed_sections),
                "in_progress_sections": len(in_progress_sections),
                "completed_sections": (data.get("stats") or {}).get("completed_sections", 0),
                "completion_ratio": (data.get("stats") or {}).get("progress_pct", 0),
            },
            capability_names=["get_plan_diagnostics", "get_plan_diagnostics_read_model"],
            limitations=["Não inclui dados fora do plano e da empresa informados."],
        )
        payload = envelope.model_dump(mode="json")
        payload["plan_id"] = plan_id
        payload["plan"] = data.get("plan") or {}
        payload["sections"] = sections
        payload["insights"] = payload["signals"]
        return payload

    @staticmethod
    def get_team_workload_read_model(
        *,
        company_id: int,
        department: str | None = None,
        employee_id: int | None = None,
        accessible_company_ids: list[int] | tuple[int, ...] | set[int] | None = None,
    ) -> dict[str, Any]:
        company_id = _ensure_accessible_company(company_id, accessible_company_ids)
        filters = [Employee.company_id == company_id, Employee.status == "active"]
        if department:
            filters.append(Employee.department == department)
        if employee_id:
            filters.append(Employee.id == employee_id)

        employees = (
            db.session.query(Employee)
            .filter(*filters)
            .order_by(Employee.name.asc())
            .all()
        )

        members: list[dict[str, Any]] = []
        total_capacity = 0.0
        total_estimated = 0.0

        for employee in employees:
            open_project_tasks, project_estimated_hours = (
                db.session.query(
                    func.count(ProjectTask.id),
                    func.coalesce(func.sum(ProjectTask.estimated_hours), 0),
                )
                .filter(ProjectTask.employee_id == employee.id)
                .filter(ProjectTask.status.notin_(["completed", "cancelled"]))
                .one()
            )
            open_process_instances, process_estimated_hours = (
                db.session.query(
                    func.count(ProcessInstance.id),
                    func.coalesce(func.sum(ProcessInstance.estimated_hours), 0),
                )
                .filter(
                    or_(
                        ProcessInstance.owner_employee_id == employee.id,
                        ProcessInstance.responsible_id == employee.id,
                        ProcessInstance.executor_id == employee.id,
                    )
                )
                .filter(ProcessInstance.status.notin_(["completed", "cancelled"]))
                .one()
            )

            weekly_hours = _to_number(employee.weekly_hours) or 40.0
            estimated_hours = _to_number(project_estimated_hours) + _to_number(process_estimated_hours)
            if estimated_hours <= 0:
                estimated_hours = float((open_project_tasks or 0) + (open_process_instances or 0)) * 2.0
            utilization_pct = round((estimated_hours / weekly_hours) * 100, 2) if weekly_hours else 0.0

            members.append(
                {
                    "employee_id": employee.id,
                    "employee_name": employee.name,
                    "department": employee.department,
                    "weekly_hours": weekly_hours,
                    "open_project_tasks": int(open_project_tasks or 0),
                    "open_process_instances": int(open_process_instances or 0),
                    "estimated_hours": round(estimated_hours, 2),
                    "utilization_pct": utilization_pct,
                    "risk_label": "overloaded" if utilization_pct >= 100 else "attention" if utilization_pct >= 70 else "balanced",
                }
            )
            total_capacity += weekly_hours
            total_estimated += estimated_hours

        envelope = build_analytics_ai_envelope(
            analysis_id="workload_team_capacity",
            read_model="workload.team_capacity",
            company_id=company_id,
            filters={"company_id": company_id, "department": department, "employee_id": employee_id},
            summary={
                "members": len(members),
                "total_capacity_hours": round(total_capacity, 2),
                "total_estimated_hours": round(total_estimated, 2),
                "avg_utilization_pct": round((total_estimated / total_capacity) * 100, 2) if total_capacity else 0.0,
            },
            rows=members,
            dimensions={"department": department, "employee_id": employee_id},
            signals={
                "overloaded_members": len([member for member in members if member["risk_label"] == "overloaded"]),
                "attention_members": len([member for member in members if member["risk_label"] == "attention"]),
            },
            capability_names=["list_team_workload", "get_team_workload_read_model"],
            limitations=["Estimativas dependem de horas estimadas preenchidas; quando ausentes, usa heurística conservadora."],
        )
        payload = envelope.model_dump(mode="json")
        payload["department"] = department
        payload["employee_id"] = employee_id
        payload["members"] = members
        return payload

    @staticmethod
    def get_projects_execution_risk_read_model(
        *,
        company_id: int,
        project_id: int | None = None,
        employee_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
        accessible_company_ids: list[int] | tuple[int, ...] | set[int] | None = None,
    ) -> dict[str, Any]:
        company_id = _ensure_accessible_company(company_id, accessible_company_ids)
        today = date.today()
        query = (
            db.session.query(
                Project.id.label("project_id"),
                Project.name.label("project_name"),
                Project.status.label("project_status"),
                ProjectTask.id.label("task_id"),
                ProjectTask.what.label("task_title"),
                ProjectTask.status.label("task_status"),
                ProjectTask.stage.label("task_stage"),
                ProjectTask.priority.label("priority"),
                ProjectTask.due_date.label("due_date"),
                ProjectTask.employee_id.label("employee_id"),
                Employee.name.label("employee_name"),
                case((ProjectTask.due_date < today, 1), else_=0).label("is_overdue"),
            )
            .join(Project, Project.id == ProjectTask.project_id)
            .outerjoin(Employee, Employee.id == ProjectTask.employee_id)
            .filter(Project.company_id == company_id)
            .filter(ProjectTask.status.notin_(["completed", "cancelled"]))
        )

        if project_id:
            query = query.filter(Project.id == project_id)
        if employee_id:
            query = query.filter(ProjectTask.employee_id == employee_id)
        if status:
            query = query.filter(ProjectTask.status == status)

        rows = (
            query.order_by(
                case((ProjectTask.priority == "urgent", 0), (ProjectTask.priority == "high", 1), else_=2),
                case((ProjectTask.due_date.is_(None), 1), else_=0),
                ProjectTask.due_date.asc(),
            )
            .limit(limit)
            .all()
        )

        risk_items: list[dict[str, Any]] = []
        overdue_count = 0

        for row in rows:
            overdue = bool(row.is_overdue)
            if overdue:
                overdue_count += 1
            risk_items.append(
                {
                    "project_id": row.project_id,
                    "project_name": row.project_name,
                    "project_status": row.project_status,
                    "task_id": row.task_id,
                    "task_title": row.task_title,
                    "task_status": row.task_status,
                    "task_stage": row.task_stage,
                    "priority": row.priority,
                    "due_date": row.due_date.isoformat() if row.due_date else None,
                    "employee_id": row.employee_id,
                    "employee_name": row.employee_name,
                    "is_overdue": overdue,
                    "risk_label": "critical" if overdue and row.priority in {"high", "urgent"} else "high" if overdue else "watch",
                }
            )

        project_summary_rows = (
            db.session.query(
                Project.id.label("project_id"),
                Project.name.label("project_name"),
                func.count(ProjectTask.id).label("open_tasks"),
                func.sum(case((ProjectTask.due_date < today, 1), else_=0)).label("overdue_tasks"),
            )
            .join(ProjectTask, ProjectTask.project_id == Project.id)
            .filter(Project.company_id == company_id)
            .filter(ProjectTask.status.notin_(["completed", "cancelled"]))
            .group_by(Project.id, Project.name)
            .order_by(func.sum(case((ProjectTask.due_date < today, 1), else_=0)).desc(), func.count(ProjectTask.id).desc())
            .limit(10)
            .all()
        )

        envelope = build_analytics_ai_envelope(
            analysis_id="projects_execution_risk",
            read_model="projects.execution_risk",
            company_id=company_id,
            filters={
                "company_id": company_id,
                "project_id": project_id,
                "employee_id": employee_id,
                "status": status,
                "limit": limit,
            },
            summary={
                "risk_items": len(risk_items),
                "overdue_items": overdue_count,
                "projects_with_risk": len(project_summary_rows),
            },
            rows=risk_items,
            dimensions={
                "projects": [
                    {
                        "project_id": row.project_id,
                        "project_name": row.project_name,
                        "open_tasks": int(row.open_tasks or 0),
                        "overdue_tasks": int(row.overdue_tasks or 0),
                    }
                    for row in project_summary_rows
                ],
            },
            signals={
                "critical_items": len([item for item in risk_items if item["risk_label"] == "critical"]),
                "high_items": len([item for item in risk_items if item["risk_label"] == "high"]),
                "watch_items": len([item for item in risk_items if item["risk_label"] == "watch"]),
            },
            capability_names=["get_projects_execution_risk_read_model"],
            limitations=["Primeira versão foca atividades de projeto abertas e não executa mutações."],
        )
        payload = envelope.model_dump(mode="json")
        payload["projects"] = [
                {
                    "project_id": row.project_id,
                    "project_name": row.project_name,
                    "open_tasks": int(row.open_tasks or 0),
                    "overdue_tasks": int(row.overdue_tasks or 0),
                }
                for row in project_summary_rows
            ]
        payload["risk_items"] = risk_items
        return payload
