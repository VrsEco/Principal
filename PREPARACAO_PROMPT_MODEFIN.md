# 📋 PREPARAÇÃO PARA PROMPT - Nova Página ModeFin

## 🎯 OBJETIVO
Criar prompt completo para construir página de Modelagem Financeira do ZERO, com novo nome (ModeFin), que funcione perfeitamente.

---

## 📊 INFORMAÇÕES QUE PRECISO COLETAR

### **1. ESTRUTURA DE DADOS DO BACKEND**

#### **1.1 Produtos (✅ JÁ FUNCIONANDO)**
- API: `/api/implantacao/<plan_id>/products/totals`
- Retorna:
```json
{
  "faturamento": {"valor": 1200000, "percentual": 100},
  "custos_variaveis": {"valor": 384000, "percentual": 32},
  "despesas_variaveis": {"valor": 0, "percentual": 0},
  "margem_contribuicao": {"valor": 816000, "percentual": 68}
}
```

#### **1.2 Custos Fixos (✅ JÁ FUNCIONANDO)**
- API: `/api/implantacao/<plan_id>/structures/fixed-costs-summary`
- Retorna:
```json
{
  "custos_fixos_mensal": 65400,
  "despesas_fixas_mensal": 8800,
  "total_gastos_mensal": 74200
}
```

#### **1.3 Investimentos das Estruturas**
- Variável: `investimentos_estruturas`
- Formato esperado:
```json
{
  "caixa": {"total": 612000, "por_mes": {"2026-05": 612000}},
  "estoques": {"total": 430000, "por_mes": {"2026-06": 430000}},
  "instalacoes": {"total": 190000, "por_mes": {"2026-05": 190000}},
  "maquinas": {"total": 258500, "por_mes": {"2026-05": 258500}}
}
```
❓ **PRECISO CONFIRMAR:** Este formato está correto?

#### **1.4 Outras Seções**
❓ **PRECISO SABER:** Quais dados vêm do backend para:
- Fontes de Recursos?
- Fluxo de Caixa do Investimento?
- Fluxo de Caixa do Negócio?
- Fluxo de Caixa do Investidor?
- Análise de Viabilidade?

---

### **2. SEÇÕES DA PÁGINA**

#### **2.1 Resultados (✅ MODELO DE REFERÊNCIA)**
**Funcionalidade:**
- Card de Margem de Contribuição (Faturamento, Custos, Despesas, Margem)
- Card de Custos Fixos (Custos, Despesas, Resultado Operacional)
- Tabela de produtos cadastrados

**Visual:**
- Gradiente verde/azul
- Cards com valores
- Dados vêm do backend + refresh via API
- ✅ FUNCIONANDO PERFEITAMENTE

#### **2.2 Investimentos**
**Funcionalidade:**
❓ **PRECISO SABER:**
1. Deve ter cards de resumo por bloco? (Sim/Não)
2. Deve ter planilha Bloco x Mês? (Sim/Não)
3. Deve ter tabela de Capital de Giro separada? (Sim/Não)
4. Deve ter botão para cadastrar novos? (Sim/Não)
5. Deve permitir editar/deletar? (Sim/Não)

**Blocos a mostrar:**
❓ **CONFIRME:**
- Caixa
- Recebíveis
- Estoques
- Instalações
- Máquinas e Equipamentos
- Móveis e Utensílios
- TI e Comunicação
- Outros?

#### **2.3 Fontes de Recursos**
❓ **PRECISO SABER:**
1. Quais tipos de fontes existem?
   - Capital próprio?
   - Empréstimos?
   - Fornecedores?
   - Outros?
2. Precisa CRUD completo? (Criar, Editar, Deletar)
3. Visual: Card de resumo + tabela?

#### **2.4 Distribuição de Lucros**
❓ **PRECISO SABER:**
1. Como é calculado?
   - % fixo do Resultado Operacional?
   - Valor manual?
2. Precisa editar?
3. Visual: Card simples?

#### **2.5 Fluxos de Caixa (3 seções)**
❓ **PRECISO SABER:**
1. Qual a diferença entre:
   - Fluxo de Caixa do Investimento
   - Fluxo de Caixa do Negócio
   - Fluxo de Caixa do Investidor
