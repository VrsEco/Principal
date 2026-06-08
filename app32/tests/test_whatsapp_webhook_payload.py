import json
import os
import sys
import threading
import time

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.webhooks.whatsapp_webhook import (
    _extract_whatsapp_message,
    _load_whatsapp_request_payload,
    _personalize_whatsapp_greeting,
    process_whatsapp_message,
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


def test_extract_whatsapp_message_supports_document_attachment_without_text():
    payload = {
        "phone": "5571999999999",
        "messageData": {
            "documentMessageData": {
                "fileName": "recibo_taxi.pdf",
                "mimeType": "application/pdf",
                "url": "https://files.example.com/recibo_taxi.pdf",
            },
        },
    }

    phone, text, metadata = _extract_whatsapp_message(payload)

    assert phone == "5571999999999"
    assert text == ""
    assert metadata["attachment"]["file_name"] == "recibo_taxi.pdf"
    assert metadata["attachment"]["mime_type"] == "application/pdf"


def test_extract_whatsapp_message_supports_image_attachment_with_image_url_and_no_filename():
    payload = {
        "phone": "5571999999999",
        "image": {
            "imageUrl": "https://files.example.com/receipt-photo.jpg",
            "mimeType": "image/jpeg",
        },
    }

    phone, text, metadata = _extract_whatsapp_message(payload)

    assert phone == "5571999999999"
    assert text == ""
    assert metadata["attachment"]["url"] == "https://files.example.com/receipt-photo.jpg"
    assert metadata["attachment"]["file_name"] == "arquivo_image.jpg"
    assert metadata["attachment"]["mime_type"] == "image/jpeg"


def test_extract_whatsapp_message_supports_multiple_image_attachments():
    payload = {
        "phone": "5571999999999",
        "images": [
            {
                "imageUrl": "https://files.example.com/receipt-photo-1.jpg",
                "mimeType": "image/jpeg",
            },
            {
                "imageUrl": "https://files.example.com/receipt-photo-2.jpg",
                "mimeType": "image/jpeg",
            },
        ],
    }

    phone, text, metadata = _extract_whatsapp_message(payload)

    assert phone == "5571999999999"
    assert text == ""
    assert len(metadata["attachments"]) == 2
    assert metadata["attachments"][0]["url"] == "https://files.example.com/receipt-photo-1.jpg"
    assert metadata["attachments"][1]["url"] == "https://files.example.com/receipt-photo-2.jpg"
    assert metadata["attachment"]["url"] == "https://files.example.com/receipt-photo-1.jpg"


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


def test_personalize_whatsapp_greeting_uses_first_name():
    result = _personalize_whatsapp_greeting("Olá! Como posso ajudar você hoje?", "Fabiano Ferreira")

    assert result == "Olá Fabiano! Como posso te ajudar?"


def test_personalize_whatsapp_greeting_preserves_non_greeting_text():
    result = _personalize_whatsapp_greeting("Segue o resumo das suas atividades.", "Fabiano Ferreira")

    assert result == "Segue o resumo das suas atividades."


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


def test_process_whatsapp_financial_attachment_enriches_workflow_payload(monkeypatch):
    app = Flask(__name__)

    class DummyUser:
        id = 7
        name = "Fabiano Ferreira"

    class DummyWorkflowResult:
        handled = True
        response_text = "Arquivo enviado para a Central."
        metadata = {"workflow_code": "361"}

    recorded = {"messages": []}

    def capture_workflow(**kwargs):
        recorded["workflow"] = kwargs
        return DummyWorkflowResult()

    monkeypatch.setattr('src.intelligence.identity.resolve_user_identity', lambda contact, channel: DummyUser())
    monkeypatch.setattr('src.intelligence.identity.build_identity_resolution_trace', lambda *args, **kwargs: type('Trace', (), {'to_safe_dict': lambda self: {}})())
    monkeypatch.setattr('src.intelligence.identity.get_best_company_id', lambda user: 9)
    monkeypatch.setattr('services.proactive_service.try_handle_summary_followup', lambda **kwargs: (False, None))
    monkeypatch.setattr('src.intelligence.menu_engine.start_channel_workflow', capture_workflow)
    monkeypatch.setattr('api.webhooks.whatsapp_webhook._download_attachment_bytes', lambda attachment: (b'%PDF-1.4 fake', None))
    monkeypatch.setattr('src.intelligence.execution._capture_workflow_usage_from_execution', lambda **kwargs: recorded.setdefault('usage', []).append(kwargs))
    monkeypatch.setattr('models.agent_message.AgentMessage', lambda **kwargs: kwargs)
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.add', lambda obj: recorded['messages'].append(obj))
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.commit', lambda: recorded.setdefault('committed', True))
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.rollback', lambda: recorded.setdefault('rolled_back', True))
    monkeypatch.setattr('services.whatsapp_service.whatsapp_service.send_message', lambda phone, message: recorded.setdefault('sent', []).append((phone, message)) or True)

    metadata = {
        "event_type": "ReceivedCallback",
        "message_id": "wamid.123",
        "instance_id": "instance-7",
        "thread_contact": "5571996426565",
        "attachments": [
            {
                "file_name": "Taxa_Alteracao_VM.pdf",
                "mime_type": "application/pdf",
                "url": "https://files.example.com/Taxa_Alteracao_VM.pdf",
            },
        ],
        "attachment": {
            "file_name": "Taxa_Alteracao_VM.pdf",
            "mime_type": "application/pdf",
            "url": "https://files.example.com/Taxa_Alteracao_VM.pdf",
        },
    }

    process_whatsapp_message(app, "5571996426565", "", metadata)

    workflow = recorded["workflow"]
    assert workflow["workflow_code"] == "361"
    assert workflow["payload"]["_source_channel"] == "whatsapp"
    assert workflow["payload"]["_source_contact"] == "5571996426565"
    assert workflow["payload"]["_source_external_reference"] == "wamid.123"
    assert workflow["payload"]["_thread_id"] == "wa_5571996426565"
    assert len(workflow["payload"]["_attachments"]) == 1


def test_process_whatsapp_multiple_financial_attachments_enriches_workflow_payload(monkeypatch):
    app = Flask(__name__)

    class DummyUser:
        id = 7
        name = "Fabiano Ferreira"

    class DummyWorkflowResult:
        handled = True
        response_text = "Arquivos enviados para a Central."
        metadata = {"workflow_code": "361"}

    recorded = {"messages": []}

    def capture_workflow(**kwargs):
        recorded["workflow"] = kwargs
        return DummyWorkflowResult()

    monkeypatch.setattr('src.intelligence.identity.resolve_user_identity', lambda contact, channel: DummyUser())
    monkeypatch.setattr('src.intelligence.identity.build_identity_resolution_trace', lambda *args, **kwargs: type('Trace', (), {'to_safe_dict': lambda self: {}})())
    monkeypatch.setattr('src.intelligence.identity.get_best_company_id', lambda user: 9)
    monkeypatch.setattr('services.proactive_service.try_handle_summary_followup', lambda **kwargs: (False, None))
    monkeypatch.setattr('src.intelligence.menu_engine.start_channel_workflow', capture_workflow)
    monkeypatch.setattr(
        'api.webhooks.whatsapp_webhook._download_attachment_bytes',
        lambda attachment: (f"bytes::{attachment['file_name']}".encode('utf-8'), None),
    )
    monkeypatch.setattr('src.intelligence.execution._capture_workflow_usage_from_execution', lambda **kwargs: recorded.setdefault('usage', []).append(kwargs))
    monkeypatch.setattr('models.agent_message.AgentMessage', lambda **kwargs: kwargs)
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.add', lambda obj: recorded['messages'].append(obj))
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.commit', lambda: recorded.setdefault('committed', True))
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.rollback', lambda: recorded.setdefault('rolled_back', True))
    monkeypatch.setattr('services.whatsapp_service.whatsapp_service.send_message', lambda phone, message: recorded.setdefault('sent', []).append((phone, message)) or True)

    metadata = {
        "event_type": "ReceivedCallback",
        "message_id": "wamid.multi",
        "instance_id": "instance-7",
        "thread_contact": "5571996426565",
        "attachments": [
            {
                "file_name": "recibo_1.jpg",
                "mime_type": "image/jpeg",
                "url": "https://files.example.com/recibo_1.jpg",
            },
            {
                "file_name": "recibo_2.jpg",
                "mime_type": "image/jpeg",
                "url": "https://files.example.com/recibo_2.jpg",
            },
        ],
    }

    process_whatsapp_message(app, "5571996426565", "", metadata)

    workflow = recorded["workflow"]
    assert workflow["workflow_code"] == "361"
    assert len(workflow["payload"]["_attachments"]) == 2
    assert workflow["payload"]["_attachments"][0]["file_name"] == "recibo_1.jpg"
    assert workflow["payload"]["_attachments"][1]["file_name"] == "recibo_2.jpg"
    assert workflow["payload"]["_source_label"] == "WhatsApp - 2 arquivo(s)"


def test_process_whatsapp_serializes_parallel_events_from_same_thread(monkeypatch):
    app = Flask(__name__)

    class DummyUser:
        id = 7
        name = "Fabiano Ferreira"

    class DummyWorkflowResult:
        handled = True
        response_text = ""
        metadata = {"workflow_code": "361"}

    state = {"current": 0, "max": 0, "calls": 0}
    state_lock = threading.Lock()

    def capture_workflow(**kwargs):
        with state_lock:
            state["current"] += 1
            state["calls"] += 1
            state["max"] = max(state["max"], state["current"])
        time.sleep(0.05)
        with state_lock:
            state["current"] -= 1
        return DummyWorkflowResult()

    monkeypatch.setattr('src.intelligence.identity.resolve_user_identity', lambda contact, channel: DummyUser())
    monkeypatch.setattr('src.intelligence.identity.build_identity_resolution_trace', lambda *args, **kwargs: type('Trace', (), {'to_safe_dict': lambda self: {}})())
    monkeypatch.setattr('src.intelligence.identity.get_best_company_id', lambda user: 9)
    monkeypatch.setattr('services.proactive_service.try_handle_summary_followup', lambda **kwargs: (False, None))
    monkeypatch.setattr('src.intelligence.menu_engine.start_channel_workflow', capture_workflow)
    monkeypatch.setattr(
        'api.webhooks.whatsapp_webhook._download_attachment_bytes',
        lambda attachment: (f"bytes::{attachment['file_name']}".encode('utf-8'), None),
    )
    monkeypatch.setattr('src.intelligence.execution._capture_workflow_usage_from_execution', lambda **kwargs: None)
    monkeypatch.setattr('models.agent_message.AgentMessage', lambda **kwargs: kwargs)
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.add', lambda obj: None)
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.commit', lambda: None)
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.rollback', lambda: None)
    monkeypatch.setattr('services.whatsapp_service.whatsapp_service.send_message', lambda phone, message: True)

    metadata_1 = {
        "event_type": "ReceivedCallback",
        "message_id": "wamid.parallel.1",
        "instance_id": "instance-7",
        "thread_contact": "5571996426565",
        "attachments": [
            {
                "file_name": "recibo_parallel_1.jpg",
                "mime_type": "image/jpeg",
                "url": "https://files.example.com/recibo_parallel_1.jpg",
            },
        ],
    }
    metadata_2 = {
        "event_type": "ReceivedCallback",
        "message_id": "wamid.parallel.2",
        "instance_id": "instance-7",
        "thread_contact": "5571996426565",
        "attachments": [
            {
                "file_name": "recibo_parallel_2.jpg",
                "mime_type": "image/jpeg",
                "url": "https://files.example.com/recibo_parallel_2.jpg",
            },
        ],
    }

    thread_a = threading.Thread(target=process_whatsapp_message, args=(app, "5571996426565", "", metadata_1))
    thread_b = threading.Thread(target=process_whatsapp_message, args=(app, "5571996426565", "", metadata_2))

    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    assert state["calls"] == 2
    assert state["max"] == 1


def test_process_whatsapp_unsupported_attachment_returns_operational_message(monkeypatch):
    app = Flask(__name__)

    class DummyUser:
        id = 7
        name = "Fabiano Ferreira"

    recorded = {"messages": [], "sent": []}

    monkeypatch.setattr('src.intelligence.identity.resolve_user_identity', lambda contact, channel: DummyUser())
    monkeypatch.setattr('src.intelligence.identity.build_identity_resolution_trace', lambda *args, **kwargs: type('Trace', (), {'to_safe_dict': lambda self: {}})())
    monkeypatch.setattr('src.intelligence.identity.get_best_company_id', lambda user: 9)
    monkeypatch.setattr('services.proactive_service.try_handle_summary_followup', lambda **kwargs: (False, None))
    monkeypatch.setattr('models.agent_message.AgentMessage', lambda **kwargs: kwargs)
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.add', lambda obj: recorded['messages'].append(obj))
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.commit', lambda: recorded.setdefault('committed', True))
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.rollback', lambda: recorded.setdefault('rolled_back', True))
    monkeypatch.setattr('services.whatsapp_service.whatsapp_service.send_message', lambda phone, message: recorded['sent'].append((phone, message)) or True)

    metadata = {
        "event_type": "ReceivedCallback",
        "message_id": "wamid.unsupported",
        "thread_contact": "5571996426565",
        "attachment": {
            "file_name": "contrato.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "url": "https://files.example.com/contrato.docx",
        },
    }

    process_whatsapp_message(app, "5571996426565", "", metadata)

    assert recorded["sent"]
    sent_message = recorded["sent"][0][1]
    assert "Tipo de arquivo ainda nao suportado" in sent_message
    assert "PDF, XML, PNG, JPG, JPEG, WEBP, HEIC" in sent_message


def test_handle_instagram_uses_menu_intercept_and_logs_messages(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(whatsapp_webhook_bp, url_prefix="/webhook")

    recorded = {"added": [], "sent": []}

    class DummyUser:
        id = 7

    class DummyMessage:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class DummyMenuResult:
        handled = True
        response_text = "*Menu operacional*\n\n1 - Resumo"
        metadata = {"workflow_code": "1"}
        override_message = None

    monkeypatch.setattr('src.intelligence.identity.resolve_user_identity', lambda contact, channel: DummyUser())
    monkeypatch.setattr('src.intelligence.identity.get_best_company_id', lambda user: 9)
    monkeypatch.setattr('src.intelligence.menu_engine.handle_menu_message', lambda **kwargs: DummyMenuResult())
    monkeypatch.setattr('src.intelligence.execution._capture_workflow_usage_from_execution', lambda **kwargs: recorded.setdefault('usage', []).append(kwargs))
    monkeypatch.setattr('services.instagram_service.instagram_service.send_message', lambda recipient, message: recorded['sent'].append((recipient, message)) or True)
    monkeypatch.setattr('models.agent_message.AgentMessage', DummyMessage)
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.add', lambda obj: recorded['added'].append(obj))
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.commit', lambda: recorded.setdefault('committed', True))
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.rollback', lambda: recorded.setdefault('rolled_back', True))

    client = app.test_client()
    response = client.post('/webhook/instagram', json={
        'sender_id': 'ig-user-1',
        'message': 'menu',
    })

    assert response.status_code == 200
    assert response.get_json()['status'] == 'success'
    assert recorded['sent'][0][0] == 'ig-user-1'
    assert 'Menu operacional' in recorded['sent'][0][1]
    assert len(recorded['added']) == 2
    assert recorded['usage'][0]['channel'] == 'instagram'


def test_handle_instagram_sends_operational_error_message(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(whatsapp_webhook_bp, url_prefix="/webhook")

    recorded = {"sent": []}

    class DummyUser:
        id = 7

    monkeypatch.setattr('src.intelligence.identity.resolve_user_identity', lambda contact, channel: DummyUser())
    monkeypatch.setattr('src.intelligence.identity.get_best_company_id', lambda user: 9)
    monkeypatch.setattr('src.intelligence.menu_engine.handle_menu_message', lambda **kwargs: None)
    monkeypatch.setattr('src.intelligence.execution.run_agent_with_context', lambda **kwargs: (_ for _ in ()).throw(RuntimeError('boom')))
    monkeypatch.setattr('services.instagram_service.instagram_service.send_message', lambda recipient, message: recorded['sent'].append((recipient, message)) or True)
    monkeypatch.setattr('api.webhooks.whatsapp_webhook.db.session.rollback', lambda: recorded.setdefault('rolled_back', True))

    client = app.test_client()
    response = client.post('/webhook/instagram', json={
        'sender_id': 'ig-user-2',
        'message': 'oi',
    })

    assert response.status_code == 200
    assert response.get_json()['status'] == 'error'
    assert recorded['rolled_back'] is True
    assert recorded['sent']
    assert 'Nao foi possivel concluir a solicitacao' in recorded['sent'][0][1]
