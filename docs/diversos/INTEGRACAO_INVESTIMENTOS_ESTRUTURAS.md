# ✅ Integração: Investimentos das Estruturas → Modelagem Financeira

**Data:** 28/10/2025  
**Status:** ✅ **IMPLEMENTADO**

---

## 🎯 Objetivo

Integrar automaticamente os valores de **investimentos** cadastrados em **Estruturas de Execução** na seção de **Investimentos** da **Modelagem Financeira**.

---

## ✅ Alterações Realizadas

### **1. Backend - Correção do Mapeamento de Investimentos**

**Arquivo:** `modules/pev/__init__.py`

**Problema:** O código estava tentando acessar campo inexistente `custo_aquisicao_total`.

**Solução:** Corrigir para usar o campo correto `investimentos` retornado por `calculate_investment_summary_by_block()`.

```python
# Linha 320 - ANTES:
valor = item.get('custo_aquisicao_total', 0)

# Linha 320 - DEPOIS:
valor = item.get('investimentos', Decimal('0'))
```

**Mapeamento dos Blocos:**
- **Instalações** + **Imóveis** → `investimentos_estruturas['instalacoes']`
- **Máquinas e Equipamentos** → `investimentos_estruturas['maquinas']`
- **Móveis e Utensílios** + **TI e Comunicação** + **Outros** + **Pessoas** → `investimentos_estruturas['outros']`

---

### **2. Frontend - Integração dos Valores no JavaScript**

**Arquivo:** `templates/implantacao/modelo_modelagem_financeira.html`

#### **2.1. Carregar Dados das Estruturas**

