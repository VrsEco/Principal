import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.webhooks import telegram_webhook


class _DummyBot:
    def __init__(self):
        self.calls = []

    def send_message(self, **payload):
        self.calls.append(payload)
        if payload.get("reply_to_message_id") is not None:
            raise RuntimeError("Bad Request: message to be replied not found")
        return True


class _DummyUser:
    id = 77


def test_telegram_reply_reference_error_is_non_critical():
    assert telegram_webhook._is_non_critical_telegram_delivery_error(
        RuntimeError("Bad Request: message to be replied not found")
    )
    assert telegram_webhook._is_reply_reference_telegram_error(
        RuntimeError("Bad Request: message to be replied not found")
    )


def test_safe_send_telegram_retries_without_stale_reply(monkeypatch):
    dummy = _DummyBot()
    monkeypatch.setattr(telegram_webhook, "bot", dummy)

    sent = telegram_webhook._safe_send_telegram_message(
        123,
        "Processando...",
        parse_mode="HTML",
        reply_to_message_id=999,
    )

    assert sent is True
    assert len(dummy.calls) == 2
    assert dummy.calls[0]["reply_to_message_id"] == 999
    assert "reply_to_message_id" not in dummy.calls[1]
    assert dummy.calls[1]["parse_mode"] == "HTML"


def test_resolve_action_company_id_is_tenant_safe(monkeypatch):
    monkeypatch.setattr("src.intelligence.identity.get_best_company_id", lambda user: 9)

    assert telegram_webhook._resolve_action_company_id(_DummyUser()) == 9
    assert telegram_webhook._resolve_action_company_id(None) is None