2. São tabelas mês a mês?
3. Quais linhas cada um tem?
4. Dados vêm do backend ou são calculados?

#### **2.6 Análise de Viabilidade**
❓ **PRECISO SABER:**
1. Quais métricas mostrar?
   - TIR (Taxa Interna de Retorno)?
   - Payback?
   - VPL (Valor Presente Líquido)?
   - ROI?
2. São calculados automaticamente?
3. Permite edição manual?

---

### **3. BANCO DE DADOS**

#### **Tabelas Envolvidas:**
❓ **CONFIRME QUAIS TABELAS EXISTEM:**
- ✅ `plan_products` - Produtos
- ✅ `plan_structures` - Estruturas
- ✅ `plan_structure_installments` - Parcelas das estruturas
- ❓ `plan_finance_investments` - Investimentos?
- ❓ `plan_finance_sources` - Fontes de recursos?
- ❓ `plan_finance_cashflow` - Fluxo de caixa?
- ❓ `plan_finance_metrics` - Métricas de viabilidade?
- ❓ Outras?

---

### **4. FUNCIONALIDADES ESPERADAS**

#### **Para cada seção, preciso saber:**

**Seção Investimentos:**
- [ ] Apenas visualização?
- [ ] CRUD de Capital de Giro?
- [ ] Integração com Estruturas?

**Seção Fontes:**
- [ ] Apenas visualização?
- [ ] CRUD completo?
- [ ] Campos: tipo, data, valor, observações?

**Seção Fluxos:**
- [ ] Apenas visualização calculada?
- [ ] Permite edição manual?
- [ ] Exportar para Excel?

**Seção Análise:**
- [ ] Cálculo automático?
- [ ] Edição de premissas?
- [ ] Histórico de análises?

---

### **5. VISUAL/DESIGN**

❓ **CONFIRME:**
- Seguir padrão da seção Resultados? (Sim/Não)
- Cores específicas por seção?
  - Investimentos: Roxo/Azul?
  - Fontes: Verde?
  - Fluxos: Laranja?
  - Análise: Rosa?

---

## 📝 RESPONDA ESTAS PERGUNTAS:

### **PERGUNTA 1: Dados Disponíveis**
Copie e cole no console e me mande o resultado:
```javascript
console.log('=== DADOS BACKEND ===');
console.log('investimentos_estruturas:', investimentosEstruturasData);
console.log('financeiro:', typeof financeiro !== 'undefined' ? financeiro : 'não definido');
console.log('resumo_investimentos:', typeof resumo_investimentos !== 'undefined' ? resumo_investimentos : 'não definido');
```

### **PERGUNTA 2: Funcionalidades**
Para cada seção, me diga:
- **Investimentos:** (visualização / CRUD / misto)
- **Fontes:** (visualização / CRUD / misto)
- **Fluxos:** (visualização / edição / ambos)
- **Análise:** (calculado / manual / ambos)

### **PERGUNTA 3: Estrutura**
Quantas linhas/tipos cada seção deve ter?

Exemplo para Investimentos:
- Caixa
- Recebíveis
- Estoques
- Instalações
- Máquinas
- Móveis
- TI
- Outros
- TOTAL

### **PERGUNTA 4: Prioridades**
Ordene por importância (1 = mais importante):
- [ ] Investimentos
- [ ] Fontes de Recursos
- [ ] Distribuição de Lucros
- [ ] Fluxo de Caixa do Investimento
- [ ] Fluxo de Caixa do Negócio
- [ ] Fluxo de Caixa do Investidor
- [ ] Análise de Viabilidade

---

## ✅ APÓS VOCÊ RESPONDER:

Vou criar um PROMPT COMPLETO que inclui:
1. Especificação técnica detalhada
2. Estrutura de dados
3. Visual esperado
4. Funcionalidades de cada seção
5. Código de referência (seção Resultados)
6. Padrões do projeto

E vamos construir a página ModeFin do ZERO, funcionando 100%!

---

**Por favor, responda as 4 perguntas acima para eu criar o prompt perfeito! 🚀**