```javascript
// Adiciona log para debug
console.log('🏗️ Investimentos das Estruturas:', investimentosEstruturasData);

// Para cada item de Imobilizado, usar valores das estruturas
if (item.category_id === 2) {
  let estruturaTotal = 0;
  
  // Mapear itens para dados de estruturas
  if (item.item_name === 'Instalações' && investimentosEstruturasData.instalacoes) {
    estruturaTotal = parseFloat(investimentosEstruturasData.instalacoes.total) || 0;
  } else if (item.item_name === 'Máquinas e Equipamentos' && investimentosEstruturasData.maquinas) {
    estruturaTotal = parseFloat(investimentosEstruturasData.maquinas.total) || 0;
  } else if (item.item_name === 'Outros Investimentos' && investimentosEstruturasData.outros) {
    estruturaTotal = parseFloat(investimentosEstruturasData.outros.total) || 0;
  }
  
  if (estruturaTotal > 0) {
    itemTotals[item.id] = estruturaTotal;
    itemsByMonth[item.id] = {}; // Não distribuir por meses
    console.log(`  🏗️ Estruturas - ${item.item_name}: R$ ${estruturaTotal.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`);
  }
}
```

#### **2.2. Renderizar Totais Corretamente**

```javascript
// Função renderInvestmentSpreadsheet - agora recebe itemTotals
async function renderInvestmentSpreadsheet(categories, itemsByMonth, itemTotals) {
  // ...
  
  // Usar itemTotals se disponível (para investimentos de estruturas), senão calcular da monthlyData
  const total = itemTotals[item.id] || Object.values(monthlyData).reduce((sum, val) => sum + val, 0);
  
  // ...
}
```

#### **2.3. Fluxo de Caixa de Investimento**

```javascript
// Função renderInvestmentCashflow - agora recebe itemTotals
async function renderInvestmentCashflow(categories, itemsByMonth, itemTotals) {
  // ...
  
  // Para investimentos de estruturas (imobilizado sem dados mensais),
  // mostrar o total no primeiro mês
  if (category.category_type === 'imobilizado' && month.key === months[0].key) {
    for (const itemId in itemTotals) {
      const item = investmentItemsCache.find(i => i.id == itemId);
      if (item && item.category_id === category.id) {
        const monthlyData = itemsByMonth[itemId] || {};
        // Se não tem dados mensais mas tem total, é investimento de estrutura
        if (Object.keys(monthlyData).length === 0 && itemTotals[itemId] > 0) {
          imobilizado += itemTotals[itemId];
        }
      }
    }
  }
  
  // ...
}
```

---

## 📊 Resultado

### **Antes:**
```
Categoria       | Item                      | Total
----------------|---------------------------|----------
Imobilizado     | Instalações               | R$ 0,00
Imobilizado     | Máquinas e Equipamentos   | R$ 0,00
Imobilizado     | Outros Investimentos      | R$ 0,00
```

### **Depois (com dados de estruturas):**
```
Categoria       | Item                      | Total
----------------|---------------------------|----------
Imobilizado     | Instalações               | R$ 180.000,00
Imobilizado     | Máquinas e Equipamentos   | R$ 0,00
Imobilizado     | Outros Investimentos      | R$ 0,00
```

---

## 🎯 Comportamento

### **Valores Dinâmicos:**
✅ Os valores são calculados **automaticamente** com base nos dados de **Estruturas de Execução**  
✅ Apenas **investimentos** são considerados (não inclui custos fixos ou despesas fixas)  
✅ Os valores são atualizados em **tempo real** ao acessar a página

### **Exibição:**
✅ **Coluna Total:** Mostra o valor total do investimento por bloco  
✅ **Colunas de Meses:** Não distribui por meses (investimentos de estrutura são valores consolidados)  
✅ **Fluxo de Caixa:** O total aparece no **primeiro mês** da projeção

### **Mapeamento de Blocos:**

| Bloco (Estruturas)       | Item (Modelagem Financeira)   |
|--------------------------|-------------------------------|
| Instalações              | → Instalações                 |
| Imóveis                  | → Instalações                 |
| Máquinas e Equipamentos  | → Máquinas e Equipamentos     |
| Móveis e Utensílios      | → Outros Investimentos        |
| TI e Comunicação         | → Outros Investimentos        |
| Outros                   | → Outros Investimentos        |
| Pessoas*                 | → Outros Investimentos        |

*_Nota: Investimentos em Pessoas (se houver) são raros, geralmente são despesas fixas._

---

## 🔧 Compatibilidade

✅ **PostgreSQL:** Funciona corretamente (usa Decimal para precisão)  
✅ **SQLite:** Funciona corretamente (usa Decimal para precisão)  
✅ **Docker:** Compatível (não há dependências específicas)

---

## 📋 Como Testar

1. **Acessar Estruturas de Execução:**
   ```
   http://127.0.0.1:5003/pev/implantacao/executivo?plan_id=8
   ```
   - Verificar valores na tabela "Resumo de Investimentos por Estrutura"
   - Anotar o valor de "Instalações" (ex: R$ 180.000,00)

2. **Acessar Modelagem Financeira:**
   ```
   http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=8
   ```
   - Na seção "Investimentos", verificar linha "Imobilizado → Instalações"
   - O valor deve ser **igual** ao valor das estruturas (R$ 180.000,00)

3. **Verificar Console do Navegador:**
   ```javascript
   🏗️ Investimentos das Estruturas: {
     instalacoes: { total: 180000, total_formatado: "R$ 180.000,00" },
     maquinas: { total: 0, total_formatado: "R$ 0,00" },
     outros: { total: 0, total_formatado: "R$ 0,00" }
   }
   
   🏗️ Estruturas - Instalações: R$ 180.000,00
   ```

---

## ✅ Arquivos Modificados

```
✅ modules/pev/__init__.py                               (1 linha alterada)
✅ templates/implantacao/modelo_modelagem_financeira.html (90+ linhas alteradas)
```

---

## 🎨 Visual

A integração é **transparente** para o usuário:

- ✅ Linhas de Imobilizado destacadas com **fundo verde claro**
- ✅ Link informativo: _"Os valores de Imobilizado são calculados automaticamente com base nos dados cadastrados em Estruturas de Execução → Resumo de Investimentos"_
- ✅ Valores aparecem formatados em **R$ xxx.xxx,xx**

---

## 🔄 Próximos Passos (Opcional)

1. ✅ Adicionar distribuição mensal dos investimentos (se necessário)
2. ✅ Permitir editar datas de investimento por bloco
3. ✅ Adicionar gráfico visual de investimentos vs. fontes de recursos

---

**Versão:** 1.0  
**Última atualização:** 28/10/2025  
**Testado:** ✅ Sim  
**Em produção:** Pronto para deploy

