"""Contrato HTTP real da rota; identidade, autorização e persistência simuladas."""
from unittest.mock import Mock

import pytest
from flask import Flask
from werkzeug.exceptions import NotFound

from api.routes import companies as routes
from services import company_org_employee_service as service
from utils import permissions


URL = "/api/companies/7/roles/12/employees"


@pytest.fixture
def client_context(monkeypatch):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(routes.companies_bp)
    access = Mock(return_value=True)
    permission = Mock(return_value=True)
    create = Mock(return_value={"id": 23, "company_id": 7, "role_id": 12, "user_id": None})
    link = Mock(return_value={"id": 23, "company_id": 7, "role_id": 12, "user_id": None})
    database = Mock()
    monkeypatch.setattr(routes, "can_access_company", access)
    monkeypatch.setattr(permissions, "has_permission", permission)
    monkeypatch.setattr(service, "create_org_employee", create)
    monkeypatch.setattr(service, "link_org_employee", link)
    monkeypatch.setattr(routes, "db", database)
    return app.test_client(), access, permission, create, link, database


@pytest.mark.parametrize("method,payload,index,status", [("post", {"name": "Ana"}, 3, 201), ("put", {"employee_id": 23}, 4, 200)])
def test_dispatch_and_tenant_from_url(client_context, method, payload, index, status):
    response = getattr(client_context[0], method)(URL, json=payload)
    assert response.status_code == status
    assert response.json["user_id"] is None
    client_context[index].assert_called_once_with(7, 12, payload)
    client_context[2].assert_called_once_with(7, "companies", "edit")
    client_context[1].assert_called_once_with(7)


@pytest.mark.parametrize("denied_index", [1, 2])
@pytest.mark.parametrize("method", ["post", "put"])
def test_denied_access_never_calls_service(client_context, denied_index, method):
    client_context[denied_index].return_value = False
    response = getattr(client_context[0], method)(URL, json={"name": "Ana"})
    assert response.status_code == 403
    client_context[3].assert_not_called()
    client_context[4].assert_not_called()


@pytest.mark.parametrize("method,index", [("post", 3), ("put", 4)])
@pytest.mark.parametrize("error,status", [(ValueError("Entrada inválida"), 400), (NotFound(), 404), (RuntimeError("secret"), 500), (OSError("secret"), 500)])
def test_errors_roll_back_and_hide_internal_details(client_context, method, index, error, status):
    client_context[index].side_effect = error
    response = getattr(client_context[0], method)(URL, json={"name": "Ana"})
    assert response.status_code == status
    assert "secret" not in response.get_data(as_text=True)
    client_context[5].session.rollback.assert_called_once()


def test_body_cannot_select_authorization_tenant(client_context):
    payload = {"employee_id": 23, "company_id": 999}
    client_context[4].side_effect = ValueError("Informe apenas employee_id.")
    response = client_context[0].put(URL, json=payload)
    assert response.status_code == 400
    client_context[2].assert_called_once_with(7, "companies", "edit")
    client_context[4].assert_called_once_with(7, 12, payload)


def test_snapshot_read_uses_view_permission(client_context, monkeypatch):
    from services import org_occupancy_read_service
    read = Mock(return_value={"company_id": 7, "assignments": [], "as_of": "2026-09-04"})
    monkeypatch.setattr(org_occupancy_read_service, "build_occupancy_snapshot", read)
    response = client_context[0].get('/api/companies/7/occupancy-snapshot?as_of=2026-09-04')
    assert response.status_code == 200
    read.assert_called_once_with(7, '2026-09-04')
    client_context[2].assert_called_once_with(7, 'companies', 'view')


@pytest.mark.parametrize('denied_index', [1, 2])
def test_snapshot_denied_never_reads(client_context, monkeypatch, denied_index):
    from services import org_occupancy_read_service
    read = Mock()
    monkeypatch.setattr(org_occupancy_read_service, "build_occupancy_snapshot", read)
    client_context[denied_index].return_value = False
    assert client_context[0].get('/api/companies/7/occupancy-snapshot?as_of=2026-09-04').status_code == 403
    read.assert_not_called()


@pytest.mark.parametrize('error,status', [(ValueError('Data inválida'), 400), (NotFound(), 404), (RuntimeError('private'), 500)])
def test_snapshot_errors_are_not_empty_results(client_context, monkeypatch, error, status):
    from services import org_occupancy_read_service
    monkeypatch.setattr(org_occupancy_read_service, 'build_occupancy_snapshot', Mock(side_effect=error))
    response = client_context[0].get('/api/companies/7/occupancy-snapshot')
    assert response.status_code == status
    assert 'private' not in response.get_data(as_text=True)


