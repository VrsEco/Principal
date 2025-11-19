# 🔧 RESOLVER: Erro ao Criar Planejamento

**Erro:** "Erro ao criar planejamento no banco de dados"  
**Data:** 23/10/2025

---

## 🚨 **CAUSA PROVÁVEL:**

A coluna `plan_mode` provavelmente não existe na tabela `plans` do banco Docker (`bd_app_versus_dev`).

---

## ✅ **SOLUÇÃO: Execute este comando**

```bash
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < adicionar_coluna_plan_mode.sql
```

---

## 📋 **OU Execute SQL Manualmente:**

### **Via Docker exec:**
```bash
docker exec -it gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev
```

### **Depois cole este SQL:**
```sql
-- Adicionar coluna plan_mode
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'plans' AND column_name = 'plan_mode'
    ) THEN
        ALTER TABLE plans ADD COLUMN plan_mode VARCHAR(32) DEFAULT 'evolucao';
    END IF;
END $$;

-- Atualizar registros existentes
UPDATE plans SET plan_mode = 'evolucao' WHERE plan_mode IS NULL;

-- Verificar
\d plans
```

---

## 🧪 **APÓS EXECUTAR:**

1. Teste criar planejamento novamente
2. Deve funcionar normalmente

---

## 🔍 **SE AINDA DER ERRO:**

### **Verificar logs do servidor:**
```bash
docker logs gestaoversus_app_dev --tail 100
```

### **Procurar por:**
- "Error creating plan"
- Nome da coluna que está faltando
- Traceback completo

### **Me envie:**
- Mensagem de erro completa
- Logs do servidor
- Vou ajustar o código

---

**Execute o SQL e teste novamente!** 🚀

