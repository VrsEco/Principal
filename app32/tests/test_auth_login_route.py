import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import auth as auth_route


class _FakeUserQuery:
    def __init__(self, user):
        self._user = user

    def filter_by(self, **kwargs):
        return self

    def first(self):
        return self._user


class _FakeEmployeeQuery:
    def __init__(self, employees):
        self._employees = employees

    def filter_by(self, **kwargs):
        return self

    def all(self):
        return list(self._employees)


def _build_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    app.register_blueprint(auth_route.auth_bp)
    return app


def test_login_redirects_single_company_user_to_my_work(monkeypatch):
    app = _build_app()
    fake_user = SimpleNamespace(
        id=13,
        email='operacao.dp@meuchapa.com.br',
        check_password=lambda password: password == 'SenhaSegura123',
    )
    fake_employee = SimpleNamespace(company_id=8)

    monkeypatch.setattr(auth_route, 'User', SimpleNamespace(query=_FakeUserQuery(fake_user)))
    monkeypatch.setattr(auth_route, 'Employee', SimpleNamespace(query=_FakeEmployeeQuery([fake_employee])))
    monkeypatch.setattr(auth_route, 'is_platform_admin', lambda: False)
    monkeypatch.setattr(auth_route, 'login_user', lambda user: True)

    client = app.test_client()
    response = client.post('/login', json={
        'email': 'operacao.dp@meuchapa.com.br',
        'password': 'SenhaSegura123',
    })

    assert response.status_code == 200
    assert response.get_json() == {'success': True, 'redirect': '/my-work'}

    with client.session_transaction() as sess:
        assert sess['active_company_id'] == 8


def test_login_keeps_portal_flow_for_multi_company_user(monkeypatch):
    app = _build_app()
    fake_user = SimpleNamespace(
        id=21,
        email='multi@empresa.com.br',
        check_password=lambda password: password == 'SenhaSegura123',
    )
    fake_employees = [SimpleNamespace(company_id=1), SimpleNamespace(company_id=2)]

    monkeypatch.setattr(auth_route, 'User', SimpleNamespace(query=_FakeUserQuery(fake_user)))
    monkeypatch.setattr(auth_route, 'Employee', SimpleNamespace(query=_FakeEmployeeQuery(fake_employees)))
    monkeypatch.setattr(auth_route, 'is_platform_admin', lambda: False)
    monkeypatch.setattr(auth_route, 'login_user', lambda user: True)

    client = app.test_client()
    response = client.post('/login', json={
        'email': 'multi@empresa.com.br',
        'password': 'SenhaSegura123',
    })

    assert response.status_code == 200
    assert response.get_json() == {'success': True, 'redirect': '/portal'}

    with client.session_transaction() as sess:
        assert 'active_company_id' not in sess
