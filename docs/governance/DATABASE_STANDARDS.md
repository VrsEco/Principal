# 🗄️ Padrões de Banco de Dados

**Última Atualização:** 28/10/2025  
**Versão:** 1.0  
**Status:** ✅ Obrigatório

---

## 🎯 Princípios

1. **Compatibilidade** - Código deve funcionar em PostgreSQL E SQLite
2. **Normalização** - Evitar redundância de dados
3. **Performance** - Indexar campos consultados frequentemente
4. **Integridade** - Usar constraints e foreign keys
5. **Documentação** - Migrations devem ser claras

---

## 🏗️ Infraestrutura Oficial (28/10/2025)

- **Instância primária:** PostgreSQL 18 instalado no host Windows (serviço corporativo oficial)  
- **Acesso por containers:** utilizar `host.docker.internal:5432` com as credenciais definidas em `.env`
- **Scripts oficiais:** `scripts/backup/run_pg_backup.ps1` gera `pg_dump` e comprime o resultado em `backups/`
- **Agendamento:** tarefa `GestaoVersus_Postgres_Backup` (Windows Task Scheduler) executa os backups às 12h, 18h e 22h
- **Restauração:** usar os scripts em `scripts/backup/` apontando para a instância do host
- **Monitoramento:** verificar `backups/postgres_backup.log` para acompanhar sucesso ou falhas diárias

### Helpers de conexão (APP30)

- Sempre que montar `SQLALCHEMY_DATABASE_URI`, `create_engine` ou `psycopg2.connect`, reutilize `utils/env_helpers.normalize_database_url()` e `normalize_docker_host()`.
- Isso garante que ambientes fora de Docker traduzam `host.docker.internal` → `localhost`, evitando `UnicodeDecodeError` e timeouts em desenvolvimento Windows.
- Novos scripts/services **devem** importar esses helpers; acessos diretos ao `.env` sem normalização estão proibidos.

---

## 🏗️ Estrutura de Tabelas

### Nomenclatura

#### Tabelas

```sql
-- ✅ BOM - Plural, snake_case
CREATE TABLE users (...);
CREATE TABLE company_projects (...);
CREATE TABLE indicator_goals (...);

-- ❌ RUIM
CREATE TABLE User (...);          -- PascalCase
CREATE TABLE user (...);          -- Singular
CREATE TABLE companyProjects (...);  -- camelCase
```

#### Colunas

```sql
-- ✅ BOM - snake_case, descritivo
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    project_name VARCHAR(200),
    start_date DATE,
    created_at TIMESTAMP,
    company_id INTEGER
);

-- ❌ RUIM
CREATE TABLE projects (
    ID INTEGER PRIMARY KEY,        -- Maiúsculo
    ProjectName VARCHAR(200),      -- PascalCase
    dt DATE,                       -- Abreviação obscura
    companyId INTEGER              -- camelCase
);
```

#### Primary Keys

```sql
-- ✅ BOM - Sempre 'id' como PK
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT
);

-- ⚠️ Aceito apenas para tabelas associativas
CREATE TABLE project_participants (
    project_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (project_id, user_id)
);

-- ❌ RUIM
CREATE TABLE projects (
    project_id INTEGER PRIMARY KEY  -- Redundante
);
```

#### Foreign Keys

```sql
-- ✅ BOM - Sufixo '_id' + nome da tabela no singular
CREATE TABLE projects (
    company_id INTEGER REFERENCES companies(id),
    owner_id INTEGER REFERENCES users(id)
);

-- ❌ RUIM
CREATE TABLE projects (
    company INTEGER,               -- Sem sufixo _id
    CompanyId INTEGER,             -- PascalCase
    fk_company INTEGER             -- Prefixo desnecessário
);
```

---

## 📊 Tipos de Dados

### Compatibilidade PostgreSQL/SQLite

| Tipo de Dado | PostgreSQL | SQLite | Uso Recomendado |
|--------------|------------|--------|-----------------|
| Inteiro | INTEGER | INTEGER | ✅ Usar INTEGER |
| Texto Curto | VARCHAR(n) | TEXT | ✅ Usar VARCHAR(n) |
| Texto Longo | TEXT | TEXT | ✅ Usar TEXT |
| Decimal | DECIMAL(10,2) | REAL | ✅ Usar DECIMAL |
| Data | DATE | TEXT | ✅ Usar DATE |
| Data/Hora | TIMESTAMP | TEXT | ✅ Usar TIMESTAMP |
| Booleano | BOOLEAN | INTEGER | ✅ Usar BOOLEAN |
| JSON | JSON | JSON | ✅ Usar JSON |

### ❌ Tipos Incompatíveis (Evitar)

```sql
-- ❌ Específico PostgreSQL
JSONB              -- Usar JSON
UUID               -- Usar VARCHAR(36)
ARRAY              -- Usar relação 1:N ou JSON
ENUM               -- Usar VARCHAR com CHECK constraint

-- ❌ Específico SQLite
BLOB               -- Usar bytea no PostgreSQL
```

