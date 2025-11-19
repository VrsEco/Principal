# 📋 PROMPT: 6 Relatórios Modulares - Sistema PEV

**Data:** 30/10/2025  
**Versão:** 4.0 (Modular e Independente)  
**Estratégia:** 6 páginas HTML separadas + 6 rotas Flask independentes

---

## 🎯 FILOSOFIA

**Por que modular?**
- ✅ Cada relatório com layout PRÓPRIO otimizado para seus dados
- ✅ Imprimir só o que precisa (capa, ou financeiro, ou atividades)
- ✅ Flexibilidade total (retrato/paisagem por necessidade)
- ✅ Mais fácil manter e ajustar
- ✅ Não força um padrão único

---

## 🎨 DESIGN GLOBAL

### **Cores (Pastéis Saturadas, Fundos Claros)**
```css
--primary: #1a76ff;
--primary-bg: #bfdbfe;
--success: #10b981;
--success-bg: #a7f3d0;
--purple: #6366f1;
--purple-bg: #c7d2fe;
--warning: #f59e0b;
--warning-bg: #fcd34d;

/* Fundos sempre claros */
--white: #ffffff;
--gray-50: #f1f5f9;
--gray-100: #e2e8f0;

/* Texto */
--text-dark: #0f172a;
--text-medium: #475569;
--text-light: #64748b;
```

### **Tipografia Consistente**
```css
font-family: 'Inter', sans-serif;
h1: 48px bold
h2: 32px bold  
h3: 22px semibold
h4: 18px semibold
body: 15px regular
```

### **Componentes Reutilizáveis**
- Feature Card (branco com borda)
- Metric Card (gradiente pastel)
- Styled Table (zebra com header azul)
- Info Box (gradiente com borda lateral)
- Abstract Image SVG (gradientes suaves)

---

## 📄 RELATÓRIO 1: CAPA + RESUMO EXECUTIVO

### **Especificações:**
- **Arquivo:** `relatorio_1_capa_resumo.html`
- **Rota:** `/pev/implantacao/relatorio/01-capa-resumo?plan_id=X`
- **Orientação:** RETRATO
- **Título:** "Estudo e Análise de Viabilidade de Implantação de Negócio"

### **Estrutura:**

**CAPA (Página 1):**
- Hero grande com gradiente pastel saturado
- Logo empresa centralizado grande
- Título: "Estudo e Análise de Viabilidade de Implantação de Negócio"
- Subtítulo: Nome do plano
- 4 cards médios de meta info (empresa, consultor, data, versão)
- SVG pattern abstrato de fundo
- Logo Versus no rodapé

**RESUMO EXECUTIVO (Página 2):**
- Header: "Resumo Executivo"
- 4 metric cards medios (segmentos, estruturas, atividades, investimento total)
- Grid 2x2 de feature cards:
  - Planejamento (nome, status, versão, consultor)
  - Projeto (nome, descrição, link kanban)
  - Escopo (totais consolidados)
  - Próximos marcos (3-4 atividades principais)
- Imagem abstrata decorativa no rodapé

### **Dados Necessários:**
```python
{
    'plan': {...},
    'projeto': {...},
    'segmentos_count': int,
    'estruturas_count': int,
    'atividades_count': int,
    'investimento_total': str,
    'proximas_atividades': [...]
}
```

---

## 📄 RELATÓRIO 2: ALINHAMENTO ESTRATÉGICO

### **Especificações:**
- **Arquivo:** `relatorio_2_alinhamento.html`
- **Rota:** `/pev/implantacao/relatorio/02-alinhamento?plan_id=X`
- **Orientação:** RETRATO
- **Correção:** Metas Financeiras igual a Visão (info box, não lista quebrada)

### **Estrutura:**

**Página 1:**
- Header: "Alinhamento Estratégico"
- Info Box: Visão Compartilhada (texto/lista)
- Info Box: Metas Financeiras (texto/lista)
- Info Box: Princípios Orientadores (lista)

**Página 2:**
- Header: "Equipe Decisora"
- Grid de cards (2-3 colunas) - um card por sócio:
  - Nome (título)
  - Papel, motivação, compromisso, risco (lista)
- Imagem abstrata decorativa

**Página 3:**
- Header: "Agenda de Convergência"
- Tabela COMPLETA (todas as atividades):
  - O que | Quem | Quando | Como
