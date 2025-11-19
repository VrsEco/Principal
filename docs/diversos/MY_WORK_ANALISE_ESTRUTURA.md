# 🔍 Análise da Estrutura Atual - My Work Backend

## 📊 Estrutura Existente

### ✅ Tabela: `company_projects`

**Campos Existentes:**
```sql
id                    SERIAL PRIMARY KEY
company_id            INTEGER NOT NULL
plan_id               INTEGER
plan_type             VARCHAR (PEV ou GRV)
title                 VARCHAR(255) NOT NULL
description           TEXT
status                VARCHAR(50) DEFAULT 'planned'
priority              VARCHAR(50)
owner                 VARCHAR(255)
responsible_id        INTEGER (FK → employees.id)
start_date            DATE
end_date              DATE
okr_area_ref          VARCHAR(255)
okr_reference         VARCHAR(255)
indicator_reference   VARCHAR(255)
activities            JSONB/TEXT
notes                 TEXT (já existe!)
code                  VARCHAR(64)
code_sequence         INTEGER
created_at            TIMESTAMP
updated_at            TIMESTAMP
```

**✅ Campos JÁ EXISTENTES que podemos usar:**
- `notes` - Pode armazenar comentários (JSON)
- `responsible_id` - Pessoa responsável

**❌ Campos que FALTAM:**
- `estimated_hours` - Horas estimadas
- `worked_hours` - Horas trabalhadas
- `executor_id` - Quem executa (pode ser diferente do responsável)

---

### ✅ Tabela: `process_instances`

**Campos Existentes** (conforme SISTEMA_INSTANCIAS_PROCESSOS.md):
```sql
id                      INTEGER PRIMARY KEY
company_id              INTEGER NOT NULL
process_id              INTEGER NOT NULL
routine_id              INTEGER
instance_code           TEXT
title                   TEXT NOT NULL
description             TEXT
status                  TEXT DEFAULT 'pending'
priority                TEXT
due_date                DATETIME
started_at              DATETIME
completed_at            DATETIME
assigned_collaborators  TEXT (JSON)
estimated_hours         REAL ✅ JÁ EXISTE!
actual_hours            REAL ✅ JÁ EXISTE!
notes                   TEXT ✅ JÁ EXISTE!
metadata                TEXT
created_by              TEXT
trigger_type            TEXT
created_at              TIMESTAMP
updated_at              TIMESTAMP
```

**✅ EXCELENTE! Process_instances JÁ TEM TUDO:**
- ✅ `estimated_hours` - Já existe!
- ✅ `actual_hours` - Já existe! (vamos padronizar como `worked_hours`)
- ✅ `notes` - Já existe!
- ✅ `assigned_collaborators` - JSON com colaboradores

**❌ Apenas falta:**
- Talvez um campo `executor_id` específico (ou usar assigned_collaborators)

---

### ✅ Tabela: `employees`

**Campos Existentes:**
```sql
id                INTEGER PRIMARY KEY
company_id        INTEGER NOT NULL
name              VARCHAR(200)
role              VARCHAR(100)
email             VARCHAR(120)
...
created_at        TIMESTAMP
updated_at        TIMESTAMP
```

---

## 🎯 Decisões de Implementação

### 1. **company_projects** - Adicionar Campos

```sql
-- PostgreSQL
ALTER TABLE company_projects 
ADD COLUMN IF NOT EXISTS estimated_hours DECIMAL(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS worked_hours DECIMAL(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS executor_id INTEGER REFERENCES employees(id);

-- SQLite
ALTER TABLE company_projects ADD COLUMN estimated_hours REAL DEFAULT 0;
ALTER TABLE company_projects ADD COLUMN worked_hours REAL DEFAULT 0;
ALTER TABLE company_projects ADD COLUMN executor_id INTEGER;
```

### 2. **process_instances** - Padronizar Nome

```sql
-- Renomear actual_hours para worked_hours (ou criar alias)
-- PostgreSQL
ALTER TABLE process_instances 
RENAME COLUMN actual_hours TO worked_hours;

-- OU criar view/alias no service layer
```

**Ou simplesmente usar `actual_hours` no backend e mapear para `worked_hours` no frontend.**

