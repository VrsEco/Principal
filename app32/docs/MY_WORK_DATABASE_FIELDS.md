# 🗄️ Campos de Banco de Dados - My Work

## 📋 Visão Geral

Este documento especifica os campos necessários nas tabelas existentes para suportar as funcionalidades da página "Minhas Atividades".

---

## 📁 Tabela: `company_projects` (Atividades de Projetos)

### Campos Existentes (Verificar)
- `id` - INTEGER, PK
- `company_id` - INTEGER, FK
- `title` - VARCHAR(200)
- `description` - TEXT
- `status` - VARCHAR(50)
- `priority` - VARCHAR(20)
- `responsible_id` - INTEGER, FK (employees.id)
- `created_at` - TIMESTAMP
- `updated_at` - TIMESTAMP

### Campos Novos Necessários

```sql
-- Campos de Horas
ALTER TABLE company_projects ADD COLUMN estimated_hours DECIMAL(5,2) DEFAULT 0;
ALTER TABLE company_projects ADD COLUMN worked_hours DECIMAL(5,2) DEFAULT 0;

-- Comentários (ou criar tabela separada)
ALTER TABLE company_projects ADD COLUMN notes JSONB; -- PostgreSQL
ALTER TABLE company_projects ADD COLUMN notes TEXT;  -- SQLite (JSON como string)
```

**Observações:**
- `estimated_hours`: Horas estimadas para conclusão (ex: 8.5 = 8h 30min)
- `worked_hours`: Total de horas já trabalhadas
- `notes`: Histórico de comentários (JSON array) ou criar tabela separada

---

## ⚙️ Tabela: `process_instances` (Instâncias de Processos)

### Campos Existentes (Verificar)
- `id` - INTEGER, PK
- `company_id` - INTEGER, FK
- `process_id` - INTEGER, FK
- `title` - VARCHAR(200)
- `description` - TEXT
- `status` - VARCHAR(50)
- `priority` - VARCHAR(20)
- `executor_id` - INTEGER, FK (employees.id)
- `created_at` - TIMESTAMP
- `updated_at` - TIMESTAMP

### Campos Novos Necessários

```sql
-- Campos de Horas
ALTER TABLE process_instances ADD COLUMN estimated_hours DECIMAL(5,2) DEFAULT 0;
ALTER TABLE process_instances ADD COLUMN worked_hours DECIMAL(5,2) DEFAULT 0;

-- Comentários
ALTER TABLE process_instances ADD COLUMN notes JSONB; -- PostgreSQL
ALTER TABLE process_instances ADD COLUMN notes TEXT;  -- SQLite
```

---

## 📝 Tabela Nova: `activity_work_logs` (Registro de Horas Trabalhadas)

**Opcional mas RECOMENDADO** para rastreabilidade detalhada.

```sql
CREATE TABLE activity_work_logs (
    id SERIAL PRIMARY KEY,  -- INTEGER PRIMARY KEY AUTOINCREMENT no SQLite
    
    -- Referência à atividade
    activity_type VARCHAR(20) NOT NULL,  -- 'project' ou 'process'
    activity_id INTEGER NOT NULL,
    
    -- Quem trabalhou
    user_id INTEGER NOT NULL REFERENCES users(id),
    user_name VARCHAR(200),  -- Cache para histórico
    
    -- Detalhes do trabalho
    work_date DATE NOT NULL,
    hours_worked DECIMAL(5,2) NOT NULL,  -- Ex: 2.5 = 2h 30min
    description TEXT,
    
    -- Auditoria
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Índices
    INDEX idx_activity (activity_type, activity_id),
    INDEX idx_user (user_id),
    INDEX idx_work_date (work_date)
);
```

**Vantagens:**
- ✅ Histórico detalhado de horas por dia
- ✅ Rastreabilidade completa
- ✅ Múltiplos usuários podem registrar horas
- ✅ Facilita relatórios e análises

---

## 💬 Tabela Nova: `activity_comments` (Comentários e Anotações)

**Recomendado** para melhor organização.

```sql
CREATE TABLE activity_comments (
    id SERIAL PRIMARY KEY,  -- INTEGER PRIMARY KEY AUTOINCREMENT no SQLite
    
    -- Referência à atividade
    activity_type VARCHAR(20) NOT NULL,  -- 'project' ou 'process'
    activity_id INTEGER NOT NULL,
    
    -- Autor
    user_id INTEGER NOT NULL REFERENCES users(id),
    user_name VARCHAR(200),  -- Cache
    
    -- Conteúdo
    comment_type VARCHAR(20),  -- 'note', 'progress', 'issue', 'solution', 'question'
    comment_text TEXT NOT NULL,
    is_private BOOLEAN DEFAULT FALSE,
    
    -- Metadados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    
    -- Índices
    INDEX idx_activity (activity_type, activity_id),
    INDEX idx_user (user_id),
    INDEX idx_created (created_at)
);
```