- Resumo no rodapé (total de atividades)

### **Dados Necessários:**
```python
{
    'alinhamento': {
        'visao': str or list,
        'metas': list,  # RENDERIZAR COMO INFO BOX
        'principios': list,
        'socios': [...],
        'agenda': [...]
    }
}
```

---

## 📄 RELATÓRIO 3: MODELO & MERCADO

### **Especificações:**
- **Arquivo:** `relatorio_3_modelo_mercado.html`
- **Rota:** `/pev/implantacao/relatorio/03-modelo-mercado?plan_id=X`
- **Orientação:** RETRATO
- **Layout:** Múltiplos segmentos por página (organizado, compacto, visualmente agradável)

### **Estrutura:**

**Estratégia:** Mostrar TODOS os segmentos sem resumir, organizando visualmente para ser bonito e compacto.

**Por Segmento:**
- Header compacto: "Segmento: [Nome]"
- Layout em colunas otimizado:
  - **Coluna 1 (60%):**
    - Info Box: Público-alvo (lista completa)
    - Info Box: Diferenciais (lista completa)
  - **Coluna 2 (40%):**
    - Info Box: Evidências (lista completa)
    - Cards de Personas (nome + perfil resumido)
- Tabela de Produtos (COMPLETA - todas colunas):
  - Produto | Preço | Custos Var | Despesas Var | Margem | Mercado | Market Share
  - Design compacto com fonte menor se necessário
- Card de totais (faturamento, margem) - compacto ao lado da tabela

**Visual:**
- Espaçamento reduzido entre segmentos (separador sutil)
- Cores alternadas por segmento (azul → verde → roxo → repetir)
- Imagens abstratas pequenas entre segmentos (decorativo)
- Máximo de conteúdo sem poluir

### **Dados Necessários:**
```python
{
    'segmentos': [  # TODOS os segmentos
        {
            'nome': str,
            'proposta': {
                'publico': [...],  # COMPLETO
                'diferenciais': [...],  # COMPLETO
                'evidencias': [...],  # COMPLETO
            },
            'personas': [...],  # TODAS
            'produtos': [...],  # TODOS
            'totais': {
                'faturamento_mensal': {...},
                'margem_contribuicao': {...}
            }
        }
    ]
}
```

---

## 📄 RELATÓRIO 4: ESTRUTURAS DE EXECUÇÃO

### **Especificações:**
- **Arquivo:** `relatorio_4_estruturas.html`
- **Rota:** `/pev/implantacao/relatorio/04-estruturas?plan_id=X`
- **Orientação:** RETRATO

### **Estrutura:**

**Página 1:**
- Header: "Estruturas de Execução"
- Grid auto de feature cards (todas as áreas):
  - Nome da área
  - Capacidade suportada (destaque)
  - Lista de blocos e pontos (COMPLETOS)

**Página 2:**
- Header: "Resumo Financeiro das Estruturas"
- Tabela COMPLETA (todas áreas):
  - Área | Investimentos | Custos Fixos | Despesas Fixas | Capacidade
  - Linha TOTAL no final
- Cards de métricas (totais gerais)

### **Dados Necessários:**
```python
{
    'estruturas': [
        {
            'area': str,
            'capacidade_formatada': str,
            'resumo': [...],  # TODOS blocos
            'total_investimentos': str,
            'custos_fixos_mensal': str,
            'despesas_fixas_mensal': str
        }
    ]
}
```

---

## 📄 RELATÓRIO 5: MODELAGEM FINANCEIRA

### **Especificações:**
- **Arquivo:** `relatorio_5_modelagem_financeira.html`
- **Rota:** `/pev/implantacao/relatorio/05-financeira?plan_id=X`
- **Orientação:** PAISAGEM (múltiplas páginas)
- **Dados:** ModeFin COMPLETO (todos os dados cadastrados na página ModeFin)
- **Páginas:** 4-6 páginas (TODAS as 8 seções)

### **Estrutura COMPLETA:**

**Seção 1: Resultados & Produtos**
- 3 Metric Cards medios:
  - Faturamento Mensal (da base de produtos)
  - Margem de Contribuição (% e valor)
  - Gastos Fixos Mensais (custos + despesas)
