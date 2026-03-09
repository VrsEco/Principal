import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import users as users_route


class _FakeSession:
    def __init__(self):
        self.added = []
        self.committed = 0
        self.rolled_back = False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back = True


class _FakeColumn:
    def in_(self, values):
        return ("in", tuple(values))

    def __eq__(self, other):
        return ("eq", other)


class _FakeUser:
    query = None

    def __init__(self, **kwargs):
        self.id = 101
        self.name = kwargs["name"]
        self.email = kwargs["email"]
        self.role = kwargs["role"]
        self.whatsapp = kwargs.get("whatsapp")
        self.telegram = kwargs.get("telegram")
        self.instagram = kwargs.get("instagram")
        self.summary_delivery_channels = kwargs.get("summary_delivery_channels")
        self.password_hash = None

    def set_password(self, password):
        self.password_hash = f"hashed::{password}"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "summary_delivery_channels": self.summary_delivery_channels,
        }


class _FakeUserQuery:
    def __init__(self, existing_email=None):
        self.existing_email = existing_email
        self.last_filter_kwargs = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        return self

    def first(self):
        email = (self.last_filter_kwargs or {}).get("email")
        if email and email == self.existing_email:
            return SimpleNamespace(id=999, email=email)
        return None


class _FakeCompanyQuery:
    def __init__(self, active_ids):
        self.active_ids = active_ids
        self.requested_ids = []

    def filter(self, *conditions):
        for condition in conditions:
            if isinstance(condition, tuple) and condition[0] == "in":
                self.requested_ids = list(condition[1])
        return self

    def all(self):
        return [SimpleNamespace(id=company_id) for company_id in self.requested_ids if company_id in self.active_ids]


class _FakeEmployeeQuery:
    def __init__(self, employees):
        self.employees = employees
        self.last_filter_kwargs = None

    def filter_by(self, **kwargs):
        self.last_filter_kwargs = kwargs
        return self

    def all(self):
        user_id = (self.last_filter_kwargs or {}).get("user_id")
        return [employee for employee in self.employees if employee.user_id == user_id]


class _FakeCompany:
    id = _FakeColumn()
    is_active = _FakeColumn()
    query = None


class _FakeEmployee:
    query = None


class _FakeUserEmployeeService:
    added_calls = []
    assigned_calls = []

    @classmethod
    def reset(cls):
        cls.added_calls = []
        cls.assigned_calls = []

    @classmethod
    def add_employee_to_multiple_companies(cls, user_id, company_ids):
        cls.added_calls.append((user_id, list(company_ids)))
        return {"success": True}

    @classmethod
    def assign_user_to_employee(cls, user_id, employee_id):
        cls.assigned_calls.append((user_id, employee_id))
        return {"success": True}


def _build_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    app.register_blueprint(users_route.usuarios_bp)
    return app


def test_create_user_route_accepts_company_ids_and_links_employees(monkeypatch):
    app = _build_app()
    session = _FakeSession()
    _FakeUser.query = _FakeUserQuery(existing_email=None)
    _FakeCompany.query = _FakeCompanyQuery(active_ids={8, 9})
    _FakeEmployee.query = _FakeEmployeeQuery([
        SimpleNamespace(id=201, user_id=101, company_id=8),
        SimpleNamespace(id=202, user_id=101, company_id=9),
        SimpleNamespace(id=203, user_id=777, company_id=8),
    ])
    _FakeUserEmployeeService.reset()

    monkeypatch.setattr(users_route, "current_user", SimpleNamespace(id=7, role="admin", is_authenticated=True))
    monkeypatch.setattr(users_route, "db", SimpleNamespace(session=session))
    monkeypatch.setattr(users_route, "User", _FakeUser)
    monkeypatch.setattr(users_route, "Company", _FakeCompany)
    monkeypatch.setattr(users_route, "Employee", _FakeEmployee)

    import services.user_employee_service as service_module
    monkeypatch.setattr(service_module, "UserEmployeeService", _FakeUserEmployeeService)

    client = app.test_client()
    response = client.post(
        "/api/usuarios",
        json={
            "name": "Novo Usuário",
            "email": "novo@empresa.com",
            "password": "123456",
            "role": "collaborator",
            "company_ids": [8, 9],
            "summary_delivery_channels": ["telegram", "email"],
        },
    )

    body = response.get_json()
    assert response.status_code == 201
    assert body["success"] is True
    assert body["user"]["email"] == "novo@empresa.com"
    assert body["user"]["summary_delivery_channels"] == "telegram,email"
    assert session.committed == 1
    assert _FakeUserEmployeeService.added_calls == [(101, [8, 9])]
    assert _FakeUserEmployeeService.assigned_calls == [(101, 201), (101, 202)]


def test_create_user_route_rejects_inactive_or_unknown_company_ids(monkeypatch):
    app = _build_app()
    session = _FakeSession()
    _FakeUser.query = _FakeUserQuery(existing_email=None)
    _FakeCompany.query = _FakeCompanyQuery(active_ids={8})
    _FakeEmployee.query = _FakeEmployeeQuery([])
    _FakeUserEmployeeService.reset()

    monkeypatch.setattr(users_route, "current_user", SimpleNamespace(id=7, role="admin", is_authenticated=True))
    monkeypatch.setattr(users_route, "db", SimpleNamespace(session=session))
    monkeypatch.setattr(users_route, "User", _FakeUser)
    monkeypatch.setattr(users_route, "Company", _FakeCompany)
    monkeypatch.setattr(users_route, "Employee", _FakeEmployee)

    import services.user_employee_service as service_module
    monkeypatch.setattr(service_module, "UserEmployeeService", _FakeUserEmployeeService)

    client = app.test_client()
    response = client.post(
        "/api/usuarios",
        json={
            "name": "Novo Usuário",
            "email": "novo@empresa.com",
            "password": "123456",
            "role": "collaborator",
            "company_ids": [8, 99],
        },
    )

    body = response.get_json()
    assert response.status_code == 400
    assert body["success"] is False
    assert "99" in body["message"]
    assert session.committed == 0
    assert _FakeUserEmployeeService.added_calls == []
    assert _FakeUserEmployeeService.assigned_calls == []
