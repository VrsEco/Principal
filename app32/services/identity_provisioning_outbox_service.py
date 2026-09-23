"""Sincronização idempotente APP32 -> Keycloak com outbox persistente.

O APP32 confirma primeiro seu estado local. A chamada remota acontece somente
depois do commit; falhas ficam pendentes para retentativa e não expõem senha.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta

from models import Company, Employee, User, db
from models.identity_principal import ExternalIdentity, IdentityPrincipal, PrincipalCompanyGrant
from models.identity_provisioning_outbox import IdentityProvisioningOutbox
from services.keycloak_identity_provisioning_service import (
    KeycloakIdentityProvisioningService,
    KeycloakProvisioningError,
)

logger = logging.getLogger(__name__)


class IdentityProvisioningOutboxService:
    """Orquestra uma identidade Keycloak por usuário APP32, sem tenant fallback."""

    max_backoff_minutes = 60

    @staticmethod
    def _dedupe_key(user: User, operation: str, previous_event_id: int | None = None) -> str:
        version = f"{user.id}|{user.email.strip().lower()}|{user.name}|{bool(user.is_active)}|{user.role}|{operation}|{previous_event_id}"
        return hashlib.sha256(version.encode("utf-8")).hexdigest()

    def queue_user_state(self, user: User) -> IdentityProvisioningOutbox:
        operation = "upsert_user" if user.is_active else "disable_user"
        payload = {"email": user.email.strip().lower(), "name": user.name,
                   "is_active": bool(user.is_active), "role": user.role}
        previous = (IdentityProvisioningOutbox.query.filter_by(user_id=user.id)
                    .order_by(IdentityProvisioningOutbox.id.desc()).first())
        # Coalescer apenas eventos ainda não iniciados. Uma projeção concluída
        # não pode impedir A -> B -> A nem uma nova alteração de memberships.
        if (previous is not None and previous.status in ("pending", "failed")
                and previous.operation == operation and previous.payload == payload):
            return previous
        dedupe_key = self._dedupe_key(user, operation, previous.id if previous else None)
        event = IdentityProvisioningOutbox(
            user_id=user.id,
            operation=operation,
            dedupe_key=dedupe_key,
            payload=payload,
            status="pending",
            next_attempt_at=datetime.utcnow(),
        )
        db.session.add(event)
        return event

    @staticmethod
    def _issuer() -> str:
        from os import getenv
        return str(getenv("APP32_MCP_OIDC_ISSUER") or "").rstrip("/")

    def reconcile_user_identity_and_grants(
        self,
        *,
        user: User,
        subject: str,
        suspend_stale_grants: bool = False,
    ) -> list[int]:
        """Reconcilia principal, identidade e grants tenant-safe de um usuário.

        A operação normal de provisionamento não suspende histórico de grants,
        pois um vínculo pode estar sendo atualizado na mesma transação. A
        recuperação OAuth é explícita e usa ``suspend_stale_grants=True`` para
        refletir exatamente os vínculos ativos do APP32 naquele instante.
        """
        issuer = self._issuer()
        if not issuer:
            raise KeycloakProvisioningError("Issuer OAuth não configurado para sincronizar a identidade.")
        principal = IdentityPrincipal.query.filter_by(user_id=user.id, subject_type="USER").first()
        if principal is None:
            principal = IdentityPrincipal(subject_type="USER", user_id=user.id, status="active", label=user.email)
            db.session.add(principal)
            db.session.flush()
        principal.status = "active" if user.is_active else "suspended"
        principal.revoked_at = None if user.is_active else datetime.utcnow()
        identity = ExternalIdentity.query.filter_by(issuer=issuer, subject=subject).first()
        if identity is not None and identity.principal_id != principal.id:
            raise KeycloakProvisioningError("Identidade Keycloak já vinculada a outro usuário APP32.")
        if identity is None:
            db.session.add(ExternalIdentity(principal_id=principal.id, issuer=issuer, subject=subject, provider_alias="keycloak"))

        # APP32 treats a null employee status as active (legacy rows); preserve
        # that exact contract. Bound the company lookup to this user's linked
        # company ids instead of scanning the global company table.
        memberships = (
            Employee.query.filter_by(user_id=user.id)
            .filter(db.or_(Employee.status.is_(None), Employee.status == "active"))
            .all()
        )
        linked_company_ids = {employee.company_id for employee in memberships if employee.company_id is not None}
        active_company_ids = (
            {
                company.id
                for company in Company.query.filter(Company.id.in_(linked_company_ids), Company.is_active.is_(True)).all()
            }
            if linked_company_ids
            else set()
        )
        effective_company_ids: set[int] = set(active_company_ids)
        for employee in memberships:
            if employee.company_id not in effective_company_ids:
                continue
            grant = PrincipalCompanyGrant.query.filter_by(
                principal_id=principal.id, company_id=employee.company_id
            ).first()
            if grant is None:
                grant = PrincipalCompanyGrant(
                    principal_id=principal.id,
                    company_id=employee.company_id,
                    role=user.role or "collaborator",
                    status="active" if user.is_active else "suspended",
                    starts_at=datetime.utcnow(),
                )
                db.session.add(grant)
            else:
                grant.role = user.role or "collaborator"
                grant.status = "active" if user.is_active else "suspended"
                grant.revoked_at = None if user.is_active else datetime.utcnow()

        if suspend_stale_grants:
            active_grant_company_ids = effective_company_ids if user.is_active else set()
            now = datetime.utcnow()
            for grant in PrincipalCompanyGrant.query.filter_by(principal_id=principal.id).all():
                if grant.company_id not in active_grant_company_ids:
                    grant.status = "suspended"
                    grant.revoked_at = now
        return sorted(effective_company_ids)

    # Mantido durante a transição para não quebrar consumidores internos.
    def _sync_principal_and_grants(self, *, user: User, subject: str) -> None:
        self.reconcile_user_identity_and_grants(user=user, subject=subject)

    def process_event(self, event_id: int) -> dict:
        event = IdentityProvisioningOutbox.query.get(event_id)
        if event is None:
            return {"success": False, "reason": "event_not_found"}
        if event.status == "succeeded":
            return {"success": True, "status": "succeeded", "event_id": event.id}
        user = User.query.get(event.user_id)
        if user is None:
            event.status, event.last_error_code, event.last_error = "failed", "user_not_found", "Usuário removido antes do provisionamento."
            db.session.commit()
            return {"success": False, "reason": "user_not_found", "event_id": event.id}
        event.status, event.attempts = "processing", event.attempts + 1
        db.session.commit()
        try:
            provisioner = KeycloakIdentityProvisioningService()
            # A outbox reconcilia o estado ATUAL do APP32, não reaplica um
            # comando histórico que pode ter sido superado por reativação.
            if not user.is_active:
                subject = provisioner.disable_user(email=user.email, name=user.name)
            else:
                principal = IdentityPrincipal.query.filter_by(user_id=user.id, subject_type="USER").first()
                existing_identity = (
                    ExternalIdentity.query.filter_by(principal_id=principal.id, issuer=self._issuer()).first()
                    if principal is not None else None
                )
                subject = provisioner.ensure_user(
                    email=user.email,
                    name=user.name,
                    # Convite ocorre uma única vez: eventos de perfil/vínculo
                    # não podem resetar ou interromper credenciais existentes.
                    # external_subject é persistido depois de o IdP concluir o
                    # convite e antes da reconciliação local. Assim, uma falha
                    # posterior a esse checkpoint não dispara outro e-mail no retry.
                    send_password_setup_email=(
                        existing_identity is None and not event.external_subject
                    ),
                    enabled=True,
                )
            if event.external_subject != subject:
                event.external_subject = subject
                db.session.commit()
            self._sync_principal_and_grants(user=user, subject=subject)
            event.status, event.external_subject, event.processed_at = "succeeded", subject, datetime.utcnow()
            event.last_error_code = event.last_error = None
            db.session.commit()
            return {"success": True, "status": "succeeded", "event_id": event.id, "subject": subject}
        except (KeycloakProvisioningError, Exception) as exc:
            db.session.rollback()
            event = IdentityProvisioningOutbox.query.get(event_id)
            delay = min(2 ** min(event.attempts, 6), self.max_backoff_minutes)
            event.status = "failed"
            event.next_attempt_at = datetime.utcnow() + timedelta(minutes=delay)
            event.last_error_code = "keycloak_provisioning_failed"
            event.last_error = str(exc)[:500]
            db.session.commit()
            logger.exception("Identity provisioning failed for event %s", event_id)
            return {"success": False, "status": "failed", "event_id": event.id}

    def process_due(self, *, limit: int = 25) -> list[dict]:
        now = datetime.utcnow()
        events = (
            IdentityProvisioningOutbox.query.filter(
                IdentityProvisioningOutbox.status.in_(["pending", "failed"]),
                (IdentityProvisioningOutbox.next_attempt_at.is_(None))
                | (IdentityProvisioningOutbox.next_attempt_at <= now),
            )
            .order_by(IdentityProvisioningOutbox.id.asc())
            .limit(max(1, min(int(limit), 100)))
            .all()
        )
        return [self.process_event(event.id) for event in events]


identity_provisioning_outbox_service = IdentityProvisioningOutboxService()
