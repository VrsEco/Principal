import logging
import re
from threading import Thread
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, request, jsonify, current_app

from services.whatsapp_service import whatsapp_service
from services.instagram_service import instagram_service
from models import db

whatsapp_webhook_bp = Blueprint('whatsapp_webhook', __name__)
logger = logging.getLogger(__name__)


def _first_non_empty_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "sim", "on"}:
            return True
        if normalized in {"false", "0", "no", "nao", "off"}:
            return False
    return None


def _normalize_phone(raw: Any) -> str:
    if raw is None:
        return ""

    text = str(raw).strip()
    if not text:
        return ""

    # Ex.: 5511999999999@c.us
    if "@" in text:
        text = text.split("@", 1)[0]

    digits = re.sub(r"\D", "", text)
    return digits or ""


def _extract_phone(payload: Dict[str, Any]) -> str:
    possible_fields = (
        "phone",
        "from",
        "sender",
        "senderPhone",
        "chatId",
        "chatLid",
        "jid",
        "participant",
        "author",
    )

    for key in possible_fields:
        value = payload.get(key)
        if isinstance(value, dict):
            value = value.get("phone") or value.get("id") or value.get("from")

        normalized = _normalize_phone(value)
        if normalized:
            return normalized

    return ""


def _extract_message_text(payload: Dict[str, Any]) -> str:
    text_block = payload.get("text")
    if isinstance(text_block, dict):
        extracted = _first_non_empty_text(
            text_block.get("message"),
            text_block.get("body"),
            text_block.get("text"),
            text_block.get("caption"),
        )
        if extracted:
            return extracted
    elif isinstance(text_block, str):
        extracted = _first_non_empty_text(text_block)
        if extracted:
            return extracted

    content = payload.get("content")
    if isinstance(content, dict):
        extracted = _first_non_empty_text(
            content.get("text"),
            content.get("body"),
            content.get("caption"),
        )
        if extracted:
            return extracted

    return _first_non_empty_text(
        payload.get("message"),
        payload.get("body"),
        payload.get("caption"),
        payload.get("value"),
    )


