import json
import logging
import mimetypes
import os
import re
from threading import Thread
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests
from flask import Blueprint, request, jsonify, current_app

from services.whatsapp_service import whatsapp_service
from services.instagram_service import instagram_service
from models import db
from utils.integration_settings import resolve_webhook_secret
from utils.security import consume_rate_limit, get_request_ip, webhook_secret_verified

whatsapp_webhook_bp = Blueprint('whatsapp_webhook', __name__)
logger = logging.getLogger(__name__)
PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."
SUPPORTED_FINANCIAL_ATTACHMENT_EXTENSIONS = {".pdf", ".xml", ".png", ".jpg", ".jpeg", ".webp", ".heic"}



def _append_request_debug_log(message: str) -> None:
    try:
        root_path = current_app.root_path if current_app else os.getcwd()
        log_path = os.path.join(root_path, "request_debug.log")
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(f"{message}\n")
    except Exception:
        logger.debug("Falha ao escrever em request_debug.log", exc_info=True)


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
    message_data = payload.get("messageData")
    if isinstance(message_data, dict):
        text_message_data = message_data.get("textMessageData")
        if isinstance(text_message_data, dict):
            extracted = _first_non_empty_text(
                text_message_data.get("textMessage"),
                text_message_data.get("text"),
            )
            if extracted:
                return extracted

        extended_text_data = message_data.get("extendedTextMessageData")
        if isinstance(extended_text_data, dict):
            extracted = _first_non_empty_text(
                extended_text_data.get("text"),
                extended_text_data.get("description"),
            )
            if extracted:
                return extracted

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
        payload.get("conversation"),
        payload.get("message"),
        payload.get("body"),
        payload.get("caption"),
        payload.get("value"),
    )


def _extract_attachment_candidate(candidate: Dict[str, Any], media_kind: str) -> Dict[str, Any]:
    url = _first_non_empty_text(
        candidate.get("url"),
        candidate.get("directUrl"),
        candidate.get("direct_url"),
        candidate.get("downloadUrl"),
        candidate.get("download_url"),
        candidate.get("fileUrl"),
        candidate.get("file_url"),
        candidate.get("mediaUrl"),
        candidate.get("media_url"),
        candidate.get("documentUrl"),
        candidate.get("document_url"),
        candidate.get("link"),
    )
    file_name = _first_non_empty_text(
        candidate.get("fileName"),
        candidate.get("filename"),
        candidate.get("name"),
        candidate.get("title"),
    )
    mime_type = _first_non_empty_text(
        candidate.get("mimeType"),
        candidate.get("mimetype"),
        candidate.get("contentType"),
        candidate.get("content_type"),
    )
    if not url and not file_name:
        return {}

    if not file_name and url:
        parsed = urlparse(url)
        file_name = os.path.basename(parsed.path or "") or f"arquivo_{media_kind or 'media'}"
    extension = os.path.splitext(file_name)[1].lower() if file_name else ""
    if not mime_type and extension:
        mime_type = mimetypes.guess_type(file_name)[0] or ""

    return {
        "media_kind": media_kind,
        "url": url,
        "file_name": file_name,
        "mime_type": mime_type or None,
        "caption": _first_non_empty_text(candidate.get("caption"), candidate.get("description")),
    }


def _extract_whatsapp_attachment(payload: Dict[str, Any]) -> Dict[str, Any]:
    candidate_specs = [
        ("document", payload.get("document")),
        ("image", payload.get("image")),
        ("file", payload.get("file")),
        ("media", payload.get("media")),
    ]

    message_data = payload.get("messageData")
    if isinstance(message_data, dict):
        candidate_specs.extend(
            [
                ("document", message_data.get("documentMessageData")),
                ("image", message_data.get("imageMessageData")),
                ("file", message_data.get("fileMessageData")),
                ("media", message_data.get("mediaData")),
            ]
        )

    for media_kind, candidate in candidate_specs:
        if not isinstance(candidate, dict):
            continue
        extracted = _extract_attachment_candidate(candidate, media_kind)
        if extracted.get("url") or extracted.get("file_name"):
            return extracted

    fallback = _extract_attachment_candidate(payload, "media")
    return fallback if fallback.get("url") or fallback.get("file_name") else {}


