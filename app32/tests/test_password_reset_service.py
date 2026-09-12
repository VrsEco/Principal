import re
import logging

import pytest
from flask import Flask

from models import PasswordResetToken, User, db
from services.password_reset_service import PasswordResetError, password_reset_service


@pytest.fixture()
def reset_app(tmp_path):
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY="password-reset-test-secret",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{tmp_path / 'reset.db'}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    with app.app_context():
        User.__table__.create(db.engine)
        PasswordResetToken.__table__.create(db.engine)
        user = User(email="pessoa@empresa.test", name="Pessoa", role="user", is_active=True)
        user.set_password("SenhaAntigaMuitoForte")
        db.session.add(user)
        db.session.commit()
        yield app
        db.session.remove()
        PasswordResetToken.__table__.drop(db.engine)
        User.__table__.drop(db.engine)


def test_request_stores_only_token_hash_and_latest_link_is_single_use(reset_app, monkeypatch):
    sent = []
    monkeypatch.setattr(password_reset_service, "TOKEN_TTL_MINUTES", 30)
    monkeypatch.setattr("services.password_reset_service.email_service.build_transactional_email_html", lambda **kwargs: "html")
    monkeypatch.setattr(
        "services.password_reset_service.email_service.send_email",
        lambda recipients, subject, body, html_body=None: sent.append((recipients, subject, body)) or True,
    )

    with reset_app.app_context():
        password_reset_service.request_reset(
            email="pessoa@empresa.test",
            request_ip="203.0.113.10",
            reset_url_prefix="https://app.example.test/password-reset",
        )
        token = re.search(r"password-reset/([^\s]+)", sent[0][2]).group(1)
        stored = PasswordResetToken.query.one()

        assert stored.token_hash != token
        assert len(stored.token_hash) == 64
        assert stored.requested_ip_hash != "203.0.113.10"

        password_reset_service.complete_reset(raw_token=token, new_password="NovaSenhaMuitoForte")
        updated_user = User.query.one()
        assert updated_user.check_password("NovaSenhaMuitoForte")
        assert updated_user.auth_session_version == 2
        assert PasswordResetToken.query.one().used_at is not None

        with pytest.raises(PasswordResetError):
            password_reset_service.complete_reset(raw_token=token, new_password="OutraSenhaMuitoForte")


def test_new_request_revokes_previous_link(reset_app, monkeypatch):
    sent = []
    monkeypatch.setattr("services.password_reset_service.email_service.build_transactional_email_html", lambda **kwargs: "html")
    monkeypatch.setattr(
        "services.password_reset_service.email_service.send_email",
        lambda recipients, subject, body, html_body=None: sent.append(body) or True,
    )

    with reset_app.app_context():
        password_reset_service.request_reset(email="pessoa@empresa.test", request_ip="ip-a", reset_url_prefix="https://app.example.test/password-reset")
        first = re.search(r"password-reset/([^\s]+)", sent[-1]).group(1)
        password_reset_service.request_reset(email="pessoa@empresa.test", request_ip="ip-b", reset_url_prefix="https://app.example.test/password-reset")
        second = re.search(r"password-reset/([^\s]+)", sent[-1]).group(1)

        with pytest.raises(PasswordResetError):
            password_reset_service.complete_reset(raw_token=first, new_password="NovaSenhaMuitoForte")
        password_reset_service.complete_reset(raw_token=second, new_password="NovaSenhaMuitoForte")


def test_complete_rejects_short_password_without_consuming_token(reset_app, monkeypatch):
    sent = []
    monkeypatch.setattr("services.password_reset_service.email_service.build_transactional_email_html", lambda **kwargs: "html")
    monkeypatch.setattr(
        "services.password_reset_service.email_service.send_email",
        lambda recipients, subject, body, html_body=None: sent.append(body) or True,
    )

    with reset_app.app_context():
        password_reset_service.request_reset(email="pessoa@empresa.test", request_ip="ip", reset_url_prefix="https://app.example.test/password-reset")
        token = re.search(r"password-reset/([^\s]+)", sent[0]).group(1)
        with pytest.raises(PasswordResetError):
            password_reset_service.complete_reset(raw_token=token, new_password="curta")
        assert PasswordResetToken.query.one().used_at is None


def test_complete_rejects_expired_token(reset_app, monkeypatch):
    sent = []
    monkeypatch.setattr("services.password_reset_service.email_service.build_transactional_email_html", lambda **kwargs: "html")
    monkeypatch.setattr(
        "services.password_reset_service.email_service.send_email",
        lambda recipients, subject, body, html_body=None: sent.append(body) or True,
    )

    with reset_app.app_context():
        password_reset_service.request_reset(email="pessoa@empresa.test", request_ip="ip", reset_url_prefix="https://app.example.test/password-reset")
        token = re.search(r"password-reset/([^\s]+)", sent[0]).group(1)
        stored = PasswordResetToken.query.one()
        stored.expires_at = stored.created_at
        db.session.commit()

        with pytest.raises(PasswordResetError):
            password_reset_service.complete_reset(raw_token=token, new_password="NovaSenhaMuitoForte")
        assert PasswordResetToken.query.one().used_at is None


def test_request_renders_reset_url_as_link_in_transactional_email(reset_app, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "services.password_reset_service.email_service.send_email",
        lambda recipients, subject, body, html_body=None: sent.append(html_body) or True,
    )

    with reset_app.app_context():
        password_reset_service.request_reset(
            email="pessoa@empresa.test",
            request_ip="ip",
            reset_url_prefix="https://app.example.test/password-reset",
        )

    assert len(sent) == 1
    assert '<a href=\'https://app.example.test/password-reset/' in sent[0]
    assert "&lt;a href=" not in sent[0]


def test_request_for_unknown_email_does_not_dispatch_message(reset_app, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "services.password_reset_service.email_service.send_email",
        lambda *args, **kwargs: sent.append((args, kwargs)) or True,
    )

    with reset_app.app_context():
        password_reset_service.request_reset(
            email="inexistente@empresa.test",
            request_ip="ip",
            reset_url_prefix="https://app.example.test/password-reset",
        )

    assert sent == []


def test_delivery_failure_does_not_log_reset_token(reset_app, monkeypatch, caplog):
    canary_token = "token-canario-nao-registrar"
    monkeypatch.setattr("services.password_reset_service.secrets.token_urlsafe", lambda _size: canary_token)
    monkeypatch.setattr(
        "services.password_reset_service.email_service.send_email",
        lambda *args, **kwargs: False,
    )

    with reset_app.app_context(), caplog.at_level(logging.WARNING):
        password_reset_service.request_reset(
            email="pessoa@empresa.test",
            request_ip="ip",
            reset_url_prefix="https://app.example.test/password-reset",
        )

    assert canary_token not in caplog.text