- Tabela de Produtos COMPLETA:
  - Produto | Preço Venda | Custos Var % | Despesas Var % | Margem Unit % | Meta Market Share
  - Linha de TOTAIS

**Seção 2: Investimentos**
- Card: Capital de Giro
  - Tabela: Item | Valores por Mês (colunas dinâmicas)
  - Itens: Caixa, Recebíveis, Estoques
- Card: Imobilizado
  - Tabela: Categoria | Valores por Mês
  - Categorias: Instalações, Máquinas e Equipamentos, Outros
- Card: Total Consolidado (métrica grande)

**Seção 3: Fontes de Recursos**
- Tabela COMPLETA:
  - Tipo | Categoria | Valor | Data de Disponibilidade | Observações
- Card resumo: Total de Fontes

**Seção 4: Distribuição de Lucros**
- Tabela de Destinações:
  - Descrição | Percentual % | Data de Início | Observações
- Card: Total de Destinações %

**Seção 5: Fluxo de Caixa do Investimento**
- ⚠️ **IMPORTANTE:** Dados construídos/calculados na página ModeFin
- Tabela com ~16 linhas:
  - 12 primeiros meses (Jan/26, Fev/26... Dez/26)
  - Restante Ano 2 (2027)
  - Ano 3 (2028)
  - Ano 4 (2029)
  - Ano 5 (2030)
  - Ano 6 (2031)
- Colunas:
  - Período | Capital de Giro | Imobilizado | Total Investimentos | Fontes de Recursos | Saldo Período | Saldo Acumulado

**Seção 6: Fluxo de Caixa do Negócio**
- ⚠️ **IMPORTANTE:** Calculado com base em produtos, custos fixos/variáveis
- Tabela com ~16 linhas (mesmo formato de período)
- Colunas:
  - Período | Receita | Custos Variáveis | Despesas Variáveis | Margem Contribuição | Custos Fixos | Despesas Fixas | Resultado Operacional | Destinações | Resultado do Período

**Seção 7: Fluxo de Caixa do Investidor**
- ⚠️ **IMPORTANTE:** Calculado com investimentos + distribuições
- Tabela com ~16 linhas (mesmo formato)
- Colunas:
  - Período | Aporte/Investimento | Distribuição de Lucros | Saldo do Período | Saldo Acumulado

**Seção 8: Análise de Viabilidade**
- Card grande destacado com:
  - VPL (Valor Presente Líquido)
  - TIR 2 anos
  - TIR 3 anos
  - TIR 5 anos
  - Payback
  - Comentários/Observações
- Parâmetros configuráveis (taxa desconto, horizonte)

### **Dados Necessários:**
```python
{
    # Seção 1
    'products': [...],  # Lista de produtos
    'products_totals': {
        'faturamento': {'valor_formatado': str, 'percentual_formatado': str},
        'margem_contribuicao': {'valor_formatado': str, 'percentual_formatado': str}
    },
    
    # Seção 2
    'capital_giro_items': [...],  # Investimentos em capital de giro
    'investimentos_estruturas': {  # Investimentos imobilizados
        'instalacoes': {...},
        'maquinas': {...},
        'outros': {...}
    },
    
    # Seção 3
    'funding_sources': [  # Fontes de recursos
        {
            'source_type': str,
            'source_category': str,
            'amount': decimal,
            'amount_formatted': str,
            'contribution_date': date,
            'notes': str
        }
    ],
    
    # Seção 4
    'profit_distribution': {...},  # Distribuição % sócios
    'result_rules': [  # Outras destinações
        {
            'description': str,
            'percentage': decimal,
            'start_date': date,
            'notes': str
        }
    ],
    
    # Seções 5, 6, 7 - CALCULADOS no frontend ModeFin
    # Precisam ser reconstruídos no backend para o relatório
    'fluxo_investimento': [  # ~16 registros
        {
            'periodo': str,  # 'Jan/26', 'Fev/26', '2027', '2028'...
            'capital_giro': decimal,
            'imobilizado': decimal,
            'total_investimentos': decimal,
            'fontes': decimal,
            'saldo_periodo': decimal,
            'saldo_acumulado': decimal
        }
    ],
    
    'fluxo_negocio': [  # ~16 registros
        {
            'periodo': str,
            'receita': decimal,
            'custos_variaveis': decimal,
            'despesas_variaveis': decimal,
            'margem_contribuicao': decimal,
            'custos_fixos': decimal,
            'despesas_fixas': decimal,
            'resultado_operacional': decimal,
            'destinacoes': decimal,
            'resultado_periodo': decimal
        }
    ],
    
    'fluxo_investidor': [  # ~16 registros
        {
            'periodo': str,
            'aporte': decimal,
            'distribuicao': decimal,
            'saldo_periodo': decimal,
            'saldo_acumulado': decimal
        }
    ],
    
    # Seção 8
    'executive_summary': {
        'vpn': str,
        'tir_2_anos': str,
        'tir_3_anos': str,
        'tir_5_anos': str,
        'payback': str,
        'comentarios': str,
        'taxa_desconto': str,
        'horizonte_anos': int
    },
    
    'fixed_costs_summary': {
        'custos_fixos_mensal': float,
        'despesas_fixas_mensal': float,
        'total_gastos_mensal': float
    }
}
```