def _is_supported_financial_attachment(attachment: Dict[str, Any]) -> bool:
    if not attachment:
        return False
    file_name = str(attachment.get("file_name") or "").strip()
    mime_type = str(attachment.get("mime_type") or "").strip().lower()
    extension = os.path.splitext(file_name)[1].lower()
    if extension in SUPPORTED_FINANCIAL_ATTACHMENT_EXTENSIONS:
        return True
    if mime_type.startswith("image/"):
        return True
    return mime_type in {"application/pdf", "text/xml", "application/xml"}


def _download_attachment_bytes(attachment: Dict[str, Any]) -> Tuple[Optional[bytes], Optional[str]]:
    url = str(attachment.get("url") or "").strip()
    if not url:
        return None, "Arquivo sem URL de download no provedor do WhatsApp."
    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            return None, f"Download do arquivo falhou com HTTP {response.status_code}."
        file_bytes = response.content or b""
        if not file_bytes:
            return None, "O provedor retornou o arquivo vazio."
        return file_bytes, None
    except Exception as exc:
        logger.exception("Falha ao baixar anexo do WhatsApp")
        return None, f"Não foi possível baixar o anexo do provedor: {exc}"


def _parse_possible_json_object(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}

    raw = value.strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _load_whatsapp_request_payload() -> Dict[str, Any]:
    json_payload = request.get_json(silent=True)
    if isinstance(json_payload, dict) and json_payload:
        return json_payload

    form_payload = request.form.to_dict(flat=True)
    if form_payload:
        for candidate_key in ("payload", "data", "body", "message", "json"):
            parsed = _parse_possible_json_object(form_payload.get(candidate_key))
            if parsed:
                merged = dict(form_payload)
                merged.pop(candidate_key, None)
                merged.update(parsed)
                return merged
        return form_payload

    raw_body = (request.get_data(cache=True, as_text=True) or "").strip()
    parsed = _parse_possible_json_object(raw_body)
    if parsed:
        return parsed

    return {}


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
    attachment = _extract_whatsapp_attachment(merged)
    if not message_text and attachment.get("caption"):
        message_text = str(attachment.get("caption") or "").strip()

    metadata = {
        "event_type": _first_non_empty_text(str(merged.get("type") or "")),
        "message_id": _first_non_empty_text(str(merged.get("messageId") or merged.get("message_id") or "")),
        "instance_id": _first_non_empty_text(str(merged.get("instanceId") or merged.get("instance_id") or "")),
        "thread_contact": phone or "unknown",
        "attachment": attachment if attachment else None,
    }

    return phone, message_text, metadata


def _normalize_text_basic(value: str) -> str:
    return (value or "").strip().lower()


def _personalize_whatsapp_greeting(text: str, user_name: Any) -> str:
    message = str(text or "").strip()
    if not message:
        return message

    first_name = str(user_name or "").strip().split(" ")[0]
    if not first_name:
        return message

    normalized = _normalize_text_basic(message)
    generic_greetings = {
        "olá! como posso ajudar você hoje?",
        "ola! como posso ajudar você hoje?",
        "olá! como posso ajudar voce hoje?",
        "ola! como posso ajudar voce hoje?",
        "olá! como posso te ajudar?",
        "ola! como posso te ajudar?",
    }
    is_generic_greeting = normalized in generic_greetings
    if not is_generic_greeting:
        starts_with_greeting = normalized.startswith(("olá!", "ola!", "olá ", "ola "))
        has_help_intent = any(
            phrase in normalized
            for phrase in (
                "como posso",
                "em que posso",
                "posso ajudar",
                "posso te ajudar",
                "ser útil para você hoje",
                "ser util para voce hoje",
            )
        )
        is_generic_greeting = starts_with_greeting and has_help_intent

    if not is_generic_greeting:
        return message

    return f"Olá {first_name}! Como posso te ajudar?"


def _is_menu_like_message(text: str) -> bool:
    lower = _normalize_text_basic(text)
    if not lower:
        return False
    return (
        lower == "menu"
        or lower.startswith("menu ")
        or lower == "/menu"
        or lower.startswith("/menu ")
    )


