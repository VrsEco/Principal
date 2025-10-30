# 🚀 PROMPT COMPLETO - Nova Página ModeFin (Modelagem Financeira)

**COPIE E COLE ESTE PROMPT EM UMA NOVA SESSÃO DO CURSOR**

---

## 🎯 CONTEXTO

Estou trabalhando no projeto **GestaoVersus** (app31), um sistema de planejamento estratégico com módulo PEV (Planejamento Estratégico Versus).

Preciso criar uma **NOVA** página de Modelagem Financeira chamada **ModeFin**, que substituirá a atual que está com problemas.

---

## 📋 REQUISITOS TÉCNICOS

### **Stack:**
- **Backend:** Python 3.9 + Flask 2.3.3
- **Database:** PostgreSQL (produção) / SQLite (desenvolvimento)
- **ORM:** SQLAlchemy 2.0.21
- **Templates:** Jinja2
- **JavaScript:** Vanilla (sem frameworks)
- **CSS:** Inline styles (padrão do projeto)
- **Docker:** Modo desenvolvimento com volumes montados

### **Arquitetura:**
- **Rota:** `/pev/implantacao/modelo/modefin?plan_id=<id>`
- **Blueprint:** `pev_bp` (já existe em `modules/pev/__init__.py`)
- **Template:** `templates/implantacao/modelo_modefin.html` (novo)
- **Variável de dados:** `plan_id` obrigatório via query string

---

## 📊 DADOS DISPONÍVEIS DO BACKEND

### **1. Produtos e Margens (✅ JÁ FUNCIONA)**

**Variável no template:** `products_totals`

**API disponível:** `GET /pev/api/implantacao/<plan_id>/products/totals`

**Estrutura:**
```json
{
  "count": 1,
  "faturamento": {"valor": 1200000.00, "percentual": 100.0},
  "custos_variaveis": {"valor": 384000.00, "percentual": 32.0},
  "despesas_variaveis": {"valor": 0.00, "percentual": 0.0},
  "margem_contribuicao": {"valor": 816000.00, "percentual": 68.0}
}
```

### **2. Custos e Despesas Fixas (✅ JÁ FUNCIONA)**

**Variável no template:** `fixed_costs_summary`

**API disponível:** `GET /pev/api/implantacao/<plan_id>/structures/fixed-costs-summary`

**Estrutura:**
```json
{
  "custos_fixos_mensal": 65400.00,
  "despesas_fixas_mensal": 8800.00,
  "total_gastos_mensal": 74200.00
}
```

### **3. Investimentos das Estruturas**

**Variável no template:** `investimentos_estruturas`

**Estrutura esperada:**
```json
{
  "caixa": {
    "total": 612000.00,
    "total_formatado": "612.000,00",
    "por_mes": {
      "2026-05": 612000.00
    }
  },
  "estoques": {
    "total": 430000.00,
    "total_formatado": "430.000,00",
    "por_mes": {
      "2026-06": 430000.00
    }
  },
  "instalacoes": {
    "total": 190000.00,
    "total_formatado": "190.000,00",
    "por_mes": {
      "2026-05": 190000.00
    }
  },
  "maquinas": {
    "total": 258500.00,
    "total_formatado": "258.500,00",
    "por_mes": {
      "2026-05": 258500.00
    }
  }
}
```

**Observação:** Os blocos de Imobilizado são dinâmicos - aparecem apenas se houver dados nas Estruturas.

### **4. Dados Financeiros Gerais**

**Variável no template:** `financeiro`

**Estrutura:**
```json
{
  "premissas": [],
  "investimento": {},
  "fluxo_negocio": {
    "variaveis": [],
    "distribuicao_lucros": {},
    "destinacao_regras": []
  },
  "fluxo_investidor": {
    "analises": {}
  }
}
```

---

## 🎨 SEÇÕES DA PÁGINA (EM ORDEM DE PRIORIDADE)

### **SEÇÃO 1: Resultados (REFERÊNCIA - COPIAR ESTE PADRÃO)**

