"""Serviços da Central de Pessoas: conta global, vínculo tenant e colaborador."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func

from models import Company, Employee, Role, User, UserCompanyMembership, db
from services.company_identity_service import CompanyIdentityService
from services.identity.identity_normalizer import normalize_email, normalize_name
from services.identity.user_employee_orchestrator_service import UserEmployeeOrchestratorService


class PeopleWorkspaceValidationError(ValueError):
    pass


class PeopleWorkspaceService:
    PROFILES = {"administrator", "client", "collaborator"}
    EMPLOYEE_FIELDS = {"name", "role_id", "department", "weekly_hours", "status", "notes"}

    @classmethod
    def build_workspace(cls, company_id: int) -> dict[str, Any]:
        summary = CompanyIdentityService.build_summary(company_id)
        memberships = (
            UserCompanyMembership.query.filter_by(company_id=company_id)
            .join(User)
            .order_by(func.lower(User.name), User.id)
            .all()
        )
        employees_by_user = {
            employee.user_id: employee
            for employee in Employee.query.filter_by(company_id=company_id).all()
            if employee.user_id
        }
        users = [cls._serialize_membership(item, employees_by_user.get(item.user_id)) for item in memberships]
        metrics = dict(summary.metrics)
        metrics.update({
            "users_total": len(users),
            "active_users_total": sum(1 for item in users if item["is_active"] and item["user_is_active"]),
        })
        return {
            "company": summary.company,
            "metrics": metrics,
            "users": users,
            "roles": summary.roles,
            "employees": summary.employees,
            "roles_tree": CompanyIdentityService.build_roles_tree(company_id),
        }

    @classmethod
    def create_or_link_user(cls, company_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
        values = cls._normalize_user_payload(payload, creating=True)
        Company.query.filter_by(id=company_id).with_for_update().first_or_404()
        user = User.query.filter(func.lower(func.trim(User.email)) == values["email"]).first()
        if not user:
            user = User(name=values["name"], email=values["email"], role="collaborator", is_active=True)
            user.set_password(values["password"])
            db.session.add(user)
            db.session.flush()
        membership = UserCompanyMembership.query.filter_by(user_id=user.id, company_id=company_id).first()
        if not membership:
            membership = UserCompanyMembership(
                user_id=user.id,
                company_id=company_id,
                access_profile=values["access_profile"],
                is_active=values["is_active"],
            )
            db.session.add(membership)
        else:
            membership.access_profile = values["access_profile"]
            membership.is_active = values["is_active"]
        db.session.flush()
        cls._link_employee_if_requested(company_id, user.id, values.get("employee_id"))
        db.session.commit()
        linked = Employee.query.filter_by(company_id=company_id, user_id=user.id).first()
        return cls._serialize_membership(membership, linked)

    @classmethod
    def update_user_membership(cls, company_id: int, user_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
        values = cls._normalize_user_payload(payload, creating=False)
        membership = UserCompanyMembership.query.filter_by(company_id=company_id, user_id=user_id).with_for_update().first()
        if not membership:
            raise PeopleWorkspaceValidationError("Usuário não está vinculado a esta empresa.")
        if "access_profile" in values:
            membership.access_profile = values["access_profile"]
        if "is_active" in values:
            membership.is_active = values["is_active"]
        if "employee_id" in values:
            cls._link_employee_if_requested(company_id, user_id, values["employee_id"])
        db.session.commit()
        linked = Employee.query.filter_by(company_id=company_id, user_id=user_id).first()
        return cls._serialize_membership(membership, linked)

    @classmethod
    def create_employee(cls, company_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
        values = cls._normalize_employee_payload(company_id, payload, creating=True)
        Company.query.filter_by(id=company_id).with_for_update().first_or_404()
        duplicate = Employee.query.filter_by(company_id=company_id).all()
        if any(normalize_name(item.name) == normalize_name(values["name"]) for item in duplicate):
            raise PeopleWorkspaceValidationError("Já existe colaborador com esse nome nesta empresa.")
        employee = Employee(company_id=company_id, **values)
        db.session.add(employee)
        db.session.commit()
        return CompanyIdentityService._serialize_employee(employee)

    @classmethod
    def update_employee(cls, company_id: int, employee_id: int, payload: dict[str, Any] | None) -> dict[str, Any]:
        employee = Employee.query.filter_by(id=employee_id, company_id=company_id).with_for_update().first()
        if not employee:
            raise PeopleWorkspaceValidationError("Colaborador não encontrado.")
        values = cls._normalize_employee_payload(company_id, payload, creating=False)
        for field, value in values.items():
            setattr(employee, field, value)
        db.session.commit()
        return CompanyIdentityService._serialize_employee(employee)

    @classmethod
    def _link_employee_if_requested(cls, company_id: int, user_id: int, employee_id: int | None) -> None:
        if employee_id is None:
            return
        employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
        if not employee:
            raise PeopleWorkspaceValidationError("Colaborador selecionado não pertence à empresa.")
        existing = Employee.query.filter_by(company_id=company_id, user_id=user_id).first()
        if existing and existing.id != employee.id:
            raise PeopleWorkspaceValidationError("Este usuário já está vinculado a outro colaborador nesta empresa.")
        if employee.user_id not in (None, user_id):
            raise PeopleWorkspaceValidationError("Este colaborador já está vinculado a outro usuário.")
        result = UserEmployeeOrchestratorService.link_existing_user_to_employee(
            company_id=company_id, user_id=user_id, employee_id=employee.id
        )
        if not result.get("success"):
            raise PeopleWorkspaceValidationError(result.get("error") or "Não foi possível vincular o colaborador.")

    @classmethod
    def _normalize_user_payload(cls, payload: dict[str, Any] | None, *, creating: bool) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise PeopleWorkspaceValidationError("Dados do usuário são obrigatórios.")
        allowed = {"name", "email", "password", "access_profile", "is_active", "employee_id"}
        values = {key: value for key, value in payload.items() if key in allowed}
        if creating:
            name = str(values.get("name") or "").strip()
            email = normalize_email(values.get("email"))
            password = values.get("password")
            if not name or len(name) > 100:
                raise PeopleWorkspaceValidationError("Nome do usuário é obrigatório e deve ter até 100 caracteres.")
            if not email:
                raise PeopleWorkspaceValidationError("E-mail válido é obrigatório.")
            if not isinstance(password, str) or len(password) < 8:
                raise PeopleWorkspaceValidationError("A senha temporária deve ter pelo menos 8 caracteres.")
            values["name"] = name
            values["email"] = email
            values["password"] = password
        if "access_profile" in values or creating:
            raw_profile = values.get("access_profile", "collaborator")
            profile = str(raw_profile).strip().lower()
            if profile not in cls.PROFILES:
                raise PeopleWorkspaceValidationError("Perfil de acesso inválido.")
            values["access_profile"] = profile
        if "is_active" in values:
            if type(values["is_active"]) is not bool:
                raise PeopleWorkspaceValidationError("Situação do vínculo deve ser verdadeira ou falsa.")
        elif creating:
            values["is_active"] = True
        if "employee_id" in values:
            raw = values["employee_id"]
            if raw in (None, ""):
                values["employee_id"] = None
            elif type(raw) is int and raw > 0:
                values["employee_id"] = raw
            else:
                raise PeopleWorkspaceValidationError("Colaborador selecionado é inválido.")
        return values

    @classmethod
    def _normalize_employee_payload(cls, company_id: int, payload: dict[str, Any] | None, *, creating: bool) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise PeopleWorkspaceValidationError("Dados do colaborador são obrigatórios.")
        values = {key: value for key, value in payload.items() if key in cls.EMPLOYEE_FIELDS}
        if creating or "name" in values:
            name = str(values.get("name") or "").strip()
            if not name or len(name) > 200:
                raise PeopleWorkspaceValidationError("Nome do colaborador é obrigatório e deve ter até 200 caracteres.")
            values["name"] = name
        if creating or "role_id" in values:
            role_id = values.get("role_id")
            if type(role_id) is not int or role_id <= 0:
                raise PeopleWorkspaceValidationError("Selecione um cargo válido.")
            role = Role.query.filter_by(id=role_id, company_id=company_id).first()
            if not role:
                raise PeopleWorkspaceValidationError("O cargo selecionado não pertence à empresa.")
            values["role_id"] = role.id
            values.setdefault("department", role.department)
        if "department" in values:
            department = str(values["department"] or "").strip()
            if len(department) > 100:
                raise PeopleWorkspaceValidationError("Área deve ter até 100 caracteres.")
            values["department"] = department or None
        if "status" in values:
            status = str(values["status"] or "").strip().lower()
            if status not in {"active", "inactive", "vacation", "ativo", "inativo", "férias", "ferias"}:
                raise PeopleWorkspaceValidationError("Situação do colaborador é inválida.")
            values["status"] = status
        elif creating:
            values["status"] = "active"
        if "weekly_hours" in values:
            raw = values["weekly_hours"]
            if raw in (None, ""):
                values["weekly_hours"] = None
            else:
                try:
                    hours = Decimal(str(raw))
                    if not hours.is_finite() or not 0 < hours <= 168:
                        raise ValueError
                except (InvalidOperation, TypeError, ValueError) as exc:
                    raise PeopleWorkspaceValidationError("Jornada semanal deve estar entre 0 e 168 horas.") from exc
                values["weekly_hours"] = hours
        if "notes" in values:
            notes = values["notes"]
            if notes is not None and (not isinstance(notes, str) or len(notes) > 10000):
                raise PeopleWorkspaceValidationError("Observações devem ter até 10000 caracteres.")
            values["notes"] = notes.strip() if notes else None
        return values

    @staticmethod
    def _serialize_membership(membership: UserCompanyMembership, employee: Employee | None) -> dict[str, Any]:
        user = membership.user
        return {
            **membership.to_dict(),
            "name": user.name,
            "email": user.email,
            "user_is_active": bool(user.is_active),
            "employee": CompanyIdentityService._serialize_employee(employee) if employee else None,
        }