### **⚠️ NOTA IMPORTANTE SOBRE FLUXOS:**

Os fluxos de caixa são **calculados dinamicamente no JavaScript** da página ModeFin.

Para o relatório, preciso **RECRIAR essa lógica no Python** OU buscar de onde o frontend está pegando esses dados calculados.

**Precisarei investigar:**
1. Como o frontend calcula os 60 meses
2. Se existe API que retorna isso
3. Ou criar a lógica de cálculo no backend do relatório
```

---

## 📄 RELATÓRIO 6: PROJETO & ATIVIDADES

### **Especificações:**
- **Arquivo:** `relatorio_6_projeto_atividades.html`
- **Rota:** `/pev/implantacao/relatorio/06-projeto?plan_id=X`
- **Orientação:** PAISAGEM

### **Estrutura:**

**Página 1:**
- Header: "Projeto e Atividades"
- Cards de info do projeto:
  - Nome, descrição, datas
  - Status, responsável
  - Métricas (total atividades, concluídas, pendentes)

**Página 2+:**
- Tabela COMPLETA de atividades (TODAS):
  - Código | Atividade | Descrição | Responsável | Prazo | Status | Prioridade | Orçamento

**Última Página:**
- Resumo visual:
  - Gráfico de status (cards com %)
  - Timeline se houver datas
  - Observações gerais

### **Dados Necessários:**
```python
{
    'projeto': {
        'nome': str,
        'descricao': str,
        'start_date': str,
        'end_date': str,
        'status': str,
        'responsible': str
    },
    'atividades': [...]  # TODAS as atividades do JSON
}
```

---

## 🗂️ ESTRUTURA DE ARQUIVOS

```
templates/implantacao/relatorios/
├── relatorio_1_capa_resumo.html
├── relatorio_2_alinhamento.html
├── relatorio_3_modelo_mercado.html
├── relatorio_4_estruturas.html
├── relatorio_5_modelagem_financeira.html
└── relatorio_6_projeto_atividades.html
```

---

## 🔗 ROTAS FLASK

```python
# Relatório 1: Capa + Resumo
@pev_bp.route('/implantacao/relatorio/01-capa-resumo')

# Relatório 2: Alinhamento
@pev_bp.route('/implantacao/relatorio/02-alinhamento')

# Relatório 3: Modelo & Mercado
@pev_bp.route('/implantacao/relatorio/03-modelo-mercado')

# Relatório 4: Estruturas
@pev_bp.route('/implantacao/relatorio/04-estruturas')

# Relatório 5: Modelagem Financeira
@pev_bp.route('/implantacao/relatorio/05-financeira')

