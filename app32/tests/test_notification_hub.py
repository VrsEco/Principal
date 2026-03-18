import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.notification_hub import NotificationHub


def test_send_to_user_uses_whatsapp_recipient_override(monkeypatch):
    hub = NotificationHub()
    sent = {}

    def fake_send_whatsapp(phone_number, message):
        sent["phone_number"] = phone_number
        sent["message"] = message
        return {"success": True, "channel": "whatsapp", "recipient": phone_number}

    monkeypatch.setattr(hub, "send_whatsapp", fake_send_whatsapp)

    user = SimpleNamespace(
        id=6,
        email="marciosimoes@uol.com.br",
        whatsapp=None,
        telegram=None,
        instagram=None,
        is_active=True,
    )

    result = hub.send_to_user(
        user,
        "whatsapp",
        "teste",
        recipient_override="5511999998888",
    )

    assert result["success"] is True
    assert sent["phone_number"] == "5511999998888"
    assert sent["message"] == "teste"
