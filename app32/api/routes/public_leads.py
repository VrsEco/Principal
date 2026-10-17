"""Endpoint público de captação de leads dos sites da Versus (sem credencial no navegador)."""

import json
import logging

from flask import Blueprint, current_app, jsonify, make_response, request

from models import db
from services import site_lead_service as leads
from utils.security import consume_rate_limit, get_request_ip

public_leads_bp = Blueprint("public_leads", __name__)
logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 4096


def _allowed_origins() -> set[str]:
    return {o.strip().rstrip("/").lower() for o in (current_app.config.get("LEADS_ALLOWED_ORIGINS") or []) if o.strip()}


# Status em que o nginx (add_header sem "always") já acrescenta Access-Control-Allow-Origin.
_PROXY_CORS_STATUSES = {200, 201, 204, 206, 301, 302, 303, 304, 307, 308}


def _respond(body: dict, status: int, origin: str | None = None):
    response = make_response(jsonify(body), status)
    # Com LEADS_EMIT_CORS_ORIGIN=false o proxy envia o cabeçalho nos status que ele cobre;
    # enviar aqui também duplicaria e o navegador rejeitaria. Nos demais (202, 4xx, 503) o
    # proxy não envia, então o Flask precisa enviar para o site conseguir ler a resposta.
    proxy_adds = (not current_app.config.get("LEADS_EMIT_CORS_ORIGIN", True)) and status in _PROXY_CORS_STATUSES
    if origin and not proxy_adds:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    response.headers["Cache-Control"] = "no-store"
    return response


def _reject(event: str, message: str, status: int, origin: str | None = None):
    leads.count(f"rejected_{event}")
    return _respond({"error": message}, status, origin)


@public_leads_bp.route("/public/leads", methods=["POST", "OPTIONS"])
def submit_lead():
    config = current_app.config
    allowed = _allowed_origins()
    sources = leads.load_sources(config)
    if not allowed or not sources or not config.get("LEADS_PRIVACY_POLICY_VERSION"):
        return _reject("unconfigured", "Serviço indisponível", 503)

    origin_header = (request.headers.get("Origin") or "").rstrip("/")
    if origin_header and origin_header.lower() not in allowed:
        return _reject("origin", "Origem não permitida", 403)
    origin = origin_header or None

    if request.method == "OPTIONS":
        response = _respond({}, 204, origin)
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Max-Age"] = "600"
        return response

    if config.get("LEADS_REQUIRE_HTTPS", True) and not config.get("TESTING") and not request.is_secure:
        return _reject("https", "HTTPS obrigatório", 400, origin)

    ip = get_request_ip()
    if not consume_rate_limit("leads.ip", ip, limit=config.get("LEADS_RATE_LIMIT_IP", 10), window_seconds=60):
        return _reject("rate_ip", "Muitas solicitações", 429, origin)

    if request.mimetype != "application/json":
        return _reject("content_type", "Content-Type deve ser application/json", 400, origin)
    if (request.content_length or 0) > MAX_BODY_BYTES:
        return _reject("size", "Corpo muito grande", 413, origin)
    raw = request.get_data(cache=True)
    if len(raw) > MAX_BODY_BYTES:
        return _reject("size", "Corpo muito grande", 413, origin)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return _reject("json", "JSON inválido", 400, origin)

    source = payload.get("source") if isinstance(payload, dict) else None
    source_cfg = sources.get(source) if isinstance(source, str) else None
    if not source_cfg:
        return _reject("source", "source inválido", 400, origin)

    if not consume_rate_limit("leads.source", source, limit=config.get("LEADS_RATE_LIMIT_SOURCE", 120), window_seconds=60):
        return _reject("rate_source", "Muitas solicitações", 429, origin)

    try:
        data = leads.validate_payload(payload, source_cfg)
    except leads.LeadValidationError as exc:
        return _reject("validation", str(exc), 400, origin)

    try:
        lead_id, duplicate = leads.SiteLeadService.create_lead(source=source, source_cfg=source_cfg, data=data, ip=ip)
    except Exception:
        db.session.rollback()
        logger.exception("site_lead persist_error source=%s", source)
        leads.count("failed_persist")
        return _respond({"error": "Falha temporária"}, 503, origin)

    leads.count("duplicate" if duplicate else "created")
    if data["redacted"]:
        leads.count("redacted")
    return _respond({"lead_id": lead_id}, 200 if duplicate else 202, origin)
