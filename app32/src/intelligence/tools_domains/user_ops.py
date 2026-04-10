from __future__ import annotations

import secrets
import string

from sqlalchemy import or_

from models import db
from src.intelligence.tools_support import get_active_user, get_active_user_id


def get_user_summary(target_user: str | None = None, range: str = "today"):
    """Gera relatório consolidado de atividades, processos e reuniões de um usuário."""
    from models.employee import Employee
    from models.user import User
    from services.proactive_service import get_user_summary_report

    requesting_user_id = get_active_user_id()
    if not requesting_user_id:
        return "Erro: Usuário não autenticado."

    try:
        req_user = User.query.get(requesting_user_id)
        if not req_user:
            return "Erro: Seu usuário não foi encontrado."
        if not target_user:
            target = req_user
        elif str(target_user).isdigit():
            target = User.query.get(int(target_user))
        else:
            target = User.query.filter(
                or_(User.email.ilike(f"{target_user}"), User.name.ilike(f"%{target_user}%"))
            ).first()
        if not target:
            return f"Erro: Usuário '{target_user}' não encontrado."

        if req_user.id != target.id:
            req_role = getattr(req_user, "role", "collaborator")
            if req_role == "admin":
                pass
            elif req_role == "client":
                req_companies = [e.company_id for e in Employee.query.filter_by(user_id=req_user.id).all()]
                target_companies = [e.company_id for e in Employee.query.filter_by(user_id=target.id).all()]
                if not set(req_companies).intersection(target_companies):
                    return f"Erro: Você não tem permissão para visualizar o resumo de {target.name}. Usuário pertence a outras empresas."
            else:
                return "Erro: Colaboradores podem visualizar apenas o seu próprio resumo. Use 'meu resumo'."

        report = get_user_summary_report(target, date_range=range)
        prefix = f"📊 RESUMO DE {target.name.upper()} ({range.upper()})\n\n" if req_user.id != target.id and "está 100% em dia" not in report else ""
        return prefix + report
    except Exception as exc:  # pragma: no cover - proteção defensiva legada
        return f"Erro ao gerar resumo: {exc}"


def list_system_users():
    """Lista todos os usuários cadastrados no sistema. Admin only."""
    from models.user import User

    user = get_active_user()
    if not user or getattr(user, "role", "collaborator") != "admin":
        return "Erro: Apenas administradores podem listar usuários."
    try:
        users = User.query.all()
        if not users:
            return "Nenhum usuário encontrado."
        output = ["USUÁRIOS DO SISTEMA:"]
        for user_item in users:
            wa = user_item.whatsapp or "N/A"
            tg = user_item.telegram or "N/A"
            output.append(f"- ID: {user_item.id} | {user_item.name} ({user_item.email}) | Papel: {user_item.role} | WA: {wa} | TG: {tg}")
        return "\n".join(output)
    except Exception as exc:  # pragma: no cover - proteção defensiva legada
        return f"Erro ao listar usuários: {exc}"


def register_system_user(name: str, email: str, role: str = "collaborator", whatsapp: str | None = None, telegram: str | None = None):
    """Cadastra novo usuário. Admin only."""
    from models.user import User

    user = get_active_user()
    if not user or getattr(user, "role", "collaborator") != "admin":
        return "Erro: Acesso restrito a administradores."
    try:
        if User.query.filter_by(email=email).first():
            return f"Erro: O e-mail '{email}' já está em uso."
        alphabet = string.ascii_letters + string.digits
        temp_password = "".join(secrets.choice(alphabet) for _ in range(12))
        new_user = User(name=name, email=email, role=role, whatsapp=whatsapp, telegram=telegram)
        new_user.set_password(temp_password)
        db.session.add(new_user)
        db.session.commit()
        return (
            f"Usuário '{name}' cadastrado com sucesso! ID: {new_user.id}\n"
            f"OBS: Uma senha temporária foi gerada. Comunique ao usuário via {whatsapp or email}.\n"
            f"Senha Temporária: {temp_password}"
        )
    except Exception as exc:  # pragma: no cover - proteção defensiva legada
        db.session.rollback()
        return f"Erro ao cadastrar usuário: {exc}"


def update_user_contacts(user_id: int, whatsapp: str | None = None, telegram: str | None = None):
    """Atualiza dados de contato do próprio usuário ou por admin."""
    from models.user import User

    try:
        user_to_update = User.query.get(user_id)
        if not user_to_update:
            return f"Erro: Usuário ID {user_id} não encontrado."
        current_user_obj = get_active_user()
        if not current_user_obj:
            return "Erro: Usuário não identificado."
        if getattr(current_user_obj, "role", "collaborator") != "admin" and current_user_obj.id != user_id:
            return "Erro: Você não tem permissão para alterar os dados deste usuário."
        if whatsapp is not None:
            user_to_update.whatsapp = whatsapp
        if telegram is not None:
            user_to_update.telegram = telegram
        db.session.commit()
        return f"Contatos do usuário '{user_to_update.name}' atualizados com sucesso."
    except Exception as exc:  # pragma: no cover - proteção defensiva legada
        db.session.rollback()
        return f"Erro ao atualizar contatos: {exc}"


__all__ = ["get_user_summary", "list_system_users", "register_system_user", "update_user_contacts"]
