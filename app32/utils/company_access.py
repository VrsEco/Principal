from __future__ import annotations

from typing import List, Optional

from flask_login import current_user

from models import Employee
from utils.permissions import is_platform_admin


def get_accessible_company_ids(user=None) -> Optional[List[int]]:
    """Return company IDs the user can access.

    For admins, returns None to indicate unrestricted access.
    For unauthenticated users, returns an empty list.
    """
    user = user or current_user
    if not user or not getattr(user, "is_authenticated", False):
        return []

    if is_platform_admin(user=user):
        return None

    employees = Employee.query.filter_by(user_id=user.id, status="active").all()
    company_ids = {e.company_id for e in employees if e.company_id}
    return sorted(company_ids)

import logging
from typing import Set

from flask import g
from flask_login import current_user

from services.my_work_service import get_user_employees

logger = logging.getLogger(__name__)


def get_user_allowed_company_ids() -> Set[int]:
    """Return the set of company IDs the current user may access."""
    if not current_user.is_authenticated:
        return set()

    cache_key = "_allowed_company_ids"
    cached = getattr(g, cache_key, None)
    if cached is not None:
        return cached

    try:
        companies = get_user_employees(current_user.id) or []
    except Exception as exc:
        logger.warning(
            "Falha ao buscar empresas permitidas para o usuário %s: %s",
            current_user.id,
            exc,
        )
        allowed_ids = set()
    else:
        allowed_ids = {
            comp["company_id"]
            for comp in companies
            if isinstance(comp.get("company_id"), int)
        }

    setattr(g, cache_key, allowed_ids)
    return allowed_ids