def _extract_whatsapp_message(data: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    # Alguns provedores enviam o conteúdo dentro de "data".
    nested = data.get("data") if isinstance(data.get("data"), dict) else {}
    merged: Dict[str, Any] = {**data, **nested}

    from_me = _coerce_bool(
        merged.get("fromMe")
        if merged.get("fromMe") is not None
        else merged.get("from_me")
    )
    if from_me is None:
        from_me = _coerce_bool(
            merged.get("fromApi")
            if merged.get("fromApi") is not None
            else merged.get("from_api")
        )

    is_group = _coerce_bool(
        merged.get("isGroup")
        if merged.get("isGroup") is not None
        else merged.get("is_group")
    )

    if from_me is True:
        return "", "", {"ignored": "self_message"}

    if is_group is True:
        return "", "", {"ignored": "group_message"}

    phone = _extract_phone(merged)
    message_text = _extract_message_text(merged)

    metadata = {
        "event_type": _first_non_empty_text(str(merged.get("type") or "")),
        "message_id": _first_non_empty_text(str(merged.get("messageId") or merged.get("message_id") or "")),
        "instance_id": _first_non_empty_text(str(merged.get("instanceId") or merged.get("instance_id") or "")),
        "thread_contact": phone or "unknown",
    }

    return phone, message_text, metadata


def process_whatsapp_message(app, phone: str, message_text: str, metadata: Dict[str, Any]):
    from src.intelligence.identity import resolve_user_identity, get_best_company_id
    from src.intelligence.execution import run_agent_with_context, extract_response_text
    from models.agent_message import AgentMessage

    with app.app_context():
        try:
            logger.info("WHATSAPP INBOUND: From %s | Msg: %s...", phone, (message_text or "")[:80])

            # 1. Resolve identidade (somente users ativos e cadastrados)
            user = resolve_user_identity(phone, "whatsapp")
            if not user:
                logger.warning("WHATSAPP: Telefone %s nao vinculado a nenhum usuario ativo.", phone)
                return

            company_id = get_best_company_id(user)
            if not company_id:
                logger.warning("WHATSAPP: usuario %s sem company_id resolvido.", user.id)
                return

            thread_id = f"wa_{metadata.get('thread_contact') or phone}"

            # 2. Executa o Agente
            response = run_agent_with_context(
                user_id=user.id,
                user_msg=message_text,
                channel="whatsapp",
                thread_prefix="wa",
                thread_id=thread_id,
                company_id=company_id,
                metadata={
                    "phone": phone,
                    "event_type": metadata.get("event_type"),
                    "message_id": metadata.get("message_id"),
                },
            )

            response_text = extract_response_text(response)
            final_agent_name = response.get("next_node") or "sapiens"
            if final_agent_name == "end":
                final_agent_name = "sapiens"
            menu_metadata = dict(response.get("menu_metadata") or {})

            # 3. Auditoria em banco (mesmo padrão de Telegram)
            db.session.add(
                AgentMessage(
                    company_id=company_id,
                    user_id=user.id,
                    agent_type="work_agent_squad",
                    agent_name="Usuário",
                    direction="inbound",
                    channel="whatsapp",
                    content=message_text,
                    metadata_json={
                        "thread_id": thread_id,
                        "contact": "sapiens",
                        "phone": phone,
                        "event_type": metadata.get("event_type"),
                        "message_id": metadata.get("message_id"),
                    },
                )
            )
            db.session.add(
                AgentMessage(
                    company_id=company_id,
                    user_id=user.id,
                    agent_type="work_agent_squad",
                    agent_name=final_agent_name,
                    direction="outbound",
                    channel="whatsapp",
                    content=response_text,
                    metadata_json={
                        "thread_id": thread_id,
                        "contact": "sapiens",
                        "phone": phone,
                        "agent": final_agent_name,
                        **menu_metadata,
                    },
                )
            )
            db.session.commit()

            # 4. Responde de volta via WhatsApp
            if response_text:
                sent_ok = whatsapp_service.send_message(phone, response_text)
                if not sent_ok:
                    logger.error("WHATSAPP: falha ao enviar resposta para %s", phone)

        except Exception as e:
            logger.exception("WHATSAPP WEBHOOK ERROR: %s", str(e))
            db.session.rollback()


@whatsapp_webhook_bp.route('/whatsapp', methods=['POST'])
def handle_whatsapp():
    """
    Webhook para recebimento de mensagens do WhatsApp (Z-API).
    Suporta também Instagram Direct se vier pelo mesmo provedor.
    """
    data = request.get_json(silent=True) or {}
    if not data:
        logger.warning("WHATSAPP WEBHOOK sem JSON. content_type=%s", request.content_type)
        return jsonify({"status": "no data"}), 200

    phone, message_text, metadata = _extract_whatsapp_message(data)

    ignored_reason = metadata.get("ignored")
    if ignored_reason:
        logger.info("WHATSAPP INBOUND ignorado: reason=%s", ignored_reason)
        return jsonify({"status": ignored_reason}), 200

    if not phone or not message_text:
        logger.warning("WHATSAPP PAYLOAD INVALIDO: keys=%s", list(data.keys()))
        return jsonify({"status": "invalid payload"}), 200

    # Processa em background para reduzir timeout/retries do provedor
    app = current_app._get_current_object()
    t = Thread(target=process_whatsapp_message, args=(app, phone, message_text, metadata))
    t.start()

    return jsonify({"status": "accepted"}), 200

@whatsapp_webhook_bp.route('/instagram', methods=['POST'])
def handle_instagram():
    """Webhook para recebimento de mensagens do Instagram Direct."""
    from src.intelligence.identity import resolve_user_identity, get_best_company_id
    from src.intelligence.execution import run_agent_with_context, extract_response_text

    data = request.json
    if not data:
        return jsonify({"status": "no data"}), 400

    sender_id = None
    message_text = None

    # Payload simples/custom
    sender_id = (
        data.get('sender_id')
        or data.get('instagram_id')
        or data.get('from')
        or (data.get('sender') or {}).get('id')
    )
    message_text = (
        data.get('message')
        or data.get('text')
        or (data.get('text') or {}).get('message')
    )

    # Payload Meta (entry -> messaging)
    if not sender_id or not message_text:
        entry = (data.get('entry') or [])
        if entry and isinstance(entry, list):
            messaging = (entry[0].get('messaging') or [])
            if messaging and isinstance(messaging, list):
                event = messaging[0]
                sender_id = sender_id or ((event.get('sender') or {}).get('id'))
                message_text = message_text or ((event.get('message') or {}).get('text'))

    if not sender_id or not message_text:
        return jsonify({"status": "invalid payload"}), 200

    sender_id = str(sender_id).strip()
    message_text = str(message_text).strip()
    if not sender_id or not message_text:
        return jsonify({"status": "invalid payload"}), 200

    logger.info(f"INSTAGRAM INBOUND: From {sender_id} | Msg: {message_text[:50]}...")

    # 1. Resolve Identidade (somente users ativos e cadastrados)
    user = resolve_user_identity(sender_id, 'instagram')
    if not user:
        logger.warning(f"INSTAGRAM: ID {sender_id} não vinculado a nenhum usuário ativo.")
        return jsonify({"status": "user not found"}), 200

    # 2. Executa o Agente
    try:
        company_id = get_best_company_id(user)
        response = run_agent_with_context(
            user_id=user.id,
            user_msg=message_text,
            channel="instagram",
            thread_prefix="ig",
            company_id=company_id,
            metadata={"instagram_id": sender_id},
        )

        response_text = extract_response_text(response)

        # 3. Envia resposta de volta via Instagram
        if response_text:
            instagram_service.send_message(sender_id, response_text)

        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"INSTAGRAM WEBHOOK ERROR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 200
