"""Ocupações temporais com referências compostas tenant-safe.

Não migra cargos legados nem presume vigência ou dedicação.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260904_1500"
down_revision = "20260904_1400"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("uq_roles_company_id", "roles", ["company_id", "id"])
    op.create_unique_constraint("uq_employees_company_id", "employees", ["company_id", "id"])
    op.create_table(
        "employee_role_occupancies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date()),
        sa.Column("weekly_hours", sa.Numeric(5, 2)),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ended_by_user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("ended_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["company_id", "employee_id"], ["employees.company_id", "employees.id"], name="fk_occupancy_tenant_employee"),
        sa.ForeignKeyConstraint(["company_id", "role_id"], ["roles.company_id", "roles.id"], name="fk_occupancy_tenant_role"),
        sa.CheckConstraint("ends_on IS NULL OR ends_on > starts_on", name="ck_occupancy_dates"),
        sa.CheckConstraint("weekly_hours IS NULL OR (weekly_hours > 0 AND weekly_hours <= 168)", name="ck_occupancy_hours"),
        sa.UniqueConstraint("company_id", "employee_id", "role_id", "starts_on", name="uq_occupancy_start"),
    )
    op.create_index("ix_occupancy_company_employee", "employee_role_occupancies", ["company_id", "employee_id"])
    op.create_index("ix_occupancy_company_role", "employee_role_occupancies", ["company_id", "role_id"])


def downgrade():
    # Exportar histórico antes de executar: rollback remove as ocupações.
    op.drop_table("employee_role_occupancies")
    op.drop_constraint("uq_employees_company_id", "employees", type_="unique")
    op.drop_constraint("uq_roles_company_id", "roles", type_="unique")