---

## 👤 Tabela: `users` ou `employees` (Configuração do Usuário)

### Campos Novos Opcionais

```sql
-- Capacidade de trabalho (opcional)
ALTER TABLE users ADD COLUMN daily_capacity DECIMAL(4,2) DEFAULT 8.0;   -- Horas por dia
ALTER TABLE users ADD COLUMN weekly_capacity DECIMAL(5,2) DEFAULT 40.0; -- Horas por semana
```

Ou criar tabela separada:

```sql
CREATE TABLE user_work_capacity (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
    daily_hours DECIMAL(4,2) DEFAULT 8.0,
    weekly_hours DECIMAL(5,2) DEFAULT 40.0,
    work_days_per_week INTEGER DEFAULT 5,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📊 Formato de Dados

### JSON para `notes` (se usar coluna JSON)

```json
{
  "comments": [
    {
      "id": 1,
      "user_id": 10,
      "user_name": "João Silva",
      "type": "progress",
      "text": "Concluída primeira etapa do projeto",
      "is_private": false,
      "created_at": "2025-10-21T14:30:00Z"
    },
    {
      "id": 2,
      "user_id": 10,
      "user_name": "João Silva",
      "type": "issue",
      "text": "Encontrado problema na integração",
      "is_private": false,
      "created_at": "2025-10-21T16:45:00Z"
    }
  ],
  "work_logs": [
    {
      "date": "2025-10-21",
      "hours": 4.5,
      "description": "Desenvolvimento e testes iniciais"
    },
    {
      "date": "2025-10-22",
      "hours": 3.0,
      "description": "Correção de bugs"
    }
  ]
}
```

---

## 🔄 Script de Migração Completo

### PostgreSQL

```sql
-- ===================================
-- MIGRAÇÃO: My Work - Campos e Tabelas
-- ===================================

