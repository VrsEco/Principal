from __future__ import annotations

from models import db
from src.intelligence.tools_support import (
    _rank_companies_by_term,
    get_active_user_id,
    sanitize_output,
)


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


__all__ = ["update_company_status", "list_my_companies"]
