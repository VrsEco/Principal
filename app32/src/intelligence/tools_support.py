from __future__ import annotations

import os
import re
import unicodedata

from models import db
from src.intelligence.tool_context import (
    active_company_id_ctx,
    active_user_id_ctx,
    get_sapiens_context,
)


def get_active_company_id():
    """Recupera o ID da empresa ativa de forma resiliente (@ARQUITETO)."""
    identity = get_sapiens_context()
    if identity.company_id:
        return identity.company_id

    metadata = identity.metadata or {}
    if metadata.get("disable_company_fallback"):
        accessible_company_ids = tuple(metadata.get("accessible_company_ids") or ())
        if len(accessible_company_ids) == 1:
            return accessible_company_ids[0]
        return None

    cid = active_company_id_ctx.get()
    if cid:
        return cid

    env_cid = os.environ.get("ACTIVE_COMPANY_ID")
    if env_cid:
        return int(env_cid)

    try:
        from flask import has_request_context, session

        if has_request_context():
            sess_cid = session.get("active_company_id") or session.get("company_id")
            if sess_cid:
                return sess_cid
    except Exception:
        pass

    uid = get_active_user_id()
    if uid:
        try:
            from models.employee import Employee

            first_emp = Employee.query.filter_by(user_id=uid).first()
            if first_emp:
                return first_emp.company_id
        except Exception:
            pass

    return None


def get_active_user_id():
    """Recupera o ID do usuário logado ou via canal (Telegram/WA/etc) (@ARQUITETO)."""
    identity = get_sapiens_context()
    if identity.user_id:
        return identity.user_id

    uid = active_user_id_ctx.get()
    if uid:
        return uid

    env_uid = os.environ.get("ACTIVE_USER_ID")
    if env_uid:
        return int(env_uid)

    try:
        from flask import has_request_context
        from flask_login import current_user

        if has_request_context() and current_user and getattr(current_user, "is_authenticated", False):
            return current_user.id
    except Exception:
        pass

    return None


def get_active_user():
    """Recupera o objeto User do banco de dados baseado no contexto ativo."""
    uid = get_active_user_id()
    if uid:
        from models.user import User

        return db.session.get(User, uid)
    return None


def sanitize_output(data):
    """Sanitiza strings para evitar erros de encoding no terminal Windows (Gold Rule)."""
    if isinstance(data, str):
        return data.encode("ascii", "ignore").decode("ascii")
    return data


def _normalize_company_text(value: str) -> str:
    text_value = (value or "").strip().lower()
    text_value = unicodedata.normalize("NFKD", text_value)
    text_value = "".join(ch for ch in text_value if not unicodedata.combining(ch))
    text_value = re.sub(r"[^a-z0-9]+", " ", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def _rank_companies_by_term(companies, search_term: str):
    if not search_term:
        return list(companies)

    search_norm = _normalize_company_text(search_term)
    if not search_norm:
        return list(companies)

    search_tokens = [t for t in search_norm.split(" ") if len(t) >= 2]
    ranked = []

    for company in companies:
        code_norm = _normalize_company_text(company.client_code or "")
        name_norm = _normalize_company_text(company.name or "")
        legal_norm = _normalize_company_text(getattr(company, "legal_name", "") or "")
        haystack = _normalize_company_text(f"{code_norm} {name_norm} {legal_norm}")

        score = 0
        if search_norm in haystack:
            score += 6
        if code_norm and search_norm == code_norm:
            score += 10
        if name_norm and search_norm == name_norm:
            score += 8
        if code_norm and code_norm in search_tokens:
            score += 4

        if search_tokens:
            token_hits = sum(1 for token in search_tokens if token in haystack)
            coverage = token_hits / len(search_tokens)
            score += int(coverage * 5)
        else:
            coverage = 0

        if score >= 6 or coverage >= 0.75:
            ranked.append((score, company))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked]


def get_meeting_in_active_company(meeting_id: int):
    from models.meeting import Meeting

    company_id = get_active_company_id()
    if not company_id:
        return None, "Erro: Nenhuma empresa ativa identificada."

    meeting = Meeting.query.filter_by(id=meeting_id, company_id=int(company_id)).first()
    if not meeting:
        return None, f"Reunião ID {meeting_id} não encontrada na empresa ativa."

    return meeting, None


def get_project_task_in_active_company(task_id: int):
    from models.project import ProjectTask

    company_id = get_active_company_id()
    if not company_id:
        return None, "Erro: Nenhuma empresa ativa identificada."

    task = ProjectTask.query.filter_by(id=task_id, company_id=int(company_id)).first()
    if not task:
        return None, f"Tarefa de projeto ID {task_id} não encontrada na empresa ativa."

    return task, None


def get_process_instance_in_active_company(instance_id: int):
    from models.process import ProcessInstance

    company_id = get_active_company_id()
    if not company_id:
        return None, "Erro: Nenhuma empresa ativa identificada."

    instance = ProcessInstance.query.filter_by(id=instance_id, company_id=int(company_id)).first()
    if not instance:
        return None, f"Instância de processo ID {instance_id} não encontrada na empresa ativa."

    return instance, None
