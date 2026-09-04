from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from werkzeug.exceptions import NotFound

from services import company_org_employee_service as service


@pytest.fixture
def dependencies(monkeypatch):
    company = Mock()
    role = Mock()
    employee = Mock()
    company.query.filter_by.return_value.with_for_update.return_value.first_or_404.return_value = SimpleNamespace(id=7)
    role.query.filter_by.return_value.first_or_404.return_value = SimpleNamespace(id=12, department="Operação")
    employee.query.filter_by.return_value.all.return_value = []
    register = Mock(return_value={"success": True, "employee": {"id": 23, "user_id": None}})
    monkeypatch.setattr(service, "Company", company)
    monkeypatch.setattr(service, "Role", role)
    monkeypatch.setattr(service, "Employee", employee)
    monkeypatch.setattr(service.UserEmployeeOrchestratorService, "register_or_link_user_employee", register)
    return company, role, employee, register


def test_create_without_access_is_tenant_scoped(dependencies):
    company, role, employee, register = dependencies
    assert service.create_org_employee(7, 12, {"name": " Ana "}) == {"id": 23, "user_id": None}
    company.query.filter_by.assert_called_once_with(id=7)
    role.query.filter_by.assert_called_once_with(id=12, company_id=7)
    employee.query.filter_by.assert_called_once_with(company_id=7)
    register.assert_called_once_with(
        company_id=7, create_system_access=False,
        employee_payload={"name": "Ana", "role_id": 12, "department": "Operação"},
    )


@pytest.mark.parametrize("payload", [None, [], {}, {"name": " "}, {"name": 123}, {"name": "a" * 201}, {"name": "Ana", "user_id": 1}, {"name": "Ana", "company_id": 8}])
def test_invalid_payload_cannot_reach_persistence(dependencies, payload):
    with pytest.raises(ValueError):
        service.create_org_employee(7, 12, payload)
    dependencies[0].query.filter_by.assert_not_called()
    dependencies[3].assert_not_called()


def test_cross_tenant_or_missing_role_is_rejected(dependencies):
    dependencies[1].query.filter_by.return_value.first_or_404.side_effect = NotFound()
    with pytest.raises(NotFound):
        service.create_org_employee(7, 99, {"name": "Ana"})
    dependencies[1].query.filter_by.assert_called_once_with(id=99, company_id=7)
    dependencies[3].assert_not_called()


def test_normalized_duplicate_requires_human_review(dependencies):
    dependencies[2].query.filter_by.return_value.all.return_value = [SimpleNamespace(name="José Silva")]
    with pytest.raises(ValueError, match="Já existe"):
        service.create_org_employee(7, 12, {"name": " JOSE   SILVA "})
    dependencies[3].assert_not_called()


def test_internal_failure_does_not_expose_orchestrator_error(dependencies):
    dependencies[3].return_value = {"success": False, "error": "private database detail"}
    with pytest.raises(RuntimeError, match="Não foi possível") as error:
        service.create_org_employee(7, 12, {"name": "Ana"})
    assert "private" not in str(error.value)


@pytest.fixture
def link_dependencies(dependencies, monkeypatch):
    employee = Mock(user_id=None, role_id=None, status="active")
    employee.to_dict.return_value = {"id": 23, "role_id": 12, "user_id": None}
    dependencies[2].query.filter_by.return_value.with_for_update.return_value.first_or_404.return_value = employee
    database = Mock()
    monkeypatch.setattr(service, "db", database)
    return dependencies, employee, database


def test_link_scopes_and_does_not_create_login(link_dependencies):
    deps, employee, database = link_dependencies
    service.link_org_employee(7, 12, {"employee_id": 23})
    deps[2].query.filter_by.assert_called_once_with(id=23, company_id=7)
    deps[1].query.filter_by.assert_called_once_with(id=12, company_id=7)
    assert employee.role_id == 12
    assert employee.user_id is None
    deps[3].assert_not_called()
    database.session.commit.assert_called_once()


@pytest.mark.parametrize("field,value", [("user_id", 2), ("role_id", 5), ("status", "inactive")])
def test_link_does_not_replace_existing_access_or_role(link_dependencies, field, value):
    _, employee, database = link_dependencies
    setattr(employee, field, value)
    with pytest.raises(ValueError):
        service.link_org_employee(7, 12, {"employee_id": 23})
    database.session.commit.assert_not_called()


@pytest.mark.parametrize("payload", [{}, None, {"employee_id": True}, {"employee_id": 1.5}, {"employee_id": 0}, {"employee_id": 23, "user_id": 4}])
def test_link_rejects_invalid_payload(link_dependencies, payload):
    with pytest.raises(ValueError):
        service.link_org_employee(7, 12, payload)
    link_dependencies[0][0].query.filter_by.assert_not_called()


def test_link_is_idempotent_for_same_role(link_dependencies):
    link_dependencies[1].role_id = 12
    assert service.link_org_employee(7, 12, {"employee_id": 23})["role_id"] == 12


def test_missing_or_cross_tenant_employee_not_linked(link_dependencies):
    deps, _, database = link_dependencies
    deps[2].query.filter_by.return_value.with_for_update.return_value.first_or_404.side_effect = NotFound()
    with pytest.raises(NotFound):
        service.link_org_employee(7, 12, {"employee_id": 23})
    database.session.commit.assert_not_called()
