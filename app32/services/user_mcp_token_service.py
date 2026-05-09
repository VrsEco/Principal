from __future__ import annotations

import hashlib
import json
import os
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterator

from flask import has_app_context

from models import Company, Employee, User, UserMcpToken, db
from services.email_service import email_service
from services.log_service import log_service
from services.whatsapp_service import whatsapp_service
from utils.permissions import (
    can_access_company,
    get_access_profile,
    get_default_company_id,
    is_platform_admin,
)


DEFAULT_PUBLIC_BASE_URL = "https://app.gestaoversus.com.br"
TOKEN_EXPIRATION_DAYS = 30
ALLOWED_SURFACES = ("user",)
PROFILE_TO_FALLBACK_ROLE = {
    "administrator": "administrador",
    "client": "cliente",
    "collaborator": "colaborador",
}


@dataclass(frozen=True)
class UserMcpResolvedContext:
    token_record_id: int
    user_id: int
    company_id: int
    fallback_role: str
    allowed_surfaces: tuple[str, ...]
    subject: str | None
    client_name: str | None


class UserMcpTokenService:
    @staticmethod
    @contextmanager
    def _ensure_app_context() -> Iterator[None]:
        if has_app_context():
            yield
            return

        from app import create_app

        app = create_app("production")
        with app.app_context():
            yield

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.utcnow()

    @staticmethod
    def _normalize_surface(surface: str | None) -> str:
        normalized = str(surface or "user").strip().lower()
        if normalized not in ALLOWED_SURFACES:
            raise ValueError("Surface MCP inválida para token pessoal.")
        return normalized

    @staticmethod
    def _generate_plaintext_token() -> str:
        return f"mcpu_{secrets.token_urlsafe(32)}"

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()

    @classmethod
    def _mask_prefix(cls, prefix: str) -> str:
        raw = str(prefix or "").strip()
        if len(raw) <= 8:
            return raw
        return f"{raw[:6]}****{raw[-2:]}"

    @classmethod
    def _expire_if_needed(cls, record: UserMcpToken) -> None:
        if record.status == "active" and record.expires_at and record.expires_at <= cls._utcnow():
            record.status = "expired"
            record.updated_at = cls._utcnow()

    @classmethod
    def _revoke_record(cls, record: UserMcpToken, *, commit: bool = False) -> None:
        if record.status == "revoked":
            return
        record.status = "revoked"
        record.revoked_at = cls._utcnow()
        record.updated_at = cls._utcnow()
        if commit:
            db.session.commit()

    @classmethod
    def get_active_token_record(cls, user_id: int) -> UserMcpToken | None:
        with cls._ensure_app_context():
            record = (
                UserMcpToken.query.filter_by(user_id=user_id, status="active")
                .order_by(UserMcpToken.created_at.desc())
                .first()
            )
            if record:
                cls._expire_if_needed(record)
                db.session.commit()
            return record if record and record.status == "active" else None

    @classmethod
    def _serialize_company(cls, company: Company, *, selected: bool = False) -> dict[str, Any]:
        label = f"{company.client_code} - {company.name}" if getattr(company, "client_code", None) else company.name
        return {
            "id": company.id,
            "name": company.name,
            "client_code": getattr(company, "client_code", None),
            "label": label,
            "selected": bool(selected),
        }

    @classmethod
    def list_accessible_companies(cls, user: User) -> list[dict[str, Any]]:
        with cls._ensure_app_context():
            if is_platform_admin(user=user):
                companies = (
                    Company.query.filter(Company.is_active.isnot(False))
                    .order_by(Company.name.asc())
                    .all()
                )
            else:
                company_ids = [
                    row.company_id
                    for row in Employee.query.filter_by(user_id=user.id, status="active").all()
                    if getattr(row, "company_id", None) is not None
                ]
                companies = []
                if company_ids:
                    companies = (
                        Company.query.filter(
                            Company.id.in_(company_ids),
                            Company.is_active.isnot(False),
                        )
                        .order_by(Company.name.asc())
                        .all()
                    )
            default_company_id = get_default_company_id(user=user)
            return [
                cls._serialize_company(company, selected=company.id == default_company_id)
                for company in companies
            ]

    @classmethod
    def _resolve_company_id_for_user(cls, user: User, requested_company_id: int | None) -> int | None:
        candidate = requested_company_id or get_default_company_id(user=user)
        if candidate and can_access_company(candidate, user=user):
            return int(candidate)
        return None

    @classmethod
    def _resolve_explicit_company_id_for_user(cls, user: User, requested_company_id: int | None) -> int | None:
        if requested_company_id in (None, 0, '0', ''):
            return None
        candidate = int(requested_company_id)
        if can_access_company(candidate, user=user):
            return candidate
        return None

    @classmethod
    def _build_status_payload(cls, user: User, record: UserMcpToken | None) -> dict[str, Any]:
        companies = cls.list_accessible_companies(user)
        default_company_id = get_default_company_id(user=user)
        days_to_expire = None
        if record and record.expires_at:
            days_to_expire = (record.expires_at.date() - cls._utcnow().date()).days

        return {
            "has_active_token": bool(record and record.status == "active"),
            "token_prefix": record.token_prefix if record else None,
            "token_masked": cls._mask_prefix(record.token_prefix) if record else None,
            "status": record.status if record else "missing",
            "created_at": record.created_at.isoformat() if record and record.created_at else None,
            "expires_at": record.expires_at.isoformat() if record and record.expires_at else None,
            "days_to_expire": days_to_expire,
            "last_used_at": record.last_used_at.isoformat() if record and record.last_used_at else None,
            "last_client_name": record.last_client_name if record else None,
            "last_surface": record.last_surface if record else None,
            "last_company_id": record.last_company_id if record else None,
            "default_company_id": default_company_id,
            "allowed_surfaces": list(ALLOWED_SURFACES),
            "companies": companies,
        }

    @classmethod
    def get_status(cls, user_id: int) -> dict[str, Any]:
        with cls._ensure_app_context():
            user = User.query.get(user_id)
            if not user or not getattr(user, "is_active", False):
                raise ValueError("Usuário inválido para token MCP.")
            record = cls.get_active_token_record(user.id)
            return cls._build_status_payload(user, record)

    @classmethod
    def _issue_token(
        cls,
        user: User,
        *,
        created_by_user_id: int | None = None,
        client_name: str | None = None,
    ) -> tuple[UserMcpToken, str]:
        active = cls.get_active_token_record(user.id)
        if active:
            cls._revoke_record(active)

        plaintext = cls._generate_plaintext_token()
        expires_at = cls._utcnow() + timedelta(days=TOKEN_EXPIRATION_DAYS)
        record = UserMcpToken(
            user_id=user.id,
            token_hash=cls._hash_token(plaintext),
            token_prefix=plaintext[:12],
            status="active",
            created_by_user_id=created_by_user_id or user.id,
            expires_at=expires_at,
            last_client_name=(client_name or "").strip() or None,
            last_company_id=None,
        )
        db.session.add(record)
        db.session.commit()
        return record, plaintext

    @classmethod
    def generate_token(
        cls,
        *,
        user_id: int,
        created_by_user_id: int | None = None,
        company_id: int | None = None,
        surface: str = "user",
        client_name: str | None = None,
    ) -> dict[str, Any]:
        with cls._ensure_app_context():
            user = User.query.get(user_id)
            if not user or not getattr(user, "is_active", False):
                raise ValueError("Usuário inválido para geração do token MCP.")
            normalized_surface = cls._normalize_surface(surface)
            resolved_company_id = cls._resolve_explicit_company_id_for_user(user, company_id)
            record, plaintext = cls._issue_token(
                user,
                created_by_user_id=created_by_user_id,
                client_name=client_name,
            )
            log_service.log_create(
                entity_type="user_mcp_token",
                entity_id=record.id,
                entity_name=f"Token MCP de {user.email}",
                new_values={
                    "user_id": user.id,
                    "surface": normalized_surface,
                    "expires_at": record.expires_at.isoformat(),
                    "company_id_context": resolved_company_id,
                },
                description=f"Token MCP pessoal gerado para {user.email}",
                company_id=resolved_company_id,
            )
            status = cls._build_status_payload(user, record)
            config = cls.build_client_config(
                user_id=user.id,
                plaintext_token=plaintext,
                company_id=resolved_company_id,
                surface=normalized_surface,
                client_name=client_name,
            )
            return {"token": plaintext, "status": status, "config": config}

    @classmethod
    def renew_token(
        cls,
        *,
        user_id: int,
        renewed_by_user_id: int | None = None,
        company_id: int | None = None,
        surface: str = "user",
        client_name: str | None = None,
    ) -> dict[str, Any]:
        return cls.generate_token(
            user_id=user_id,
            created_by_user_id=renewed_by_user_id,
            company_id=company_id,
            surface=surface,
            client_name=client_name,
        )

    @classmethod
    def revoke_token(cls, *, user_id: int, revoked_by_user_id: int | None = None) -> dict[str, Any]:
        with cls._ensure_app_context():
            user = User.query.get(user_id)
            if not user:
                raise ValueError("Usuário inválido para revogação do token MCP.")
            record = cls.get_active_token_record(user.id)
            if record:
                cls._revoke_record(record)
                db.session.commit()
                log_service.log_delete(
                    entity_type="user_mcp_token",
                    entity_id=record.id,
                    entity_name=f"Token MCP de {user.email}",
                    old_values={"status": "active", "expires_at": record.expires_at.isoformat() if record.expires_at else None},
                    description=f"Token MCP revogado para {user.email}",
                    company_id=record.last_company_id,
                )
            return cls._build_status_payload(user, None)

    @classmethod
    def build_client_config(
        cls,
        *,
        user_id: int,
        plaintext_token: str | None = None,
        company_id: int | None = None,
        surface: str = "user",
        client_name: str | None = None,
    ) -> dict[str, Any]:
        with cls._ensure_app_context():
            user = User.query.get(user_id)
            if not user:
                raise ValueError("Usuário inválido para configuração MCP.")
            normalized_surface = cls._normalize_surface(surface)
            resolved_company_id = cls._resolve_explicit_company_id_for_user(user, company_id)
            companies = cls.list_accessible_companies(user)
            company_lookup = {item["id"]: item for item in companies}
            selected_company = company_lookup.get(resolved_company_id) if resolved_company_id else None
            public_base = str(os.environ.get("APP32_MCP_PUBLIC_BASE_URL") or DEFAULT_PUBLIC_BASE_URL).rstrip("/")
            url = f"{public_base}/mcp/{normalized_surface}/"
            if resolved_company_id:
                url = f"{url}?company_id={resolved_company_id}"
            display_name = selected_company["label"] if selected_company else "Sem empresa padrão"
            token_value = plaintext_token or "TOKEN_GERADO_APENAS_NA_RENOVACAO"
            config_json = {
                "auth_type": "bearer",
                "name": f"Sapiens {normalized_surface.title()}",
                "token": token_value,
                "url": url,
            }
            config_text = (
                f"Nome: Sapiens {normalized_surface.title()}\n"
                f"Empresa: {display_name}\n"
                f"URL: {url}\n"
                f"Autenticação: Bearer Token\n"
                f"Token: {token_value}"
            )
            technical_config_text = (
                f"{config_text}\n\n"
                f"JSON:\n{json.dumps(config_json, ensure_ascii=False, indent=2)}"
            )
            activation_prompt = "\n".join([
                "Quero que você ative o Sapiens neste cliente usando a conexão MCP abaixo.",
                "",
                "Dados da conexão:",
                f"- Nome: Sapiens {normalized_surface.title()}",
                f"- Empresa padrão: {display_name}",
                f"- URL: {url}",
                "- Autenticação: Bearer Token",
                f"- Token: {token_value}",
                "",
                "JSON:",
                json.dumps(config_json, ensure_ascii=False, indent=2),
                "",
                "Sua tarefa:",
                "1. Verifique se este cliente suporta configuração MCP automática.",
                "2. Se suportar, faça a configuração.",
                "3. Se este cliente permitir criar atalho, comando, agente ou persona, crie um atalho chamado Sapiens.",
                "4. Ao ativar, use esta mensagem inicial:",
                "",
                "◆ SAPIENS · Gestão Versus ● ativo",
                "",
                "Olá! Sou o Sapiens, assistente virtual da Versus.",
                "Estamos conectados ao Sistema de Gestão Versus — pode começar.",
                "",
                "Se você encontrar algum bug, tiver uma observação ou sugestão, me avise que eu registro um card formal para o Squad de Engenharia.",
                "Se você pedir para registrar, abrir card, encaminhar ao squad ou anotar uma melhoria, eu devo usar a tool request_engineering_suggestion.",
                "",
                "5. Se este cliente não suportar configuração automática, atalho, agente ou integração MCP nativa, responda exatamente assim:",
                "- Este cliente não suporta ativação automática do Sapiens.",
                "- A conexão técnica está pronta, mas precisa ser configurada manualmente.",
                "- Se quiser, eu posso te mostrar o passo a passo manual para este cliente.",
                "6. Se este cliente suportar MCP mas não suportar atalho, mantenha a conexão ativa e informe ao usuário como chamar o Sapiens de forma simples na conversa.",
                "7. Não invente valores. Use exatamente os dados fornecidos.",
                "",
                "Formato da resposta:",
                "1. Diagnóstico",
                "2. Ação executada",
                "3. Resultado final",
                "4. Como usar o Sapiens neste cliente",
                "5. Se não suportar, mostrar a resposta padrão",
            ])
            return {
                "client_name": (client_name or "").strip() or None,
                "surface": normalized_surface,
                "company_id": resolved_company_id,
                "company_label": display_name,
                "url": url,
                "text": config_text,
                "json": config_json,
                "technical_config_text": technical_config_text,
                "activation_prompt": activation_prompt,
                "companies": companies,
            }

    @classmethod
    def resolve_for_http_request(
        cls,
        *,
        token: str,
        surface: str,
        company_id: int | None,
        client_name: str | None,
    ) -> UserMcpResolvedContext | None:
        normalized_surface = cls._normalize_surface(surface)
        token_hash = cls._hash_token(token)
        with cls._ensure_app_context():
            record = (
                UserMcpToken.query.filter_by(token_hash=token_hash)
                .order_by(UserMcpToken.created_at.desc())
                .first()
            )
            if not record:
                return None
            cls._expire_if_needed(record)
            if record.status != "active":
                db.session.commit()
                return None
            user = User.query.get(record.user_id)
            if not user or not getattr(user, "is_active", False):
                return None
            resolved_company_id = cls._resolve_company_id_for_user(user, company_id or record.last_company_id)
            if resolved_company_id is None:
                return None
            profile = get_access_profile(resolved_company_id, user=user) or "collaborator"
            fallback_role = PROFILE_TO_FALLBACK_ROLE.get(profile, "colaborador")
            record.last_used_at = cls._utcnow()
            record.last_surface = normalized_surface
            record.last_company_id = resolved_company_id
            record.last_client_name = (client_name or "").strip() or record.last_client_name
            record.updated_at = cls._utcnow()
            db.session.commit()
            return UserMcpResolvedContext(
                token_record_id=record.id,
                user_id=user.id,
                company_id=resolved_company_id,
                fallback_role=fallback_role,
                allowed_surfaces=ALLOWED_SURFACES,
                subject=user.email,
                client_name=record.last_client_name,
            )

    @classmethod
    def _build_notification_body(cls, user: User, record: UserMcpToken, *, days_remaining: int) -> tuple[str, str, str]:
        expiry = record.expires_at.strftime("%d/%m/%Y %H:%M") if record.expires_at else "-"
        profile_url = "/profile"
        if days_remaining > 0:
            subject = "Seu token MCP expira em 3 dias"
            body = (
                f"Olá, {user.name}!\n\n"
                f"Seu token MCP do Sapiens expira em {days_remaining} dias, em {expiry}.\n"
                f"Acesse {profile_url} para renovar o token antes do vencimento."
            )
            whatsapp_message = (
                f"Olá, {user.name}! Seu token MCP do Sapiens expira em {days_remaining} dias ({expiry}). "
                f"Entre em /profile e renove o token para não perder a conexão."
            )
        else:
            subject = "Seu token MCP venceu hoje"
            body = (
                f"Olá, {user.name}!\n\n"
                f"Seu token MCP do Sapiens vence hoje ({expiry}).\n"
                f"Acesse {profile_url} para renovar e atualizar a configuração do seu cliente remoto."
            )
            whatsapp_message = (
                f"Olá, {user.name}! Seu token MCP vence hoje ({expiry}). "
                f"Entre em /profile e renove o token do Sapiens para continuar usando a conexão remota."
            )
        html_body = email_service.build_transactional_email_html(
            subject=subject,
            body=body,
            title=subject,
            footer_note="Aviso automático do acesso MCP do Sapiens.",
        )
        return subject, html_body, whatsapp_message

    @classmethod
    def send_expiration_notifications(cls, *, reference_date: date | None = None) -> dict[str, Any]:
        with cls._ensure_app_context():
            today = reference_date or cls._utcnow().date()
            tokens = (
                UserMcpToken.query.filter(UserMcpToken.status == "active")
                .order_by(UserMcpToken.expires_at.asc())
                .all()
            )
            processed = 0
            notified = 0
            for record in tokens:
                cls._expire_if_needed(record)
                if record.status != "active" or not record.expires_at:
                    continue
                days_remaining = (record.expires_at.date() - today).days
                if days_remaining not in {3, 0}:
                    continue
                if days_remaining == 3 and record.notice_d3_sent_at:
                    continue
                if days_remaining == 0 and record.notice_d0_sent_at:
                    continue
                user = User.query.get(record.user_id)
                if not user or not getattr(user, "is_active", False):
                    continue
                subject, html_body, whatsapp_message = cls._build_notification_body(
                    user,
                    record,
                    days_remaining=days_remaining,
                )
                plain_text = html_body.replace("<br>", "\n")
                email_ok = bool(user.email) and email_service.send_email([user.email], subject, plain_text, html_body=html_body)
                whatsapp_ok = bool(user.whatsapp) and whatsapp_service.send_message(user.whatsapp, whatsapp_message)
                if email_ok or whatsapp_ok:
                    notified += 1
                    if days_remaining == 3:
                        record.notice_d3_sent_at = cls._utcnow()
                    else:
                        record.notice_d0_sent_at = cls._utcnow()
                processed += 1
            db.session.commit()
            return {"processed": processed, "notified": notified}


user_mcp_token_service = UserMcpTokenService()
