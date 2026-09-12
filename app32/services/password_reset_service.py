"""Fluxo seguro de redefinição de senha local do APP32.

O token enviado por e-mail nunca é persistido em claro. Esta service não sabe
empresa ativa: identidade local é global e o tenant somente é escolhido após a
autenticação, evitando que o fluxo público revele associações empresariais.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta

from flask import current_app

from models import PasswordResetToken, User, db
from services.email_service import email_service


logger = logging.getLogger(__name__)


class PasswordResetError(ValueError):
    """Erro público, propositalmente neutro, do fluxo de redefinição."""


class PasswordResetService:
    TOKEN_TTL_MINUTES = 30
    TOKEN_BYTES = 32

    @staticmethod
    def _secret() -> bytes:
        secret = str(current_app.config.get("SECRET_KEY") or "").strip()
        if not secret:
            raise RuntimeError("SECRET_KEY é obrigatória para redefinição de senha.")
        return secret.encode("utf-8")

    @classmethod
    def _digest(cls, value: str, *, purpose: str) -> str:
        return hmac.new(
            cls._secret(),
            f"{purpose}:{value}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def normalize_email(value: str | None) -> str:
        return str(value or "").strip().lower()

    @classmethod
    def request_reset(cls, *, email: str | None, request_ip: str | None, reset_url_prefix: str) -> None:
        """Emite um token quando houver usuário ativo, sem revelar a existência."""
        normalized_email = cls.normalize_email(email)
        if not normalized_email:
            return

        user = User.query.filter_by(email=normalized_email, is_active=True).first()
        if user is None:
            return

        now = datetime.utcnow()
        raw_token = secrets.token_urlsafe(cls.TOKEN_BYTES)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=cls._digest(raw_token, purpose="password-reset-token"),
            requested_ip_hash=cls._digest(str(request_ip or ""), purpose="password-reset-ip"),
            expires_at=now + timedelta(minutes=cls.TOKEN_TTL_MINUTES),
        )
        try:
            # Apenas o último link permanece válido; tokens usados/expirados
            # ficam como trilha mínima de segurança até a política de retenção.
            PasswordResetToken.query.filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
            db.session.add(token)
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Falha ao registrar solicitação de redefinição de senha para user_id=%s", user.id)
            return

        reset_url = f"{reset_url_prefix.rstrip('/')}/{raw_token}"
        subject = "Redefinição de senha — Gestão Versus"
        body = (
            "Recebemos uma solicitação para redefinir sua senha.\n\n"
            f"Use este link em até {cls.TOKEN_TTL_MINUTES} minutos:\n{reset_url}\n\n"
            "Se você não solicitou a alteração, ignore esta mensagem."
        )
        html_body = email_service.build_transactional_email_html(
            subject=subject,
            title="Redefina sua senha",
            preheader="Link temporário para redefinição de senha.",
            body=(
                "Recebemos uma solicitação para redefinir sua senha.\n\n"
                "Acesse o link seguro abaixo:\n"
                f"{reset_url}\n\n"
                f"Este link expira em {cls.TOKEN_TTL_MINUTES} minutos e só pode ser usado uma vez. "
                "Se você não solicitou a alteração, ignore esta mensagem."
            ),
        )
        if not email_service.send_email([user.email], subject, body, html_body=html_body):
            # Não inclui link, token ou e-mail nos logs. A resposta HTTP segue neutra.
            logger.warning("Falha no envio de redefinição de senha para user_id=%s", user.id)

    @classmethod
    def complete_reset(cls, *, raw_token: str | None, new_password: str | None) -> User:
        token_value = str(raw_token or "").strip()
        password_value = str(new_password or "")
        if not token_value or len(password_value) < 12:
            raise PasswordResetError("Link inválido, expirado ou já utilizado.")

        token_hash = cls._digest(token_value, purpose="password-reset-token")
        now = datetime.utcnow()
        try:
            token = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
            if token is None:
                raise PasswordResetError("Link inválido, expirado ou já utilizado.")

            # Consumo condicional impede a reutilização inclusive sob corrida.
            consumed = (
                PasswordResetToken.query.filter(
                    PasswordResetToken.id == token.id,
                    PasswordResetToken.used_at.is_(None),
                    PasswordResetToken.expires_at > now,
                ).update({PasswordResetToken.used_at: now}, synchronize_session=False)
            )
            if consumed != 1:
                db.session.rollback()
                raise PasswordResetError("Link inválido, expirado ou já utilizado.")

            user = User.query.filter_by(id=token.user_id, is_active=True).first()
            if user is None:
                db.session.rollback()
                raise PasswordResetError("Link inválido, expirado ou já utilizado.")

            user.set_password(password_value)
            user.auth_session_version = int(getattr(user, "auth_session_version", 1) or 1) + 1
            user.updated_at = now
            db.session.commit()
            logger.info("Senha redefinida com sucesso para user_id=%s", user.id)
            return user
        except PasswordResetError:
            raise
        except Exception as exc:
            db.session.rollback()
            logger.exception("Falha ao concluir redefinição de senha")
            raise PasswordResetError("Não foi possível concluir a redefinição. Solicite um novo link.") from exc


password_reset_service = PasswordResetService()
