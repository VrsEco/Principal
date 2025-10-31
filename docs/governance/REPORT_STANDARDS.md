# 📊 Padrões de Relatórios - GestaoVersus

## 🎯 Objetivo

Este documento estabelece os padrões para criação, design e implementação de relatórios no sistema GestaoVersus. Seguindo estes padrões, você pode criar relatórios profissionais, rápidos e consistentes.

## 📚 Índice

1. [Filosofia](#filosofia)
2. [Arquitetura de Relatórios](#arquitetura-de-relatórios)
3. [Padrões de Design](#padrões-de-design)
4. [Estrutura de Arquivos](#estrutura-de-arquivos)
5. [Componentes Reutilizáveis](#componentes-reutilizáveis)
6. [Configuração de Página](#configuração-de-página)
7. [Fluxo de Criação](#fluxo-de-criação)
8. [Exemplos Práticos](#exemplos-práticos)
9. [Checklist de Qualidade](#checklist-de-qualidade)

---

## 📖 Filosofia

### Princípios Fundamentais

1. **Reutilização**: Componentes devem ser reutilizáveis entre diferentes relatórios
2. **Consistência**: Design visual deve ser uniforme em todo o sistema
3. **Manutenibilidade**: Fácil de atualizar e manter
4. **Performance**: Leve e rápido de gerar
5. **Acessibilidade**: Legível em tela e impressão
6. **Profissionalismo**: Visual corporativo e executivo

### Regras de Ouro

```text
✅ DRY: Don't Repeat Yourself - Reutilize componentes
✅ Separação de responsabilidades: CSS, HTML, dados
✅ Mobile-first: Responsivo por padrão
✅ Print-ready: Otimizado para impressão
✅ Data-driven: Dados vêm do backend, não hardcoded
```

---

## 🏗️ Arquitetura de Relatórios

### Sistema de 3 Camadas

```
┌─────────────────────────────────────────────────────────┐
│                  CAMADA 1: CONFIGURAÇÃO                  │
│           (Margens, Papel, Cabeçalho, Rodapé)           │
│                    report_models                         │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                  CAMADA 2: PADRÃO/TEMPLATE               │
│              (Seções, Estrutura, Componentes)           │
│                   report_patterns                        │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                 CAMADA 3: CONTEÚDO                       │
│               (Dados específicos do relatório)           │
│                    Template HTML                         │
└─────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

```python
# 1. Backend coleta dados
def relatorio_final():
    plan_id = _resolve_plan_id()
    db = get_db()
    
    # Buscar dados
    plan = build_plan_context(db, plan_id)
    canvas_data = load_alignment_canvas(db, plan_id)
    estruturas = load_structures(db, plan_id)
    
    # Montar payload
    report_payload = build_final_report_payload(
        plan, canvas_data, estruturas, ...
    )
    
    # Renderizar template
    return render_template(
        "reports/relatorio_final.html",
        **report_payload
    )
```

```jinja2
{# 2. Template usa componentes #}
{% extends "reports/base_report.html" %}
{% from "reports/components.html" import section_header, story_card %}

{% block content %}
  {{ section_header("01", "Alinhamento Estratégico") }}
  {{ story_card(title="Visão", content=alinhamento.visao) }}
{% endblock %}
```

---

## 🎨 Padrões de Design

### Paleta de Cores

```css
/* Cores Primárias */
--color-primary: #3b82f6;           /* Azul principal */
--color-primary-dark: #1d4ed8;      /* Azul escuro */
--color-primary-light: #93c5fd;     /* Azul claro */

/* Cores de Fundo */
--color-background: #ffffff;        /* Branco */
--color-background-alt: #f8fafc;    /* Cinza muito claro */
--color-background-muted: #e9edf5;  /* Cinza claro */

/* Cores de Texto */
--color-text-primary: #0f172a;      /* Quase preto */
--color-text-secondary: #1e293b;    /* Cinza escuro */
--color-text-muted: #64748b;        /* Cinza médio */

/* Cores de Status */
--color-success: #22c55e;           /* Verde */
--color-success-dark: #166534;      /* Verde escuro */
--color-warning: #f59e0b;           /* Laranja */
--color-danger: #ef4444;            /* Vermelho */

/* Cores de Destaque */
--color-highlight-bg: rgba(59, 130, 246, 0.12);
--color-highlight-border: rgba(59, 130, 246, 0.35);
```

### Tipografia

```css
/* Família de Fontes */
font-family: "Segoe UI", "Inter", Arial, sans-serif;

/* Escala Tipográfica */
--font-size-xs: 11px;     /* Labels, notas de tabela */
--font-size-sm: 13px;     /* Texto de tabela, descrições */
--font-size-base: 15px;   /* Texto corpo */
--font-size-lg: 18px;     /* Subtítulos */
--font-size-xl: 22px;     /* Títulos de card */
--font-size-2xl: 30px;    /* Títulos de seção */
--font-size-3xl: 46px;    /* Título de capa */

/* Pesos */
--font-weight-normal: 400;
--font-weight-medium: 500;
--font-weight-semibold: 600;
--font-weight-bold: 700;

/* Line Height */
--line-height-tight: 1.4;
--line-height-normal: 1.6;
--line-height-relaxed: 1.8;
```

### Espaçamento

```css
/* Sistema de 8px */
--spacing-xs: 6px;
--spacing-sm: 12px;
--spacing-md: 18px;
--spacing-lg: 24px;
--spacing-xl: 32px;
--spacing-2xl: 48px;

/* Margens de Página */
--page-margin-top: 5mm;      /* Retrato */
--page-margin-right: 5mm;
--page-margin-bottom: 5mm;
--page-margin-left: 5mm;

--page-margin-top-landscape: 5mm;   /* Paisagem */
--page-margin-right-landscape: 5mm;
```

> **Largura padrão**: o contêiner raiz (`.model7-report`) deve ter `width: 794px` (equivalente a 210 mm) para que a visualização em tela reflita a página A4 retrato. Use `max-width` com o mesmo valor e centralize com `margin: 0 auto`.

```css
@page portrait {
  size: A4 portrait;
  margin: 5mm;
}

@page landscapePage {
  size: A4 landscape;
  margin: 5mm;
}
```

### Componentes Base

#### 1. Página (Page)

```css
.page {
  position: relative;
  background: #ffffff;
  border-radius: 0;
  border: none;
  box-shadow: none;
  margin: 0 auto 32px;
  width: 100%;
  page-break-after: always;
}

.page.portrait {
  padding: var(--page-margin-top) var(--page-margin-right)
           var(--page-margin-bottom) var(--page-margin-left);
  min-height: calc(297mm - 10mm);
  page: portrait;
}

.page.landscape {
  padding: var(--page-margin-top-landscape) var(--page-margin-right-landscape);
  min-height: calc(210mm - 10mm);
  page: landscapePage;
}

@media screen {
  .page::before {
    content: "";
    position: absolute;
    inset: 0;
    border: 1px solid rgba(15, 23, 42, 0.25);
    pointer-events: none;
  }

  .page::after {
    content: "";
    position: absolute;
    top: var(--page-margin-top);
    right: var(--page-margin-right);
    bottom: var(--page-margin-bottom);
    left: var(--page-margin-left);
    border: 1px dashed rgba(37, 99, 235, 0.45);
    pointer-events: none;
  }
}
```

> **Governança**: toda página deve apresentar, no modo HTML, exatamente o mesmo enquadramento da impressão/PDF. Os contornos (linha externa) e as margens tracejadas são exibidos apenas em tela para facilitar ajustes, mas não aparecem no resultado impresso. Qualquer alteração nas variáveis de margem ou na largura/altura mínimas deve ser feita pensando em ambos os contextos.

#### 2. Cabeçalho de Seção

```css
.section-header span {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #3b82f6;
}

.section-header h3 {
  font-size: 30px;
  font-weight: 700;
  margin-top: 6px;
  color: #0f172a;
}
```

#### 3. Card/Bloco de História

```css
.story-block {
  background: rgba(148, 163, 184, 0.12);
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  padding: 22px 26px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
```

#### 4. Tabela

```css
table.model7-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 16px;
  font-size: 13px;
  box-shadow: 0 18px 30px rgba(15, 23, 42, 0.05);
  page-break-inside: avoid;
}

table.model7-table thead tr {
  background: rgba(59, 130, 246, 0.18);
}

table.model7-table th {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 11px;
  color: #1d4ed8;
  padding: 12px 14px;
  text-align: left;
}
```

#### 5. Card de Resultado

```css
.result-card {
  background: rgba(15, 23, 42, 0.03);
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-card .label {
  font-size: 12px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #475569;
}

.result-card .value {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}
```

### Responsividade

```css
/* Grid Responsivo */
.model7-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 22px;
}

/* Duas Colunas */
.two-column {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}
```

### Impressão

```css
@media print {
  body {
    background: #ffffff !important;
    padding: 0;
  }

  .page {
    border-radius: 0;
    border: none;
    box-shadow: none;
    margin: 0;
    padding: 20mm 20mm 24mm;
  }

  /* Preservar cores de fundo */
  .cover-page,
  .footer-page {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
}
```

---

## 📁 Estrutura de Arquivos

### Organização Recomendada

```
app31/
├── static/
│   └── css/
│       ├── reports.css              # CSS global de relatórios
│       ├── reports-print.css        # CSS específico para impressão
│       └── reports-components.css   # CSS de componentes
│
├── templates/
│   ├── reports/
│   │   ├── base_report.html        # Template base
│   │   ├── components.html         # Macros reutilizáveis
│   │   └── layouts/
│   │       ├── cover.html          # Layout de capa
│   │       ├── section.html        # Layout de seção
│   │       └── footer.html         # Layout de rodapé
│   │
│   └── [modulo]/
│       └── relatorio_[nome].html   # Relatórios específicos
│
└── modules/
    ├── report_models.py            # Configurações de página
    ├── report_patterns.py          # Padrões de relatório
    └── [modulo]/
        └── report_builder.py       # Builder de dados
```

### Convenções de Nomenclatura

```python
# Arquivos Python
report_models.py          # Configurações de página
report_patterns.py        # Padrões/templates
[entidade]_report_builder.py  # Ex: pev_report_builder.py

# Templates HTML
base_report.html          # Template base
components.html           # Componentes
relatorio_[nome].html     # Ex: relatorio_final.html

# CSS
reports.css               # Estilos globais
reports-[tema].css        # Ex: reports-executive.css
```

---

## 🧩 Componentes Reutilizáveis

### Macros Jinja2 (components.html)

#### 1. Cabeçalho de Seção

```jinja2
{% macro section_header(number, title, subtitle="") %}
<div class="section-header">
  <span>{{ number }}</span>
  <h3>{{ title }}</h3>
  {% if subtitle %}
    <p class="section-subtitle">{{ subtitle }}</p>
  {% endif %}
</div>
{% endmacro %}
```

**Uso:**
```jinja2
{{ section_header("01", "Alinhamento Estratégico") }}
{{ section_header("02", "Modelo & Mercado", "Análise de segmentos") }}
```

#### 2. Card de História/Bloco

```jinja2
{% macro story_card(title, content, type="default") %}
<div class="story-block story-block-{{ type }}">
  {% if title %}
    <h4>{{ title }}</h4>
  {% endif %}
  
  {% if content is string %}
    <p>{{ content }}</p>
  {% elif content is mapping %}
    <div class="story-columns">
      {% for key, value in content.items() %}
        <div>
          <h5>{{ key }}</h5>
          <p>{{ value }}</p>
        </div>
      {% endfor %}
    </div>
  {% elif content is iterable %}
    <ul class="story-list">
      {% for item in content %}
        <li>{{ item }}</li>
      {% endfor %}
    </ul>
  {% endif %}
</div>
{% endmacro %}
```

**Uso:**
```jinja2
{{ story_card("Visão", "Consolidamos a visão...") }}
{{ story_card("Metas", alinhamento.metas) }}
```

#### 3. Tabela Padrão

```jinja2
{% macro data_table(headers, rows, caption="") %}
<table class="model7-table">
  {% if caption %}
    <caption>{{ caption }}</caption>
  {% endif %}
  <thead>
    <tr>
      {% for header in headers %}
        <th>{{ header }}</th>
      {% endfor %}
    </tr>
  </thead>
  <tbody>
    {% for row in rows %}
      <tr>
        {% for cell in row %}
          <td>{{ cell }}</td>
        {% endfor %}
      </tr>
    {% endfor %}
  </tbody>
</table>
{% endmacro %}
```

**Uso:**
```jinja2
{{ data_table(
    ["Nome", "Valor", "Status"],
    [
      ["Item 1", "R$ 100,00", "Ativo"],
      ["Item 2", "R$ 200,00", "Inativo"]
    ],
    "Tabela de Investimentos"
) }}
```

#### 4. Card de Resultado/Métrica

```jinja2
{% macro result_card(label, value, note="", status="neutral") %}
<div class="result-card result-card-{{ status }}">
  <span class="label">{{ label }}</span>
  <span class="value">{{ value }}</span>
  {% if note %}
    <span class="note">{{ note }}</span>
  {% endif %}
</div>
{% endmacro %}
```

**Uso:**
```jinja2
{{ result_card("Faturamento Total", "R$ 1.500.000,00", "Soma dos períodos", "positive") }}
{{ result_card("Margem de Contribuição", "32%", "", "neutral") }}
```

#### 5. Box de Destaque

```jinja2
{% macro highlight_box(content, type="success") %}
<div class="highlight-box highlight-box-{{ type }}">
  {{ content }}
</div>
{% endmacro %}
```

**Uso:**
```jinja2
{% call highlight_box("success") %}
  <strong>Resumo:</strong>
  <ul>
    <li>Total suportado: R$ 500.000,00</li>
    <li>Gargalo: R$ 300.000,00 (Comercial)</li>
  </ul>
{% endcall %}
```

#### 6. Grid Responsivo

```jinja2
{% macro responsive_grid(items, min_width="260px") %}
<div class="model7-grid" style="grid-template-columns: repeat(auto-fit, minmax({{ min_width }}, 1fr));">
  {% for item in items %}
    <div class="model7-card">
      {{ item }}
    </div>
  {% endfor %}
</div>
{% endmacro %}
```

#### 7. Formatadores de Dados

```jinja2
{% macro format_currency(value) -%}
  {%- if value is not none -%}
    {%- set numeric = value|float -%}
    {%- set sign = '-' if numeric < 0 else '' -%}
    {%- set absolute = numeric|abs -%}
    {%- set formatted = '{:,.2f}'.format(absolute).replace(',', '_').replace('.', ',').replace('_', '.') -%}
    {{ sign }}R$ {{ formatted }}
  {%- else -%}
    R$ 0,00
  {%- endif -%}
{%- endmacro %}

{% macro format_percent(value) -%}
  {%- if value is not none -%}
    {%- set numeric = value|float -%}
    {%- set text = ('%.2f' % numeric).rstrip('0').rstrip('.') -%}
    {{ text }}%
  {%- else -%}
    0%
  {%- endif -%}
{%- endmacro %}

{% macro format_date(value, format='%d/%m/%Y') -%}
  {%- if value -%}
    {{ value.strftime(format) if value is datetime else value }}
  {%- else -%}
    -
  {%- endif -%}
{%- endmacro %}
```

---

## ⚙️ Configuração de Página

### Estrutura do Banco (report_models)

```sql
CREATE TABLE report_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                -- "Model 7 - Relatórios Executivos"
    description TEXT,
    paper_size TEXT DEFAULT 'A4',      -- A4, Carta, Ofício
    orientation TEXT DEFAULT 'Retrato', -- Retrato, Paisagem
    margin_top INTEGER DEFAULT 20,     -- mm
    margin_right INTEGER DEFAULT 15,
    margin_bottom INTEGER DEFAULT 15,
    margin_left INTEGER DEFAULT 20,
    header_height INTEGER DEFAULT 25,  -- mm
    header_rows INTEGER DEFAULT 2,
    header_columns INTEGER DEFAULT 3,
    header_content TEXT,               -- Markdown/HTML
    footer_height INTEGER DEFAULT 12,
    footer_rows INTEGER DEFAULT 1,
    footer_columns INTEGER DEFAULT 2,
    footer_content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'system'
);
```

### Modelos Pré-Definidos

#### Model 7 - Relatórios Executivos

```python
{
    'name': 'Model 7 - Relatórios Executivos',
    'description': 'Padrão para relatórios executivos com design moderno',
    'paper_size': 'A4',
    'orientation': 'Retrato',
    'margin_top': 25,
    'margin_right': 20,
    'margin_bottom': 20,
    'margin_left': 25,
    'header_height': 30,
    'header_rows': 2,
    'header_columns': 3,
    'header_content': '''
## {{ company.name }}
**{{ report.title }}**
Data: {{ date }} | Sistema GestaoVersus
    ''',
    'footer_height': 15,
    'footer_rows': 1,
    'footer_columns': 2,
    'footer_content': '© {{ year }} {{ company.name }} | Página {{ page }} de {{ pages }}'
}
```

#### Model 8 - Relatórios Técnicos

```python
{
    'name': 'Model 8 - Relatórios Técnicos',
    'description': 'Padrão para relatórios técnicos detalhados',
    'paper_size': 'A4',
    'orientation': 'Retrato',
    'margin_top': 20,
    'margin_right': 20,
    'margin_bottom': 20,
    'margin_left': 20,
    'header_height': 25,
    'header_rows': 3,
    'header_columns': 2,
    'header_content': '''
### {{ company.name }}
**{{ report.title }}**
Versão: {{ version }} | {{ date }}
    ''',
    'footer_height': 15,
    'footer_rows': 1,
    'footer_columns': 3,
    'footer_content': 'Confidencial | Página {{ page }} | {{ report.code }}'
}
```

### Variáveis Disponíveis

```jinja2
{# Empresa #}
{{ company.name }}           # Nome da empresa
{{ company.logo_url }}       # URL do logo

{# Relatório #}
{{ report.title }}           # Título do relatório
{{ report.code }}            # Código do relatório
{{ report.version }}         # Versão

{# Datas #}
{{ date }}                   # Data atual (dd/mm/yyyy)
{{ datetime }}               # Data e hora
{{ year }}                   # Ano atual

{# Paginação #}
{{ page }}                   # Página atual
{{ pages }}                  # Total de páginas

{# Usuário #}
{{ user.name }}              # Nome do usuário
{{ user.email }}             # Email do usuário
```

---

## 🚀 Fluxo de Criação

### Passo a Passo para Criar um Novo Relatório

#### 1. Definir Objetivo e Seções

```markdown
**Objetivo:** Relatório Final de Implantação PEV
**Público:** Executivos e gestores
**Seções:**
1. Alinhamento Estratégico
2. Modelo & Mercado
3. Estruturas de Execução
4. Modelagem Financeira
```

#### 2. Escolher/Criar Configuração de Página

```python
# Usar Model 7 existente ou criar novo
from modules.report_models import ReportModelsManager

manager = ReportModelsManager()
model = manager.get_model(7)  # Model 7 - Executivo
```

#### 3. Criar Builder de Dados (Backend)

```python
# modules/pev/report_builder.py

def build_final_report_payload(
    plan: Dict,
    canvas_data: Dict,
    estruturas: List,
    financeiro: Dict
) -> Dict:
    """
    Monta o payload completo do relatório final.
    
    Args:
        plan: Dados do plano
        canvas_data: Dados do canvas de alinhamento
        estruturas: Lista de estruturas
        financeiro: Modelagem financeira
        
    Returns:
        Dict com todos os dados formatados para o template
    """
    return {
        "plan": {
            "id": plan.get("id"),
            "name": plan.get("plan_name"),
            "company_name": plan.get("company_name"),
            "consultant": plan.get("consultant"),
            "last_update": datetime.now().strftime("%d/%m/%Y"),
        },
        "alinhamento": {
            "visao": canvas_data.get("visao_compartilhada"),
            "metas": canvas_data.get("metas_financeiras"),
            "socios": canvas_data.get("socios", []),
            "principios": canvas_data.get("principios", []),
        },
        "estruturas": estruturas,
        "financeiro": financeiro,
        "issued_at": datetime.now().strftime("%d/%m/%Y às %H:%M"),
    }
```

#### 4. Criar Rota (Backend)

```python
# modules/pev/__init__.py

@pev_bp.route('/implantacao/entrega/relatorio-final')
def implantacao_relatorio_final():
    """Relatório final de implantação."""
    plan_id = _resolve_plan_id()
    db = get_db()
    
    # Buscar dados
    plan = build_plan_context(db, plan_id)
    canvas_data = load_alignment_canvas(db, plan_id)
    estruturas = load_structures(db, plan_id)
    financeiro = load_financial_model(db, plan_id)
    
    # Montar payload
    payload = build_final_report_payload(
        plan, canvas_data, estruturas, financeiro
    )
    
    # Renderizar
    return render_template(
        "reports/pev/relatorio_final.html",
        **payload
    )
```

#### 5. Criar Template HTML

```jinja2
{# templates/reports/pev/relatorio_final.html #}

{% extends "reports/base_report.html" %}
{% from "reports/components.html" import section_header, story_card, data_table, result_card %}

{% block report_title %}Relatório Final de Implantação{% endblock %}
{% block report_subtitle %}{{ plan.name }}{% endblock %}

{% block cover %}
  {# Capa customizada #}
  <div class="cover-meta-grid">
    <div class="cover-meta-card">
      <span>Empresa</span>
      <strong>{{ plan.company_name }}</strong>
    </div>
    <div class="cover-meta-card">
      <span>Consultor</span>
      <strong>{{ plan.consultant }}</strong>
    </div>
  </div>
{% endblock %}

{% block content %}
  {# Seção 1: Alinhamento #}
  <section class="page portrait">
    {{ section_header("01", "Alinhamento Estratégico") }}
    <div class="section-body">
      {{ story_card("Visão Compartilhada", alinhamento.visao) }}
      {{ story_card("Metas Financeiras", alinhamento.metas) }}
    </div>
  </section>

  {# Seção 2: Modelo & Mercado #}
  <section class="page portrait">
    {{ section_header("02", "Modelo & Mercado") }}
    <div class="section-body">
      {# Conteúdo... #}
    </div>
  </section>
{% endblock %}

{% block footer %}
  <span>Versus Gestão Corporativa - Emitido em: {{ issued_at }}</span>
  <span>Consultor: {{ plan.consultant }}</span>
{% endblock %}
```

#### 6. Testar e Refinar

```bash
# 1. Rodar servidor
python app_pev.py

# 2. Acessar relatório
http://127.0.0.1:5003/pev/implantacao/entrega/relatorio-final?plan_id=6

# 3. Testar impressão
Ctrl+P ou Cmd+P

# 4. Validar responsividade
Redimensionar janela
```

---

## 💡 Exemplos Práticos

### Exemplo 1: Relatório Simples

```python
# Backend
@bp.route('/relatorio-simples')
def relatorio_simples():
    data = {
        "title": "Relatório de Vendas",
        "vendas": [
            {"produto": "A", "valor": 1000},
            {"produto": "B", "valor": 2000},
        ]
    }
    return render_template("relatorio_simples.html", **data)
```

```jinja2
{# Template #}
{% extends "reports/base_report.html" %}
{% from "reports/components.html" import section_header, data_table %}

{% block content %}
  <section class="page portrait">
    {{ section_header("01", title) }}
    {{ data_table(
        ["Produto", "Valor"],
        [[v.produto, v.valor] for v in vendas]
    ) }}
  </section>
{% endblock %}
```

### Exemplo 2: Relatório com Métricas

```jinja2
{% from "reports/components.html" import result_card %}

<div class="result-summary-grid">
  {{ result_card("Total de Vendas", "R$ 150.000,00", "Mês atual", "positive") }}
  {{ result_card("Meta", "R$ 200.000,00", "75% atingido", "neutral") }}
  {{ result_card("Variação", "-5%", "vs. mês anterior", "negative") }}
</div>
```

### Exemplo 3: Relatório com Dados Dinâmicos

```python
# Backend - Formatação
def format_estruturas_for_report(estruturas):
    """Formata estruturas para exibição no relatório."""
    result = []
    for est in estruturas:
        result.append({
            "area": est.get("area"),
            "capacidade": format_currency(est.get("capacidade")),
            "resumo": [
                {
                    "escopo": bloco.get("nome"),
                    "pontos": bloco.get("itens", [])
                }
                for bloco in est.get("blocos", [])
            ]
        })
    return result
```

```jinja2
{# Template #}
{% for area in estruturas %}
  <div class="model7-card">
    <h4>{{ area.area }}</h4>
    <p>Capacidade: {{ area.capacidade }}</p>
    <ul>
      {% for bloco in area.resumo %}
        <li>
          <strong>{{ bloco.escopo }}:</strong>
          <ul>
            {% for ponto in bloco.pontos %}
              <li>{{ ponto }}</li>
            {% endfor %}
          </ul>
        </li>
      {% endfor %}
    </ul>
  </div>
{% endfor %}
```

---

## ✅ Checklist de Qualidade

### Antes de Publicar um Relatório

#### Design

- [ ] Usa CSS de `reports.css` (não inline)
- [ ] Componentes reutilizáveis estão em `components.html`
- [ ] Paleta de cores segue o padrão
- [ ] Tipografia segue a escala definida
- [ ] Espaçamento usa variáveis CSS
- [ ] Responsivo (grid auto-fit)
- [ ] Otimizado para impressão (@media print)

#### Código

- [ ] Extends `base_report.html`
- [ ] Usa macros de `components.html`
- [ ] Dados vêm do backend (não hardcoded)
- [ ] Formatadores (currency, percent, date) corretos
- [ ] Sem lógica de negócio no template
- [ ] Tratamento de dados vazios/nulos
- [ ] Comentários em seções complexas

#### Performance

- [ ] CSS externo (não inline)
- [ ] Imagens otimizadas
- [ ] Evita queries N+1 (usa eager loading)
- [ ] Paginação em listas longas
- [ ] Lazy loading para imagens (se aplicável)

#### Conteúdo

- [ ] Título descritivo
- [ ] Seções numeradas e organizadas
- [ ] Labels claros e objetivos
- [ ] Unidades de medida explícitas (R$, %, etc)
- [ ] Datas formatadas corretamente
- [ ] Sem dados de exemplo/mockup

#### Acessibilidade

- [ ] Contraste adequado (mínimo 4.5:1)
- [ ] Texto legível (tamanho mínimo 13px)
- [ ] Estrutura semântica (h1, h2, h3...)
- [ ] Tabelas com <thead> e <caption>
- [ ] Alt text em imagens (se houver)

#### Testes

- [ ] Testado em Chrome/Edge
- [ ] Testado em modo impressão
- [ ] Testado com dados reais
- [ ] Testado com dados vazios
- [ ] Testado responsividade (mobile/tablet/desktop)
- [ ] Validado com múltiplos plan_ids

---

## 🔧 Troubleshooting

### Problemas Comuns

#### 1. Relatório não carrega dados

**Problema:** Template vazio ou com erros

**Solução:**
```python
# Debugar no backend
print(f"DEBUG payload: {payload}")

# Verificar no template
{{ data | pprint }}  {# Mostrar estrutura #}
```

#### 2. CSS não aplicado

**Problema:** CSS inline sobrescrevendo

**Solução:**
```css
/* Usar !important apenas quando necessário */
.page {
  padding: 48mm 58px !important;
}

/* Ou aumentar especificidade */
.model7-report .page.portrait {
  padding: 48mm 58px;
}
```

#### 3. Quebra de página incorreta

**Problema:** Conteúdo cortado na impressão

**Solução:**
```css
/* Evitar quebra dentro do elemento */
.model7-card {
  page-break-inside: avoid;
}

/* Forçar quebra antes */
.page {
  page-break-after: always;
}
```

#### 4. Dados não formatados

**Problema:** Números sem máscara

**Solução:**
```jinja2
{# Usar formatadores #}
{{ format_currency(value) }}  {# R$ 1.234,56 #}
{{ format_percent(value) }}   {# 12.5% #}
{{ format_date(value) }}      {# 31/10/2025 #}
```

---

## 📚 Referências

### Documentos Relacionados

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Arquitetura geral do sistema
- [CODING_STANDARDS.md](./CODING_STANDARDS.md) - Padrões de código Python
- [FRONTEND_STANDARDS.md](./FRONTEND_STANDARDS.md) - Padrões de frontend
- [DATABASE_STANDARDS.md](./DATABASE_STANDARDS.md) - Padrões de banco

### Recursos Externos

- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [CSS Grid Guide](https://css-tricks.com/snippets/css/complete-guide-grid/)
- [Print CSS Best Practices](https://www.smashingmagazine.com/2018/05/print-stylesheets-in-2018/)
- [Web Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

## 📝 Changelog

### v1.0 - 30/10/2025
- ✅ Versão inicial do documento
- ✅ Definição de arquitetura de 3 camadas
- ✅ Padrões de design (cores, tipografia, componentes)
- ✅ Componentes reutilizáveis (macros Jinja2)
- ✅ Fluxo de criação completo
- ✅ Exemplos práticos
- ✅ Checklist de qualidade

---

**Versão:** 1.0  
**Última atualização:** 30/10/2025  
**Responsável:** Sistema GestaoVersus  
**Status:** ✅ Aprovado

