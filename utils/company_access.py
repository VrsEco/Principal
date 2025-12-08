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
