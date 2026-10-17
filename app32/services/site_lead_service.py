"""Captação de leads de sites públicos: validação, antispam, LGPD e persistência."""

import hashlib
import hmac
import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from flask import current_app

from models import db
from models.site_lead import SiteLead

logger = logging.getLogger(__name__)

DEFAULT_ASSUNTOS = ("orcamento", "duvida", "parceria", "suporte", "outro")
ALLOWED_FIELDS = {"source", "nome", "assunto", "relato", "consent", "origin", "page", "ts"}
ORIGIN_FIELDS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "referrer", "landing")
REDACTED = "[removido]"

_CPF_RE = re.compile(r"(?<!\d)\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}(?!\d)")
_CNPJ_RE = re.compile(r"(?<!\d)\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2}(?!\d)")
_SECRET_RE = re.compile(r"(?i)\b(senha|password|passwd|pwd|token|cvv)\b\s*[:=]?\s*\S+")
_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)")

_COUNTERS: dict[str, int] = {}


def count(event: str) -> None:
    """Contador em memória por processo + log estruturado (sem nome nem relato)."""
    _COUNTERS[event] = _COUNTERS.get(event, 0) + 1
    logger.info("site_lead event=%s total=%s", event, _COUNTERS[event])


def counters() -> dict[str, int]:
    return dict(_COUNTERS)


class LeadValidationError(ValueError):
    pass


def load_sources(config: dict) -> dict[str, dict[str, Any]]:
    raw = config.get("LEADS_SOURCES_JSON") or ""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        logger.error("site_lead LEADS_SOURCES_JSON inválido")
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(key): value
        for key, value in data.items()
        if isinstance(value, dict) and isinstance(value.get("company_id"), int)
    }


def redact_sensitive(text: str) -> tuple[str, bool]:
    result = text
    for pattern in (_SECRET_RE, _CNPJ_RE, _CPF_RE, _CARD_RE):
        result = pattern.sub(REDACTED, result)
    return result, result != text


def _clean_text(value: Any, field: str, max_len: int, *, required: bool = False) -> str | None:
    if value is None or value == "":
        if required:
            raise LeadValidationError(f"{field} é obrigatório")
        return None
    if not isinstance(value, str):
        raise LeadValidationError(f"{field} inválido")
    cleaned = "".join(ch for ch in value if ch == "\n" or ch >= " ").strip()
    if len(cleaned) > max_len:
        raise LeadValidationError(f"{field} excede {max_len} caracteres")
    if required and not cleaned:
        raise LeadValidationError(f"{field} é obrigatório")
    return cleaned or None


def _clean_path(value: Any, field: str) -> str | None:
    text = _clean_text(value, field, 300)
    if text and not text.startswith("/"):
        raise LeadValidationError(f"{field} deve ser um caminho iniciado por /")
    return text


def _referrer_host(value: Any) -> str | None:
    text = _clean_text(value, "origin.referrer", 255)
    if not text:
        return None
    host = urlparse(text if "//" in text else f"//{text}").hostname
    return (host or text.split("/")[0])[:255].lower() or None


