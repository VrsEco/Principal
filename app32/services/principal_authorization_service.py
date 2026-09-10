"""Resolução de principal e grants empresariais para OAuth/OIDC.

Esta service não valida JWT nem emite tokens. Ela transforma uma identidade já
validada em uma decisão de autorização APP32, sempre exigindo company_id
explícito para dados empresariais.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Callable, Iterator

from flask import has_app_context

from models.identity_principal import ExternalIdentity, IdentityPrincipal, PrincipalCompanyGrant


@dataclass(frozen=True)
class PrincipalAuthorizationDecision:
    """Resultado auditável e sem efeitos colaterais da resolução de grant."""

    allowed: bool
    company_id: int | None
    reason: str
    principal: IdentityPrincipal | None = None
    grant: PrincipalCompanyGrant | None = None

    @property
    def role(self) -> str | None:
        return self.grant.role if self.allowed and self.grant is not None else None


@dataclass(frozen=True)
class ExternalPrincipalResolution:
    """Resultado do vínculo global ``issuer/sub`` antes do escopo de tenant.

    O resultado não autoriza dados empresariais por si só. O consumidor deve
    ainda resolver o ``PrincipalCompanyGrant`` para uma empresa explícita.
    """

    allowed: bool
    reason: str
    principal: IdentityPrincipal | None = None
    external_identity: ExternalIdentity | None = None

    @property
    def principal_id(self) -> int | None:
        if not self.allowed or self.principal is None:
            return None
        return self.principal.id


class PrincipalAuthorizationService:
    """Autoridade de vínculo principal → empresa, independente de HTTP/MCP."""

    def __init__(
        self,
        *,
        now_provider: Callable[[], datetime] = datetime.utcnow,
        principal_lookup: Callable[[int], IdentityPrincipal | None] | None = None,
        grant_lookup: Callable[[int, int], PrincipalCompanyGrant | None] | None = None,
        external_identity_lookup: Callable[[str, str], ExternalIdentity | None] | None = None,
    ):
        self._now_provider = now_provider
        self._principal_lookup = principal_lookup or self._lookup_principal
        self._grant_lookup = grant_lookup or self._lookup_grant
        self._external_identity_lookup = external_identity_lookup or self._lookup_external_identity

    @staticmethod
    @lru_cache(maxsize=1)
    def _mcp_flask_app():
        """Cria uma única app Flask enxuta para os lookups ORM do ASGI."""

        from app import create_app

        return create_app("production")

    @staticmethod
    @contextmanager
    def _ensure_app_context() -> Iterator[None]:
        """Fornece contexto Flask ao transporte MCP ASGI sem subir workers.

        O streamable HTTP roda fora da pilha WSGI. Os lookups ORM de principal
        e grant precisam de um contexto curto quando chamados desse transporte,
        da mesma forma que o resolver de tokens MCP existentes. Isso não altera
        o caminho de testes com lookups injetados nem inicializa workers.
        """

        if has_app_context():
            yield
            return

        names = ("APP_BOOTSTRAP_DB_SCHEMA", "APP_BOOTSTRAP_RUNTIME_SERVICES")
        previous = {name: os.environ.get(name) for name in names}
        os.environ.setdefault("APP_BOOTSTRAP_DB_SCHEMA", "0")
        os.environ.setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "0")
        try:
            app = PrincipalAuthorizationService._mcp_flask_app()
            with app.app_context():
                yield
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    @classmethod
    def _lookup_principal(cls, principal_id: int) -> IdentityPrincipal | None:
        with cls._ensure_app_context():
            return IdentityPrincipal.query.filter_by(id=principal_id).first()

    @classmethod
    def _lookup_grant(cls, principal_id: int, company_id: int) -> PrincipalCompanyGrant | None:
        with cls._ensure_app_context():
            return PrincipalCompanyGrant.query.filter_by(
                principal_id=principal_id,
                company_id=company_id,
            ).first()

    @classmethod
    def _lookup_external_identity(cls, issuer: str, subject: str) -> ExternalIdentity | None:
        with cls._ensure_app_context():
            return ExternalIdentity.query.filter_by(issuer=issuer, subject=subject).first()

    @staticmethod
    def _coerce_company_id(company_id: int | str | None) -> int | None:
        if isinstance(company_id, bool) or company_id is None:
            return None
        if isinstance(company_id, int):
            return company_id if company_id > 0 else None
        raw = str(company_id).strip()
        return int(raw) if raw.isdigit() and int(raw) > 0 else None

    @staticmethod
    def _coerce_exact_external_identifier(value: str | None) -> str | None:
        """Valida presença sem normalizar issuer/sub vinculados no banco."""

        if not isinstance(value, str) or not value or not value.strip():
            return None
        return value

    def evaluate_grant(
        self,
        *,
        principal: IdentityPrincipal | None,
        grant: PrincipalCompanyGrant | None,
        company_id: int | str | None,
    ) -> PrincipalAuthorizationDecision:
        """Avalia o grant sem fallback de tenant ou autorização implícita."""

        resolved_company_id = self._coerce_company_id(company_id)
        if resolved_company_id is None:
            return PrincipalAuthorizationDecision(False, None, "company_id obrigatório para autorização empresarial")
        if principal is None:
            return PrincipalAuthorizationDecision(False, resolved_company_id, "principal não encontrado")
        if not principal.is_active:
            return PrincipalAuthorizationDecision(
                False,
                resolved_company_id,
                "principal inativo, suspenso ou revogado",
                principal=principal,
            )
        if grant is None:
            return PrincipalAuthorizationDecision(
                False,
                resolved_company_id,
                "grant do principal para a empresa não encontrado",
                principal=principal,
            )
        if grant.company_id != resolved_company_id:
            return PrincipalAuthorizationDecision(
                False,
                resolved_company_id,
                "grant não pertence à empresa solicitada",
                principal=principal,
                grant=grant,
            )
        if principal.id is not None and grant.principal_id != principal.id:
            return PrincipalAuthorizationDecision(
                False,
                resolved_company_id,
                "grant não pertence ao principal autenticado",
                principal=principal,
                grant=grant,
            )
        now = self._now_provider()
        inactive_reason = grant.inactive_reason_at(now)
        if inactive_reason == "inactive":
            return PrincipalAuthorizationDecision(
                False,
                resolved_company_id,
                "grant inativo, suspenso ou revogado",
                principal=principal,
                grant=grant,
            )
        if inactive_reason == "not_started":
            return PrincipalAuthorizationDecision(
                False,
                resolved_company_id,
                "grant ainda não está vigente",
                principal=principal,
                grant=grant,
            )
        if inactive_reason == "expired":
            return PrincipalAuthorizationDecision(
                False,
                resolved_company_id,
                "grant expirado",
                principal=principal,
                grant=grant,
            )
        return PrincipalAuthorizationDecision(
            True,
            resolved_company_id,
            "ok",
            principal=principal,
            grant=grant,
        )

    def resolve_for_company(
        self,
        *,
        principal_id: int,
        company_id: int | str | None,
    ) -> PrincipalAuthorizationDecision:
        """Busca o principal e somente o grant da empresa solicitada."""

        return self._resolve_for_company_in_context(
            principal_id=principal_id,
            company_id=company_id,
        )

    def _resolve_for_company_in_context(
        self,
        *,
        principal_id: int,
        company_id: int | str | None,
    ) -> PrincipalAuthorizationDecision:
        """Implementação que pressupõe contexto Flask já estabelecido."""

        resolved_company_id = self._coerce_company_id(company_id)
        if resolved_company_id is None:
            return self.evaluate_grant(principal=None, grant=None, company_id=company_id)
        principal = self._principal_lookup(principal_id)
        if principal is None:
            return self.evaluate_grant(principal=None, grant=None, company_id=resolved_company_id)
        grant = self._grant_lookup(principal.id, resolved_company_id)
        return self.evaluate_grant(principal=principal, grant=grant, company_id=resolved_company_id)

    def resolve_external_principal(
        self,
        *,
        issuer: str,
        subject: str,
    ) -> ExternalPrincipalResolution:
        """Resolve um vínculo OIDC provisionado, sem conceder escopo de tenant.

        Esta é a fronteira usada pelo futuro verifier JWT: somente ``issuer``
        e ``subject`` já validados podem chegar aqui. Não há fallback por
        e-mail, client_id, label ou dados controlados pelo cliente.
        """

        return self._resolve_external_principal_in_context(issuer=issuer, subject=subject)

    def _resolve_external_principal_in_context(
        self,
        *,
        issuer: str,
        subject: str,
    ) -> ExternalPrincipalResolution:
        normalized_issuer = self._coerce_exact_external_identifier(issuer)
        normalized_subject = self._coerce_exact_external_identifier(subject)
        if not normalized_issuer or not normalized_subject:
            return ExternalPrincipalResolution(
                False,
                "issuer e subject são obrigatórios para identidade externa",
            )

        external_identity = self._external_identity_lookup(normalized_issuer, normalized_subject)
        if external_identity is None:
            return ExternalPrincipalResolution(False, "identidade externa não vinculada")

        principal = self._principal_lookup(external_identity.principal_id)
        if principal is None:
            return ExternalPrincipalResolution(
                False,
                "principal da identidade externa não encontrado",
                external_identity=external_identity,
            )
        if not principal.is_active:
            return ExternalPrincipalResolution(
                False,
                "principal da identidade externa está inativo, suspenso ou revogado",
                principal=principal,
                external_identity=external_identity,
            )
        return ExternalPrincipalResolution(
            True,
            "ok",
            principal=principal,
            external_identity=external_identity,
        )

    def resolve_external_identity_for_company(
        self,
        *,
        issuer: str,
        subject: str,
        company_id: int | str | None,
    ) -> PrincipalAuthorizationDecision:
        """Resolve issuer/sub previamente vinculados; nunca faz auto-link por e-mail."""

        resolved_company_id = self._coerce_company_id(company_id)
        if resolved_company_id is None:
            return self.evaluate_grant(principal=None, grant=None, company_id=company_id)
        resolution = self._resolve_external_principal_in_context(issuer=issuer, subject=subject)
        if not resolution.allowed or resolution.principal_id is None:
            return PrincipalAuthorizationDecision(
                False,
                resolved_company_id,
                resolution.reason,
            )
        return self._resolve_for_company_in_context(
            principal_id=resolution.principal_id,
            company_id=resolved_company_id,
        )


principal_authorization_service = PrincipalAuthorizationService()
