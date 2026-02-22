# Guia de Implementação - Migrations PEV no APP32

## ✅ Checklist Pré-Implementação

- [ ] Backup do banco de dados criado
- [ ] Ambiente de testes validado
- [ ] Permissões de banco verificadas
- [ ] Documentação revisada

## 📋 Passo a Passo de Implementação

### Passo 1: Preparação

```bash
# Comandos de preparação
# Certifique-se de estar no diretório correto do projeto
cd /caminho/para/seu/projeto

# Ative o ambiente virtual, se aplicável
source venv/bin/activate

# Verifique a versão atual do banco de dados
alembic current
```

### Passo 2: Criação de Arquivos

Crie os seguintes arquivos de migration no diretório `migrations/versions/`:

#### Arquivo 1: `001_pev_base.py`

```python
"""Create PEV base tables

Revision ID: 001_pev_base
Revises: 
Create Date: 2026-02-15 20:04:30

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_pev_base'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create base PEV tables."""
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='draft'),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('progress_overall', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('objectives', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("type IN ('growth', 'implantation')", name='check_plan_type'),
        sa.CheckConstraint("status IN ('draft', 'active', 'completed', 'archived')", name='check_plan_status'),
        sa.CheckConstraint('progress_overall >= 0 AND progress_overall <= 100', name='check_progress_range'),
        sa.UniqueConstraint('company_id', 'name', name='unique_plan_name_per_company')
    )

def downgrade():
    """Drop base PEV tables."""
    op.drop_table('plans')
```

#### Arquivo 2: `002_pev_growth.py`

```python
"""Create PEV growth tables

Revision ID: 002_pev_growth
Revises: 001_pev_base
Create Date: 2026-02-15 20:04:30

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_pev_growth'
down_revision = '001_pev_base'
branch_labels = None
depends_on = None

def upgrade():
    """Create growth-specific PEV tables."""
    op.create_table(
        'okrs_global',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('objective', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id']),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    """Drop growth-specific PEV tables."""
    op.drop_table('okrs_global')
```

### Passo 3: Execução de Migrations

```bash
# Comandos para executar
alembic upgrade head
```

### Passo 4: Validação

```sql
-- Queries de validação
SELECT * FROM plans LIMIT 1;
SELECT * FROM okrs_global LIMIT 1;
```

### Passo 5: Testes

```python
# Testes a executar
# Teste de criação de um novo plano
def test_create_plan(session):
    new_plan = Plan(name="New Plan", company_id=1, type="growth")
    session.add(new_plan)
    session.commit()
    assert new_plan.id is not None

# Teste de criação de um novo OKR
def test_create_okr(session):
    new_okr = OKRGlobal(plan_id=1, objective="Increase Sales")
    session.add(new_okr)
    session.commit()
    assert new_okr.id is not None
```

## 🔧 Troubleshooting

### Problema 1: Erro de Conexão
**Solução:** Verifique se o banco de dados está ativo e se as credenciais estão corretas no arquivo de configuração do Alembic.

### Problema 2: Erro de Foreign Key
**Solução:** Certifique-se de que as tabelas referenciadas já existem e que as constraints estão corretas.

## 📊 Validação Final

```sql
-- Queries para confirmar sucesso
SELECT COUNT(*) FROM plans;
SELECT COUNT(*) FROM okrs_global;
```

## 🎯 Próximos Passos

1. Revisar logs de execução para garantir que não houve erros.
2. Atualizar a documentação do projeto com as novas tabelas e suas relações.
3. Planejar a próxima fase de desenvolvimento ou migração.