def validate_payload(payload: Any, source_cfg: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise LeadValidationError("corpo deve ser um objeto JSON")
    if set(payload) - ALLOWED_FIELDS:
        raise LeadValidationError("campos não permitidos")
    if payload.get("consent") is not True:
        raise LeadValidationError("consentimento é obrigatório")

    assuntos = tuple(source_cfg.get("assuntos") or DEFAULT_ASSUNTOS)
    assunto = _clean_text(payload.get("assunto"), "assunto", 60, required=True)
    if assunto not in assuntos:
        raise LeadValidationError("assunto fora da lista permitida")

    nome = _clean_text(payload.get("nome"), "nome", 80)
    relato = _clean_text(payload.get("relato"), "relato", 600)
    redacted = False
    if relato:
        relato, redacted = redact_sensitive(relato)
    if nome:
        nome, nome_redacted = redact_sensitive(nome)
        redacted = redacted or nome_redacted

    origin = payload.get("origin") or {}
    if not isinstance(origin, dict) or set(origin) - set(ORIGIN_FIELDS):
        raise LeadValidationError("origin inválido")
    cleaned_origin = {key: _clean_text(origin.get(key), f"origin.{key}", 120) for key in ORIGIN_FIELDS[:5]}

    client_ts = None
    if payload.get("ts"):
        try:
            client_ts = datetime.fromisoformat(str(payload["ts"]).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            raise LeadValidationError("ts inválido")

    return {
        "nome": nome,
        "assunto": assunto,
        "relato": relato,
        "origin": cleaned_origin,
        "referrer_host": _referrer_host(origin.get("referrer")),
        "landing": _clean_path(origin.get("landing"), "origin.landing"),
        "page": _clean_path(payload.get("page"), "page"),
        "client_ts": client_ts,
        "redacted": redacted,
    }


def dedupe_hash(source: str, data: dict[str, Any]) -> str:
    origin = data["origin"]
    parts = [source, data["nome"] or "", data["assunto"], data["relato"] or ""]
    parts += [origin.get(key) or "" for key in ORIGIN_FIELDS[:5]] + [data["referrer_host"] or ""]
    return hashlib.sha256("\x1f".join(p.strip().lower() for p in parts).encode("utf-8")).hexdigest()


def hash_ip(ip: str) -> str:
    salt = current_app.config.get("LEADS_IP_HASH_SALT") or current_app.config.get("SECRET_KEY") or ""
    return hmac.new(salt.encode("utf-8"), (ip or "").encode("utf-8"), hashlib.sha256).hexdigest()


class SiteLeadService:
    @staticmethod
    def create_lead(*, source: str, source_cfg: dict[str, Any], data: dict[str, Any], ip: str) -> tuple[str, bool]:
        """Retorna (lead_id, duplicado). Dedupe por (empresa, hash) numa janela curta."""
        company_id = int(source_cfg["company_id"])
        digest = dedupe_hash(source, data)
        window = int(current_app.config.get("LEADS_DEDUPE_WINDOW_SECONDS") or 600)
        existing = (
            SiteLead.query.filter(
                SiteLead.company_id == company_id,
                SiteLead.dedupe_hash == digest,
                SiteLead.created_at >= datetime.utcnow() - timedelta(seconds=window),
            )
            .order_by(SiteLead.created_at.desc())
            .first()
        )
        if existing:
            return existing.id, True

        origin = data["origin"]
        lead = SiteLead(
            company_id=company_id,
            source=source,
            nome=data["nome"],
            assunto=data["assunto"],
            relato=data["relato"],
            utm_source=origin["utm_source"],
            utm_medium=origin["utm_medium"],
            utm_campaign=origin["utm_campaign"],
            utm_content=origin["utm_content"],
            utm_term=origin["utm_term"],
            referrer_host=data["referrer_host"],
            landing=data["landing"],
            page=data["page"],
            client_ts=data["client_ts"],
            consent_at=datetime.utcnow(),
            privacy_policy_version=current_app.config.get("LEADS_PRIVACY_POLICY_VERSION"),
            ip_hash=hash_ip(ip),
            dedupe_hash=digest,
        )
        db.session.add(lead)
        db.session.commit()
        # A tarefa vem depois do commit do lead: create_project_task comita por conta própria e,
        # dentro de begin_nested, fechava a transação e a tarefa nunca era ligada ao lead.
        task_id = SiteLeadService._create_owner_task(lead, source_cfg)
        if task_id:
            lead.project_task_id = task_id
            db.session.commit()
        return lead.id, False

    @staticmethod
    def _task_notes(lead: SiteLead) -> str:
        return (
            f"lead_id={lead.id}\nOrigem: {lead.utm_source or 'direto'}/{lead.utm_medium or '-'}"
            f"/{lead.utm_campaign or '-'}\nPágina: {lead.page or '-'}\nNome: {lead.nome or '-'}\n"
            f"Relato: {lead.relato or '-'}"
        )

    @staticmethod
    def next_business_day(today: date | None = None) -> date:
        """Prazo padrão da tarefa do lead: 1 dia útil (segunda a sexta, sem feriados) em America/Bahia (UTC-3)."""
        base = today or (datetime.utcnow() - timedelta(hours=3)).date()
        due = base + timedelta(days=1)
        while due.weekday() >= 5:
            due += timedelta(days=1)
        return due

    @staticmethod
    def _task_kwargs(lead: SiteLead, source_cfg: dict[str, Any], today: date | None = None) -> dict[str, Any]:
        return {
            "company_id": lead.company_id,
            "user_id": int(source_cfg["task_user_id"]),
            "project_code": str(source_cfg["project_code"]),
            "task_name": f"Lead novo: {lead.assunto}",
            "notes": SiteLeadService._task_notes(lead),
            "idempotency_key": f"site_lead:{lead.id}",
            "due_date": SiteLeadService.next_business_day(today).isoformat(),
        }

    @staticmethod
    def _create_owner_task(lead: SiteLead, source_cfg: dict[str, Any]) -> int | None:
        """Tarefa 'novo' no projeto do dono; falha aqui nunca derruba o registro do lead."""
        project_code = source_cfg.get("project_code")
        user_id = source_cfg.get("task_user_id")
        if not project_code or not user_id:
            return None
        try:
            from services.project_task_mcp_service import ProjectTaskMCPService

            result, error = ProjectTaskMCPService.create_task(**SiteLeadService._task_kwargs(lead, source_cfg))
            if error or not result:
                logger.warning("site_lead task_not_created lead=%s error=%s", lead.id, error or "sem resultado")
                return None
            return int(result["task"]["id"])
        except Exception:
            db.session.rollback()
            logger.exception("site_lead task_error lead=%s", lead.id)
            return None

    @staticmethod
    def erase(*, company_id: int, lead_id: str) -> bool:
        """Exclusão LGPD: anula dados pessoais e mantém a contagem agregada por canal."""
        lead = SiteLead.query.filter_by(id=lead_id, company_id=company_id).first()
        if not lead or lead.erased_at:
            return False
        lead.nome = None
        lead.relato = None
        lead.ip_hash = None
        lead.dedupe_hash = hashlib.sha256(lead.id.encode("utf-8")).hexdigest()
        lead.erased_at = datetime.utcnow()
        if lead.project_task_id:
            from models.project import ProjectTask

            task = db.session.get(ProjectTask, lead.project_task_id)
            if task:
                task.notes = f"lead_id={lead.id} (dados pessoais excluídos sob solicitação)"
        db.session.commit()
        return True
