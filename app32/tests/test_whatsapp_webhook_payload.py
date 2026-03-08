import json
import os
import sys

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.webhooks.whatsapp_webhook import (
    _extract_whatsapp_message,
    _load_whatsapp_request_payload,
    whatsapp_webhook_bp,
)


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


def test_extract_whatsapp_message_from_message_data():
    payload = {
        "phone": "5571999999999",
        "messageData": {
            "textMessageData": {"textMessage": "quero meu resumo"},
        },
    }

    phone, text, metadata = _extract_whatsapp_message(payload)

    assert phone == "5571999999999"
    assert text == "quero meu resumo"
    assert metadata["thread_contact"] == "5571999999999"


def test_load_whatsapp_request_payload_from_form_json_field():
    app = Flask(__name__)

    raw = json.dumps({"phone": "5511999999999", "message": "oi"})
    with app.test_request_context(
        "/webhook/whatsapp",
        method="POST",
        data={"payload": raw},
        content_type="application/x-www-form-urlencoded",
    ):
        payload = _load_whatsapp_request_payload()

    assert payload["phone"] == "5511999999999"
    assert payload["message"] == "oi"


def test_handle_whatsapp_accepts_form_encoded_payload(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(whatsapp_webhook_bp, url_prefix="/webhook")

    called = {}

    class DummyThread:
        def __init__(self, target=None, args=None, kwargs=None):
            called["target"] = target
            called["args"] = args or ()

        def start(self):
            called["started"] = True

    monkeypatch.setattr("api.webhooks.whatsapp_webhook.Thread", DummyThread)

    client = app.test_client()
    response = client.post(
        "/webhook/whatsapp",
        data={
            "payload": json.dumps({
                "phone": "5511999999999",
                "message": "oi sapiens",
                "type": "ReceivedCallback",
            })
        },
        content_type="application/x-www-form-urlencoded",
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "accepted"
    assert called["started"] is True
    assert called["args"][1] == "5511999999999"
    assert called["args"][2] == "oi sapiens"