-- 1. Adicionar campos em company_projects
ALTER TABLE company_projects 
ADD COLUMN IF NOT EXISTS estimated_hours DECIMAL(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS worked_hours DECIMAL(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS notes JSONB;

-- 2. Adicionar campos em process_instances
ALTER TABLE process_instances 
ADD COLUMN IF NOT EXISTS estimated_hours DECIMAL(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS worked_hours DECIMAL(5,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS notes JSONB;

-- 3. Criar tabela de logs de trabalho
CREATE TABLE IF NOT EXISTS activity_work_logs (
    id SERIAL PRIMARY KEY,
    activity_type VARCHAR(20) NOT NULL,
    activity_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    user_name VARCHAR(200),
    work_date DATE NOT NULL,
    hours_worked DECIMAL(5,2) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_work_logs_activity ON activity_work_logs(activity_type, activity_id);
CREATE INDEX IF NOT EXISTS idx_work_logs_user ON activity_work_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_work_logs_date ON activity_work_logs(work_date);

-- 4. Criar tabela de comentários
CREATE TABLE IF NOT EXISTS activity_comments (
    id SERIAL PRIMARY KEY,
    activity_type VARCHAR(20) NOT NULL,
    activity_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id),
    user_name VARCHAR(200),
    comment_type VARCHAR(20),
    comment_text TEXT NOT NULL,
    is_private BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comments_activity ON activity_comments(activity_type, activity_id);
CREATE INDEX IF NOT EXISTS idx_comments_user ON activity_comments(user_id);

-- 5. Adicionar campos de capacidade em users (opcional)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS daily_capacity DECIMAL(4,2) DEFAULT 8.0,
ADD COLUMN IF NOT EXISTS weekly_capacity DECIMAL(5,2) DEFAULT 40.0;

-- 6. Função para atualizar worked_hours automaticamente (PostgreSQL)
CREATE OR REPLACE FUNCTION update_activity_worked_hours()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.activity_type = 'project' THEN
        UPDATE company_projects 
        SET worked_hours = (
            SELECT COALESCE(SUM(hours_worked), 0) 
            FROM activity_work_logs 
            WHERE activity_type = 'project' AND activity_id = NEW.activity_id
        )
        WHERE id = NEW.activity_id;
    ELSIF NEW.activity_type = 'process' THEN
        UPDATE process_instances 
        SET worked_hours = (
            SELECT COALESCE(SUM(hours_worked), 0) 
            FROM activity_work_logs 
            WHERE activity_type = 'process' AND activity_id = NEW.activity_id
        )
        WHERE id = NEW.activity_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_worked_hours
AFTER INSERT ON activity_work_logs
FOR EACH ROW
EXECUTE FUNCTION update_activity_worked_hours();
```

### SQLite

```sql
-- ===================================
-- MIGRAÇÃO: My Work - Campos e Tabelas
-- ===================================

-- 1. Adicionar campos em company_projects
ALTER TABLE company_projects ADD COLUMN estimated_hours REAL DEFAULT 0;
ALTER TABLE company_projects ADD COLUMN worked_hours REAL DEFAULT 0;
ALTER TABLE company_projects ADD COLUMN notes TEXT;  -- JSON como string

-- 2. Adicionar campos em process_instances
ALTER TABLE process_instances ADD COLUMN estimated_hours REAL DEFAULT 0;
ALTER TABLE process_instances ADD COLUMN worked_hours REAL DEFAULT 0;
ALTER TABLE process_instances ADD COLUMN notes TEXT;

-- 3. Criar tabela de logs de trabalho
CREATE TABLE IF NOT EXISTS activity_work_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_type TEXT NOT NULL,
    activity_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    user_name TEXT,
    work_date TEXT NOT NULL,  -- ISO format: YYYY-MM-DD
    hours_worked REAL NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_work_logs_activity ON activity_work_logs(activity_type, activity_id);
CREATE INDEX IF NOT EXISTS idx_work_logs_user ON activity_work_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_work_logs_date ON activity_work_logs(work_date);

-- 4. Criar tabela de comentários
CREATE TABLE IF NOT EXISTS activity_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_type TEXT NOT NULL,
    activity_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    user_name TEXT,
    comment_type TEXT,
    comment_text TEXT NOT NULL,
    is_private INTEGER DEFAULT 0,  -- 0 = false, 1 = true
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_comments_activity ON activity_comments(activity_type, activity_id);
CREATE INDEX IF NOT EXISTS idx_comments_user ON activity_comments(user_id);

-- 5. Adicionar campos de capacidade em users
ALTER TABLE users ADD COLUMN daily_capacity REAL DEFAULT 8.0;
ALTER TABLE users ADD COLUMN weekly_capacity REAL DEFAULT 40.0;

-- Nota: SQLite não suporta triggers complexos como PostgreSQL
-- O cálculo de worked_hours deve ser feito no application layer
```

---

## 🔍 Queries Úteis

### Buscar horas trabalhadas de um usuário no dia
```sql
SELECT 
    awl.activity_type,
    awl.activity_id,
    CASE 
        WHEN awl.activity_type = 'project' THEN cp.title
        WHEN awl.activity_type = 'process' THEN pi.title
    END as activity_title,
    awl.hours_worked,
    awl.description,
    awl.work_date
FROM activity_work_logs awl
LEFT JOIN company_projects cp ON awl.activity_type = 'project' AND awl.activity_id = cp.id
LEFT JOIN process_instances pi ON awl.activity_type = 'process' AND awl.activity_id = pi.id
WHERE awl.user_id = ?
  AND awl.work_date = ?
ORDER BY awl.created_at DESC;
```

### Calcular total de horas por atividade
```sql
SELECT 
    activity_type,
    activity_id,
    SUM(hours_worked) as total_hours,
    COUNT(*) as num_entries
FROM activity_work_logs
WHERE activity_type = ? AND activity_id = ?
GROUP BY activity_type, activity_id;
```

### Buscar comentários de uma atividade
```sql
SELECT 
    id,
    user_name,
    comment_type,
    comment_text,
    is_private,
    created_at
FROM activity_comments
WHERE activity_type = ?
  AND activity_id = ?
  AND (is_private = 0 OR user_id = ?)  -- Privados só para o autor
ORDER BY created_at DESC;
```

---

## ✅ Checklist de Implementação

- [ ] Adicionar campos `estimated_hours` e `worked_hours` em `company_projects`
- [ ] Adicionar campos `estimated_hours` e `worked_hours` em `process_instances`
- [ ] Criar tabela `activity_work_logs` para histórico de horas
- [ ] Criar tabela `activity_comments` para comentários
- [ ] Adicionar campos de capacidade em `users` (opcional)
- [ ] Criar índices para performance
- [ ] Testar queries de agregação
- [ ] Implementar APIs no backend
- [ ] Migrar dados existentes (se houver)

---

## 🔄 Compatibilidade

✅ **PostgreSQL:** Totalmente suportado (com triggers)  
✅ **SQLite:** Totalmente suportado (cálculos no application layer)

**Nota:** O código deve funcionar em AMBOS os bancos (requisito do projeto).

---

**Versão:** 1.0  
**Data:** 21/10/2025  
**Status:** Aguardando Implementação