### ✅ Exemplos Compatíveis

```sql
-- Inteiros
id INTEGER PRIMARY KEY
quantity INTEGER NOT NULL DEFAULT 0

-- Strings
name VARCHAR(200) NOT NULL
description TEXT
email VARCHAR(255) UNIQUE

-- Decimais
price DECIMAL(10, 2)
percentage DECIMAL(5, 2)

-- Datas
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
birth_date DATE
updated_at TIMESTAMP

-- Booleanos
is_active BOOLEAN DEFAULT TRUE
is_deleted BOOLEAN DEFAULT FALSE

-- JSON
metadata JSON
settings JSON
```

---

## 🔗 Relacionamentos

### One-to-Many (1:N)

```sql
-- ✅ BOM
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL
);

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE
);

-- SQLAlchemy
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    projects = db.relationship('Project', backref='company', cascade='all, delete-orphan')

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
```

### Many-to-Many (N:M)

```sql
-- ✅ BOM - Tabela associativa
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL
);

CREATE TABLE project_participants (
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, user_id)
);

-- SQLAlchemy
class Project(db.Model):
    participants = db.relationship(
        'User',
        secondary='project_participants',
        backref='participating_projects'
    )
```

### Self-Referencing

```sql
-- ✅ BOM - Hierarquia
CREATE TABLE departments (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    parent_id INTEGER REFERENCES departments(id) ON DELETE SET NULL
);

-- SQLAlchemy
class Department(db.Model):
    parent_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    parent = db.relationship('Department', remote_side=[id], backref='children')
```

---

## 🔐 Constraints

### NOT NULL

```sql
-- ✅ Campos obrigatórios
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(200) NOT NULL,
    bio TEXT  -- Opcional
);
```

### UNIQUE

```sql
-- ✅ Garantir unicidade
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    cpf VARCHAR(14) UNIQUE
);

-- ✅ Unique composto
CREATE TABLE company_codes (
    company_id INTEGER,
    code VARCHAR(50),
    UNIQUE (company_id, code)
);
```

### CHECK

```sql
-- ✅ Validação no banco
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    status VARCHAR(20) CHECK (status IN ('active', 'paused', 'completed', 'cancelled')),
    progress INTEGER CHECK (progress >= 0 AND progress <= 100),
    start_date DATE,
    end_date DATE,
    CHECK (end_date IS NULL OR end_date >= start_date)
);
```

### DEFAULT

```sql
-- ✅ Valores padrão
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    role VARCHAR(20) DEFAULT 'user'
);
```

---

## 📇 Índices

### Quando Criar Índices

- ✅ Foreign keys (automático no PostgreSQL, manual no SQLite)
- ✅ Campos usados em WHERE/JOIN frequentemente
- ✅ Campos usados em ORDER BY
- ✅ Campos UNIQUE

### Sintaxe

```sql
-- ✅ Índice simples
CREATE INDEX idx_projects_company_id ON projects(company_id);
CREATE INDEX idx_users_email ON users(email);

-- ✅ Índice composto
CREATE INDEX idx_logs_user_date ON user_logs(user_id, created_at);

-- ✅ Índice único
CREATE UNIQUE INDEX idx_users_email_unique ON users(email);

-- ✅ Índice parcial (PostgreSQL)
CREATE INDEX idx_active_projects ON projects(company_id) WHERE is_active = TRUE;
```

### Nomenclatura de Índices

```
idx_[tabela]_[campo1]_[campo2]

Exemplos:
idx_projects_company_id
idx_users_email
idx_logs_user_date
```

---

## 🔄 Migrations

### Estrutura de uma Migration

```python
"""
Nome descritivo da migration

Revision ID: abc123
Revises: def456
Create Date: 2025-10-18 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123'
down_revision = 'def456'
branch_labels = None
depends_on = None

def upgrade():
    """Aplicar mudanças."""
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Criar índice
    op.create_index('idx_projects_company_id', 'projects', ['company_id'])

def downgrade():
    """Reverter mudanças."""
    op.drop_index('idx_projects_company_id', table_name='projects')
    op.drop_table('projects')
```

### Boas Práticas de Migrations

```python
# ✅ BOM - Reversível
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(20)))

def downgrade():
    op.drop_column('users', 'phone')

# ✅ BOM - Migration de dados segura
def upgrade():
    # 1. Adicionar coluna nullable
    op.add_column('users', sa.Column('status', sa.String(20), nullable=True))
    
    # 2. Preencher dados
    op.execute("UPDATE users SET status = 'active' WHERE is_active = TRUE")
    op.execute("UPDATE users SET status = 'inactive' WHERE is_active = FALSE")
    
    # 3. Tornar NOT NULL
    op.alter_column('users', 'status', nullable=False)
    
    # 4. Remover coluna antiga
    op.drop_column('users', 'is_active')

# ❌ RUIM - Perda de dados
def upgrade():
    op.drop_column('users', 'old_field')  # Sem backup!
```