@pytest.mark.parametrize('denied_resource', ['companies', 'financial'])
def test_cost_read_requires_both_permissions(client_context, monkeypatch, denied_resource):
    from services import role_cost_profile_service
    read = Mock()
    monkeypatch.setattr(role_cost_profile_service, 'build_planned_cost_snapshot', read)
    client_context[2].side_effect = lambda company, resource, action: resource != denied_resource
    response = client_context[0].get('/api/companies/7/planned-role-costs?as_of=2026-09-04')
    assert response.status_code == 403
    read.assert_not_called()


def test_authorized_cost_snapshot(client_context, monkeypatch):
    from services import role_cost_profile_service
    read = Mock(return_value={"company_id": 7, "planned_monthly_total": None})
    monkeypatch.setattr(role_cost_profile_service, 'build_planned_cost_snapshot', read)
    response = client_context[0].get('/api/companies/7/planned-role-costs?as_of=2026-09-04')
    assert response.status_code == 200
    read.assert_called_once_with(7, '2026-09-04')


@pytest.mark.parametrize('denied_resource', ['companies', 'financial'])
def test_cost_write_requires_both_edit_permissions(client_context, monkeypatch, denied_resource):
    from services import role_cost_profile_service
    write = Mock()
    monkeypatch.setattr(role_cost_profile_service, 'create_cost_profile', write)
    client_context[2].side_effect = lambda company, resource, action: resource != denied_resource
    response = client_context[0].post('/api/companies/7/roles/12/cost-profiles', json={})
    assert response.status_code == 403
    write.assert_not_called()


def test_cost_write_records_authenticated_actor_and_commits(client_context, monkeypatch):
    from services import role_cost_profile_service
    monkeypatch.setattr(routes, 'current_user', Mock(id=33))
    write = Mock(return_value=Mock(id=44))
    monkeypatch.setattr(role_cost_profile_service, 'create_cost_profile', write)
    payload = {'starts_on': '2026-09-01', 'currency': 'BRL'}
    response = client_context[0].post('/api/companies/7/roles/12/cost-profiles', json=payload)
    assert response.status_code == 201
    write.assert_called_once_with(7, 12, payload, actor_user_id=33)
    client_context[5].session.commit.assert_called_once()


@pytest.mark.parametrize('error,status', [(ValueError('Conflito'), 400), (NotFound(), 404), (RuntimeError('private'), 500)])
def test_cost_write_failure_rolls_back(client_context, monkeypatch, error, status):
    from services import role_cost_profile_service
    monkeypatch.setattr(routes, 'current_user', Mock(id=33))
    monkeypatch.setattr(role_cost_profile_service, 'create_cost_profile', Mock(side_effect=error))
    response = client_context[0].post('/api/companies/7/roles/12/cost-profiles', json={})
    assert response.status_code == status
    client_context[5].session.rollback.assert_called_once()
    client_context[5].session.commit.assert_not_called()
    assert 'private' not in response.get_data(as_text=True)


def test_qualification_evidence_uses_actor_and_commit(client_context, monkeypatch):
    from services import employee_qualification_service
    monkeypatch.setattr(routes, 'current_user', Mock(id=33))
    record = Mock()
    record.to_dict.return_value = {'id': 88, 'company_id': 7, 'employee_id': 23, 'evidence_source': 'declared'}
    create = Mock(return_value=record)
    monkeypatch.setattr(employee_qualification_service, 'create', create)
    payload = {'qualification_name': 'Excel', 'evidence_source': 'declared'}
    response = client_context[0].post('/api/companies/7/employees/23/qualification-evidences', json=payload)
    assert response.status_code == 201
    create.assert_called_once_with(7, 23, payload, actor_user_id=33)
    client_context[5].session.commit.assert_called_once()


@pytest.mark.parametrize('error,status', [(ValueError('inválido'), 400), (NotFound(), 404), (RuntimeError('private'), 500)])
def test_qualification_evidence_failure_rolls_back(client_context, monkeypatch, error, status):
    from services import employee_qualification_service
    monkeypatch.setattr(routes, 'current_user', Mock(id=33))
    monkeypatch.setattr(employee_qualification_service, 'create', Mock(side_effect=error))
    response = client_context[0].post('/api/companies/7/employees/23/qualification-evidences', json={})
    assert response.status_code == status
    client_context[5].session.rollback.assert_called_once()
    assert 'private' not in response.get_data(as_text=True)


def test_qualification_evidence_read_uses_tenant_and_view_permission(client_context, monkeypatch):
    from services import employee_qualification_service
    read = Mock(return_value={'company_id': 7, 'employee_id': 23, 'items': [], 'qualification_match_evaluated': False})
    monkeypatch.setattr(employee_qualification_service, 'list_for_employee', read)
    response = client_context[0].get('/api/companies/7/employees/23/qualification-evidences?as_of=2026-09-04')
    assert response.status_code == 200
    read.assert_called_once_with(7, 23, reference_date='2026-09-04')
    client_context[2].assert_called_once_with(7, 'companies', 'view')
