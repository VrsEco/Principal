from api.webhooks import telegram_webhook


class _FailingBot:
    def __init__(self, error: Exception):
        self.error = error
        self.calls = []

    def send_message(self, **payload):
        self.calls.append(payload)
        raise self.error


def test_safe_send_telegram_message_swallows_chat_not_found(monkeypatch):
    fake_bot = _FailingBot(
        Exception(
            "A request to the Telegram API was unsuccessful. Error code: 400. Description: Bad Request: chat not found"
        )
    )
    monkeypatch.setattr(telegram_webhook, "bot", fake_bot)

    sent = telegram_webhook._safe_send_telegram_message(
        123456,
        "Teste",
        parse_mode="HTML",
        reply_to_message_id=99,
    )

    assert sent is False
    assert fake_bot.calls == [
        {
            "chat_id": 123456,
            "text": "Teste",
            "parse_mode": "HTML",
            "reply_to_message_id": 99,
        }
    ]


def test_non_critical_delivery_error_detection():
    assert telegram_webhook._is_non_critical_telegram_delivery_error(
        Exception("Bad Request: chat not found")
    )
    assert telegram_webhook._is_non_critical_telegram_delivery_error(
        Exception("Forbidden: bot was blocked by the user")
    )
    assert not telegram_webhook._is_non_critical_telegram_delivery_error(
        Exception("timeout while connecting")
    )
