"""Onboarding administrativo MCP/OAuth; APP32 é a autoridade de grants tenant-safe."""
from __future__ import annotations

import os
from datetime import datetime

from models import Company, Employee, User, db
from models.identity_principal import ExternalIdentity, IdentityPrincipal, PrincipalCompanyGrant
from services.keycloak_identity_provisioning_service import KeycloakProvisioningError, KeycloakIdentityProvisioningService
from services.mcp_oauth_codex_connector_service import mcp_oauth_codex_connector_service


class McpOAuthOnboardingError(ValueError):
    pass


class McpOAuthOnboardingService:
    def __init__(self, *, provisioner_factory=KeycloakIdentityProvisioningService):
        self._provisioner_factory = provisioner_factory

    @staticmethod
    def _issuer() -> str:
        return str(os.getenv("APP32_MCP_OIDC_ISSUER") or "").rstrip("/")

    @staticmethod
    def _linked_company(user_id: int, company_id: int) -> bool:
        return Employee.query.filter_by(user_id=user_id, company_id=company_id, status="active").first() is not None

    def status(self, *, user_id: int) -> dict:
        principal = IdentityPrincipal.query.filter_by(user_id=user_id, subject_type="USER").first()
        grants = [] if principal is None else PrincipalCompanyGrant.query.filter_by(principal_id=principal.id).all()
        return {
            "enabled": bool(principal and principal.is_active and any(grant.is_active for grant in grants)),
            "principal_status": principal.status if principal else "not_provisioned",
            "grants": [
                {"company_id": grant.company_id, "company_name": getattr(grant.company, "name", None), "role": grant.role, "status": grant.status}
                for grant in grants
            ],
            "connector": mcp_oauth_codex_connector_service.build_config(),
        }

    def enable(self, *, user_id: int, company_id: int, temporary_password: str, actor_user_id: int) -> dict:
        user = User.query.filter_by(id=user_id, is_active=True).first()
        company = Company.query.filter_by(id=company_id, is_active=True).first()
        if user is None or company is None:
            raise McpOAuthOnboardingError("Usuário ou empresa ativa não encontrada.")
        if not self._linked_company(user.id, company.id):
            raise McpOAuthOnboardingError("O usuário deve estar vinculado à empresa no APP32 antes de habilitar o MCP.")
        issuer = self._issuer()
        if not issuer:
            raise McpOAuthOnboardingError("Issuer OAuth não está configurado para este ambiente.")
        try:
            keycloak_subject = self._provisioner_factory().ensure_user(
                email=user.email, name=user.name, temporary_password=temporary_password,
            )
        except KeycloakProvisioningError as exc:
            raise McpOAuthOnboardingError(str(exc)) from exc
        principal = IdentityPrincipal.query.filter_by(user_id=user.id, subject_type="USER").first()
        if principal is None:
            principal = IdentityPrincipal(subject_type="USER", user_id=user.id, status="active", label=user.email)
            db.session.add(principal)
            db.session.flush()
        principal.status, principal.revoked_at = "active", None
        identity = ExternalIdentity.query.filter_by(issuer=issuer, subject=keycloak_subject).first()
        if identity is not None and identity.principal_id != principal.id:
            raise McpOAuthOnboardingError("A identidade Keycloak já está vinculada a outro usuário APP32.")
        if identity is None:
            db.session.add(ExternalIdentity(principal_id=principal.id, issuer=issuer, subject=keycloak_subject, provider_alias="keycloak"))
        grant = PrincipalCompanyGrant.query.filter_by(principal_id=principal.id, company_id=company.id).first()
        if grant is None:
            grant = PrincipalCompanyGrant(principal_id=principal.id, company_id=company.id, role=user.role or "collaborator", granted_by_user_id=actor_user_id, status="active", starts_at=datetime.utcnow())
            db.session.add(grant)
        else:
            grant.status, grant.revoked_at, grant.role, grant.granted_by_user_id = "active", None, user.role or "collaborator", actor_user_id
        db.session.commit()
        return self.status(user_id=user.id)

    def revoke(self, *, user_id: int, company_id: int, actor_user_id: int) -> dict:
        principal = IdentityPrincipal.query.filter_by(user_id=user_id, subject_type="USER").first()
        if principal is None:
            raise McpOAuthOnboardingError("Usuário não possui onboarding MCP OAuth.")
        grant = PrincipalCompanyGrant.query.filter_by(principal_id=principal.id, company_id=company_id).first()
        if grant is None:
            raise McpOAuthOnboardingError("Grant MCP OAuth não encontrado para esta empresa.")
        grant.status, grant.revoked_at, grant.granted_by_user_id = "revoked", datetime.utcnow(), actor_user_id
        db.session.commit()
        return self.status(user_id=user_id)


mcp_oauth_onboarding_service = McpOAuthOnboardingService()