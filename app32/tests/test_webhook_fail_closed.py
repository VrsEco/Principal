"""Webhooks sem segredo configurado não podem ficar abertos em produção."""
import pytest
from flask import Flask

from utils.security import webhook_secret_verified


def _verify(app, expected, headers=None, query=""):
    with app.test_request_context("/webhook/x" + query, method="POST", headers=headers or {}):
        return webhook_secret_verified(
            expected_secret=expected,
            header_names=["X-Webhook-Secret"],
            query_names=["secret"],
        )


def _app(testing=False, debug=False):
    app = Flask(__name__)
    app.testing = testing
    app.debug = debug
    return app


@pytest.fixture(autouse=True)
def _no_optin(monkeypatch):
    monkeypatch.delenv("WEBHOOK_ALLOW_UNSIGNED", raising=False)


def test_missing_secret_is_denied_in_production():
    assert _verify(_app(), "") is False
    assert _verify(_app(), None) is False


def test_missing_secret_is_allowed_only_in_testing_or_debug():
    assert _verify(_app(testing=True), "") is True
    assert _verify(_app(debug=True), "") is True


def test_explicit_opt_in_allows_unsigned(monkeypatch):
    monkeypatch.setenv("WEBHOOK_ALLOW_UNSIGNED", "true")
    assert _verify(_app(), "") is True


def test_configured_secret_still_required():
    app = _app()
    assert _verify(app, "s3", headers={"X-Webhook-Secret": "s3"}) is True
    assert _verify(app, "s3", query="?secret=s3") is True
    assert _verify(app, "s3", headers={"X-Webhook-Secret": "errado"}) is False
    assert _verify(app, "s3") is False


def test_secret_is_required_even_in_testing_when_configured():
    assert _verify(_app(testing=True), "s3") is False


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/webhook/whatsapp", {"phone": "5511999999999", "message": "oi"}),
        ("/webhook/instagram", {"sender": {"id": "1"}, "message": "oi"}),
        ("/webhook/email", {"from": "a@b.com", "body": "oi"}),
        ("/webhook/telegram", {"update_id": 1}),
    ],
)
def test_public_webhook_routes_forbid_unsigned_requests_in_production(path, payload, monkeypatch):
    from api.webhooks.email_webhook import email_webhook_bp
    from api.webhooks.telegram_webhook import telegram_bp
    from api.webhooks.whatsapp_webhook import whatsapp_webhook_bp

    for name in ("WEBHOOK_SHARED_SECRET", "WHATSAPP_WEBHOOK_SECRET", "INSTAGRAM_WEBHOOK_SECRET",
                 "EMAIL_WEBHOOK_SECRET", "TELEGRAM_WEBHOOK_SECRET"):
        monkeypatch.delenv(name, raising=False)
    app = _app()
    for bp in (whatsapp_webhook_bp, email_webhook_bp, telegram_bp):
        app.register_blueprint(bp, url_prefix="/webhook")
    response = app.test_client().post(path, json=payload)
    assert response.status_code == 403
