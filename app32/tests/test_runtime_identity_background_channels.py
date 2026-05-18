import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.security import runtime_identity


class _FakeRole:
    def __init__(self, permissions=None):
        self.permissions = permissions or {}


class _FakeEmployee:
    def __init__(self, employee_id=77, company_id=9, role=None):
        self.id = employee_id
        self.company_id = company_id
        self.role = role or _FakeRole({"projects": ["view"]})


class _FakeQuery:
    def __init__(self, employee):
        self._employee = employee

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._employee


class _FakeEmployeeModel:
    class _FakeColumn:
        def asc(self):
            return self

        def __eq__(self, _other):
            return self

    user_id = _FakeColumn()
    company_id = _FakeColumn()
    id = _FakeColumn()

    query = _FakeQuery(_FakeEmployee())


class _FakeUser:
    def __init__(self, user_id=3, role="client"):
        self.id = user_id
        self.role = role
        self.is_authenticated = True


class _FakeCompany:
    def __init__(self, company_id):
        self.id = company_id


class _FakeCompanyQuery:
    def __init__(self, companies):
        self._companies = companies

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return list(self._companies)


class _FakeCompanyModel:
    class _FakeColumn:
        def isnot(self, _other):
            return self

        def asc(self):
            return self

    is_active = _FakeColumn()
    id = _FakeColumn()
    query = _FakeCompanyQuery([_FakeCompany(1), _FakeCompany(10)])


def test_resolve_runtime_identity_supports_background_channel_without_current_user(monkeypatch):
    monkeypatch.setattr(runtime_identity, "Employee", _FakeEmployeeModel)
    monkeypatch.setattr(runtime_identity, "get_accessible_company_ids", lambda user=None: [9] if user else [])
    monkeypatch.setattr(runtime_identity, "get_access_profile", lambda company_id=None, user=None: "client" if user else None)
    monkeypatch.setattr(
        runtime_identity,
        "_load_runtime_user",
        lambda user_id: _FakeUser(user_id=user_id, role="client"),
    )

    result = runtime_identity.resolve_runtime_identity(user_id=3, company_id=9)

    assert result == {
        "company_id": 9,
        "employee_id": 77,
        "role": "client",
        "permissions": {"projects": ["view"]},
        "accessible_company_ids": [9],
    }


def test_resolve_runtime_identity_keeps_company_unselected_for_platform_admin(monkeypatch):
    monkeypatch.setattr(runtime_identity, "Employee", _FakeEmployeeModel)
    monkeypatch.setattr(runtime_identity, "Company", _FakeCompanyModel)
    monkeypatch.setattr(runtime_identity, "get_accessible_company_ids", lambda user=None: None)
    monkeypatch.setattr(runtime_identity, "is_platform_admin", lambda user=None: True)
    monkeypatch.setattr(runtime_identity, "get_access_profile", lambda company_id=None, user=None: "administrator" if user else None)
    monkeypatch.setattr(
        runtime_identity,
        "_load_runtime_user",
        lambda user_id: _FakeUser(user_id=user_id, role="administrator"),
    )

    result = runtime_identity.resolve_runtime_identity(user_id=3, company_id=None)

    assert result == {
        "company_id": None,
        "employee_id": None,
        "role": "administrator",
        "permissions": {},
        "accessible_company_ids": [1, 10],
    }
