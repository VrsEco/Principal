from types import SimpleNamespace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import services.mcp_oauth_onboarding_service as onboarding_module


class _Query:
    def __init__(self, result):
        self.result = result
        self.filters = None

    def filter_by(self, **kwargs):
        self.filters = kwargs
        return self

    def first(self):
        return self.result


def test_global_admin_can_be_onboarded_without_synthetic_employee(monkeypatch):
    user_query = _Query(SimpleNamespace(id=3, is_active=True, role="admin"))
    monkeypatch.setattr(onboarding_module, "User", SimpleNamespace(query=user_query))
    monkeypatch.setattr(onboarding_module, "Employee", SimpleNamespace(query=_Query(None)))
    monkeypatch.setattr(onboarding_module, "is_platform_admin", lambda *, user: user.id == 3)

    assert onboarding_module.McpOAuthOnboardingService._linked_company(user_id=3, company_id=9) is True
    assert user_query.filters == {"id": 3, "is_active": True}
