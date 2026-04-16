from __future__ import annotations

from typing import Any

from models.employee import Employee
from models.user import User
from utils.company_access import get_accessible_company_ids
from utils.permissions import get_access_profile


def _load_runtime_user(user_id: int) -> User | None:
    if not user_id:
        return None
    return User.query.get(user_id)


def resolve_runtime_identity(*, user_id: int, company_id: int | None) -> dict[str, Any]:
    query = Employee.query.filter(Employee.user_id == user_id)
    if company_id is not None:
        query = query.filter(Employee.company_id == company_id)

    employee = query.order_by(Employee.company_id.asc(), Employee.id.asc()).first()
    if employee is None:
        employee = Employee.query.filter(Employee.user_id == user_id).order_by(Employee.company_id.asc(), Employee.id.asc()).first()

    resolved_company_id = company_id or getattr(employee, 'company_id', None)
    permissions = {}
    if employee and employee.role and isinstance(getattr(employee.role, 'permissions', None), dict):
        permissions = dict(employee.role.permissions)

    runtime_user = _load_runtime_user(user_id)
    accessible_company_ids = get_accessible_company_ids(user=runtime_user) or []
    if accessible_company_ids is None:
        accessible_company_ids = []

    return {
        'company_id': resolved_company_id,
        'employee_id': getattr(employee, 'id', None),
        'role': get_access_profile(resolved_company_id, user=runtime_user),
        'permissions': permissions,
        'accessible_company_ids': accessible_company_ids,
    }
