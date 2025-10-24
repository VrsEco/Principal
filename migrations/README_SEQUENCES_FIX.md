# 🔧 Correção de Sequences - routine_collaborators

## 📋 Problema Identificado

**Data:** 2025-10-21  
**Erro:** `null value in column "id" of relation "routine_collaborators" violates not-null constraint`

### Causa Raiz

A tabela `routine_collaborators` foi criada com a seguinte estrutura:

```sql
CREATE TABLE public.routine_collaborators (
    id integer NOT NULL,
    routine_id integer NOT NULL,
    employee_id integer NOT NULL,
    hours_used real NOT NULL,
    notes text,
    created_at text DEFAULT CURRENT_TIMESTAMP,
    updated_at text DEFAULT CURRENT_TIMESTAMP
);
```

**Problema:** A coluna `id` foi definida como `INTEGER NOT NULL`, mas **SEM SERIAL ou SEQUENCE**, então o PostgreSQL não gera automaticamente valores para o `id`.

### Sintoma

Ao tentar inserir um registro sem especificar o `id`:

```sql
INSERT INTO routine_collaborators (routine_id, employee_id, hours_used, notes)
VALUES (19, 19, 4, '')
RETURNING id;
```

O PostgreSQL tentava inserir `NULL` no `id`, violando a constraint `NOT NULL`.

---

## ✅ Solução Aplicada

### Migration: `20251021_fix_routine_collaborators_sequence.sql`

**Ações executadas:**

1. ✅ Criada sequence `routine_collaborators_id_seq`
2. ✅ Ajustado valor inicial baseado no maior ID existente
3. ✅ Configurado `id` para usar `nextval()` como default
4. ✅ Associada sequence à coluna (OWNED BY)

**Resultado:**

```sql
-- Verificação
SELECT column_name, column_default 
FROM information_schema.columns 
WHERE table_name = 'routine_collaborators' AND column_name = 'id';

-- Resultado:
-- column_name | column_default
-- ------------|---------------------------------------------------
-- id          | nextval('routine_collaborators_id_seq'::regclass)
```

Agora o PostgreSQL gera automaticamente o `id` em cada INSERT! 🎉

---

## 🔍 Como Identificar Tabelas com o Mesmo Problema

Execute esta query no PostgreSQL para encontrar outras tabelas com `id INTEGER NOT NULL` mas sem default:

```sql
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM 
    information_schema.columns
WHERE 
    table_schema = 'public'
    AND column_name = 'id'
    AND data_type = 'integer'
    AND is_nullable = 'NO'
    AND column_default IS NULL
ORDER BY 
    table_name;
```

---

## 🚀 Como Aplicar em Outros Ambientes

### Desenvolvimento (Já aplicado ✅)

```bash
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < migrations/20251021_fix_routine_collaborators_sequence.sql
```

### Produção (⚠️ Quando necessário)

1. **Fazer backup do banco:**
   ```bash
   pg_dump -h localhost -U postgres bd_app_versus > backup_pre_fix_sequences.sql
   ```

2. **Aplicar migration:**
   ```bash
   psql -h localhost -U postgres -d bd_app_versus < migrations/20251021_fix_routine_collaborators_sequence.sql
   ```

3. **Verificar:**
   ```bash
   psql -h localhost -U postgres -d bd_app_versus -c "SELECT column_default FROM information_schema.columns WHERE table_name = 'routine_collaborators' AND column_name = 'id';"
   ```

4. **Testar inserção:**
   ```sql
   INSERT INTO routine_collaborators (routine_id, employee_id, hours_used, notes)
   VALUES (1, 1, 4.0, 'Teste')
   RETURNING id;
   ```

---

## 📝 Lições Aprendidas

### ❌ Problema Original

```sql
-- ERRADO: id sem auto-incremento
CREATE TABLE routine_collaborators (
    id INTEGER NOT NULL PRIMARY KEY,
    ...
);
```

### ✅ Forma Correta (Para novas tabelas)

```sql
-- CORRETO: usar SERIAL (PostgreSQL)
CREATE TABLE routine_collaborators (
    id SERIAL PRIMARY KEY,
    ...
);

-- Ou explicitamente:
CREATE SEQUENCE routine_collaborators_id_seq;

CREATE TABLE routine_collaborators (
    id INTEGER NOT NULL DEFAULT nextval('routine_collaborators_id_seq') PRIMARY KEY,
    ...
);

ALTER SEQUENCE routine_collaborators_id_seq OWNED BY routine_collaborators.id;
```

---

## 📚 Documentação Relacionada

- **PostgreSQL SERIAL:** https://www.postgresql.org/docs/current/datatype-numeric.html#DATATYPE-SERIAL
- **PostgreSQL SEQUENCE:** https://www.postgresql.org/docs/current/sql-createsequence.html
- **Erro NotNullViolation:** https://www.postgresql.org/docs/current/errcodes-appendix.html

---

**Autor:** AI Assistant  
**Revisor:** Dev Team  
**Status:** ✅ Aplicado em DEV | ⏳ Pendente em PROD




