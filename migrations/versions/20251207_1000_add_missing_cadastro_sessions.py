"""Create cadastro_sessions table if the migration that originally added it did not run.

Revision ID: 20251207_1000
Revises: 20251203_1100
Create Date: 2025-12-07 10:00:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251207_1000"
down_revision = "20251203_1100"
branch_labels = None
depends_on = None


def _cadastro_table_exists() -> bool:
    inspector = sa.inspect(op.get_bind())
    return "cadastro_sessions" in inspector.get_table_names()


def upgrade():
    """Ensure cadastro_sessions exists before inserting assisted registrations."""
    if _cadastro_table_exists():
        return

    op.create_table(
        "cadastro_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tipo_cadastro", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=50), nullable=True, server_default="'inicial'"),
        sa.Column("dados_coletados", sa.JSON(), nullable=True),
        sa.Column("empresa_id", sa.Integer(), nullable=True),
        sa.Column("campo_atual", sa.String(length=50), nullable=True),
        sa.Column("progresso", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["empresa_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_cadastro_sessions_user_id", "cadastro_sessions", ["user_id"])
    op.create_index("ix_cadastro_sessions_empresa_id", "cadastro_sessions", ["empresa_id"])
    op.create_index("ix_cadastro_sessions_is_deleted", "cadastro_sessions", ["is_deleted"])


def downgrade():
    """Remove cadastro_sessions so downgrade stays consistent."""
    if not _cadastro_table_exists():
        return

    op.execute(sa.text("DROP INDEX IF EXISTS ix_cadastro_sessions_is_deleted"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_cadastro_sessions_empresa_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_cadastro_sessions_user_id"))

    op.drop_table("cadastro_sessions")
