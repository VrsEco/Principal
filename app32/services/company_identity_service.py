from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import joinedload

from models import Company, Employee, Role


ACTIVE_EMPLOYEE_STATUSES = {"active", "ativo", None, ""}


@dataclass(frozen=True)
class IdentitySummary:
    company: dict[str, Any]
    metrics: dict[str, Any]
    roles: list[dict[str, Any]]
    employees: list[dict[str, Any]]


class CompanyIdentityService:
    """Agrega a leitura da identidade organizacional de uma empresa."""

    @staticmethod
    def build_summary(company_id: int) -> IdentitySummary:
        company = Company.query.filter_by(id=company_id).first_or_404()
        roles = Role.query.filter_by(company_id=company_id).order_by(Role.title.asc()).all()
        employees = (
            Employee.query.options(joinedload(Employee.role))
            .filter_by(company_id=company_id)
            .order_by(Employee.name.asc())
            .all()
        )

        roles_payload = [CompanyIdentityService._serialize_role(role, employees) for role in roles]
        employees_payload = [CompanyIdentityService._serialize_employee(employee) for employee in employees]

        active_employees = [
            employee for employee in employees if (employee.status or "").strip().lower() in {"", "active", "ativo"}
        ]
        employees_without_role = [employee for employee in employees if not employee.role_id]
        departments = sorted(
            {
                (role.department or "").strip()
                for role in roles
                if (role.department or "").strip()
            }
            | {
                (employee.department or "").strip()
                for employee in employees
                if (employee.department or "").strip()
            }
        )

        metrics = {
            "roles_total": len(roles),
            "employees_total": len(employees),
            "active_employees_total": len(active_employees),
            "departments_total": len(departments),
            "employees_without_role_total": len(employees_without_role),
            "planned_headcount_total": sum(int(role.headcount_planned or 0) for role in roles),
        }

        return IdentitySummary(
            company=company.to_dict(),
            metrics=metrics,
            roles=roles_payload,
            employees=employees_payload,
        )

    @staticmethod
    def build_roles_tree(company_id: int) -> list[dict[str, Any]]:
        roles = Role.query.filter_by(company_id=company_id).order_by(Role.title.asc()).all()
        employees = (
            Employee.query.options(joinedload(Employee.role))
            .filter_by(company_id=company_id)
            .order_by(Employee.name.asc())
            .all()
        )

        employees_by_role: dict[int, list[Employee]] = defaultdict(list)
        for employee in employees:
            if employee.role_id:
                employees_by_role[int(employee.role_id)].append(employee)

        nodes_by_id: dict[int, dict[str, Any]] = {}
        roots: list[dict[str, Any]] = []

        for role in roles:
            assigned_employees = employees_by_role.get(role.id, [])
            active_assigned = [
                employee
                for employee in assigned_employees
                if (employee.status or "").strip().lower() in {"", "active", "ativo"}
            ]
            nodes_by_id[role.id] = {
                "id": role.id,
                "parent_id": role.parent_role_id,
                "title": role.title,
                "department": role.department,
                "color": role.color or "#D9ECFF",
                "headcount_planned": int(role.headcount_planned or 0),
                "employee_count": len(assigned_employees),
                "active_employee_count": len(active_assigned),
                "employees": [
                    {
                        "id": employee.id,
                        "name": employee.name,
                        "status": employee.status,
                    }
                    for employee in assigned_employees
                ],
                "children": [],
            }

        for node in nodes_by_id.values():
            parent_id = node["parent_id"]
            parent = nodes_by_id.get(parent_id) if parent_id else None
            if parent:
                parent["children"].append(node)
            else:
                roots.append(node)

        for node in nodes_by_id.values():
            node["children"].sort(key=lambda item: (item.get("department") or "", item.get("title") or ""))

        roots.sort(key=lambda item: (item.get("department") or "", item.get("title") or ""))
        return roots

    @staticmethod
    def _serialize_role(role: Role, employees: list[Employee]) -> dict[str, Any]:
        assigned = [employee for employee in employees if employee.role_id == role.id]
        active_assigned = [
            employee
            for employee in assigned
            if (employee.status or "").strip().lower() in {"", "active", "ativo"}
        ]
        planned_headcount = int(role.headcount_planned or 0)
        vacancy_count = max(planned_headcount - len(active_assigned), 0)

        return {
            "id": role.id,
            "company_id": role.company_id,
            "title": role.title,
            "parent_role_id": role.parent_role_id,
            "parent_role_title": role.reports_to,
            "department": role.department,
            "color": role.color,
            "headcount_planned": planned_headcount,
            "weekly_hours": float(role.weekly_hours) if role.weekly_hours is not None else None,
            "notes": role.notes,
            "employee_count": len(assigned),
            "active_employee_count": len(active_assigned),
            "vacancy_count": vacancy_count,
        }

    @staticmethod
    def _serialize_employee(employee: Employee) -> dict[str, Any]:
        payload = employee.to_dict()
        payload["status_label"] = CompanyIdentityService._status_label(employee.status)
        payload["role_title"] = employee.role.title if employee.role else payload.get("role_title")
        payload["role_department"] = employee.role.department if employee.role else None
        return payload

    @staticmethod
    def _status_label(status: str | None) -> str:
        normalized = (status or "").strip().lower()
        if normalized in {"", "active", "ativo"}:
            return "Ativo"
        if normalized in {"inactive", "inativo"}:
            return "Inativo"
        if normalized in {"vacation", "ferias", "férias"}:
            return "Férias"
        return status or "Não informado"
