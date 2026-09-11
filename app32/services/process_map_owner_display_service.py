"""Resolve a forma de exibir o dono do macroprocesso no mapa emitido."""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_

from models import Employee, Role, db


OWNER_DISPLAY_EMPLOYEE = "employee"
OWNER_DISPLAY_ROLE = "role"
VALID_OWNER_DISPLAY_MODES = frozenset({OWNER_DISPLAY_EMPLOYEE, OWNER_DISPLAY_ROLE})


def normalize_owner_display_mode(value: str | None) -> str:
    """Normaliza a opção de impressão sem aceitar modos implícitos."""
    mode = (value or OWNER_DISPLAY_EMPLOYEE).strip().lower()
    if mode not in VALID_OWNER_DISPLAY_MODES:
        raise ValueError("Modo de exibição do dono inválido.")
    return mode


def apply_owner_display_mode(
    map_data: dict[str, Any],
    *,
    company_id: int,
    owner_display_mode: str,
) -> None:
    """Acrescenta campos de apresentação sem alterar o dono persistido.

    O legado armazena o nome do colaborador em ``macro_processes.owner``. A
    resolução para cargo ocorre exclusivamente no tenant informado e somente
    para a emissão atual; portanto, não altera o dado de origem nem permite
    atravessamento de empresas.
    """
    mode = normalize_owner_display_mode(owner_display_mode)
    macros = [
        macro
        for area in map_data.get("areas", [])
        for macro in area.get("macros", [])
    ]

    owners = {
        str(macro.get("owner") or "").strip()
        for macro in macros
        if str(macro.get("owner") or "").strip()
    }
    role_by_owner: dict[str, str] = {}

    if mode == OWNER_DISPLAY_ROLE and owners:
        rows = (
            db.session.query(Employee.name, Role.title)
            .outerjoin(
                Role,
                and_(Role.id == Employee.role_id, Role.company_id == company_id),
            )
            .filter(Employee.company_id == company_id, Employee.name.in_(owners))
            .order_by(Employee.name.asc(), Employee.id.asc())
            .all()
        )
        for employee_name, role_title in rows:
            normalized_name = str(employee_name or "").strip()
            normalized_role = str(role_title or "").strip()
            if normalized_name and normalized_role and normalized_name not in role_by_owner:
                role_by_owner[normalized_name] = normalized_role

    for macro in macros:
        owner = str(macro.get("owner") or "").strip()
        if not owner:
            macro["owner_display"] = "-"
        elif mode == OWNER_DISPLAY_ROLE:
            macro["owner_display"] = role_by_owner.get(owner, "Cargo não informado")
        else:
            macro["owner_display"] = owner
