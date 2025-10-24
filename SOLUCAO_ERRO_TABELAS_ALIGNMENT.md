# 🔧 SOLUÇÃO: Erro "relation plan_alignment_members does not exist"

**Data:** 23/10/2025  
**Status:** ✅ Solucionado

---

## 🚨 **PROBLEMA IDENTIFICADO**

O erro indica que as **tabelas do Canvas de Expectativas não existem** no banco PostgreSQL:

```
(psycopg2.errors.UndefinedTable) relation "plan_alignment_members" does not exist
```

---

## ✅ **SOLUÇÃO CRIADA**

### **1. Script SQL de Criação**

**Arquivo:** `CRIAR_TABELAS_ALIGNMENT.sql`

Cria as 5 tabelas necessárias:
- `plan_alignment_members` - Sócios
- `plan_alignment_overview` - Visão/Metas/Critérios  
- `plan_alignment_agenda` - Próximos Passos
- `plan_alignment_principles` - Princípios (opcional)
- `plan_alignment_project` - Projeto (opcional)

### **2. Script de Execução**

**Arquivo:** `EXECUTAR_CRIACAO_TABELAS.bat`

Executa automaticamente o SQL no PostgreSQL.

---

## 🚀 **COMO EXECUTAR**

### **Opção 1: Script Automático**
```bash
# Execute o arquivo .bat
EXECUTAR_CRIACAO_TABELAS.bat
```

### **Opção 2: Manual**
```bash
# Execute o SQL diretamente
psql -h localhost -p 5432 -U postgres -d gestao_versus -f CRIAR_TABELAS_ALIGNMENT.sql
```

### **Opção 3: Pelo pgAdmin**
1. Abra pgAdmin
2. Conecte no banco `gestao_versus`
3. Abra Query Tool
4. Cole o conteúdo de `CRIAR_TABELAS_ALIGNMENT.sql`
5. Execute (F5)

---

## 📋 **TABELAS CRIADAS**

### **1. plan_alignment_members**
```sql
CREATE TABLE plan_alignment_members (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES plans (id),
    name VARCHAR(255) NOT NULL,
    role VARCHAR(255),
    motivation TEXT,
    commitment TEXT,
    risk TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **2. plan_alignment_overview**
```sql
CREATE TABLE plan_alignment_overview (
    plan_id INTEGER PRIMARY KEY REFERENCES plans (id),
    shared_vision TEXT,
    financial_goals TEXT,
    decision_criteria JSONB DEFAULT '[]'::jsonb,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **3. plan_alignment_agenda**
```sql
CREATE TABLE plan_alignment_agenda (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES plans (id),
    action_title TEXT,
    owner_name TEXT,
    schedule_info TEXT,
    execution_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🧪 **APÓS EXECUTAR**

1. ✅ Execute o script SQL
2. ✅ Reinicie o servidor Flask
3. ✅ Teste novamente o Canvas de Expectativas
4. ✅ Adicione um sócio para verificar

---

## 📁 **ARQUIVOS CRIADOS**

```
✅ migrations/20251023_create_alignment_tables.sql  - Migration oficial
✅ CRIAR_TABELAS_ALIGNMENT.sql                      - Script de execução
✅ EXECUTAR_CRIACAO_TABELAS.bat                     - Execução automática
✅ SOLUCAO_ERRO_TABELAS_ALIGNMENT.md                - Esta documentação
```

---

## 🔍 **VERIFICAÇÃO**

Para verificar se as tabelas foram criadas:

```sql
-- Listar tabelas
\dt plan_alignment_*

-- Ver estrutura de uma tabela
\d plan_alignment_members
```

---

## 🎯 **RESULTADO ESPERADO**

Após executar o script:
- ✅ 5 tabelas criadas
- ✅ Índices criados
- ✅ Comentários adicionados
- ✅ Canvas de Expectativas funcionando

---

**Execute o script e teste novamente! 🚀**