### Comandos de Migration

```bash
# Criar nova migration
flask db migrate -m "Adicionar tabela projects"

# Aplicar migrations pendentes
flask db upgrade

# Reverter última migration
flask db downgrade

# Ver histórico
flask db history

# Ver SQL sem aplicar
flask db upgrade --sql
```

---

## 🎯 Padrões de Tabelas

### Tabela de Auditoria

```sql
-- ✅ Padrão para todas as tabelas importantes
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    
    -- Auditoria obrigatória
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    
    -- Soft delete (recomendado)
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    deleted_at TIMESTAMP,
    deleted_by INTEGER REFERENCES users(id)
);

-- SQLAlchemy Mixin
class AuditMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
```

### Tabela de Logs

```sql
-- ✅ Padrão de log de ações
CREATE TABLE user_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL,  -- CREATE, UPDATE, DELETE
    old_values JSON,
    new_values JSON,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_user_logs_user_id ON user_logs(user_id);
CREATE INDEX idx_user_logs_entity ON user_logs(entity_type, entity_id);
CREATE INDEX idx_user_logs_created_at ON user_logs(created_at);
```

### Tabela de Configurações

```sql
-- ✅ Padrão key-value para configs
CREATE TABLE settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    data_type VARCHAR(20) DEFAULT 'string',  -- string, integer, boolean, json
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🚀 Performance

### N+1 Query Problem

```python
# ❌ RUIM - N+1 queries
projects = Project.query.all()
for project in projects:
    print(project.company.name)  # Query para cada projeto!

# ✅ BOM - Eager loading
projects = Project.query.options(db.joinedload(Project.company)).all()
for project in projects:
    print(project.company.name)  # Sem queries adicionais
```

### Paginação

```python
# ✅ Sempre paginar listas grandes
page = request.args.get('page', 1, type=int)
per_page = request.args.get('per_page', 20, type=int)

projects = Project.query.paginate(
    page=page,
    per_page=per_page,
    error_out=False
)

return {
    'data': [p.to_dict() for p in projects.items],
    'total': projects.total,
    'page': page,
    'pages': projects.pages
}
```

### Bulk Operations

```python
# ❌ RUIM - Loop com commits individuais
for item in items:
    project = Project(**item)
    db.session.add(project)
    db.session.commit()  # Lento!

# ✅ BOM - Bulk insert
projects = [Project(**item) for item in items]
db.session.bulk_save_objects(projects)
db.session.commit()
```

---

## 🔒 Segurança

### SQL Injection Prevention

```python
# ✅ BOM - Usar ORM
projects = Project.query.filter_by(name=user_input).all()

# ✅ BOM - Usar parâmetros
query = "SELECT * FROM projects WHERE name = :name"
result = db.session.execute(query, {'name': user_input})

# ❌ RUIM - String concatenation
query = f"SELECT * FROM projects WHERE name = '{user_input}'"  # VULNERÁVEL!
```

### Sensitive Data

```python
# ✅ Nunca logar senhas ou tokens
logger.info(f"User login: {user.email}")  # OK
logger.info(f"Password: {password}")  # NUNCA!

# ✅ Criptografar dados sensíveis
from sqlalchemy_utils import EncryptedType

class User(db.Model):
    ssn = db.Column(EncryptedType(String, key='secret_key'))
```

---

## 🧪 Testes

### Testes com Banco de Dados

```python
# ✅ Usar banco de teste separado
@pytest.fixture
def db_session():
    """Cria sessão de teste com rollback."""
    connection = db.engine.connect()
    transaction = connection.begin()
    
    yield db.session
    
    transaction.rollback()
    connection.close()

# Teste
def test_create_project(db_session):
    project = Project(name="Test Project")
    db_session.add(project)
    db_session.commit()
    
    assert project.id is not None
```

---

## 📋 Checklist de Nova Tabela

- [ ] Nome no plural e snake_case
- [ ] PK chamada 'id' (INTEGER PRIMARY KEY)
- [ ] FK com sufixo '_id' e REFERENCES
- [ ] Campos obrigatórios com NOT NULL
- [ ] Timestamps (created_at, updated_at)
- [ ] Soft delete (is_deleted) se aplicável
- [ ] Índices em FKs e campos consultados
- [ ] Migration criada e testada
- [ ] Migration reversível (downgrade)
- [ ] Modelo SQLAlchemy criado
- [ ] Testes de CRUD criados

---

## 📚 Referências

- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **Alembic:** https://alembic.sqlalchemy.org/
- **PostgreSQL:** https://www.postgresql.org/docs/
- **SQLite:** https://www.sqlite.org/docs.html

---

**Próxima revisão:** Trimestral  
**Responsável:** DBA/Backend Lead



