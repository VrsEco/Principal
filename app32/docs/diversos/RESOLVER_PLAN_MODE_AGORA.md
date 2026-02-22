# 🔧 RESOLVER PROBLEMA DO PLAN_MODE - AGORA!

**Situação:** Ambos os planejamentos vão para "Evolução" mesmo tendo criado um como "Novo Negócio"

---

## 🚀 SOLUÇÃO RÁPIDA (3 Passos)

### **Passo 1: Verificar Console do Navegador**

1. Abra: `http://127.0.0.1:5003/pev/dashboard`
2. Pressione **F12** (DevTools)
3. Vá na aba **Console**
4. Recarregue a página (**Ctrl+Shift+R**)
5. Procure por:

```
🔍 Plans loaded for company [Nome] : [...]
```

**📸 TIRE UM PRINT e me envie!**

---

### **Passo 2: Verificar Banco de Dados**

Execute este comando:

```bash
docker exec -it gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "SELECT id, name, plan_mode, created_at FROM plans ORDER BY created_at DESC LIMIT 5;"
```

**OU use o script Python:**

```bash
python atualizar_plan_mode_manual.py
```

Isso vai listar todos os planos e seus tipos.

**📸 TIRE UM PRINT do resultado!**

---

### **Passo 3A: Se o Banco Está Correto (plan_mode = 'implantacao')**

Significa que o problema é no JavaScript. 

**Solução:**
1. Limpar cache (**Ctrl+Shift+R**)
2. Fechar e abrir navegador
3. Testar novamente

---

### **Passo 3B: Se o Banco Está Errado (plan_mode = NULL ou 'evolucao')**

O plano foi salvo incorretamente. **Vamos corrigir!**

#### **Opção 1: Usar Script Python (RECOMENDADO)**

```bash
# Listar planos
python atualizar_plan_mode_manual.py

# Escolher opção 1
# Digite o ID do plano
# Digite: implantacao
```

#### **Opção 2: SQL Direto**

```bash
# Entre no PostgreSQL
docker exec -it gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev

# Veja os planos
SELECT id, name, plan_mode FROM plans ORDER BY created_at DESC LIMIT 5;

# Atualize o plano (substitua X pelo ID)
UPDATE plans SET plan_mode = 'implantacao' WHERE id = X;

# Verifique
SELECT id, name, plan_mode FROM plans WHERE id = X;

# Saia
\q
```

---

## 🧪 TESTE COMPLETO

Depois de corrigir, teste:

1. Acesse: `http://127.0.0.1:5003/pev/dashboard`
2. Abra Console (F12)
3. Selecione empresa
4. **Veja no console:** 
   ```
   🔍 Plans loaded for company ...
   ```
   - Deve mostrar `plan_mode: "implantacao"` no plano correto

5. Selecione o planejamento
6. **Veja no console:**
   ```
   📋 Plan selected: { planId: X, planMode: "implantacao", ... }
   ```

7. Clique em "Ir para planejamento"
8. **Veja no console ANTES de redirecionar:**
   ```
   🚀 Redirecting - Plan ID: X, Plan Mode: implantacao
   ✅ Going to IMPLANTACAO: /pev/implantacao?plan_id=X
   ```

9. ✅ **Deve ir para:** `/pev/implantacao?plan_id=X`

---

## ❓ Ainda Não Funciona?

Me envie:

1. **Print do console do navegador** (toda a saída)
2. **Resultado do comando SQL:**
   ```sql
   SELECT id, name, plan_mode FROM plans ORDER BY created_at DESC LIMIT 5;
   ```
3. **URL que está sendo acessada** (copie da barra de endereços)

---

## 🛠️ Arquivos de Debug Criados

- ✅ `DEBUG_PLAN_MODE.md` - Guia completo de debug
- ✅ `verificar_plan_mode_banco.sql` - SQL para verificar banco
- ✅ `atualizar_plan_mode_manual.py` - Script para corrigir

---

## 🎯 Causa Mais Provável

**99% dos casos:** O plano foi criado ANTES de aplicar a migration ou o `plan_mode` não foi salvo corretamente.

**Solução:** Atualizar manualmente o `plan_mode` no banco usando o script Python.

---

**Teste e me fale o resultado! 🚀**

