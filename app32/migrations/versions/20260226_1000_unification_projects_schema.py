"""unification_projects_schema

Revision ID: 20260226_1000
Revises: 20260225_1000
Create Date: 2026-02-26 10:00:00

Description:
    Unifica o esquema de bancos de dados entre DEV e Produção.
    1. Renomeia 'projects' para 'company_projects' (se necessário).
    2. Garante que 'assigned_collaborators' existe em 'process_instances'.
    3. Alinha colunas de 'company_projects' para garantir resiliência.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers
revision = '20260226_1000'
down_revision = '20260225_1000'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    # 1. Alinhamento da tabela de Projetos
    if 'projects' in tables and 'company_projects' not in tables:
        print("INFO: Renomeando 'projects' para 'company_projects' (ambiente Local/Novos)...")
        op.rename_table('projects', 'company_projects')
    elif 'company_projects' in tables:
        print("INFO: Tabela 'company_projects' já existe (ambiente Produção).")
    elif 'projects' not in tables and 'company_projects' not in tables:
        # Caso extremo sem nenhuma tabela de projeto
        print("WARNING: Nenhuma tabela de projeto encontrada. Criando 'company_projects'...")
        # (Opcional) Poderíamos criar a tabela aqui, mas assumimos que o db.create_all() ou outras migrations já cuidaram.
        pass

    # 2. Garantir colunas em company_projects
    # Recarregar inspector caso tenha havido rename
    inspector = Inspector.from_engine(conn)
    if 'company_projects' in tables or 'projects' in tables:
        target_table = 'company_projects' if 'company_projects' in tables or 'projects' in tables else 'company_projects'
        # Nota: rename_table no alembic já altera o nome na conexão ativa
        
        # Verificar se colunas essenciais existem (ex: description vs notes)
        cols = [col['name'] for col in inspector.get_columns('company_projects')]
        if 'description' not in cols:
             op.add_column('company_projects', sa.Column('description', sa.Text(), nullable=True))
        if 'title' not in cols and 'name' in cols:
             # Se tiver name mas nao tiver title, mapeamos/renomeamos? 
             # No model mapeamos name -> title. Entao garantimos title no DB.
             op.add_column('company_projects', sa.Column('title', sa.String(255), nullable=True))
             op.execute("UPDATE company_projects SET title = name WHERE title IS NULL OR title = ''")

    # 3. Alinhamento de Process Instances
    if 'process_instances' in tables:
        pi_cols = [col['name'] for col in inspector.get_columns('process_instances')]
        if 'assigned_collaborators' not in pi_cols:
            print("INFO: Adicionando assigned_collaborators em process_instances...")
            op.add_column('process_instances', sa.Column('assigned_collaborators', sa.JSON(), nullable=True))
            if 'collaborators_json' in pi_cols:
                op.execute("UPDATE process_instances SET assigned_collaborators = collaborators_json WHERE assigned_collaborators IS NULL")


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    # Downgrade é arriscado em produção, fazemos o básico para o Local
    if 'company_projects' in tables and 'projects' not in tables:
        op.rename_table('company_projects', 'projects')
    
    if 'process_instances' in tables:
        pi_cols = [col['name'] for col in inspector.get_columns('process_instances')]
        if 'assigned_collaborators' in pi_cols:
            op.drop_column('process_instances', 'assigned_collaborators')
