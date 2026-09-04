"""Perfis de custo estimado por cargo e vigência; não cadastra valores presumidos."""
from alembic import op
import sqlalchemy as sa

revision = "20260904_1600"
down_revision = "20260904_1500"
branch_labels = None
depends_on = None


def upgrade():
    components = ("base_salary", "charges", "benefits", "other_costs")
    op.create_table(
        "role_cost_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date()),
        sa.Column("currency", sa.String(3), nullable=False),
        *(sa.Column(field, sa.Numeric(14, 2)) for field in components),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["company_id", "role_id"], ["roles.company_id", "roles.id"], name="fk_role_cost_tenant_role"),
        sa.CheckConstraint("ends_on IS NULL OR ends_on > starts_on", name="ck_role_cost_dates"),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_role_cost_currency"),
        *(sa.CheckConstraint(f"{field} IS NULL OR ({field} >= 0 AND {field} <= 999999999999.99)", name=f"ck_role_cost_{field}") for field in components),
        sa.UniqueConstraint("company_id", "role_id", "starts_on", name="uq_role_cost_start"),
    )


def downgrade():
    # Exportar perfis e histórico antes do rollback.
    op.drop_table("role_cost_profiles")
