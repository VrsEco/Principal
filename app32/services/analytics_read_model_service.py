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
    def get_plan_diagnostics_read_model(*, company_id: int, plan_id: int) -> dict[str, Any]:
        data = PlanService.get_plan_dashboard_data(plan_id, company_id)
        if not data:
            raise ValueError("Plano não encontrado para a empresa informada.")

        sections = data.get("sections") or []
        delayed_sections = [section for section in sections if section.get("status") == "pending"]
        in_progress_sections = [section for section in sections if section.get("status") == "in_progress"]

        return {
            "company_id": company_id,
            "plan_id": plan_id,
            "plan": data.get("plan") or {},
            "stats": data.get("stats") or {},
            "sections": sections,
            "insights": {
                "pending_sections": len(delayed_sections),
                "in_progress_sections": len(in_progress_sections),
                "completed_sections": (data.get("stats") or {}).get("completed_sections", 0),
                "completion_ratio": (data.get("stats") or {}).get("progress_pct", 0),
            },
        }

    @staticmethod
    def get_team_workload_read_model(
        *,
        company_id: int,
        department: str | None = None,
        employee_id: int | None = None,
    ) -> dict[str, Any]:
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

        return {
            "company_id": company_id,
            "department": department,
            "employee_id": employee_id,
            "summary": {
                "members": len(members),
                "total_capacity_hours": round(total_capacity, 2),
                "total_estimated_hours": round(total_estimated, 2),
                "avg_utilization_pct": round((total_estimated / total_capacity) * 100, 2) if total_capacity else 0.0,
            },
            "members": members,
        }

    @staticmethod
    def get_projects_execution_risk_read_model(
        *,
        company_id: int,
        project_id: int | None = None,
        employee_id: int | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
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

        return {
            "company_id": company_id,
            "project_id": project_id,
            "employee_id": employee_id,
            "status": status,
            "summary": {
                "risk_items": len(risk_items),
                "overdue_items": overdue_count,
                "projects_with_risk": len(project_summary_rows),
            },
            "projects": [
                {
                    "project_id": row.project_id,
                    "project_name": row.project_name,
                    "open_tasks": int(row.open_tasks or 0),
                    "overdue_tasks": int(row.overdue_tasks or 0),
                }
                for row in project_summary_rows
            ],
            "risk_items": risk_items,
        }
