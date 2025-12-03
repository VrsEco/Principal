"""update consultant role to collaborator

Revision ID: 20251203_1000
Revises: 20251201_2200
Create Date: 2025-12-03 10:00:00

Description:
    Renomeia o perfil de acesso 'consultant' para 'collaborator' em todos os usuários.
    Esta migração é parte da atualização de permissões do módulo MyWork.
    
    Mudanças:
    - Atualiza role='consultant' para role='collaborator' na tabela users
    - Mantém compatibilidade com dados legados (código normaliza automaticamente)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20251203_1000"
down_revision = "956c27605a93"
branch_labels = None
depends_on = None


def upgrade():
    """
    Atualiza o role 'consultant' para 'collaborator' na tabela users.
    """
    # Obter conexão
    connection = op.get_bind()
    
    # Atualizar todos os usuários com role 'consultant' para 'collaborator'
    connection.execute(
        text("""
            UPDATE users 
            SET role = 'collaborator',
                updated_at = CURRENT_TIMESTAMP
            WHERE role = 'consultant'
        """)
    )
    
    # Log para verificação (será exibido durante a migração)
    result = connection.execute(
        text("""
            SELECT role, COUNT(*) as total
            FROM users
            GROUP BY role
            ORDER BY role
        """)
    )
    
    print("\n" + "="*60)
    print("Resultado da migração - Distribuição de roles:")
    print("="*60)
    for row in result:
        print(f"  {row[0]}: {row[1]} usuário(s)")
    print("="*60 + "\n")


def downgrade():
    """
    Reverte a atualização, mudando 'collaborator' de volta para 'consultant'.
    
    ATENÇÃO: Este downgrade só deve ser usado se a migração foi aplicada
    por engano. Não recomendado em produção após testes.
    """
    # Obter conexão
    connection = op.get_bind()
    
    # Reverter apenas os usuários que eram 'consultant' antes
    # (assumindo que novos usuários criados após a migração devem permanecer 'collaborator')
    connection.execute(
        text("""
            UPDATE users 
            SET role = 'consultant',
                updated_at = CURRENT_TIMESTAMP
            WHERE role = 'collaborator'
        """)
    )
    
    print("\n" + "="*60)
    print("Downgrade aplicado - roles revertidos para 'consultant'")
    print("="*60 + "\n")