# Relatório 6: Projeto & Atividades
@pev_bp.route('/implantacao/relatorio/06-projeto')
```

---

## 📐 LAYOUT POR RELATÓRIO

| Relatório | Orientação | Páginas | Layout Principal |
|-----------|------------|---------|------------------|
| 1. Capa + Resumo | Retrato | 2 | Hero + Grid 2x2 |
| 2. Alinhamento | Retrato | 2-3 | Info boxes + Cards + Tabela |
| 3. Modelo & Mercado | Retrato | 1 por segmento | Grid 2x2 + Tabela |
| 4. Estruturas | Retrato | 2 | Grid cards + Tabela resumo |
| 5. ModeFin | Paisagem | 3-5 | 8 seções com tabelas/cards |
| 6. Projeto | Paisagem | 2-3 | Cards info + Tabela atividades |

---

## ✅ PRIORIDADES DE IMPLEMENTAÇÃO

### **Ordem de Execução:**

1. **Relatório 1** (Capa + Resumo) - Base visual, capa melhorada
2. **Relatório 2** (Alinhamento) - Corrigir metas (info box)
3. **Relatório 3** (Modelo & Mercado) - Múltiplos segmentos organizados
4. **Relatório 4** (Estruturas) - Tabela resumo financeiro
5. **Relatório 5** (ModeFin) - **TODAS as 8 seções completas** (mais complexo)
6. **Relatório 6** (Projeto) - Todas as atividades

### **⚠️ ATENÇÃO ESPECIAL: Relatório 5**

O Relatório 5 é o mais complexo pois precisa:
- ✅ Recriar lógica de cálculo dos fluxos de caixa (atualmente em JavaScript)
- ✅ Gerar ~16 registros de fluxo (12 meses + 4 anos consolidados)
- ✅ Mostrar TODAS as 8 seções (nada resumido)
- ✅ Múltiplas páginas paisagem (4-6 páginas)

---

## 🎨 CAPA MELHORADA (Relatório 1)

### **Arte Sugerida:**

```html
<div class="cover-hero">
  <!-- Gradiente de fundo mais rico -->
  <div class="hero-gradient-bg"></div>
  
  <!-- Pattern SVG complexo -->
  <svg class="hero-pattern">
    <!-- Circles em camadas -->
    <circle cx="10%" cy="20%" r="150" fill="#4a90ff" opacity="0.15"/>
    <circle cx="85%" cy="30%" r="200" fill="#8b5cf6" opacity="0.12"/>
    <circle cx="20%" cy="75%" r="180" fill="#34d399" opacity="0.15"/>
    <circle cx="90%" cy="80%" r="140" fill="#fbbf24" opacity="0.18"/>
    
    <!-- Ondas decorativas -->
    <path d="M0,300 Q200,250 400,300 T800,300" stroke="#60a5ff" opacity="0.2"/>
  </svg>
  
  <!-- Conteúdo -->
  <div class="hero-content">
    <img src="logo-empresa" class="hero-logo-large">
    
    <span class="hero-badge-large">Estudo de Viabilidade</span>
    
    <h1>Estudo e Análise de Viabilidade<br>de Implantação de Negócio</h1>
    <h2>{{ plan_name }}</h2>
    
    <!-- Grid 2x2 de meta cards -->
    <div class="hero-meta-grid">
      <div class="meta-card">
        <span class="meta-icon">🏢</span>
        <span class="meta-label">Empresa</span>
        <span class="meta-value">{{ company_name }}</span>
      </div>
      
      <div class="meta-card">
        <span class="meta-icon">👤</span>
        <span class="meta-label">Consultor</span>
        <span class="meta-value">{{ consultant }}</span>
      </div>
      
      <div class="meta-card">
        <span class="meta-icon">📅</span>
        <span class="meta-label">Emitido em</span>
        <span class="meta-value">{{ date }}</span>
      </div>
      
      <div class="meta-card">
        <span class="meta-icon">📊</span>
        <span class="meta-label">Versão</span>
        <span class="meta-value">{{ version }}</span>
      </div>
    </div>
  </div>
  
  <!-- Rodapé discreto -->
  <div class="hero-footer">
    <img src="versus-logo">
    <span>Versus Gestão Corporativa</span>
  </div>
</div>
```

---

## 🔧 BACKEND - ESTRUTURA COMUM

### **Helper para Carregar Dados:**

```python
def _load_common_data(db, plan_id):
    """Dados comuns a todos os relatórios"""
    return {
        'plan': build_plan_context(db, plan_id),
        'projeto': load_alignment_project(db, plan_id),
        'issued_at': datetime.now().strftime('%d/%m/%Y às %H:%M')
    }

def _load_alinhamento_data(db, plan_id):
    """Dados específicos de alinhamento"""
    canvas = load_alignment_canvas(db, plan_id)
    principles = db.list_alignment_principles(plan_id)
    project = load_alignment_project(db, plan_id)
    
    return {
        'visao': canvas.get('vision'),
        'metas': canvas.get('goals') or canvas.get('metas') or [],
        'principios': principles,
        'socios': canvas.get('partners') or [],
        'agenda': project.get('agenda') or []
    }

