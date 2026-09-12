from pathlib import Path

from flask import Flask

from api.routes import auth as auth_route


def _build_app():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test-secret")
    app.register_blueprint(auth_route.auth_bp)
    return app


def test_request_response_is_neutral_for_known_and_unknown_addresses(monkeypatch):
    requested = []
    monkeypatch.setattr(
        auth_route.password_reset_service,
        "request_reset",
        lambda **kwargs: requested.append(kwargs),
    )
    app = _build_app()
    client = app.test_client()

    known = client.post('/password-reset', json={'email': 'known@empresa.test'})
    unknown = client.post('/password-reset', json={'email': 'unknown@empresa.test'})

    assert known.status_code == unknown.status_code == 202
    assert known.get_json() == unknown.get_json()
    assert [item['email'] for item in requested] == ['known@empresa.test', 'unknown@empresa.test']


def test_request_is_rate_limited_without_account_lookup(monkeypatch):
    monkeypatch.setattr(auth_route.password_reset_service, "request_reset", lambda **kwargs: None)
    app = _build_app()
    client = app.test_client()

    for _ in range(3):
        assert client.post('/password-reset', json={'email': 'same@empresa.test'}).status_code == 202
    assert client.post('/password-reset', json={'email': 'same@empresa.test'}).status_code == 429


def test_complete_requires_matching_strong_passwords(monkeypatch):
    completed = []
    monkeypatch.setattr(
        auth_route.password_reset_service,
        "complete_reset",
        lambda **kwargs: completed.append(kwargs),
    )
    app = _build_app()
    client = app.test_client()

    mismatch = client.post('/password-reset/token-opaco', json={
        'new_password': 'NovaSenhaMuitoForte',
        'confirm_password': 'OutraSenhaMuitoForte',
    })
    success = client.post('/password-reset/token-opaco', json={
        'new_password': 'NovaSenhaMuitoForte',
        'confirm_password': 'NovaSenhaMuitoForte',
    })

    assert mismatch.status_code == 400
    assert success.status_code == 200
    assert completed == [{'raw_token': 'token-opaco', 'new_password': 'NovaSenhaMuitoForte'}]


def test_reset_request_template_gives_immediate_feedback_and_cooldown():
    template = (Path(__file__).resolve().parents[1] / 'templates' / 'auth' / 'password_reset_request.html').read_text(encoding='utf-8')

    assert "Processando sua solicitação. Aguarde." in template
    assert "Confira sua caixa de e-mail antes de solicitar novamente." in template
    assert "window.setTimeout" in template
    assert "90000" in template
    assert "credentials:'same-origin'" in template
    assert "/static/img/versus-logo.png" in template
    assert "button.classList.add('is-loading')" in template
    assert "button.classList.add('is-complete')" in template
