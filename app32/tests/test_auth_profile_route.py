import os
import sys
from types import SimpleNamespace

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.routes import auth as auth_route


class _FakeAuthService:
    def __init__(self):
        self.update_calls = []
        self.password_calls = []
        self.password_result = True

    def update_user_profile(self, user, **kwargs):
        self.update_calls.append((user, kwargs))
        for key, value in kwargs.items():
            if key != 'summary_delivery_channels':
                setattr(user, key, value)
        user.summary_delivery_channels = kwargs.get('summary_delivery_channels')
        return True

    def change_password(self, user, old_password, new_password):
        self.password_calls.append((user, old_password, new_password))
        return self.password_result


def _build_app():
    app = Flask(
        __name__,
        template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")),
    )
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True
    app.register_blueprint(auth_route.auth_bp)
    app.jinja_env.globals['url_for'] = lambda endpoint, **values: '/' + endpoint.replace('.', '/')
    app.jinja_env.globals['has_permission'] = lambda *args, **kwargs: False
    return app


def test_profile_route_updates_basic_user_fields(monkeypatch):
    app = _build_app()
    fake_service = _FakeAuthService()
    fake_user = SimpleNamespace(
        id=10,
        name='Ana',
        email='ana@empresa.com',
        whatsapp=None,
        telegram=None,
        instagram=None,
        summary_delivery_channels='telegram',
        is_authenticated=True,
        to_dict=lambda: {
            'id': 10,
            'name': fake_user.name,
            'email': fake_user.email,
            'summary_delivery_channels': fake_user.summary_delivery_channels,
        },
    )

    monkeypatch.setattr(auth_route, 'current_user', fake_user)
    monkeypatch.setattr(auth_route, 'auth_service', fake_service)

    client = app.test_client()
    response = client.post('/profile', json={
        'name': 'Ana Maria',
        'whatsapp': '5571999999999',
        'telegram': '123456',
        'instagram': '@ana',
        'summary_delivery_channels': ['email', 'whatsapp'],
    })

    payload = response.get_json()
    assert response.status_code == 200
    assert payload['success'] is True
    assert fake_service.update_calls[0][1]['name'] == 'Ana Maria'
    assert fake_service.update_calls[0][1]['summary_delivery_channels'] == 'email,whatsapp'


def test_profile_route_accepts_auth_prefix_alias(monkeypatch):
    app = _build_app()
    fake_service = _FakeAuthService()
    fake_user = SimpleNamespace(
        id=11,
        name='Bruno',
        email='bruno@empresa.com',
        whatsapp=None,
        telegram=None,
        instagram=None,
        summary_delivery_channels='telegram',
        is_authenticated=True,
        to_dict=lambda: {'id': 11, 'name': 'Bruno'},
    )

    monkeypatch.setattr(auth_route, 'current_user', fake_user)
    monkeypatch.setattr(auth_route, 'auth_service', fake_service)

    client = app.test_client()
    response = client.post('/auth/profile', json={'name': 'Bruno Lima', 'summary_delivery_channels': ['telegram']})

    assert response.status_code == 200
    assert response.get_json()['success'] is True


def test_change_password_route_validates_current_password(monkeypatch):
    app = _build_app()
    fake_service = _FakeAuthService()
    fake_service.password_result = False
    fake_user = SimpleNamespace(id=12, name='Carla', is_authenticated=True)

    monkeypatch.setattr(auth_route, 'current_user', fake_user)
    monkeypatch.setattr(auth_route, 'auth_service', fake_service)

    client = app.test_client()
    response = client.post('/change-password', json={
        'old_password': 'errada',
        'new_password': 'NovaSenha123',
        'confirm_password': 'NovaSenha123',
    })

    payload = response.get_json()
    assert response.status_code == 400
    assert payload['message'] == 'Senha atual incorreta'
    assert fake_service.password_calls[0][1] == 'errada'


def test_profile_get_hides_advanced_squads_for_non_admin(monkeypatch):
    app = _build_app()
    fake_user = SimpleNamespace(
        id=20,
        name='Cliente',
        email='cliente@empresa.com',
        role='client',
        whatsapp=None,
        telegram=None,
        instagram=None,
        summary_delivery_channels='telegram',
        is_authenticated=True,
    )

    monkeypatch.setattr(auth_route, 'current_user', fake_user)
    app.jinja_env.globals['current_user'] = fake_user

    response = app.test_client().get('/profile')

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Instalar Squad' in html
    assert '1. Configurar MCP' in html
    assert '2. Instalar Squad' in html
    assert 'Squad que será instalado' in html
    assert 'Qual Cliente de IA você irá usar?' in html
    assert 'Claude Code / Desktop' in html
    assert 'Sapiens Cliente' in html
    assert 'Como essa combinação vai funcionar' in html
    assert 'Como criar a conexão MCP neste cliente' in html
    assert 'Dados para preencher na conexão' in html
    assert 'Teste inicial recomendado' in html
    assert 'Comandos oficiais de ativação' in html
    assert '/sapiens-cliente-on' in html
    assert 'Família inicial oficial do Squad Cliente' in html
    assert 'Quem vai te atender no Sapiens Cliente' in html
    assert 'Ajuda com clientes, propostas, negociação, preço e oportunidades.' in html
    assert 'Para você, continua sendo uma única conversa, simples e contínua.' in html
    assert 'Agente Coordenador' in html
    assert 'Copie seu token agora' in html
    assert '.mcp-token-modal__dialog' in html
    assert 'Seu perfil atual instala apenas o Sapiens Cliente' in html
    assert 'data-choice-value="squad_versus"' not in html
    assert 'data-choice-value="engineering"' not in html


def test_profile_get_shows_consultor_and_cliente_for_consultant(monkeypatch):
    app = _build_app()
    fake_user = SimpleNamespace(
        id=30,
        name='Consultor',
        email='consultor@versus.com',
        role='consultant',
        whatsapp=None,
        telegram=None,
        instagram=None,
        summary_delivery_channels='telegram',
        is_authenticated=True,
    )

    monkeypatch.setattr(auth_route, 'current_user', fake_user)
    app.jinja_env.globals['current_user'] = fake_user

    response = app.test_client().get('/profile')

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Sapiens Cliente' in html
    assert 'Sapiens Consultor' in html
    assert 'data-choice-value="engineering"' not in html


def test_profile_get_shows_all_squads_for_admin(monkeypatch):
    app = _build_app()
    fake_user = SimpleNamespace(
        id=21,
        name='Admin',
        email='admin@empresa.com',
        role='admin',
        whatsapp=None,
        telegram=None,
        instagram=None,
        summary_delivery_channels='telegram',
        is_authenticated=True,
    )

    monkeypatch.setattr(auth_route, 'current_user', fake_user)
    app.jinja_env.globals['current_user'] = fake_user

    response = app.test_client().get('/profile')

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'Seu perfil atual pode instalar Sapiens Cliente, Sapiens Consultor e Sapiens Engenharia.' in html
    assert 'Sapiens Cliente' in html
    assert 'Sapiens Consultor' in html
    assert 'Sapiens Engenharia' in html