### 3. **Novas Tabelas** - Criar

#### A) `teams` - Equipes
```sql
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    leader_id INTEGER REFERENCES employees(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);
```

#### B) `team_members` - Membros de Equipe
```sql
CREATE TABLE team_members (
    id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    role VARCHAR(50) DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, employee_id)
);
```

#### C) `activity_work_logs` - Registro de Horas
```sql
CREATE TABLE activity_work_logs (
    id SERIAL PRIMARY KEY,
    activity_type VARCHAR(20) NOT NULL,  -- 'project' ou 'process'
    activity_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    employee_name VARCHAR(200),
    work_date DATE NOT NULL,
    hours_worked DECIMAL(5,2) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### D) `activity_comments` - Comentários
```sql
CREATE TABLE activity_comments (
    id SERIAL PRIMARY KEY,
    activity_type VARCHAR(20) NOT NULL,
    activity_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    employee_name VARCHAR(200),
    comment_type VARCHAR(20),
    comment_text TEXT NOT NULL,
    is_private BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📋 Compatibilidade: Users vs Employees

### **Descoberta:**
O sistema usa **`employees`** (não `users`) para colaboradores!

**Ajustes necessários:**
- Todos os FKs apontam para `employees.id`
- Login provavelmente usa `users` (flask-login)
- Precisamos mapear `current_user.id` → `employee_id`

**Solução:**
```python
# Verificar se existe relação user → employee
# Ou adicionar campo employee_id na tabela users
ALTER TABLE users ADD COLUMN employee_id INTEGER REFERENCES employees(id);
```

---

## 🔄 Plano de Migração

### **Fase 1: Preparar Tabelas**
1. ✅ Adicionar campos em `company_projects`
2. ✅ Padronizar `process_instances` (actual_hours → worked_hours)
3. ✅ Criar tabela `teams`
4. ✅ Criar tabela `team_members`
5. ✅ Criar tabela `activity_work_logs`
6. ✅ Criar tabela `activity_comments`

### **Fase 2: Criar Models**
1. ✅ `models/team.py`
2. ✅ `models/activity_work_log.py`
3. ✅ `models/activity_comment.py`

### **Fase 3: Criar Services**
1. ✅ `services/my_work_service.py`

### **Fase 4: Criar Rotas**
1. ✅ `modules/my_work/__init__.py`
2. ✅ `modules/my_work/routes.py`

---

## ⚠️ **Pontos de Atenção**

### 1. **Users vs Employees**
```python
# Descobrir relação
SELECT u.id as user_id, e.id as employee_id, e.name
FROM users u
LEFT JOIN employees e ON e.email = u.email
```

**Opções:**
- A) Adicionar `employee_id` em `users`
- B) Join via email
- C) Criar tabela de mapeamento

### 2. **process_instances.actual_hours**
- Já existe como `actual_hours`
- Podemos renomear OU usar alias no código
- Preferível: **usar como está e mapear no service**

### 3. **notes já existe**
- Em `company_projects.notes` (TEXT)
- Em `process_instances.notes` (TEXT)
- Podemos usar para armazenar JSON de comentários
- OU criar tabela `activity_comments` (recomendado)

### 4. **assigned_collaborators (process_instances)**
- JSON com estrutura:
```json
[
  {"employee_id": 10, "name": "João", "estimated_hours": 4},
  {"employee_id": 11, "name": "Maria", "estimated_hours": 3}
]
```
- Já resolve parte do problema!

---

## ✅ **Decisão Final**

### **Usar o que já existe:**
- ✅ `process_instances.estimated_hours` (renomear no código se necessário)
- ✅ `process_instances.actual_hours` → mapear como `worked_hours`
- ✅ `process_instances.notes` → usar para comentários JSON
- ✅ `assigned_collaborators` → usar para executor

### **Adicionar o mínimo:**
- ✅ `company_projects.estimated_hours` (REAL/DECIMAL)
- ✅ `company_projects.worked_hours` (REAL/DECIMAL)
- ✅ `company_projects.executor_id` (INTEGER)
- ✅ Tabelas: `teams`, `team_members`, `activity_work_logs`, `activity_comments`

---

**Próximo passo:** Criar script de migração!

