"""Recuperação idempotente da conexão OAuth de um usuário APP32.

O serviço é deliberadamente self-service: recebe somente o ``user_id`` da
sessão autenticada. Ele não aceita empresa, subject ou e-mail informados pelo
browser, e nunca emite token ou senha.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from models import User, db
from models.identity_provisioning_outbox import OAuthConnectionRecoveryAudit
from services.identity_provisioning_outbox_service import identity_provisioning_outbox_service
from services.keycloak_identity_provisioning_service import (
    KeycloakIdentityProvisioningService,
    KeycloakProvisioningError,
)


class OAuthConnectionRecoveryError(Exception):
    """Erro seguro e apresentável na recuperação OAuth."""


class OAuthConnectionRecoveryRateLimitError(OAuthConnectionRecoveryError):
    """Evita reenvio abusivo de e-mails de ação do Keycloak."""


class OAuthConnectionRecoveryService:
    max_requests_per_hour = 3

    def recover_authenticated_user(self, *, user_id: int) -> dict:
        user = User.query.get(user_id)
        if user is None or not user.is_active:
            raise OAuthConnectionRecoveryError("Seu usuário não está ativo para recuperar a conexão OAuth.")
        email = str(user.email or "").strip().lower()
        if not email:
            raise OAuthConnectionRecoveryError("Seu perfil não possui um e-mail válido para recuperar a conexão OAuth.")

        window_start = datetime.utcnow() - timedelta(hours=1)
        attempts = OAuthConnectionRecoveryAudit.query.filter(
            OAuthConnectionRecoveryAudit.user_id == user.id,
            OAuthConnectionRecoveryAudit.created_at >= window_start,
            # Falha de infraestrutura/IdP não pode impedir o usuário de
            # recuperar a conexão depois de uma correção. Só envios aceitos
            # (ou em processamento) entram na contenção antiabuso.
            OAuthConnectionRecoveryAudit.status.in_(["processing", "succeeded"]),
        ).count()
        if attempts >= self.max_requests_per_hour:
            raise OAuthConnectionRecoveryRateLimitError(
                "Você já solicitou a recuperação três vezes na última hora. Aguarde antes de tentar novamente."
            )

        audit = OAuthConnectionRecoveryAudit(user_id=user.id, status="processing")
        db.session.add(audit)
        db.session.commit()

        try:
            provisioner = KeycloakIdentityProvisioningService()
            subject = provisioner.ensure_user(
                email=email,
                name=user.name,
                enabled=True,
                send_password_setup_email=False,
            )
            company_ids = identity_provisioning_outbox_service.reconcile_user_identity_and_grants(
                user=user,
                subject=subject,
                suspend_stale_grants=True,
            )
            audit.external_subject = subject
            audit.company_ids = company_ids
            # O convite só é enviado após validar e persistir os vínculos.
            # Uma colisão issuer/sub ou falha de grants não deve gerar e-mail.
            db.session.commit()
            provisioner.send_password_setup_email(subject=subject)
            audit.status = "succeeded"
            audit.completed_at = datetime.utcnow()
            db.session.commit()
            return {
                "success": True,
                "company_ids": company_ids,
                "message": "Conexão OAuth reconciliada. Enviamos um e-mail para você definir ou atualizar a senha do Keycloak.",
            }
        except (KeycloakProvisioningError, OAuthConnectionRecoveryError) as exc:
            db.session.rollback()
            self._mark_failed(audit.id, str(exc), "oauth_recovery_failed")
            raise OAuthConnectionRecoveryError("Não foi possível recuperar a conexão OAuth agora. Tente novamente mais tarde.") from exc
        except Exception as exc:
            db.session.rollback()
            self._mark_failed(audit.id, "Falha interna na recuperação OAuth; detalhes sensíveis omitidos.", "oauth_recovery_unexpected")
            raise OAuthConnectionRecoveryError("Não foi possível recuperar a conexão OAuth agora. Tente novamente mais tarde.") from exc

    @staticmethod
    def _mark_failed(audit_id: int, detail: str, error_code: str) -> None:
        audit = OAuthConnectionRecoveryAudit.query.get(audit_id)
        if audit is None:
            return
        audit.status = "failed"
        audit.error_code = error_code
        audit.error_summary = str(detail)[:500]
        audit.completed_at = datetime.utcnow()
        db.session.commit()


oauth_connection_recovery_service = OAuthConnectionRecoveryService()
