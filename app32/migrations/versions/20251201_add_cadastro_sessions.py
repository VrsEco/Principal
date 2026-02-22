"""add_cadastro_sessions

Revision ID: 20251201_0001
Revises: 20251130_1131
Create Date: 2025-12-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251201_0001'
down_revision = '20251130_1131'  # Última migration válida
branch_labels = None
depends_on = None


def upgrade():
    """
    Cria tabela cadastro_sessions para persistir cadastros em andamento
    
    ⚠️ PostgreSQL ONLY - SQLite não é suportado
    Este sistema usa APENAS PostgreSQL conforme política do projeto
    """
    
    # Verificar se a tabela já existe
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'cadastro_sessions' in existing_tables:
        print("Tabela cadastro_sessions já existe. Pulando criação.")
        return
    
    # ⚠️ PostgreSQL ONLY - Usar sa.JSON() que é tipo nativo PostgreSQL
    # SQLite não é suportado neste projeto
    op.create_table(
        'cadastro_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('tipo_cadastro', sa.String(length=20), nullable=False),
        sa.Column('estado', sa.String(length=50), nullable=True, server_default='inicial'),
        sa.Column('dados_coletados', sa.JSON(), nullable=True),  # PostgreSQL JSON type
        sa.Column('empresa_id', sa.Integer(), nullable=True),
        sa.Column('campo_atual', sa.String(length=50), nullable=True),
        sa.Column('progresso', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['empresa_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar índices para melhor performance
    op.create_index('ix_cadastro_sessions_user_id', 'cadastro_sessions', ['user_id'])
    op.create_index('ix_cadastro_sessions_empresa_id', 'cadastro_sessions', ['empresa_id'])
    op.create_index('ix_cadastro_sessions_is_deleted', 'cadastro_sessions', ['is_deleted'])


def downgrade():
    """Remove tabela cadastro_sessions"""
    op.drop_index('ix_cadastro_sessions_is_deleted', table_name='cadastro_sessions')
    op.drop_index('ix_cadastro_sessions_empresa_id', table_name='cadastro_sessions')
    op.drop_index('ix_cadastro_sessions_user_id', table_name='cadastro_sessions')
    op.drop_table('cadastro_sessions')

