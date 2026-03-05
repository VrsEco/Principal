import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.webhooks.whatsapp_webhook import _extract_whatsapp_message


def test_extract_whatsapp_message_standard_payload():
    payload = {
        "phone": "5511999999999",
        "text": {"message": "oi sapiens"},
        "type": "ReceivedCallback",
    }

    phone, text, metadata = _extract_whatsapp_message(payload)

    assert phone == "5511999999999"
    assert text == "oi sapiens"
    assert metadata["event_type"] == "ReceivedCallback"


def test_extract_whatsapp_message_nested_payload():
    payload = {
        "type": "ReceivedCallback",
        "data": {
            "phone": "55 (71) 99642-6565",
            "text": {"message": "menu"},
            "messageId": "abc123",
        },
    }

    phone, text, metadata = _extract_whatsapp_message(payload)

    assert phone == "5571996426565"
    assert text == "menu"
    assert metadata["message_id"] == "abc123"
    assert metadata["thread_contact"] == "5571996426565"


def test_extract_whatsapp_message_ignores_self_message():
    payload = {
        "phone": "5511999999999",
        "fromMe": True,
        "text": {"message": "mensagem enviada pela api"},
    }

    phone, text, metadata = _extract_whatsapp_message(payload)

    assert phone == ""
    assert text == ""
    assert metadata["ignored"] == "self_message"


def test_extract_whatsapp_message_from_chat_id():
    payload = {
        "chatId": "5511912345678@c.us",
        "body": "status?",
    }

    phone, text, metadata = _extract_whatsapp_message(payload)

    assert phone == "5511912345678"
    assert text == "status?"
    assert metadata["thread_contact"] == "5511912345678"

