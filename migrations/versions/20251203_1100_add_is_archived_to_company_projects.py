"""add is_archived to company_projects

Revision ID: 20251203_1100
Revises: 20251203_1000
Create Date: 2025-12-03 11:00:00

Description:
    Adiciona campo is_archived à tabela company_projects para suportar
    arquivamento de projetos concluídos.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251203_1100"
down_revision = "20251203_1000"
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona o campo is_archived à tabela company_projects.
    """
    # Adicionar coluna is_archived
    with op.batch_alter_table("company_projects") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_archived",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
    
    print("\n" + "="*60)
    print("✅ Campo is_archived adicionado à tabela company_projects")
    print("="*60 + "\n")


def downgrade():
    """
    Remove o campo is_archived da tabela company_projects.
    """
    with op.batch_alter_table("company_projects") as batch_op:
        batch_op.drop_column("is_archived")
    
    print("\n" + "="*60)
    print("⚠️  Campo is_archived removido da tabela company_projects")
    print("="*60 + "\n")




