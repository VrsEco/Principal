# ✅ Correção API de Fontes de Recursos

## 🐛 PROBLEMA

Erro ao salvar fonte:
```
'PostgreSQLDatabase' object has no attribute 'create_plan_finance_source'
```

## ✅ CAUSA

A API antiga estava chamando método que não existe:
```python
source_id = db.create_plan_finance_source(plan_id, data)  # ❌ NÃO EXISTE
```

O método correto que criei é:
```python
source_id = db.add_plan_finance_source(...)  # ✅ CORRETO
```

## ✅ CORREÇÃO APLICADA

### Arquivo: `modules/pev/__init__.py`

**CREATE (POST):**
```python
# ANTES (errado):
source_id = db.create_plan_finance_source(plan_id, data)

# DEPOIS (correto):
source_id = db.add_plan_finance_source(
    plan_id=plan_id,
    category=data.get('category', ''),
    description=data['description'],
    amount=str(data.get('amount', '')),
    availability=data.get('availability'),
    contribution_date=data.get('contribution_date'),
    notes=data.get('notes')
)
```

**UPDATE (PUT):**
```python
# ANTES (errado):
success = db.update_plan_finance_source(source_id, plan_id, data)

# DEPOIS (correto):
success = db.update_plan_finance_source(
    source_id=source_id,
    category=data.get('category'),
    description=data.get('description'),
    amount=data.get('amount'),
    # ... outros campos
)
```

**DELETE:**
```python
# ANTES (passava plan_id desnecessário):
success = db.delete_plan_finance_source(source_id, plan_id)

# DEPOIS (correto):
success = db.delete_plan_finance_source(source_id)
```

## 🚀 TESTE AGORA

Container foi reiniciado. Aguarde 10 segundos e:

1. **Recarregue a página:** `F5`
2. **Vá na Seção 3:** Fontes de Recursos
3. **Clique em:** `+ Nova Fonte`
4. **Preencha:**
   - Tipo: `Capital Próprio`
   - Descrição: `Aporte inicial dos sócios`
   - Data: `01/05/2026`
   - Valor: `500000`
5. **Clique:** `Salvar`

**Deve funcionar agora!** ✅

---

## 📊 TESTE COMPLETO DE FONTES

### CRIAR:
- Tipo: Capital Próprio, Valor: R$ 500.000
- Tipo: Empréstimos, Valor: R$ 200.000
- Tipo: Fornecedores, Valor: R$ 100.000

### EDITAR:
- Alterar valor de uma fonte
- Verificar atualização

### DELETAR:
- Remover uma fonte
- Verificar total recalculado

---

**AÇÃO:** Aguarde 10 segundos, recarregue (`F5`) e teste!

