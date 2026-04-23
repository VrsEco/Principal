import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.identity.duplicate_identity_service import DuplicateIdentityService


def test_replace_value_recursive_updates_nested_employee_ids_and_tokens():
    payload = {
        "employee_id": 12,
        "participants": [
            {"employee_id": 12, "recipient_key": "employee:12"},
            {"children": [12, "employee:12", {"employee_id": 99}]},
        ],
    }

    updated, changed = DuplicateIdentityService._replace_value_recursive(
        payload,
        old_value=12,
        new_value=77,
    )

    assert changed is True
    assert updated["employee_id"] == 77
    assert updated["participants"][0]["employee_id"] == 77
    assert updated["participants"][0]["recipient_key"] == "employee:77"
    assert updated["participants"][1]["children"][0] == 77
    assert updated["participants"][1]["children"][1] == "employee:77"
    assert updated["participants"][1]["children"][2]["employee_id"] == 99


def test_audit_duplicate_users_groups_by_normalized_email(monkeypatch):
    fake_users = [
        SimpleNamespace(id=1, email="Teste@Empresa.com", name="A", is_active=True),
        SimpleNamespace(id=2, email="teste@empresa.com", name="B", is_active=False),
        SimpleNamespace(id=3, email="outro@empresa.com", name="C", is_active=True),
    ]
    fake_employees = {
        1: [SimpleNamespace(company_id=10)],
        2: [SimpleNamespace(company_id=10), SimpleNamespace(company_id=11)],
        3: [],
    }

    class _UserQuery:
        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return fake_users

    class _EmployeeQuery:
        def filter_by(self, **kwargs):
            self._user_id = kwargs["user_id"]
            return self

        def all(self):
            return fake_employees[self._user_id]

    monkeypatch.setattr(
        "services.identity.duplicate_identity_service.User",
        SimpleNamespace(query=_UserQuery(), id=SimpleNamespace(asc=lambda: None)),
    )
    monkeypatch.setattr(
        "services.identity.duplicate_identity_service.Employee",
        SimpleNamespace(
            query=_EmployeeQuery(),
            company_id=SimpleNamespace(asc=lambda: None),
            id=SimpleNamespace(asc=lambda: None),
        ),
    )

    duplicates = DuplicateIdentityService.audit_duplicate_users()
    assert len(duplicates) == 1
    assert duplicates[0]["normalized_email"] == "teste@empresa.com"
    assert duplicates[0]["count"] == 2
    assert duplicates[0]["users"][1]["company_ids"] == [10, 11]


def test_audit_duplicate_employees_groups_by_company_and_email(monkeypatch):
    fake_employees = [
        SimpleNamespace(id=10, company_id=5, user_id=1, name="Maria", email="maria@empresa.com", phone=None, whatsapp=None, status="active"),
        SimpleNamespace(id=11, company_id=5, user_id=None, name="Maria Silva", email="MARIA@empresa.com", phone=None, whatsapp=None, status="active"),
        SimpleNamespace(id=12, company_id=7, user_id=None, name="João", email="joao@empresa.com", phone=None, whatsapp=None, status="active"),
    ]

    class _EmployeeQuery:
        def __init__(self):
            self._company_id = None

        def order_by(self, *_args, **_kwargs):
            return self

        def filter_by(self, **kwargs):
            self._company_id = kwargs.get("company_id")
            return self

        def all(self):
            if self._company_id is None:
                return fake_employees
            return [employee for employee in fake_employees if employee.company_id == self._company_id]

    monkeypatch.setattr("services.identity.duplicate_identity_service.Employee", SimpleNamespace(query=_EmployeeQuery(), company_id=SimpleNamespace(asc=lambda: None), id=SimpleNamespace(asc=lambda: None)))

    duplicates = DuplicateIdentityService.audit_duplicate_employees()
    assert len(duplicates) == 1
    assert duplicates[0]["company_id"] == 5
    assert duplicates[0]["strategy"] == "email"
    assert duplicates[0]["count"] == 2
