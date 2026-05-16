from __future__ import annotations

from marshmallow import ValidationError

from models import db
from schemas.company import company_schema
from src.intelligence.tools_support import (
    _rank_companies_by_term,
    get_active_company_id,
    get_active_user,
    get_active_user_id,
    sanitize_output,
)


_EDITABLE_COMPANY_FIELDS = (
    "name",
    "legal_name",
    "cnpj",
    "client_code",
    "description",
    "segment",
    "size",
    "city",
    "state",
    "coverage_physical",
    "coverage_online",
    "experience_total",
    "experience_segment",
    "mission",
    "vision",
    "values",
    "logo_primary",
    "logo_secondary",
    "logo_icon",
)

_DIAGNOSTIC_GROUPS = {
    "identificacao": ("name", "legal_name", "cnpj", "client_code", "is_active"),
    "posicionamento": ("description", "segment", "size"),
    "localizacao": ("city", "state"),
    "cobertura": ("coverage_physical", "coverage_online"),
    "experiencia": ("experience_total", "experience_segment"),
    "mvv": ("mission", "vision", "values"),
    "branding": ("logo_primary", "logo_secondary", "logo_icon"),
}


def _resolve_company_with_access(company_id: int | None = None):
    from models.company import Company
    from utils.permissions import can_access_company, get_access_profile, is_platform_admin

    actor = get_active_user()
    actor_user_id = get_active_user_id()
    if actor is None or actor_user_id is None:
        return None, None, None, "Erro: Usuário não autenticado."

    resolved_company_id = int(company_id) if company_id is not None else get_active_company_id()
    if resolved_company_id is None:
        return None, None, None, "Erro: Nenhuma empresa ativa identificada."

    if not is_platform_admin(user=actor) and not can_access_company(int(resolved_company_id), user=actor):
        return None, None, None, f"Erro: Usuário sem acesso à empresa ID {resolved_company_id}."

    company = Company.query.get(int(resolved_company_id))
    if company is None:
        return None, None, None, f"Erro: Empresa com ID {resolved_company_id} não encontrada."

    access_profile = get_access_profile(int(resolved_company_id), user=actor)
    return company, int(resolved_company_id), access_profile, None


def _company_payload(company, *, access_profile: str | None = None):
    payload = company.to_dict()
    payload["access_profile"] = access_profile
    payload["editable_fields"] = list(_EDITABLE_COMPANY_FIELDS)
    return payload


def update_company_status(company_id: int, is_active: bool, reason: str | None = None):
    """Atualiza o status de atividade de uma empresa."""
    from models.company import Company

    try:
        company = Company.query.get(company_id)
        if not company:
            return f"Erro: Empresa com ID {company_id} não encontrada."
        company.is_active = is_active
        db.session.commit()
        status_text = "Inativada" if not is_active else "Ativada"
        return f"Sucesso: A empresa '{company.name}' (ID: {company_id}) foi {status_text}. Motivo: {reason or 'Não informado'}."
    except Exception as exc:  # pragma: no cover - proteção defensiva legada
        db.session.rollback()
        return f"Erro ao atualizar status da empresa: {exc}"


def get_company_profile(company_id: int | None = None):
    """Retorna o cadastro detalhado de uma empresa acessível ao usuário ativo."""
    company, resolved_company_id, access_profile, error = _resolve_company_with_access(company_id=company_id)
    if error:
        return {"success": False, "error": error}

    return {
        "success": True,
        "company_id": resolved_company_id,
        "company": _company_payload(company, access_profile=access_profile),
    }


def update_company_profile(changes: dict | None = None, company_id: int | None = None):
    """Atualiza parcialmente o cadastro de uma empresa, com whitelist de campos editáveis."""
    company, resolved_company_id, access_profile, error = _resolve_company_with_access(company_id=company_id)
    if error:
        return {"success": False, "error": error}

    if not isinstance(changes, dict) or not changes:
        return {
            "success": False,
            "error": "Informe um dicionário changes com pelo menos um campo editável do cadastro.",
            "editable_fields": list(_EDITABLE_COMPANY_FIELDS),
        }

    sanitized_changes = {
        key: value
        for key, value in changes.items()
        if key in _EDITABLE_COMPANY_FIELDS
    }
    ignored_fields = sorted(set(changes.keys()) - set(sanitized_changes.keys()))

    if not sanitized_changes:
        return {
            "success": False,
            "error": "Nenhum campo editável válido foi informado.",
            "editable_fields": list(_EDITABLE_COMPANY_FIELDS),
            "ignored_fields": ignored_fields,
        }

    try:
        updated_company = company_schema.load(sanitized_changes, instance=company, partial=True)
        db.session.commit()
        return {
            "success": True,
            "company_id": resolved_company_id,
            "updated_fields": sorted(sanitized_changes.keys()),
            "ignored_fields": ignored_fields,
            "company": _company_payload(updated_company, access_profile=access_profile),
        }
    except ValidationError as exc:
        db.session.rollback()
        return {
            "success": False,
            "error": "Erro de validação ao atualizar cadastro da empresa.",
            "details": exc.messages,
            "ignored_fields": ignored_fields,
        }
    except Exception as exc:  # pragma: no cover - proteção defensiva legada
        db.session.rollback()
        return {
            "success": False,
            "error": f"Erro ao atualizar cadastro da empresa: {exc}",
            "ignored_fields": ignored_fields,
        }


