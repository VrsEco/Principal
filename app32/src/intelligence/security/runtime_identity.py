from __future__ import annotations

from typing import Any

from models.company import Company
from models.employee import Employee
from models.user import User
from utils.company_access import get_accessible_company_ids
from utils.permissions import get_access_profile, is_platform_admin


def _load_runtime_user(user_id: int) -> User | None:
    if not user_id:
        return None
    return User.query.get(user_id)


def resolve_runtime_identity(*, user_id: int, company_id: int | None) -> dict[str, Any]:
    runtime_user = _load_runtime_user(user_id)
    raw_accessible_company_ids = get_accessible_company_ids(user=runtime_user)
    if raw_accessible_company_ids is None and is_platform_admin(user=runtime_user):
        accessible_company_ids = [
            int(company.id)
            for company in Company.query.filter(Company.is_active.isnot(False)).order_by(Company.id.asc()).all()
            if getattr(company, "id", None) is not None
        ]
    else:
        accessible_company_ids = list(raw_accessible_company_ids or [])

    resolved_company_id = company_id
    if resolved_company_id is None and len(accessible_company_ids) == 1:
        resolved_company_id = int(accessible_company_ids[0])

    employee = None
    if resolved_company_id is not None:
        employee = (
            Employee.query
            .filter(Employee.user_id == user_id, Employee.company_id == resolved_company_id)
            .order_by(Employee.company_id.asc(), Employee.id.asc())
            .first()
        )

    permissions = {}
    if employee and employee.role and isinstance(getattr(employee.role, 'permissions', None), dict):
        permissions = dict(employee.role.permissions)

    return {
        'company_id': resolved_company_id,
        'employee_id': getattr(employee, 'id', None),
        'role': get_access_profile(resolved_company_id, user=runtime_user),
        'permissions': permissions,
        'accessible_company_ids': accessible_company_ids,
    }
