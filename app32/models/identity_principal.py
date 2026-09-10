"""Identidades técnicas e grants de tenant para a evolução OAuth/OIDC.

Estes modelos não emitem nem validam tokens. Eles preservam a autoridade de
autorização do APP32 e permitem que USER, SERVICE e AGENT tenham vínculo
explícito, auditável e escopado por empresa.
"""

from datetime import datetime

from . import db


class IdentityPrincipal(db.Model):
    """Ator autenticável do APP32, humano ou técnico.

    ``user_id`` é exclusivo de USER. SERVICE e AGENT nunca usam usuário humano
    sintético: exigem responsável humano e finalidade persistidos, ambos
    definidos por fluxo de gestão e nunca inferidos do token.
    """

    __tablename__ = "identity_principals"
    __table_args__ = (
        db.CheckConstraint(
            "subject_type IN ('USER', 'SERVICE', 'AGENT')",
            name="ck_identity_principal_subject_type",
        ),
        db.CheckConstraint(
            "status IN ('active', 'suspended', 'revoked')",
            name="ck_identity_principal_status",
        ),
        db.CheckConstraint(
            "(subject_type = 'USER' AND user_id IS NOT NULL AND responsible_user_id IS NULL AND purpose IS NULL) OR "
            "(subject_type IN ('SERVICE', 'AGENT') AND user_id IS NULL "
            "AND responsible_user_id IS NOT NULL AND purpose IS NOT NULL)",
            name="ck_identity_principal_subject_binding",
        ),
        db.UniqueConstraint("user_id", name="uq_identity_principal_user"),
        db.Index("ix_identity_principal_type_status", "subject_type", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    subject_type = db.Column(db.String(16), nullable=False, default="USER")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    responsible_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    status = db.Column(db.String(16), nullable=False, default="active", index=True)
    label = db.Column(db.String(160), nullable=True)
    purpose = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    revoked_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", foreign_keys=[user_id], backref=db.backref("identity_principals", lazy="dynamic"))
    responsible_user = db.relationship("User", foreign_keys=[responsible_user_id])
    external_identities = db.relationship(
        "ExternalIdentity",
        back_populates="principal",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    company_grants = db.relationship(
        "PrincipalCompanyGrant",
        back_populates="principal",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    @property
    def is_active(self) -> bool:
        return self.status == "active" and self.revoked_at is None


class ExternalIdentity(db.Model):
    """Vínculo idempotente entre ``issuer/sub`` OIDC e principal APP32."""

    __tablename__ = "external_identities"
    __table_args__ = (
        db.UniqueConstraint("issuer", "subject", name="uq_external_identity_issuer_subject"),
        db.Index("ix_external_identity_principal", "principal_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    principal_id = db.Column(
        db.Integer,
        db.ForeignKey("identity_principals.id", ondelete="CASCADE"),
        nullable=False,
    )
    issuer = db.Column(db.String(512), nullable=False)
    subject = db.Column(db.String(512), nullable=False)
    provider_alias = db.Column(db.String(80), nullable=True)
    linked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=True)

    principal = db.relationship("IdentityPrincipal", back_populates="external_identities")


class PrincipalCompanyGrant(db.Model):
    """Grant atual de um principal para uma empresa específica.

    Capabilities não são duplicadas aqui: continuam no catálogo/policy
    canônicos. Este registro delimita o tenant, o papel-base e o lifecycle do
    vínculo; toda autorização efetiva ainda é reavaliada pelo APP32.
    """

    __tablename__ = "principal_company_grants"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('active', 'suspended', 'revoked', 'expired')",
            name="ck_principal_company_grant_status",
        ),
        db.CheckConstraint(
            "expires_at IS NULL OR starts_at IS NULL OR expires_at >= starts_at",
            name="ck_principal_company_grant_validity",
        ),
        db.UniqueConstraint("principal_id", "company_id", name="uq_principal_company_grant"),
        db.Index("ix_principal_company_grant_company_status", "company_id", "status"),
        db.Index("ix_principal_company_grant_principal_status", "principal_id", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    principal_id = db.Column(
        db.Integer,
        db.ForeignKey("identity_principals.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(64), nullable=False, default="colaborador")
    status = db.Column(db.String(16), nullable=False, default="active")
    starts_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    granted_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    principal = db.relationship("IdentityPrincipal", back_populates="company_grants")
    company = db.relationship("Company", foreign_keys=[company_id], backref=db.backref("principal_grants", lazy="dynamic"))
    granted_by = db.relationship("User", foreign_keys=[granted_by_user_id])

    def inactive_reason_at(self, now: datetime) -> str | None:
        """Retorna o motivo canônico de inatividade no instante UTC informado."""

        if self.status != "active" or self.revoked_at is not None:
            return "inactive"
        if self.starts_at is not None and self.starts_at > now:
            return "not_started"
        if self.expires_at is not None and self.expires_at < now:
            return "expired"
        return None

    def is_active_at(self, now: datetime) -> bool:
        return self.inactive_reason_at(now) is None

    @property
    def is_active(self) -> bool:
        return self.is_active_at(datetime.utcnow())
