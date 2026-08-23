from __future__ import annotations

import re
from typing import Any

from models import Role, db
from services.rbac_permission_catalog_service import RbacPermissionCatalogService


class RoleHierarchyValidationError(ValueError):
    """Erro de contrato ao criar ou reposicionar um cargo na hierarquia."""


class CompanyRoleHierarchyService:
    """Mantém cargos e sua hierarquia com isolamento estrito por empresa."""

    EDITABLE_FIELDS = {
        "title",
        "department",
        "parent_role_id",
        "headcount_planned",
        "weekly_hours",
        "notes",
        "color",
        "permissions",
    }
    COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

    @classmethod
    def create(cls, company_id: int, payload: dict[str, Any] | None) -> Role:
        values = cls._normalize_payload(company_id, payload)
        values.setdefault("permissions", RbacPermissionCatalogService.normalize_payload(None))
        role = Role(company_id=company_id, **values)
        db.session.add(role)
        db.session.commit()
        return role

    @classmethod
    def update(cls, company_id: int, role_id: int, payload: dict[str, Any] | None) -> Role:
        role = Role.query.filter_by(id=role_id, company_id=company_id).first_or_404()
        values = cls._normalize_payload(company_id, payload, role_id=role.id)
        for field, value in values.items():
            setattr(role, field, value)
        db.session.commit()
        return role

    @classmethod
    def _normalize_payload(
        cls,
        company_id: int,
        payload: dict[str, Any] | None,
        *,
        role_id: int | None = None,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise RoleHierarchyValidationError("Payload do cargo é obrigatório.")

        values = {key: value for key, value in payload.items() if key in cls.EDITABLE_FIELDS}
        if "title" in values or role_id is None:
            title = str(values.get("title") or "").strip()
            if not title:
                raise RoleHierarchyValidationError("Título do cargo é obrigatório.")
            if len(title) > 100:
                raise RoleHierarchyValidationError("Título do cargo deve ter até 100 caracteres.")
            values["title"] = title

        if "department" in values:
            department = str(values.get("department") or "").strip()
            if len(department) > 100:
                raise RoleHierarchyValidationError("Departamento deve ter até 100 caracteres.")
            values["department"] = department or None

        if "headcount_planned" in values:
            try:
                headcount = int(values.get("headcount_planned") or 0)
            except (TypeError, ValueError) as exc:
                raise RoleHierarchyValidationError("Pessoas previstas deve ser um número inteiro.") from exc
            if headcount < 0:
                raise RoleHierarchyValidationError("Pessoas previstas não pode ser negativo.")
            values["headcount_planned"] = headcount

        if "color" in values:
            color = str(values.get("color") or "").strip()
            if color and not cls.COLOR_PATTERN.fullmatch(color):
                raise RoleHierarchyValidationError("Cor do card deve estar no formato hexadecimal #RRGGBB.")
            values["color"] = color.upper() if color else None

        if "permissions" in values:
            values["permissions"] = RbacPermissionCatalogService.normalize_payload(values.get("permissions"))

        if "parent_role_id" in values:
            parent_id = cls._optional_int(values.get("parent_role_id"))
            cls._validate_parent(company_id, role_id, parent_id)
            values["parent_role_id"] = parent_id

        return values

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise RoleHierarchyValidationError("Cargo superior inválido.") from exc

    @classmethod
    def _validate_parent(cls, company_id: int, role_id: int | None, parent_id: int | None) -> None:
        if parent_id is None:
            return
        if role_id is not None and parent_id == role_id:
            raise RoleHierarchyValidationError("Um cargo não pode responder para ele mesmo.")

        parent = Role.query.filter_by(id=parent_id, company_id=company_id).first()
        if not parent:
            raise RoleHierarchyValidationError("Cargo superior não pertence a esta empresa.")

        visited: set[int] = set()
        current = parent
        while current:
            if current.id in visited:
                raise RoleHierarchyValidationError("A hierarquia existente possui um ciclo e precisa ser corrigida.")
            visited.add(current.id)
            if role_id is not None and current.id == role_id:
                raise RoleHierarchyValidationError("Esta alteração criaria um ciclo na hierarquia.")
            if not current.parent_role_id:
                break
            current = Role.query.filter_by(id=current.parent_role_id, company_id=company_id).first()
