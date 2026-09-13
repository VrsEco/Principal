"""Authorization boundary for the Incentives module.

The active company in a session is an input to authorization, not proof that
the current user may operate on that company.  Keep that rule in one place so
HTTP routes and Flask-RESTful resources cannot diverge.
"""

from __future__ import annotations

from utils.permissions import can_access_company, has_permission


class IncentiveAccessService:
    """Checks permission against the same company used by the operation."""

    RESOURCE = "incentives"

    @classmethod
    def is_allowed(cls, company_id: int | None, action: str) -> bool:
        if not company_id:
            return False

        try:
            normalized_company_id = int(company_id)
        except (TypeError, ValueError):
            return False

        if normalized_company_id <= 0:
            return False

        return bool(
            can_access_company(normalized_company_id)
            and has_permission(normalized_company_id, cls.RESOURCE, action)
        )
