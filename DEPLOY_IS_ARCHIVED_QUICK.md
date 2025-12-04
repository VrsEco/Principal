# ⚡ Deploy Rápido - Campo `is_archived` no GCP

## 🎯 **Objetivo:**
Adicionar campo `is_archived` à tabela `company_projects` no Google Cloud SQL.

---

## ✅ **Método Rápido (Cloud SQL Studio):**

### **1. Acesse Cloud SQL Studio:**
https://console.cloud.google.com/sql/instances

### **2. Execute este SQL:**

```sql
-- Adicionar coluna
ALTER TABLE company_projects
ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;

-- Atualizar versão do Alembic
INSERT INTO alembic_version (version_num)
VALUES ('20251203_1100')
ON CONFLICT (version_num) DO NOTHING;
```

### **3. Verificar:**

```sql
-- Verificar coluna criada
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'company_projects' 
  AND column_name = 'is_archived';

-- Verificar versão
SELECT * FROM alembic_version ORDER BY version_num DESC LIMIT 3;
```

---

## ✅ **Pronto!**

Agora todos os projetos podem ser arquivados via interface.

---

**Guia completo:** `docs/DEPLOY_MIGRATION_IS_ARCHIVED_GCP.md`