def get_company_registration_diagnostics(company_id: int | None = None):
    """Analisa a completude do cadastro da empresa e aponta lacunas para organização."""
    company, resolved_company_id, access_profile, error = _resolve_company_with_access(company_id=company_id)
    if error:
        return {"success": False, "error": error}

    company_data = company.to_dict()
    groups: dict[str, dict[str, object]] = {}
    total_fields = 0
    filled_fields = 0
    missing_fields_flat: list[str] = []

    for group_name, fields in _DIAGNOSTIC_GROUPS.items():
        missing = []
        filled = []
        for field in fields:
            total_fields += 1
            value = company_data.get(field)
            has_value = value not in (None, "", [], {})
            if field == "is_active":
                has_value = value is not None
            if has_value:
                filled_fields += 1
                filled.append(field)
            else:
                missing.append(field)
                missing_fields_flat.append(field)

        groups[group_name] = {
            "filled_fields": filled,
            "missing_fields": missing,
            "completion_percent": round((len(filled) / len(fields)) * 100, 1) if fields else 100.0,
        }

    completion_percent = round((filled_fields / total_fields) * 100, 1) if total_fields else 100.0
    recommended_next_steps = []
    if groups["identificacao"]["missing_fields"]:
        recommended_next_steps.append("Completar identificação jurídica/comercial da empresa.")
    if groups["posicionamento"]["missing_fields"]:
        recommended_next_steps.append("Preencher segmento, porte e descrição para melhorar contexto operacional.")
    if groups["mvv"]["missing_fields"]:
        recommended_next_steps.append("Registrar missão, visão e valores para sustentar estratégia e onboarding.")
    if groups["branding"]["missing_fields"]:
        recommended_next_steps.append("Definir logos principais/secundárias/ícone para consistência visual.")

    return {
        "success": True,
        "company_id": resolved_company_id,
        "access_profile": access_profile,
        "company_name": company.name,
        "completion_percent": completion_percent,
        "filled_fields": filled_fields,
        "total_fields": total_fields,
        "missing_fields": missing_fields_flat,
        "groups": groups,
        "recommended_next_steps": recommended_next_steps,
    }


def list_my_companies(search_term: str | None = None):
    """Lista empresas acessíveis ao usuário ativo."""
    from models.company import Company
    from models.employee import Employee
    from models.user import User

    user_id = get_active_user_id()
    if not user_id:
        return "Erro: Usuário não autenticado."

    try:
        user = User.query.get(user_id)
        user_role = getattr(user, "role", "collaborator")
        if user_role == "admin":
            query = db.session.query(Company)
        else:
            query = db.session.query(Company).join(Employee, Employee.company_id == Company.id).filter(Employee.user_id == user_id)
        companies = query.all()
        if search_term:
            companies = _rank_companies_by_term(companies, search_term)
        if not companies:
            if search_term:
                return f"Nenhuma empresa encontrada para o termo '{search_term}'. Use um prefixo (ex: AA) ou parte do nome."
            return "Nenhuma empresa vinculada ao seu usuário."
        lines = ["🏢 SUAS EMPRESAS ACESSÍVEIS:", ""]
        for company in companies:
            prefix = company.client_code or "SEM PREFIXO"
            lines.append(f"- ID: {company.id} | Prefixo: {prefix} | Nome: {company.name}")
        return sanitize_output("\n".join(lines))
    except Exception as exc:  # pragma: no cover - proteção defensiva legada
        return f"Erro ao listar empresas: {exc}"


__all__ = [
    "get_company_profile",
    "get_company_registration_diagnostics",
    "list_my_companies",
    "update_company_profile",
    "update_company_status",
]