def _fallback_root_menu(company_id, channel: str = "whatsapp") -> str:
    try:
        from src.intelligence.menu_engine import list_menu_options
        from src.intelligence.workflows.presenters import build_root_menu_message

        roots = list_menu_options(
            company_id=company_id,
            parent_code=None,
            include_inactive=False,
            include_global=True,
        )
        return build_root_menu_message(
            [f"{opt.code} - {opt.title}" for opt in roots],
            channel=channel,
        )
    except Exception as exc:
        logger.exception("Falha ao montar menu fallback no canal %s: %s", channel, exc)
        from src.intelligence.workflows.presenters import build_menu_recovery_message
        return build_menu_recovery_message(channel=channel)


def process_whatsapp_message(app, phone: str, message_text: str, metadata: Dict[str, Any]):
    from src.intelligence.identity import resolve_user_identity, get_best_company_id
    from src.intelligence.execution import (
        _capture_workflow_usage_from_execution,
        run_agent_with_context,
        extract_response_text,
    )
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
            attachment = dict(metadata.get("attachment") or {})
            inbound_content = message_text or (f"[arquivo] {attachment.get('file_name')}" if attachment else "")

            try:
                from services.proactive_service import try_handle_summary_followup

                handled_followup, followup_response = try_handle_summary_followup(
                    user=user,
                    company_id=company_id,
                    incoming_text=message_text,
                    channel="whatsapp",
                )
            except Exception as followup_err:
                logger.exception("Falha ao processar follow-up do resumo no WhatsApp: %s", followup_err)
                handled_followup, followup_response = False, None

            if handled_followup and followup_response:
                db.session.add(
                    AgentMessage(
                        company_id=company_id,
                        user_id=user.id,
                        agent_type="work_agent_squad",
                        agent_name="Usuário",
                        direction="inbound",
                        channel="whatsapp",
                        content=inbound_content,
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
                        agent_name="sapiens",
                        direction="outbound",
                        channel="whatsapp",
                        content=followup_response,
                        metadata_json={
                            "thread_id": thread_id,
                            "contact": "sapiens",
                            "phone": phone,
                            "flow": "summary_followup",
                        },
                    )
                )
                db.session.commit()

                sent_ok = whatsapp_service.send_message(phone, followup_response)
                if not sent_ok:
                    logger.error("WHATSAPP: falha ao enviar follow-up do resumo para %s", phone)
                return

            response_text = ""
            final_agent_name = "sapiens"
            menu_metadata: Dict[str, Any] = {}

            if attachment and _is_supported_financial_attachment(attachment):
                from src.intelligence.menu_engine import start_channel_workflow

                file_bytes, download_error = _download_attachment_bytes(attachment)
                if download_error:
                    response_text = f"Recebi o arquivo, mas não consegui baixá-lo do provedor: {download_error}"
                else:
                    workflow_result = start_channel_workflow(
                        user_id=user.id,
                        company_id=company_id,
                        channel="whatsapp",
                        thread_id=thread_id,
                        workflow_code="361",
                        user_message=message_text or str(attachment.get("file_name") or "recibo"),
                        payload={
                            "_attachment": {
                                **attachment,
                                "file_bytes": file_bytes,
                            },
                            "_channel_label": "WhatsApp",
                            "_source_label": f"WhatsApp - {attachment.get('file_name') or 'recibo'}",
                        },
                    )
                    if workflow_result and workflow_result.handled:
                        response_text = workflow_result.response_text or ""
                        menu_metadata = dict(workflow_result.metadata or {})
                        _capture_workflow_usage_from_execution(
                            user_id=user.id,
                            company_id=company_id,
                            channel="whatsapp",
                            thread_id=thread_id,
                            user_msg=inbound_content,
                            response_text=response_text,
                            menu_metadata=menu_metadata,
                        )
                    else:
                        response_text = "Recebi o arquivo, mas não consegui iniciar o fluxo financeiro agora."
            else:
                from src.intelligence.menu_engine import handle_menu_message

                menu_like = _is_menu_like_message(message_text)
                menu_result = None
                try:
                    menu_result = handle_menu_message(
                        user_id=user.id,
                        company_id=company_id,
                        channel="whatsapp",
                        thread_id=thread_id,
                        message=message_text,
                    )
                except Exception as menu_err:
                    logger.exception("Erro no handle_menu_message do WhatsApp: %s", menu_err)

                if menu_result and menu_result.handled:
                    response_text = menu_result.response_text or _fallback_root_menu(company_id, channel="whatsapp")
                    menu_metadata = dict(menu_result.metadata or {})
                    _capture_workflow_usage_from_execution(
                        user_id=user.id,
                        company_id=company_id,
                        channel="whatsapp",
                        thread_id=thread_id,
                        user_msg=message_text,
                        response_text=response_text,
                        menu_metadata=menu_metadata,
                    )
                elif menu_like:
                    response_text = _fallback_root_menu(company_id, channel="whatsapp")
                    logger.warning(
                        "MENU FALLBACK FORCADO [WHATSAPP]: user=%s company=%s thread=%s message=%r",
                        user.id, company_id, thread_id, message_text
                    )
                else:
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
                    response_text = _personalize_whatsapp_greeting(response_text, getattr(user, "name", ""))
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
                    content=inbound_content,
                    metadata_json={
                        "thread_id": thread_id,
                        "contact": "sapiens",
                        "phone": phone,
                        "event_type": metadata.get("event_type"),
                        "message_id": metadata.get("message_id"),
                        "attachment": {
                            "file_name": attachment.get("file_name"),
                            "mime_type": attachment.get("mime_type"),
                            "url": attachment.get("url"),
                        } if attachment else None,
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
            try:
                from src.intelligence.workflows.presenters import build_internal_error_message
                whatsapp_service.send_message(phone, build_internal_error_message(channel="whatsapp"))
            except Exception:
                logger.exception("WHATSAPP: falha ao enviar mensagem de erro operacional")


@whatsapp_webhook_bp.route('/whatsapp', methods=['POST'])
def handle_whatsapp():
    """
    Webhook para recebimento de mensagens do WhatsApp (Z-API).
    Suporta também Instagram Direct se vier pelo mesmo provedor.
    """
    if not webhook_secret_verified(
        expected_secret=resolve_webhook_secret("whatsapp"),
        header_names=["X-Webhook-Secret", "X-WhatsApp-Secret", "X-Hub-Signature-256", "X-API-Key"],
        query_names=["secret", "token"],
    ):
        return jsonify({"status": "forbidden"}), 403

    if not consume_rate_limit("webhook.whatsapp", get_request_ip(), limit=120, window_seconds=60):
        return jsonify({"status": "rate_limited"}), 429

    data = _load_whatsapp_request_payload()
    if not data:
        raw_body = (request.get_data(cache=True, as_text=True) or "")[:500]
        logger.warning(
            "WHATSAPP WEBHOOK sem payload interpretavel. content_type=%s raw=%r",
            request.content_type,
            raw_body,
        )
        _append_request_debug_log(
            f"WHATSAPP WEBHOOK sem payload | content_type={request.content_type} | raw={raw_body!r}"
        )
        return jsonify({"status": "no data"}), 200

    phone, message_text, metadata = _extract_whatsapp_message(data)
    has_supported_attachment = _is_supported_financial_attachment(dict(metadata.get("attachment") or {}))

    ignored_reason = metadata.get("ignored")
    if ignored_reason:
        logger.info("WHATSAPP INBOUND ignorado: reason=%s", ignored_reason)
        _append_request_debug_log(
            f"WHATSAPP INBOUND ignorado | reason={ignored_reason} | keys={sorted(data.keys())}"
        )
        return jsonify({"status": ignored_reason}), 200

    if not phone or (not message_text and not has_supported_attachment):
        logger.warning(
            "WHATSAPP PAYLOAD INVALIDO: content_type=%s keys=%s payload=%r",
            request.content_type,
            list(data.keys()),
            {k: data.get(k) for k in list(data.keys())[:12]},
        )
        _append_request_debug_log(
            "WHATSAPP PAYLOAD INVALIDO | "
            f"content_type={request.content_type} | keys={sorted(data.keys())} | payload={data!r}"
        )
        return jsonify({"status": "invalid payload"}), 200

    _append_request_debug_log(
        "WHATSAPP INBOUND aceito | "
        f"content_type={request.content_type} | phone={phone} | event={metadata.get('event_type')} | "
        f"message_id={metadata.get('message_id')}"
    )

    # Processa em background para reduzir timeout/retries do provedor
    app = current_app._get_current_object()
    t = Thread(target=process_whatsapp_message, args=(app, phone, message_text, metadata))
    t.start()

    return jsonify({"status": "accepted"}), 200

@whatsapp_webhook_bp.route('/instagram', methods=['POST'])
def handle_instagram():
    """Webhook para recebimento de mensagens do Instagram Direct."""
    from src.intelligence.identity import resolve_user_identity, get_best_company_id
    from src.intelligence.execution import (
        _capture_workflow_usage_from_execution,
        extract_response_text,
        run_agent_with_context,
    )
    from src.intelligence.menu_engine import handle_menu_message
    from models.agent_message import AgentMessage

    if not webhook_secret_verified(
        expected_secret=resolve_webhook_secret("instagram"),
        header_names=["X-Webhook-Secret", "X-Instagram-Secret", "X-Hub-Signature-256", "X-API-Key"],
        query_names=["secret", "token"],
    ):
        return jsonify({"status": "forbidden"}), 403

    if not consume_rate_limit("webhook.instagram", get_request_ip(), limit=120, window_seconds=60):
        return jsonify({"status": "rate_limited"}), 429

    data = request.json
    if not data:
        return jsonify({"status": "no data"}), 400

    sender_id = None
    message_text = None

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

    user = resolve_user_identity(sender_id, 'instagram')
    if not user:
        logger.warning(f"INSTAGRAM: ID {sender_id} não vinculado a nenhum usuário ativo.")
        return jsonify({"status": "user not found"}), 200

    try:
        company_id = get_best_company_id(user)
        if not company_id:
            logger.warning("INSTAGRAM: usuario %s sem company_id resolvido.", user.id)
            return jsonify({"status": "company not found"}), 200

        thread_id = f"ig_{sender_id}"
        final_agent_name = "sapiens"
        menu_like = _is_menu_like_message(message_text)

        menu_result = None
        try:
            menu_result = handle_menu_message(
                user_id=user.id,
                company_id=company_id,
                channel="instagram",
                thread_id=thread_id,
                message=message_text,
            )
        except Exception as menu_err:
            logger.exception("Erro no handle_menu_message do Instagram: %s", menu_err)

        if menu_result and menu_result.handled:
            response_text = menu_result.response_text or _fallback_root_menu(company_id, channel="instagram")
            menu_metadata = dict(menu_result.metadata or {})
            _capture_workflow_usage_from_execution(
                user_id=user.id,
                company_id=company_id,
                channel="instagram",
                thread_id=thread_id,
                user_msg=message_text,
                response_text=response_text,
                menu_metadata=menu_metadata,
            )
        elif menu_like:
            response_text = _fallback_root_menu(company_id, channel="instagram")
            menu_metadata = {}
        else:
            effective_msg = menu_result.override_message if menu_result and menu_result.override_message else message_text
            response = run_agent_with_context(
                user_id=user.id,
                user_msg=effective_msg,
                channel="instagram",
                thread_prefix="ig",
                thread_id=thread_id,
                company_id=company_id,
                metadata={"instagram_id": sender_id},
            )
            response_text = extract_response_text(response)
            menu_metadata = dict(response.get("menu_metadata") or {})
            final_agent_name = response.get("next_node") or "sapiens"
            if final_agent_name == "end":
                final_agent_name = "sapiens"

        db.session.add(
            AgentMessage(
                company_id=company_id,
                user_id=user.id,
                agent_type="work_agent_squad",
                agent_name="Usuário",
                direction="inbound",
                channel="instagram",
                content=message_text,
                metadata_json={
                    "thread_id": thread_id,
                    "contact": "sapiens",
                    "instagram_id": sender_id,
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
                channel="instagram",
                content=response_text,
                metadata_json={
                    "thread_id": thread_id,
                    "contact": "sapiens",
                    "instagram_id": sender_id,
                    "agent": final_agent_name,
                    **menu_metadata,
                },
            )
        )
        db.session.commit()

        if response_text:
            instagram_service.send_message(sender_id, response_text)

        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"INSTAGRAM WEBHOOK ERROR: {str(e)}")
        db.session.rollback()
        try:
            from src.intelligence.workflows.presenters import build_internal_error_message
            instagram_service.send_message(sender_id, build_internal_error_message(channel="instagram"))
        except Exception:
            logger.exception("INSTAGRAM: falha ao enviar mensagem de erro operacional")
        return jsonify({"status": "error", "message": PUBLIC_ERROR_MESSAGE}), 200