**Prioridade:** BASE (usar como modelo)

**Funcionalidade:**
- ✅ Card de Margem de Contribuição
  - Faturamento, Custos Variáveis, Despesas Variáveis, Margem
- ✅ Card de Custos e Despesas Fixas
  - Custos Fixos, Despesas Fixas, Resultado Operacional
- ✅ Tabela de produtos cadastrados (link para página de produtos)

**Visual:**
- Gradiente verde/azul
- Cards com valores grandes
- ícones: 📦 💰 🏗️ 💎
- Valores formatados: R$ 1.200.000,00

**Dados:**
- Vêm do backend: `products_totals` e `fixed_costs_summary`
- Renderização imediata
- Refresh via API (opcional)

**⚠️ IMPORTANTE:** Esta seção JÁ ESTÁ FUNCIONANDO! Use como MODELO VISUAL e TÉCNICO!

---

### **SEÇÃO 2: Investimentos**

**Prioridade:** 1 (mais importante)

**Funcionalidade:**
- ✅ Cards de resumo por bloco
- ✅ Planilha: Bloco x Mês (layout especial)
- ✅ CRUD de Capital de Giro (Caixa, Recebíveis, Estoques)
- ✅ Integração com Estruturas (Imobilizado vem de lá)

**Visual:**
- Gradiente roxo/azul (#8b5cf6 → #6366f1)
- Cards individuais para cada bloco
- Card de total destacado

**Layout da Planilha (IMPORTANTE):**
```
┌─────────────────┬──────────┐┌────────┬────────┬────────┐
│ Bloco (FIXO)    │ Total    ││ Mês 01 │ Mês 02 │ Mês 03 │
├─────────────────┼──────────┤├────────┼────────┼────────┤
│ TOTAL           │1.490.500 ││ ...    │ ...    │ ...    │
│ Caixa           │ 612.000  ││ 612K   │ -      │ -      │
│ Recebíveis      │ 0        ││ -      │ -      │ -      │
│ Estoques        │ 430.000  ││ -      │ 430K   │ -      │
│ Instalações     │ 190.000  ││ 190K   │ -      │ -      │
│ Máquinas        │ 258.500  ││ 258K   │ -      │ -      │
└─────────────────┴──────────┘└────────┴────────┴────────┘
  ↑ FIXO (sem scroll)          ↑ SCROLL HORIZONTAL →
```

**CRÍTICO:**
- Duas divs lado a lado
- Esquerda (Bloco + Total): flex-shrink: 0
- Direita (Meses): overflow-x: auto

**Blocos:**
- **Capital de Giro:** Caixa, Recebíveis, Estoques
- **Imobilizado (dinâmico):** Instalações, Máquinas, Móveis, TI, Outros
  - Apenas aparecem se houver dados em `investimentos_estruturas`

**CRUD Capital de Giro:**
- Botão: "+ Novo Investimento em Capital de Giro"
- Modal com campos:
  - Tipo: select (Caixa | Recebíveis | Estoques)
  - Data do aporte: date
  - Valor: number (R$)
  - Descrição: textarea
  - Observações: textarea
- APIs necessárias:
  - POST `/api/implantacao/<plan_id>/finance/capital-giro`
  - PUT `/api/implantacao/<plan_id>/finance/capital-giro/<id>`
  - DELETE `/api/implantacao/<plan_id>/finance/capital-giro/<id>`
  - GET `/api/implantacao/<plan_id>/finance/capital-giro`

**Dados:**
- Imobilizado: vem de `investimentos_estruturas` (backend)
- Capital de Giro: vem de API (banco `plan_finance_capital_giro` - criar se não existir)

---

### **SEÇÃO 3: Fontes de Recursos**

**Prioridade:** 2

**Funcionalidade:**
- ✅ Card de resumo (total por tipo)
- ✅ Tabela listando todas as fontes
- ✅ CRUD completo

**Visual:**
- Gradiente verde escuro (#059669 → #047857)
- Ícone: 💼

**Tipos de Fontes:**
- Capital Próprio
- Empréstimos e Financiamentos
- Fornecedores
- Outros

**CRUD:**
- Botão: "+ Nova Fonte de Recursos"
- Modal com campos:
  - Tipo: select (opções acima)
  - Data do aporte: date
  - Valor: number (R$)
  - Observações: textarea
- APIs necessárias:
  - POST `/api/implantacao/<plan_id>/finance/sources`
  - PUT `/api/implantacao/<plan_id>/finance/sources/<id>`
  - DELETE `/api/implantacao/<plan_id>/finance/sources/<id>`
  - GET `/api/implantacao/<plan_id>/finance/sources` (✅ JÁ EXISTE)

**Dados:**
- Tabela: `plan_finance_sources` (verificar se existe via `db.list_plan_finance_sources()`)

---

### **SEÇÃO 4: Distribuição de Lucros e Outras Destinações**

**Prioridade:** 3

**Funcionalidade:**
- ✅ Card de Distribuição de Lucros
  - % do Resultado Operacional
  - Valor calculado automaticamente
  - Editar % via modal
- ✅ Card de Outras Destinações
  - % do Resultado Operacional (ou valor fixo)
  - Tabela de regras cadastradas
- ✅ Card de Resultado Final do Período
  - Resultado Operacional - Distribuição - Destinações

**Visual:**
- Gradiente laranja (#f59e0b → #d97706)
- Ícones: 💰 📊 🎯

**Cálculos:**
```
Resultado Operacional = Margem de Contribuição - Custos Fixos - Despesas Fixas
Distribuição de Lucros = Resultado Operacional × (% configurado)
Outras Destinações = Soma das regras cadastradas
Resultado Final = Resultado Operacional - Distribuição - Destinações
```

**CRUD Distribuição:**
- Modal simples:
  - Percentual: number (%)
  - Data início: date
  - Observações: textarea
- API: PUT `/api/implantacao/<plan_id>/finance/profit-distribution`

**CRUD Outras Destinações:**
- Botão: "+ Nova Destinação"
- Modal:
  - Descrição: text
  - Tipo: select (% ou Valor fixo)
  - Percentual OU Valor: number
  - Observações: textarea
- APIs:
  - POST `/api/implantacao/<plan_id>/finance/result-rules`
  - PUT `/api/implantacao/<plan_id>/finance/result-rules/<id>` (✅ JÁ EXISTEM)
  - DELETE `/api/implantacao/<plan_id>/finance/result-rules/<id>`

---

### **SEÇÃO 5: Fluxo de Caixa do Investimento**

**Prioridade:** 4

**Funcionalidade:**
- ✅ Apenas visualização
- ✅ Calculado automaticamente
- ✅ Tabela: Mês x Linhas

**Visual:**
- Gradiente azul claro (#0ea5e9 → #0284c7)
- Ícone: 📊

**Linhas da Tabela:**
1. (+) Fontes de Recursos
2. (-) Investimentos
3. (=) Saldo do Período
4. (=) Saldo Acumulado

**Cálculo:**
- Para cada mês:
  - Fontes = soma das fontes cadastradas naquele mês
  - Investimentos = soma dos investimentos naquele mês
  - Saldo Período = Fontes - Investimentos
  - Saldo Acumulado = Acumulado do mês anterior + Saldo Período

**Dados:**
- Usar `investimentos_estruturas.por_mes` + Capital de Giro
- Usar fontes cadastradas

**Sem CRUD:** Apenas visualização

---

### **SEÇÃO 6: Fluxo de Caixa do Negócio**

**Prioridade:** 5

**Funcionalidade:**
- ✅ Apenas visualização
- ✅ Calculado automaticamente
- ✅ Tabela: Mês x Linhas

**Visual:**
- Gradiente verde água (#14b8a6 → #0d9488)
- Ícone: 💹

**Linhas da Tabela:**
1. (+) Receita (Faturamento)
2. (-) Custos Variáveis
3. (-) Despesas Variáveis
4. (=) Margem de Contribuição
5. (-) Custos Fixos
6. (-) Despesas Fixas
7. (=) Resultado Operacional
8. (-) Distribuição de Lucros
9. (-) Outras Destinações
10. (=) Resultado do Período
11. (=) Saldo Acumulado

**Cálculo:**
- Usar valores mensais de:
  - Produtos (faturamento × market share)
  - Custos/Despesas fixas
  - Distribuição de lucros
  - Outras destinações

**Sem CRUD:** Apenas visualização

---

### **SEÇÃO 7: Fluxo de Caixa do Investidor**

**Prioridade:** 6

**Funcionalidade:**
- ✅ Apenas visualização
- ✅ Calculado automaticamente
- ✅ Tabela: Mês x Linhas

**Visual:**
- Gradiente roxo escuro (#7c3aed → #6d28d9)
- Ícone: 💎

**Linhas da Tabela:**
1. (+) Aportes dos Sócios
2. (-) Investimentos
3. (+) Resultado do Negócio
4. (-) Distribuição de Lucros
5. (=) Fluxo do Período
6. (=) Saldo Acumulado

**Cálculo:**
- Combinar:
  - Fluxo de Caixa do Investimento
  - Fluxo de Caixa do Negócio

**Sem CRUD:** Apenas visualização

---

### **SEÇÃO 8: Análise de Viabilidade**

**Prioridade:** 7

**Funcionalidade:**
- ✅ Métricas calculadas automaticamente:
  - TIR (Taxa Interna de Retorno)
  - Payback (meses para recuperar investimento)
  - VPL (Valor Presente Líquido)
  - ROI (Return on Investment)
- ✅ Campo de Resumo Executivo (editável pelo consultor)

**Visual:**
- Gradiente rosa (#ec4899 → #db2777)
- Ícones: 📈 📊 💡

**Layout:**
```
┌─────────────────────────────────┐
│ 📈 Métricas de Viabilidade      │
│                                 │
│ TIR: 45,2% ao ano              │
│ Payback: 18 meses              │
│ VPL: R$ 850.000,00             │
│ ROI: 120%                      │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ 💡 Resumo Executivo             │
│ [Botão Editar]                  │
│                                 │
│ (Texto editável pelo consultor) │
│ Este resumo vai para o          │
│ relatório final.                │
└─────────────────────────────────┘
```

**CRUD do Resumo:**
- Modal simples:
  - Resumo: textarea (grande)
  - Botão Salvar
- API: PUT `/api/implantacao/<plan_id>/finance/executive-summary`

**Cálculos (simplificados se não houver fórmulas prontas):**
- TIR: Placeholder "Calcular" (implementação futura)
- Payback: Total Investimentos / Resultado Operacional Médio
- VPL: Placeholder "Calcular"
- ROI: (Resultado Total / Investimento Total) × 100

---

## 🎨 PADRÃO VISUAL (COPIAR DA SEÇÃO RESULTADOS)

### **Card Padrão:**
```html
<div style="background: linear-gradient(135deg, #COR1 0%, #COR2 100%); 
            border-radius: 12px; padding: 20px; color: white; margin-bottom: 24px;">
  <div style="font-size: 13px; font-weight: 500; opacity: 0.9; margin-bottom: 16px;">
    📊 Título da Seção
  </div>
  
  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;">
    <div style="background: rgba(255, 255, 255, 0.15); border-radius: 8px; padding: 12px;">
      <div style="font-size: 11px; opacity: 0.9; margin-bottom: 4px;">Label</div>
      <div style="font-size: 18px; font-weight: 700;" id="elemento-id">R$ 0,00</div>
    </div>
  </div>
</div>
```

### **Cores por Seção:**
- Resultados: #22c55e → #16a34a (verde)
- Investimentos: #8b5cf6 → #6366f1 (roxo/azul)
- Fontes: #059669 → #047857 (verde escuro)
- Distribuição: #f59e0b → #d97706 (laranja)
- Fluxo Investimento: #0ea5e9 → #0284c7 (azul claro)
- Fluxo Negócio: #14b8a6 → #0d9488 (verde água)
- Fluxo Investidor: #7c3aed → #6d28d9 (roxo escuro)
- Análise: #ec4899 → #db2777 (rosa)

---

## 🏗️ ESTRUTURA DO CÓDIGO

### **1. Rota no Backend**

**Arquivo:** `modules/pev/__init__.py`

```python
@pev_bp.route('/implantacao/modelo/modefin')
def implantacao_modefin():
    """Nova página de modelagem financeira"""
    plan_id = _resolve_plan_id()
    db = get_db()
    plan = build_plan_context(db, plan_id)
    
    # Carregar dados
    from modules.pev.implantation_data import (
        load_financial_model,
        load_structures,
        calculate_investment_summary_by_block,
        aggregate_structure_investments,
        serialize_structure_investment_summary,
    )
    from modules.pev import products_service
    
    # Produtos e margens
    products = products_service.fetch_products(plan_id)
    products_totals = products_service.calculate_totals(products)
    
    # Estruturas e custos fixos
    estruturas = load_structures(db, plan_id)
    resumo_investimentos = calculate_investment_summary_by_block(estruturas)
    
    resumo_totais = next(
        (item for item in resumo_investimentos 
         if item.get("is_total") or (item.get("bloco") or "").strip().upper() == "TOTAL"),
        {}
    )
    
    fixed_costs_summary = {
        "custos_fixos_mensal": float(resumo_totais.get("custos_fixos_mensal") or 0),
        "despesas_fixas_mensal": float(resumo_totais.get("despesas_fixas_mensal") or 0),
        "total_gastos_mensal": float(resumo_totais.get("total_gastos_mensal") or 0),
    }
    
    # Investimentos das estruturas
    estrutura_investimentos_payload = aggregate_structure_investments(estruturas)
    investimentos_estruturas = serialize_structure_investment_summary(
        estrutura_investimentos_payload.get("categories", {})
    )
    
    # Modelo financeiro geral
    financeiro = load_financial_model(db, plan_id)
    
    # Capital de giro (novo)
    capital_giro_items = db.list_plan_capital_giro(plan_id) if hasattr(db, 'list_plan_capital_giro') else []
    
    # Fontes de recursos
    funding_sources = db.list_plan_finance_sources(plan_id)
    
    return render_template(
        "implantacao/modelo_modefin.html",
        user_name=plan.get("consultant", "Consultor responsável"),
        plan_id=plan_id,
        plan=plan,
        products_totals=products_totals,
        fixed_costs_summary=fixed_costs_summary,
        investimentos_estruturas=investimentos_estruturas,
        capital_giro_items=capital_giro_items,
        funding_sources=funding_sources,
        financeiro=financeiro,
    )
```

### **2. APIs Necessárias**

**Criar estas APIs (se não existirem):**

```python
# Capital de Giro
GET    /api/implantacao/<plan_id>/finance/capital-giro
POST   /api/implantacao/<plan_id>/finance/capital-giro
PUT    /api/implantacao/<plan_id>/finance/capital-giro/<id>
DELETE /api/implantacao/<plan_id>/finance/capital-giro/<id>

# Fontes (✅ GET já existe)
POST   /api/implantacao/<plan_id>/finance/sources
PUT    /api/implantacao/<plan_id>/finance/sources/<id>
DELETE /api/implantacao/<plan_id>/finance/sources/<id>

# Resumo Executivo
PUT    /api/implantacao/<plan_id>/finance/executive-summary
```

### **3. Tabelas do Banco**

**Verificar/Criar:**

```sql
-- Capital de Giro (NOVA)
CREATE TABLE IF NOT EXISTS plan_finance_capital_giro (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL, -- 'caixa', 'recebiveis', 'estoques'
    contribution_date DATE NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    description TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Fontes de Recursos (verificar se existe)
-- plan_finance_sources

-- Resumo Executivo (NOVA - campo simples)
ALTER TABLE plan_finance_metrics 
ADD COLUMN IF NOT EXISTS executive_summary TEXT;
```

---

## 📝 TEMPLATE ESTRUTURADO

**Arquivo:** `templates/implantacao/modelo_modefin.html`

### **Estrutura Base:**

```jinja2
{% extends "base.html" %}
{% block title %}Modelagem Financeira | Implantação{% endblock %}

{% block header_actions %}
  <!-- Navegação padrão PEV -->
  <div class="header-nav">
    <a href="/main" class="nav-link">Ecossistema</a>
    <a href="{{ url_for('pev.pev_dashboard') }}" class="nav-link active">PEV</a>
    <a href="{{ url_for('grv.grv_dashboard') }}" class="nav-link">GRV</a>
  </div>
  <div class="user-pill">
    <span class="user-name">{{ user_name }}</span>
  </div>
{% endblock %}

{% block content %}
<style>
  /* Copiar estilos da página atual (finance-card, btn-add, etc) */
  /* OU simplificar e usar apenas inline styles */
</style>

<div class="finance-wrapper" style="padding: 32px; display: flex; flex-direction: column; gap: 24px;">
  
  <!-- Header da Página -->
  <div>
    <h1 style="margin: 0 0 8px; font-size: 32px; color: #0f172a;">💰 Modelagem Financeira</h1>
    <p style="margin: 0; color: #64748b;">Plano: {{ plan.name }}</p>
    <a href="{{ url_for('pev.pev_implantacao_overview', plan_id=plan_id) }}" 
       style="display: inline-block; margin-top: 12px; color: #3b82f6; text-decoration: underline;">
      ← Voltar para Implantação
    </a>
  </div>
  
  <!-- SEÇÃO 1: RESULTADOS (usar código atual que funciona) -->
  
  <!-- SEÇÃO 2: INVESTIMENTOS -->
  
  <!-- SEÇÃO 3: FONTES DE RECURSOS -->
  
  <!-- SEÇÃO 4: DISTRIBUIÇÃO DE LUCROS -->
  
  <!-- SEÇÃO 5: FLUXO DE CAIXA DO INVESTIMENTO -->
  
  <!-- SEÇÃO 6: FLUXO DE CAIXA DO NEGÓCIO -->
  
  <!-- SEÇÃO 7: FLUXO DE CAIXA DO INVESTIDOR -->
  
  <!-- SEÇÃO 8: ANÁLISE DE VIABILIDADE -->
  
</div>

<!-- Modals -->
<div class="modal" id="capitalGiroModal">...</div>
<div class="modal" id="fundingSourceModal">...</div>
<div class="modal" id="profitDistributionModal">...</div>
<div class="modal" id="resultRuleModal">...</div>
<div class="modal" id="executiveSummaryModal">...</div>

<script>
  const planId = {{ plan_id }};
  
  // Dados do backend
  const productsTotals = {{ products_totals | tojson | safe }};
  const fixedCostsSummary = {{ fixed_costs_summary | tojson | safe }};
  const investimentosEstruturas = {{ investimentos_estruturas | tojson | safe }};
  const capitalGiroItems = {{ capital_giro_items | tojson | safe }};
  const fundingSources = {{ funding_sources | tojson | safe }};
  
  // Funções de cada seção
  function renderResultados() { ... }
  function renderInvestimentos() { ... }
  function renderFontes() { ... }
  function renderDistribuicao() { ... }
  function renderFluxoInvestimento() { ... }
  function renderFluxoNegocio() { ... }
  function renderFluxoInvestidor() { ... }
  function renderAnalise() { ... }
  
  // Inicializar
  renderResultados();
  renderInvestimentos();
  renderFontes();
  renderDistribuicao();
  renderFluxoInvestimento();
  renderFluxoNegocio();
  renderFluxoInvestidor();
  renderAnalise();
</script>
{% endblock %}
```

---

## ⚙️ PADRÕES DO PROJETO

### **Segurança:**
- ✅ Sempre usar `@login_required` nas APIs
- ✅ Validar `plan_id` pertence ao usuário
- ✅ Usar `@auto_log_crud` para auditoria

### **Código Python:**
- ✅ Seguir PEP 8
- ✅ Type hints em funções públicas
- ✅ Docstrings em formato Google
- ✅ Funcionar em PostgreSQL E SQLite

### **APIs REST:**
- ✅ URLs: `/api/recursos` (plural, snake_case)
- ✅ Status: 200 (OK), 201 (Created), 400 (Bad Request), 404 (Not Found)
- ✅ Response: `{"success": bool, "data": ..., "error": ...}`

### **JavaScript:**
- ✅ Vanilla JS (sem jQuery, sem frameworks)
- ✅ Async/await para APIs
- ✅ Tratamento de erros com try/catch
- ✅ Logs para debug: `[TAG] Mensagem`
- ✅ Sem emojis em console.log (causam encoding issues)

---

## 🚀 TAREFAS A EXECUTAR

Crie a nova página ModeFin seguindo exatamente esta especificação:

### **PASSO 1: Backend**
1. Criar rota `/implantacao/modelo/modefin`
2. Criar APIs faltantes (capital-giro, sources CRUD, executive-summary)
3. Criar tabela `plan_finance_capital_giro` se não existir
4. Verificar se tabela `plan_finance_sources` existe

### **PASSO 2: Template**
1. Criar arquivo `templates/implantacao/modelo_modefin.html`
2. Implementar as 8 seções na ordem de prioridade
3. Usar padrão visual da seção Resultados
4. JavaScript simples e direto

### **PASSO 3: Validação**
1. Testar seção por seção
2. Verificar encoding UTF-8
3. Verificar funcionamento em Docker
4. Confirmar que todos os valores aparecem

---

## ✅ CRITÉRIOS DE SUCESSO

A página estará pronta quando:
- ✅ Todas as 8 seções aparecem sem erros
- ✅ Dados corretos em cada seção:
  - Faturamento: R$ 1.200.000,00
  - Custos Variáveis: R$ 384.000,00
  - Margem: R$ 816.000,00
  - Custos Fixos: R$ 65.400,00
  - Despesas Fixas: R$ 8.800,00
  - Resultado Operacional: R$ 741.800,00
  - Total Investimentos: R$ 1.490.500,00
- ✅ CRUD de Capital de Giro funciona
- ✅ CRUD de Fontes funciona
- ✅ Fluxos de caixa calculados corretamente
- ✅ Análise de viabilidade mostra métricas
- ✅ Sem erros no console
- ✅ Sem caracteres estranhos (encoding correto)

---

## 📌 OBSERVAÇÕES IMPORTANTES

1. **Use a seção Resultados como MODELO** - ela está funcionando perfeitamente
2. **Dados do backend primeiro** - renderize imediatamente, APIs são complementares
3. **JavaScript simples** - sem complexidade desnecessária
4. **Encoding UTF-8** - evite emojis problemáticos em logs
5. **Docker com volumes** - mudanças aparecem automaticamente
6. **Teste incremental** - seção por seção

---

## 🔗 ARQUIVOS DE REFERÊNCIA

Para copiar código funcionando:
- `templates/implantacao/modelo_modelagem_financeira.html` - Seção Resultados (linhas 432-577)
- `modules/pev/__init__.py` - Rota implantacao_modelagem_financeira (linha 240-300)
- `modules/pev/products_service.py` - Exemplo de service layer

---

**FIM DO PROMPT**

---

**ESTE PROMPT ESTÁ COMPLETO E PRONTO PARA SER USADO EM UMA NOVA SESSÃO!**

**Copie tudo acima e cole em uma nova conversa do Cursor.** 🚀

