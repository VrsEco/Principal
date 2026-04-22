from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import and_, func, or_

from models import db
from models.employee import Employee
from models.user import User
from models.user_employee_assignment import UserEmployeeAssignment
from services.identity.identity_normalizer import (
    normalize_email,
    normalize_name,
    normalize_phone,
)


@dataclass
class IdentityPayload:
    name: str | None
    email: str | None
    phone: str | None
    whatsapp: str | None

    @property
    def normalized_email(self) -> str | None:
        return normalize_email(self.email)

    @property
    def normalized_phone(self) -> str | None:
        return normalize_phone(self.phone or self.whatsapp)

    @property
    def normalized_name(self) -> str | None:
        return normalize_name(self.name)


class UserEmployeeOrchestratorService:
    """Fonte canônica para criação e vínculo usuário x colaborador."""

    @staticmethod
    def register_or_link_user_employee(
        *,
        company_id: int,
        user_payload: dict[str, Any] | None = None,
        employee_payload: dict[str, Any] | None = None,
        create_system_access: bool = True,
        employee_id: int | None = None,
        existing_user_id: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        user_payload = dict(user_payload or {})
        employee_payload = dict(employee_payload or {})
        identity = UserEmployeeOrchestratorService._build_identity_payload(
            user_payload=user_payload,
            employee_payload=employee_payload,
        )

        try:
            user = UserEmployeeOrchestratorService._resolve_user(
                existing_user_id=existing_user_id,
                create_system_access=create_system_access,
                user_payload=user_payload,
                identity=identity,
            )
            employee = UserEmployeeOrchestratorService._resolve_employee(
                company_id=company_id,
                employee_payload=employee_payload,
                user=user,
                identity=identity,
                employee_id=employee_id,
            )

            action_parts: list[str] = []

            if not user and create_system_access:
                user = UserEmployeeOrchestratorService._create_user(
                    user_payload=user_payload,
                    identity=identity,
                )
                action_parts.append("created_user")

            if not employee:
                employee = UserEmployeeOrchestratorService._create_employee(
                    company_id=company_id,
                    employee_payload=employee_payload,
                    user=user,
                    identity=identity,
                )
                action_parts.append("created_employee")
            else:
                UserEmployeeOrchestratorService._sync_employee_identity(
                    employee=employee,
                    user=user,
                    identity=identity,
                    employee_payload=employee_payload,
                )

            assignment = None
            if create_system_access and user:
                assignment_result = UserEmployeeOrchestratorService._ensure_assignment(
                    user=user,
                    employee=employee,
                    start_date=start_date,
                    end_date=end_date,
                    notes=notes,
                )
                if not assignment_result["success"]:
                    db.session.rollback()
                    return assignment_result
                assignment = assignment_result.get("assignment")
                action_parts.append(assignment_result.get("action", "linked_existing"))

            db.session.commit()
            return {
                "success": True,
                "action": UserEmployeeOrchestratorService._collapse_actions(action_parts),
                "user": user.to_dict() if user else None,
                "employee": employee.to_dict() if employee else None,
                "assignment": assignment.to_dict() if assignment else None,
            }
        except Exception as exc:
            db.session.rollback()
            return {"success": False, "error": str(exc)}

    @staticmethod
    def link_existing_user_to_employee(
        *,
        company_id: int,
        user_id: int,
        employee_id: int,
        start_date: str | None = None,
        end_date: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
        if not employee:
            return {"success": False, "error": "Colaborador não encontrado"}

        return UserEmployeeOrchestratorService.register_or_link_user_employee(
            company_id=company_id,
            create_system_access=True,
            employee_id=employee_id,
            existing_user_id=user_id,
            employee_payload={
                "name": employee.name,
                "email": employee.email,
                "phone": employee.phone,
                "whatsapp": employee.whatsapp,
            },
            start_date=start_date,
            end_date=end_date,
            notes=notes,
        )

    @staticmethod
    def link_user_to_companies(
        *,
        user_id: int,
        company_ids: list[int],
        employee_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not company_ids:
            return {"success": False, "error": "Nenhuma empresa foi fornecida"}

        results = []
        failures = []
        for company_id in company_ids:
            result = UserEmployeeOrchestratorService.register_or_link_user_employee(
                company_id=company_id,
                existing_user_id=user_id,
                create_system_access=True,
                employee_payload=employee_payload,
            )
            if result.get("success"):
                results.append(result)
            else:
                failures.append({"company_id": company_id, "error": result.get("error")})

        return {
            "success": not failures,
            "results": results,
            "failures": failures,
            "linked_count": len(results),
            "failed_count": len(failures),
            "employees": [item["employee"] for item in results if item.get("employee")],
        }

    @staticmethod
    def _build_identity_payload(
        *,
        user_payload: dict[str, Any],
        employee_payload: dict[str, Any],
    ) -> IdentityPayload:
        return IdentityPayload(
            name=user_payload.get("name") or employee_payload.get("name"),
            email=user_payload.get("email") or employee_payload.get("email"),
            phone=employee_payload.get("phone") or user_payload.get("phone"),
            whatsapp=employee_payload.get("whatsapp") or user_payload.get("whatsapp"),
        )

    @staticmethod
    def _resolve_user(
        *,
        existing_user_id: int | None,
        create_system_access: bool,
        user_payload: dict[str, Any],
        identity: IdentityPayload,
    ) -> User | None:
        if existing_user_id:
            user = User.query.get(existing_user_id)
            if not user:
                raise ValueError("Usuário não encontrado")
            return user
        if not create_system_access:
            return None
        email = identity.normalized_email
        if not email:
            raise ValueError("Email é obrigatório para criar acesso ao sistema")
        return UserEmployeeOrchestratorService._find_user_by_email(email)

    @staticmethod
    def _resolve_employee(
        *,
        company_id: int,
        employee_payload: dict[str, Any],
        user: User | None,
        identity: IdentityPayload,
        employee_id: int | None,
    ) -> Employee | None:
        if employee_id:
            return Employee.query.filter_by(id=employee_id, company_id=company_id).first()

        if user:
            employee = Employee.query.filter_by(company_id=company_id, user_id=user.id).first()
            if employee:
                return employee

        email = identity.normalized_email
        if email:
            employee = Employee.query.filter(
                Employee.company_id == company_id,
                func.lower(func.trim(Employee.email)) == email,
            ).first()
            if employee:
                return employee

        phone = identity.normalized_phone
        if phone:
            employees = Employee.query.filter(Employee.company_id == company_id).all()
            matches = [
                employee
                for employee in employees
                if normalize_phone(employee.phone) == phone
                or normalize_phone(employee.whatsapp) == phone
            ]
            if len(matches) == 1:
                return matches[0]

        name = identity.normalized_name
        if name:
            employees = Employee.query.filter(Employee.company_id == company_id).all()
            matches = [
                employee
                for employee in employees
                if normalize_name(employee.name) == name
            ]
            if len(matches) == 1:
                return matches[0]

        return None

    @staticmethod
    def _find_user_by_email(email: str) -> User | None:
        return User.query.filter(func.lower(func.trim(User.email)) == email).first()

    @staticmethod
    def _create_user(*, user_payload: dict[str, Any], identity: IdentityPayload) -> User:
        password = user_payload.get("password")
        if not password:
            raise ValueError("Senha é obrigatória para criar novo usuário")

        user = User(
            name=user_payload.get("name") or identity.name or "Usuário",
            email=identity.normalized_email,
            role=user_payload.get("role", "collaborator"),
            whatsapp=user_payload.get("whatsapp"),
            telegram=user_payload.get("telegram"),
            instagram=user_payload.get("instagram"),
            summary_delivery_channels=user_payload.get("summary_delivery_channels", "telegram"),
            is_active=user_payload.get("is_active", True),
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        return user

    @staticmethod
    def _create_employee(
        *,
        company_id: int,
        employee_payload: dict[str, Any],
        user: User | None,
        identity: IdentityPayload,
    ) -> Employee:
        employee = Employee(
            company_id=company_id,
            user_id=user.id if user else None,
            role_id=employee_payload.get("role_id"),
            name=employee_payload.get("name") or user_payload_name(user) or identity.name or "Colaborador",
            email=identity.normalized_email,
            phone=employee_payload.get("phone"),
            whatsapp=employee_payload.get("whatsapp") or getattr(user, "whatsapp", None),
            telegram=employee_payload.get("telegram") or getattr(user, "telegram", None),
            department=employee_payload.get("department"),
            hire_date=employee_payload.get("hire_date"),
            status=employee_payload.get("status", "active"),
            weekly_hours=employee_payload.get("weekly_hours"),
            notes=employee_payload.get("notes"),
        )
        db.session.add(employee)
        db.session.flush()
        return employee

    @staticmethod
    def _sync_employee_identity(
        *,
        employee: Employee,
        user: User | None,
        identity: IdentityPayload,
        employee_payload: dict[str, Any],
    ) -> None:
        if user and employee.user_id in (None, user.id):
            employee.user_id = user.id
        if not employee.email and identity.normalized_email:
            employee.email = identity.normalized_email
        if not employee.phone and employee_payload.get("phone"):
            employee.phone = employee_payload.get("phone")
        if not employee.whatsapp and employee_payload.get("whatsapp"):
            employee.whatsapp = employee_payload.get("whatsapp")
        if not employee.department and employee_payload.get("department"):
            employee.department = employee_payload.get("department")
        if not employee.name and identity.name:
            employee.name = identity.name
        if not employee.status:
            employee.status = "active"

    @staticmethod
    def _ensure_assignment(
        *,
        user: User,
        employee: Employee,
        start_date: str | None,
        end_date: str | None,
        notes: str | None,
    ) -> dict[str, Any]:
        conflicting_employee = (
            Employee.query.filter_by(company_id=employee.company_id, user_id=user.id)
            .filter(Employee.id != employee.id)
            .first()
        )
        if conflicting_employee:
            return {
                "success": False,
                "error": "Este usuário já está vinculado a outro colaborador nesta empresa",
            }

        today = date.today()
        active_assignment = (
            UserEmployeeAssignment.query.filter_by(employee_id=employee.id, is_active=True)
            .filter(
                or_(
                    UserEmployeeAssignment.end_date.is_(None),
                    UserEmployeeAssignment.end_date >= today,
                )
            )
            .first()
        )

        if active_assignment:
            if active_assignment.user_id != user.id:
                return {
                    "success": False,
                    "error": (
                        "O colaborador selecionado já possui outro usuário vinculado "
                        f"(ID: {active_assignment.user_id})"
                    ),
                }
            employee.user_id = user.id
            return {
                "success": True,
                "assignment": active_assignment,
                "action": "already_linked",
            }

        assignment = UserEmployeeAssignment(
            user_id=user.id,
            employee_id=employee.id,
            start_date=UserEmployeeOrchestratorService._parse_date(start_date) or today,
            end_date=UserEmployeeOrchestratorService._parse_date(end_date),
            is_active=True,
            status="active",
            notes=notes,
        )
        employee.user_id = user.id
        if not employee.email and user.email:
            employee.email = user.email
        if not employee.name and user.name:
            employee.name = user.name
        employee.status = employee.status or "active"
        db.session.add(assignment)
        db.session.flush()
        return {
            "success": True,
            "assignment": assignment,
            "action": "linked_existing",
        }

    @staticmethod
    def _collapse_actions(actions: list[str]) -> str:
        normalized = [item for item in actions if item]
        if not normalized:
            return "no_op"
        unique = list(dict.fromkeys(normalized))
        if unique == ["already_linked"]:
            return "already_linked"
        return "+".join(unique)

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        return datetime.strptime(value, "%Y-%m-%d").date()


def user_payload_name(user: User | None) -> str | None:
    return getattr(user, "name", None) if user else None
