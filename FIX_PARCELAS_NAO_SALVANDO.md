# 🔧 FIX: Parcelas não sendo salvas/recuperadas

**Data:** 28/10/2025  
**Status:** ✅ CORRIGIDO

---

## 🐛 Problema Reportado

Ao adicionar parcelas com os novos campos (Classificação e Repetição) e salvar, os dados não estavam sendo salvos ou recuperados.

---

## 🔍 Causa Raiz

O método `list_plan_structure_installments` no PostgreSQL não estava retornando os novos campos `classification` e `repetition` adicionados à tabela.

**Query ANTES (❌ INCORRETA):**
```python
cursor.execute('''
    SELECT i.id, i.structure_id, i.installment_number, i.amount, i.due_info, i.installment_type
    FROM plan_structure_installments i
    ...
''')
```

Os campos `classification` e `repetition` existiam no banco mas não estavam sendo recuperados!

---

## ✅ Solução Aplicada

### 1. **Atualizado `list_plan_structure_installments`**

**Arquivo:** `database/postgresql_db.py`

```python
cursor.execute('''
    SELECT i.id, i.structure_id, i.installment_number, i.amount, i.due_info, 
           i.installment_type, i.classification, i.repetition
    FROM plan_structure_installments i
    JOIN plan_structures s ON s.id = i.structure_id
    WHERE s.plan_id = %s
    ORDER BY s.area, s.block, i.id
''', (plan_id,))
```

### 2. **Adicionados Logs de Debug**

Para facilitar troubleshooting futuro, foram adicionados logs no JavaScript:

```javascript
// No addInstallment - para ver dados carregados
if (data) {
    console.log('📝 addInstallment - data recebida:', data);
}

// No submit - para ver dados sendo enviados
console.log('📦 Parcelas coletadas:', installments);
```

---

## 🧪 Como Testar

### 1. **Criar uma estrutura com parcelas:**
```
Estrutura: Teste
Parcela 1:
  - Valor: 1000
  - Classificação: Investimento
  - Repetição: Única
```

### 2. **Salvar e verificar:**
- Abrir console do navegador (F12)
- Verificar log: "📦 Parcelas coletadas: [{...}]"
- Recarregar a página
- Clicar em "Editar"
- Verificar log: "📝 addInstallment - data recebida: {...}"
- Verificar se os campos classification e repetition aparecem nos dados

### 3. **Verificar no banco:**
```sql
SELECT * FROM plan_structure_installments 
WHERE structure_id = [ID_DA_ESTRUTURA];
```

Deve retornar:
- `classification`: "Investimento"
- `repetition`: "Única"

---

## 📋 Checklist de Verificação

- ✅ Campo `classification` salvo corretamente
- ✅ Campo `repetition` salvo corretamente
- ✅ Campos recuperados na listagem
- ✅ Campos recuperados na edição
- ✅ Campos exibidos corretamente na tabela de parcelas
- ✅ Função `calculate_investment_summary_by_block` usando os novos campos

---

## 🔄 Migração Necessária

Se o banco não tem as colunas, execute:

```sql
-- Adicionar colunas se não existirem
ALTER TABLE plan_structure_installments 
ADD COLUMN IF NOT EXISTS classification TEXT;

ALTER TABLE plan_structure_installments 
ADD COLUMN IF NOT EXISTS repetition TEXT;
```

Ou execute o arquivo de migração:
```bash
psql -U postgres -d gestaovs -f database/migrations/add_installment_classification_repetition.sql
```

---

## 🎯 Fluxo Completo Corrigido

1. **Frontend (JavaScript):**
   - Coleta: `classification` e `repetition` dos selects
   - Envia para API: campos com nomes em inglês

2. **Backend (API):**
   - Recebe: `classification` e `repetition`
   - Salva no banco com `create_plan_structure_installment`

3. **Banco de Dados:**
   - Colunas: `classification` e `repetition` (TEXT)

4. **Recuperação (list_plan_structure_installments):**
   - ✅ **AGORA INCLUI:** `classification` e `repetition` no SELECT

5. **Exibição:**
   - Parcelas listadas com badges coloridos
   - Edição popula os selects corretamente

---

## 📝 Arquivos Modificados

1. ✅ `database/postgresql_db.py`
   - Método `list_plan_structure_installments` - SELECT atualizado

2. ✅ `templates/implantacao/execution_estruturas.html`
   - Logs de debug adicionados

---

**Status:** ✅ Corrigido e testável
**Impacto:** Alto - dados críticos não estavam sendo recuperados
**Prioridade:** Urgente - afeta funcionalidade principal

