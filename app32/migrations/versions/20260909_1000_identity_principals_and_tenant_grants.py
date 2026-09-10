"""Base aditiva de principals OAuth/OIDC e grants tenant-safe.

Não há backfill ou alteração no login/tokens legados nesta migration.
"""

from alembic import op
import sqlalchemy as sa


revision = "20260909_1000"
down_revision = "20260907_1900"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "identity_principals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_type", sa.String(length=16), nullable=False, server_default="USER"),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("responsible_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("label", sa.String(length=160), nullable=True),
        sa.Column("purpose", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "subject_type IN ('USER', 'SERVICE', 'AGENT')",
            name="ck_identity_principal_subject_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'revoked')",
            name="ck_identity_principal_status",
        ),
        sa.CheckConstraint(
            "(subject_type = 'USER' AND user_id IS NOT NULL AND responsible_user_id IS NULL AND purpose IS NULL) OR "
            "(subject_type IN ('SERVICE', 'AGENT') AND user_id IS NULL "
            "AND responsible_user_id IS NOT NULL AND purpose IS NOT NULL)",
            name="ck_identity_principal_subject_binding",
        ),
        sa.UniqueConstraint("user_id", name="uq_identity_principal_user"),
    )
    op.create_index("ix_identity_principals_user_id", "identity_principals", ["user_id"])
    op.create_index("ix_identity_principals_responsible_user_id", "identity_principals", ["responsible_user_id"])
    op.create_index("ix_identity_principals_status", "identity_principals", ["status"])
    op.create_index("ix_identity_principal_type_status", "identity_principals", ["subject_type", "status"])

    op.create_table(
        "external_identities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "principal_id",
            sa.Integer(),
            sa.ForeignKey("identity_principals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("issuer", sa.String(length=512), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("provider_alias", sa.String(length=80), nullable=True),
        sa.Column("linked_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("issuer", "subject", name="uq_external_identity_issuer_subject"),
    )
    op.create_index("ix_external_identity_principal", "external_identities", ["principal_id"])

    op.create_table(
        "principal_company_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "principal_id",
            sa.Integer(),
            sa.ForeignKey("identity_principals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False, server_default="colaborador"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("granted_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'revoked', 'expired')",
            name="ck_principal_company_grant_status",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR starts_at IS NULL OR expires_at >= starts_at",
            name="ck_principal_company_grant_validity",
        ),
        sa.UniqueConstraint("principal_id", "company_id", name="uq_principal_company_grant"),
    )
    op.create_index(
        "ix_principal_company_grant_company_status",
        "principal_company_grants",
        ["company_id", "status"],
    )
    op.create_index(
        "ix_principal_company_grant_principal_status",
        "principal_company_grants",
        ["principal_id", "status"],
    )


def downgrade():
    op.drop_table("principal_company_grants")
    op.drop_table("external_identities")
    op.drop_table("identity_principals")
