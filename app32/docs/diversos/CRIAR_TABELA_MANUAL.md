# 🔧 CRIAR TABELA MANUALMENTE

## O PROBLEMA

A tabela `plan_finance_capital_giro` não existe no PostgreSQL.

## ✅ SOLUÇÃO MANUAL (MAIS RÁPIDA)

### Opção 1: Via pgAdmin ou DBeaver

1. Conecte no PostgreSQL:
   - Host: `localhost`
   - Port: `5432`
   - Database: `bd_app_versus`
   - User: `postgres`
   - Password: `*Paraiso1978`

2. Execute este SQL:

```sql
-- Criar tabela
CREATE TABLE IF NOT EXISTS plan_finance_capital_giro (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL,
    item_type VARCHAR(50) NOT NULL,
    contribution_date DATE NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    description TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Criar índice
CREATE INDEX IF NOT EXISTS idx_capital_giro_plan_id 
ON plan_finance_capital_giro(plan_id);

-- Adicionar coluna
ALTER TABLE plan_finance_metrics 
ADD COLUMN IF NOT EXISTS executive_summary TEXT;
```

3. Execute (F5 ou botão "Execute")

4. Confirme que tabela foi criada:
```sql
SELECT * FROM plan_finance_capital_giro LIMIT 1;
```

---

### Opção 2: Via Terminal do PostgreSQL (se tiver psql)

```bash
psql -h localhost -U postgres -d bd_app_versus
```

Depois cole o SQL acima.

---

### Opção 3: Adicionar o SQL manualmente no projeto

Se nenhuma das opções acima funcionar, posso adicionar a criação da tabela no `init_database()` do PostgreSQLDatabase.

---

## 🚀 DEPOIS DE CRIAR A TABELA

1. ✅ Recarregue a página: `F5`
2. ✅ Abra o modal: `+ Capital de Giro`
3. ✅ Preencha os campos
4. ✅ Clique em `Salvar`
5. ✅ Deve funcionar agora!

---

**Qual opção você prefere usar?**

