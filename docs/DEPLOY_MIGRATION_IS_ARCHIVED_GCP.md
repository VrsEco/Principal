# 🚀 Deploy da Migração `is_archived` no Google Cloud SQL

## 📋 **Migração:**
- **Arquivo:** `migrations/versions/20251203_1100_add_is_archived_to_company_projects.py`
- **Descrição:** Adiciona campo `is_archived` (BOOLEAN) à tabela `company_projects`
- **Valor padrão:** `FALSE` (todos os projetos existentes ficam não-arquivados)

---

## ✅ **Opção 1: Via Cloud SQL Studio (Recomendado)**

### **Passo 1: Acessar Cloud SQL Studio**
1. Acesse: https://console.cloud.google.com/sql/instances
2. Selecione a instância: `gestaoversus-db-prod` (ou o nome da sua instância)
3. Clique em **"Cloud SQL Studio"** (ou use o botão "Abrir Cloud SQL Studio")

### **Passo 2: Executar SQL**
Execute este comando SQL:

```sql
-- Verificar se a coluna já existe
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'company_projects' 
  AND column_name = 'is_archived';

-- Se não existir, adicionar a coluna
ALTER TABLE company_projects
ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;

-- Verificar resultado
SELECT column_name, data_type, column_default, is_nullable
FROM information_schema.columns
WHERE table_name = 'company_projects' 
  AND column_name = 'is_archived';
```

### **Passo 3: Atualizar alembic_version**
```sql
-- Verificar versão atual
SELECT * FROM alembic_version;

-- Adicionar nova versão
INSERT INTO alembic_version (version_num)
VALUES ('20251203_1100')
ON CONFLICT (version_num) DO NOTHING;

-- Verificar
SELECT * FROM alembic_version ORDER BY version_num DESC;
```

---

## ✅ **Opção 2: Via gcloud CLI (Alternativa)**

### **Pré-requisitos:**
```bash
# Autenticar
gcloud auth login

# Configurar projeto
gcloud config set project vrs-eco-478714
```

### **Executar SQL:**
```bash
# Conectar e executar SQL
gcloud sql connect gestaoversus-db-prod --user=postgres

# Dentro do psql, execute:
ALTER TABLE company_projects
ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;

INSERT INTO alembic_version (version_num)
VALUES ('20251203_1100')
ON CONFLICT (version_num) DO NOTHING;

\q
```

---

## ✅ **Opção 3: Via Cloud SQL Proxy (Local)**

### **Passo 1: Iniciar Proxy**
```bash
# No terminal local
cloud_sql_proxy -instances=vrs-eco-478714:southamerica-east1:gestaoversus-db-prod=tcp:5432
```

### **Passo 2: Executar Migração**
```bash
# Em outro terminal
export DATABASE_URL="postgresql://usuario:senha@localhost:5432/gestaoversus_prod"
export FLASK_APP=app_pev.py
flask db upgrade
```

---

## 🔍 **Verificação Pós-Migração**

### **1. Verificar Coluna:**
```sql
SELECT 
    column_name, 
    data_type, 
    column_default, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'company_projects' 
  AND column_name = 'is_archived';
```

**Resultado esperado:**
```
column_name  | data_type | column_default | is_nullable
-------------|-----------|---------------|-------------
is_archived  | boolean   | false         | NO
```

### **2. Verificar Valores:**
```sql
-- Todos os projetos devem ter is_archived = false
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE is_archived = TRUE) as arquivados,
    COUNT(*) FILTER (WHERE is_archived = FALSE) as nao_arquivados
FROM company_projects;
```

**Resultado esperado:**
```
total | arquivados | nao_arquivados
------|------------|---------------
  X   |     0      |       X
```

### **3. Verificar alembic_version:**
```sql
SELECT * FROM alembic_version ORDER BY version_num DESC LIMIT 5;
```

**Deve incluir:**
```
version_num
-----------
20251203_1100
20251203_1000
...
```

---

## ⚠️ **Troubleshooting**

### **Erro: "column already exists"**
```sql
-- Verificar se já existe
SELECT column_name 
FROM information_schema.columns
WHERE table_name = 'company_projects' 
  AND column_name = 'is_archived';

-- Se existir, apenas atualizar alembic_version
INSERT INTO alembic_version (version_num)
VALUES ('20251203_1100')
ON CONFLICT (version_num) DO NOTHING;
```

### **Erro: "permission denied"**
- Verifique se o usuário tem permissão `ALTER TABLE` na tabela `company_projects`
- Use um usuário com privilégios de administrador

---

## ✅ **Checklist Final**

- [ ] Coluna `is_archived` criada na tabela `company_projects`
- [ ] Todos os projetos existentes têm `is_archived = FALSE`
- [ ] Versão `20251203_1100` adicionada em `alembic_version`
- [ ] Teste local funcionando
- [ ] Deploy do código atualizado no Cloud Run

---

## 📝 **Notas**

- ✅ **Seguro:** A migração usa `DEFAULT FALSE`, então projetos existentes não são afetados
- ✅ **Idempotente:** Pode executar múltiplas vezes sem problemas (usa `IF NOT EXISTS`)
- ✅ **Reversível:** A migração tem `downgrade()` caso precise reverter

---

**Data:** 03/12/2025  
**Autor:** Sistema de Migrações  
**Status:** ✅ Pronto para deploy



