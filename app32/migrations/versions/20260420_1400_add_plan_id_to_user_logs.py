"""Adiciona coluna plan_id ausente em user_logs

A coluna plan_id faz parte do modelo UserLog (schema legado, tipo TEXT),
mas nunca foi criada no banco de dados via migration, causando erro
'column user_logs.plan_id does not exist' em qualquer consulta ORM na tabela.

Revision ID: 20260420_1400
Revises: 20260420_1300
Create Date: 2026-04-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260420_1400"
down_revision = "20260420_1300"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("user_logs")}
    if "plan_id" not in columns:
        op.add_column("user_logs", sa.Column("plan_id", sa.Text(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("user_logs")}
    if "plan_id" in columns:
        op.drop_column("user_logs", "plan_id")
