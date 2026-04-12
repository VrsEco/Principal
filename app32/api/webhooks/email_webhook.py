import logging
import os

from flask import Blueprint, jsonify, request

from services.email_service import email_service
from src.intelligence.email_monitor import process_incoming_email

email_webhook_bp = Blueprint("email_webhook", __name__)
logger = logging.getLogger(__name__)


def _first_non_empty(*values):
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


@email_webhook_bp.route("/email", methods=["POST"])
def handle_email_webhook():
    """
    Webhook genérico para entrada de e-mails.
    Formatos suportados:
      - from / sender / sender_email
      - subject
      - body / text / plain
    """
    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({"success": False, "error": "Payload vazio"}), 400

    sender = _first_non_empty(
        payload.get("from"),
        payload.get("sender"),
        payload.get("sender_email"),
    )
    subject = _first_non_empty(payload.get("subject"))
    body = _first_non_empty(
        payload.get("body"),
        payload.get("text"),
        payload.get("plain"),
        payload.get("message"),
    )

    if not sender or not body:
        logger.warning("EMAIL WEBHOOK payload inválido: sender/body ausentes")
        return jsonify({"success": False, "error": "sender/body obrigatórios"}), 200

    logger.info("EMAIL INBOUND webhook: from=%s subject=%s", sender, subject[:120])

    response_text = process_incoming_email(sender, subject, body)
    if not response_text:
        # Remetente não vinculado ou erro interno.
        return jsonify({"success": True, "status": "ignored"}), 200

    auto_reply = os.environ.get("EMAIL_AUTO_REPLY", "false").strip().lower() == "true"
    if auto_reply:
        reply_subject = f"Re: {subject}" if subject else "Resposta automática"
        sent = email_service.send_email([sender], reply_subject, response_text)
        return jsonify(
            {
                "success": True,
                "status": "processed",
                "auto_reply": bool(sent),
            }
        ), 200

    return jsonify({"success": True, "status": "processed", "auto_reply": False}), 200
