"""Unifica as linhagens OAuth e memberships já aplicadas em produção.

A revisão ``20260909_1100`` foi aplicada no ambiente Configr e não pode ser
removida do histórico. Esta revisão de merge não executa DDL: apenas transforma
as duas cabeças versionadas em uma única linha Alembic auditável.

Revision ID: 20260910_1000
Revises: 20260909_1000, 20260909_1100
Create Date: 2026-09-10 18:00:00.000000
"""

revision = "20260910_1000"
down_revision = ("20260909_1000", "20260909_1100")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass