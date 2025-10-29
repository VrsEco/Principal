# ✅ Correção: Cálculo de Investimentos por Bloco

**Data:** 27/10/2025  
**Arquivo:** `modules/pev/implantation_data.py`  
**Função:** `calculate_investment_summary_by_block()`

---

## 🐛 Problema Identificado

A classificação dos investimentos estava incorreta:

**Exemplo do Galpão:**
- ❌ **Antes:** R$ 180.000 aparecendo em "Gastos Recorrentes Mensais"
- ✅ **Correto:** R$ 180.000 em "Custo de Aquisição" + R$ 3.200 em "Gastos Recorrentes Mensais"

---

## 🔍 Causa Raiz

A função não estava tratando corretamente itens com **repetição = "parcelada"**:

1. **Problema 1:** Valor total do item parcelado ia para custo de aquisição, mas sem considerar as parcelas mensais
2. **Problema 2:** Não distinguia entre valor de aquisição e valor de parcela mensal

---

## ✅ Solução Aplicada

### **Nova Lógica (linhas 1751-1768):**

```python
if repeticao in ["parcelada"] and parcelas:
    # Valor total vai para custo de aquisição
    blocos_totais[bloco_nome]["custo_aquisicao"] += valor
    
    # Parcela mensal vai para gasto mensal recorrente
    parcelas_mensais = [p for p in parcelas if p.get("tipo") == "mensal"]
    if parcelas_mensais:
        valor_parcela = parcelas_mensais[0].get("valor")
        blocos_totais[bloco_nome]["gasto_mensal"] += valor_parcela
```

---

## 📋 Regras de Classificação

### **1. Repetição = "parcelada" COM parcelas cadastradas:**
- ✅ Valor total → **Custo de Aquisição**
- ✅ Valor da parcela mensal → **Gasto Recorrente Mensal**

### **2. Repetição = "única":**
- ✅ Valor total → **Custo de Aquisição**

### **3. Repetição = "mensal":**
- ✅ Valor → **Gasto Recorrente Mensal**

### **4. Repetição = "anual":**
- ✅ Valor → **Gasto Recorrente Anual**

### **5. Repetição = "trimestral":**
- ✅ Valor ÷ 3 → **Gasto Recorrente Mensal**

### **6. Repetição = "semestral":**
- ✅ Valor ÷ 6 → **Gasto Recorrente Mensal**

---

## 🧪 Exemplo de Cálculo Correto

### **Galpão:**
- Valor de aquisição: R$ 180.000,00
- Repetição: "parcelada"
- Parcelas: 60x de R$ 3.200,00 (mensal)

**Resultado esperado:**
- Custo de Aquisição: **R$ 180.000,00**
- Gasto Recorrente Mensal: **R$ 3.200,00**
- Gasto Recorrente Anual: **R$ 38.400,00** (R$ 3.200 × 12)

---

## 🚀 Como Testar

1. Acesse: http://127.0.0.1:5003/implantacao/executivo?plan_id=1

2. Verifique a tabela "Resumo de Investimentos por Estrutura"

3. **Validar:**
   - Instalações → Custo de Aquisição deve incluir o valor total do galpão
   - Instalações → Gasto Mensal deve incluir a parcela mensal do galpão

---

## 📊 Estrutura de Dados

### **Item com Parcelas:**
```python
{
    "valor": "180000.00",  # Valor total
    "repeticao": "parcelada",
    "parcelas": [
        {"numero": 1, "valor": "3200.00", "tipo": "mensal"},
        {"numero": 2, "valor": "3200.00", "tipo": "mensal"},
        ...
    ]
}
```

### **Processamento:**
- `valor` (R$ 180.000) → custo_aquisicao
- `parcelas[0].valor` (R$ 3.200) → gasto_mensal

---

## ⚠️ Casos Especiais

### **Caso 1: Parcelado sem parcelas cadastradas**
```python
if repeticao == "parcelada" and not parcelas:
    # Fallback: vai para custo_aquisicao
    blocos_totais[bloco_nome]["custo_aquisicao"] += valor
```

### **Caso 2: Parcelas anuais**
```python
parcelas_anuais = [p for p in parcelas if p.get("tipo") == "anual"]
# Parcela anual → gasto_anual
```

---

## 🔧 Arquivos Modificados

- ✅ `modules/pev/implantation_data.py` (linhas 1750-1781)

---

## 📝 Notas Técnicas

1. **Decimal Precision:** Usa `Decimal` para evitar erros de arredondamento
2. **Parcela de Referência:** Usa primeira parcela mensal como valor recorrente
3. **Tipo de Parcela:** Verifica campo `tipo` para distinguir mensal/anual/etc.

---

**Status:** ✅ CORRIGIDO  
**Testado:** Aguardando validação do usuário  
**Próximos Passos:** Testar com dados reais e validar todos os blocos