def _load_modefin_data(db, plan_id):
    """Dados ModeFin completos"""
    products = products_service.fetch_products(plan_id)
    products_totals = products_service.calculate_totals(products)
    
    estruturas = load_structures(db, plan_id)
    investimentos = aggregate_structure_investments(estruturas)
    
    funding_sources = db.list_plan_finance_sources(plan_id)
    
    executive_summary = db.get_executive_summary(plan_id) if hasattr(db, 'get_executive_summary') else None
    
    return {
        'products_totals': products_totals,
        'investimentos_estruturas': investimentos,
        'funding_sources': funding_sources,
        'executive_summary': executive_summary
    }
```

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

### Fase 1: Setup
- [ ] Criar diretório `templates/implantacao/relatorios/`
- [ ] Criar arquivo base de estilos (pode ser reutilizado)

### Fase 2: Relatórios (ordem prioritária)
- [ ] Relatório 1: Capa + Resumo
- [ ] Relatório 2: Alinhamento (CORRIGIR metas)
- [ ] Relatório 5: ModeFin (mais importante - dados financeiros)
- [ ] Relatório 3: Modelo & Mercado
- [ ] Relatório 4: Estruturas
- [ ] Relatório 6: Projeto

### Fase 3: Backend
- [ ] 6 rotas Flask
- [ ] Helpers de carregamento
- [ ] Tratamento de erros

### Fase 4: Teste
- [ ] Testar cada relatório individualmente
- [ ] Testar impressão PDF
- [ ] Validar dados

---

## 🎯 VANTAGENS DA ABORDAGEM MODULAR

✅ **Flexibilidade:** Cada relatório otimizado para seus dados  
✅ **Manutenção:** Mais fácil ajustar um sem afetar outros  
✅ **Performance:** Carrega só os dados necessários  
✅ **Impressão:** Imprimir só o que precisa  
✅ **Qualidade:** Layout específico = resultado melhor  
✅ **Escalabilidade:** Fácil adicionar novos relatórios  

---

## 🚀 EXECUÇÃO

Vou implementar os 6 relatórios na ordem de prioridade, testando cada um antes de avançar.

**Começar pelo Relatório 1 (Capa + Resumo) como base visual.**

---

---

## ✅ DECISÕES APROVADAS PELO USUÁRIO

### **1. Fluxos de Caixa (~16 registros)**

**Nome das Seções:**
- ✅ Fluxo de Caixa do **Investimento** (não "Projeto")
- ✅ Fluxo de Caixa do **Negócio**
- ✅ Fluxo de Caixa do **Investidor**

**Estrutura dos Períodos (~16 linhas):**
```
Mês 1  - Jan/2026
Mês 2  - Fev/2026
...
Mês 12 - Dez/2026
Ano 2  - 2027 (consolidado)
Ano 3  - 2028 (consolidado)
Ano 4  - 2029 (consolidado)
Ano 5  - 2030 (consolidado)
Ano 6  - 2031 (consolidado) [opcional]
```

**Como são gerados:**
- Construídos/calculados na página ModeFin (JavaScript)
- Precisam ser **recriados no backend Python** para o relatório
- Base de dados: produtos, estruturas, investimentos, fontes, destinações

### **2. Relatório 5 - Nível de Detalhe**

✅ **TODAS as 8 seções com tabelas COMPLETAS**
- Não resumir nada
- Mostrar todos os dados cadastrados
- 4-6 páginas paisagem se necessário
- Visual com cards + tabelas

### **3. Relatório 3 - Segmentos**

✅ **Múltiplos segmentos por página**
- Não resumir (mostrar TODOS os dados)
- Organizar visualmente bonito
- Layout compacto mas não poluído
- Cores alternadas entre segmentos
- Separadores sutis

---

## 🚀 EXECUÇÃO APROVADA

**PROMPT REVISADO E APROVADO!**

Ordem de implementação:
1. Relatórios 1, 2, 3, 4, 6 (mais simples)
2. Relatório 5 (mais complexo - precisa calcular fluxos)

**Começar implementação agora!** 🎯

