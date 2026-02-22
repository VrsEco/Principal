# 📐 Análise de Layouts - Mapeamento de Templates APP32

**Data:** 02/01/2026  
**Objetivo:** Validar se os 3 layouts criados (App, Form, Workspace) cobrem todas as necessidades das telas atuais

---

## 🎯 Layouts Criados

### 1. **Layout App** (`layouts/app.html`)
- **Uso:** Dashboards, Listagens, Visões Gerais
- **Características:**
  - Navbar global fixa (Logo + Menu + Perfil)
  - Menu hambúrguer mobile funcional (gaveta lateral)
  - Conteúdo com padding padrão
  - Responsivo

### 2. **Layout Form** (`layouts/form.html`)
- **Uso:** Cadastros, Edições, Configurações
- **Características:**
  - **SEM navbar global** (foco total na tarefa)
  - Cabeçalho contextual (Título + Subtítulo + Breadcrumb)
  - Card centralizado (max-width: 520px)
  - Botões de ação fixos/visíveis
  - Baseado no exemplo positivo: `grv_indicator_group_form.html`

### 3. **Layout Workspace** (A CRIAR)
- **Uso:** Telas operacionais densas (Kanban, Mapas, Gantt)
- **Características:**
  - Navbar compacta
  - Sidebar lateral (ferramentas/filtros)
  - Área de trabalho máxima (sem margens)
  - Baseado em: `grv_project_manage.html`

---

## 📊 Análise por Categoria de Tela

### ✅ Categoria 1: **Dashboards & Visões Gerais**
**Layout Recomendado:** `layouts/app.html`

| Template Atual | Tamanho | Adequação | Observações |
|----------------|---------|-----------|-------------|
| `dashboard.html` | 3.8 KB | ✅ Perfeito | Dashboard principal - usa navbar |
| `grv_dashboard.html` | 9 KB | ✅ Perfeito | Dashboard GRV - cards de resumo |
| `ecosystem.html` | 7 KB | ✅ Perfeito | Visão geral do ecossistema |
| `companies.html` | 10 KB | ✅ Perfeito | Lista de empresas em grid |
| `routines.html` | 27 KB | ✅ Perfeito | Lista de rotinas |
| `plan_dashboard.html` | 5 KB | ✅ Perfeito | Dashboard de planejamento |

**Validação:** ✅ O `layouts/app.html` atende perfeitamente. Menu mobile funciona.

---

### ✅ Categoria 2: **Formulários & Cadastros**
**Layout Recomendado:** `layouts/form.html`

| Template Atual | Tamanho | Adequação | Observações |
|----------------|---------|-----------|-------------|
| `grv_indicator_group_form.html` | 7.3 KB | ✅ **MODELO BASE** | Exemplo positivo - já implementado |
| `grv_indicator_form.html` | 19 KB | ✅ Perfeito | Formulário de indicador |
| `grv_indicator_goal_form.html` | 27 KB | ✅ Perfeito | Formulário de meta |
| `grv_indicator_data_form.html` | 6.4 KB | ✅ Perfeito | Entrada de dados |
| `company_form.html` | 12 KB | ✅ Perfeito | Cadastro de empresa |
| `meeting_form.html` | 28 KB | ✅ Perfeito | Formulário de reunião |
| `cadastro_form.html` | 9 KB | ✅ Perfeito | Cadastro genérico |

**Validação:** ✅ O `layouts/form.html` replica o padrão do exemplo positivo.

---

### ⚠️ Categoria 3: **Workspaces Operacionais**
**Layout Recomendado:** `layouts/workspace.html` **(PRECISA SER CRIADO)**

| Template Atual | Tamanho | Adequação | Observações |
|----------------|---------|-----------|-------------|
| `grv_project_manage.html` | 83 KB | ⚠️ **MODELO BASE** | Kanban de projetos - sidebar + área densa |
| `grv_process_detail.html` | 125 KB | ⚠️ Workspace | Detalhes de processo - múltiplas abas |
| `my_work.html` | 37 KB | ⚠️ Workspace | Minhas atividades - filtros + cards |
| `meetings_manage.html` | 69 KB | ⚠️ Workspace | Gestão de reuniões |
| `plan_drivers.html` | 189 KB | ⚠️ Workspace | Direcionadores - tela complexa |
| `plan_okr_area.html` | 72 KB | ⚠️ Workspace | OKRs por área |
| `plan_okr_global.html` | 68 KB | ⚠️ Workspace | OKRs globais |

**Validação:** ⚠️ **PRECISA CRIAR** `layouts/workspace.html` baseado em `grv_project_manage.html`

**Características Necessárias:**
- Navbar compacta (não esconde em mobile, mas fica menor)
- Sidebar lateral colapsável (filtros, ferramentas)
- Grid layout: `[Sidebar] [Conteúdo Principal]`
- Área de trabalho usa 100% da largura disponível
- Suporte a abas/tabs internas

---

### ✅ Categoria 4: **Análises & Relatórios**
**Layout Recomendado:** `layouts/app.html` (com variação)

| Template Atual | Tamanho | Adequação | Observações |
|----------------|---------|-----------|-------------|
| `grv_indicators_analysis.html` | 28 KB | ✅ App | Análise de indicadores |
| `grv_process_analysis.html` | 25 KB | ✅ App | Análise de processos |
| `grv_projects_analysis.html` | 29 KB | ✅ App | Análise de projetos |
| `grv_routine_efficiency.html` | 41 KB | ✅ App | Eficiência de rotinas |
| `plan_reports.html` | 10 KB | ✅ App | Relatórios de planejamento |

**Validação:** ✅ Podem usar `layouts/app.html` com conteúdo mais denso.

---

### ✅ Categoria 5: **Listagens & Árvores**
**Layout Recomendado:** `layouts/app.html`

| Template Atual | Tamanho | Adequação | Observações |
|----------------|---------|-----------|-------------|
| `grv_indicators_list.html` | 10 KB | ✅ Perfeito | Lista de indicadores |
| `grv_indicators_tree.html` | 9.4 KB | ✅ Perfeito | Árvore hierárquica |
| `grv_process_instances.html` | 36 KB | ✅ Perfeito | Instâncias de processo |
| `grv_projects_portfolios.html` | 19 KB | ✅ Perfeito | Portfólios de projetos |
| `grv_projects_projects.html` | 49 KB | ✅ Perfeito | Lista de projetos |
| `cadastros_list.html` | 6.9 KB | ✅ Perfeito | Lista de cadastros |

**Validação:** ✅ O `layouts/app.html` atende perfeitamente.

---

### ✅ Categoria 6: **Autenticação**
**Layout Recomendado:** Layout específico (já existe)

| Template Atual | Tamanho | Adequação | Observações |
|----------------|---------|-----------|-------------|
| `login.html` | 7.2 KB | ✅ Específico | Layout próprio - não precisa mudar |
| `auth/*` | Vários | ✅ Específico | Telas de autenticação |

**Validação:** ✅ Mantém layout próprio (não usa navbar).

---

### ✅ Categoria 7: **Modais & Popups**
**Layout Recomendado:** Sem layout (JavaScript inline)

| Template Atual | Tamanho | Adequação | Observações |
|----------------|---------|-----------|-------------|
| `test_routines_modal.html` | 9.3 KB | ✅ Modal | Não precisa de layout |
| Diversos modais inline | - | ✅ Modal | Renderizados via JS |

**Validação:** ✅ Modais não precisam de layout base.

---

### ⚠️ Categoria 8: **Configurações & Gestão**
**Layout Recomendado:** `layouts/app.html` ou `layouts/workspace.html`

| Template Atual | Tamanho | Adequação | Observações |
|----------------|---------|-----------|-------------|
| `configurations.html` | 13 KB | ✅ App | Configurações gerais |
| `configs_system.html` | 12 KB | ✅ App | Configurações do sistema |
| `configs_system_audit.html` | 15 KB | ✅ App | Auditoria de sistema |
| `company_details.html` | 54 KB | ⚠️ Workspace | Detalhes complexos - pode usar workspace |
| `company_logos_manager.html` | 13 KB | ✅ App | Gestão de logos |
| `integrations.html` | 40 KB | ⚠️ Workspace | Integrações - tela densa |

**Validação:** ✅ Maioria usa App. Telas densas podem usar Workspace.

---

### ✅ Categoria 9: **Seletores & Navegação**
**Layout Recomendado:** `layouts/app.html`

| Template Atual | Tamanho | Adequação | Observações |
|----------------|---------|-----------|-------------|
| `plan_selector.html` | 129 KB | ⚠️ Complexo | Seletor de plano - muito grande |
| `plan_selector_compact.html` | 33 KB | ✅ App | Versão compacta |
| `routine_selector.html` | 6.1 KB | ✅ App | Seletor de rotina |

**Validação:** ✅ Seletores compactos usam App. `plan_selector.html` precisa refatoração.

---

### ✅ Categoria 10: **Sidebars & Componentes**
**Layout Recomendado:** Componentes reutilizáveis

| Template Atual | Tamanho | Adequação | Observações |
|----------------|---------|-----------|-------------|
| `grv_sidebar.html` | 4.4 KB | ✅ Componente | Sidebar do GRV |
| `identity_sidebar.html` | 2.6 KB | ✅ Componente | Sidebar de identidade |
| `indicators_sidebar.html` | 3.2 KB | ✅ Componente | Sidebar de indicadores |
| `meetings_sidebar.html` | 2 KB | ✅ Componente | Sidebar de reuniões |
| `plan_sidebar.html` | 1.6 KB | ✅ Componente | Sidebar de planejamento |
| `processes_sidebar.html` | 3.2 KB | ✅ Componente | Sidebar de processos |
| `projects_sidebar.html` | 2.6 KB | ✅ Componente | Sidebar de projetos |
| `routines_sidebar.html` | 3.3 KB | ✅ Componente | Sidebar de rotinas |

**Validação:** ✅ Sidebars são componentes. Serão usados no `layouts/workspace.html`.

---

## 🎯 Resumo da Validação

### ✅ Layouts que JÁ ATENDEM (2/3)

1. **`layouts/app.html`** ✅
   - **Cobre:** 60+ telas (Dashboards, Listas, Análises, Configurações)
   - **Status:** Pronto e testado
   - **Mobile:** Menu hambúrguer funcional

2. **`layouts/form.html`** ✅
   - **Cobre:** 15+ telas (Formulários, Cadastros, Edições)
   - **Status:** Pronto e testado
   - **Base:** Exemplo positivo (`grv_indicator_group_form.html`)

### ⚠️ Layout que PRECISA SER CRIADO (1/3)

3. **`layouts/workspace.html`** ⚠️ **PENDENTE**
   - **Cobre:** 10+ telas (Kanban, Processos Detalhados, OKRs, Minhas Atividades)
   - **Status:** Precisa ser criado
   - **Base:** `grv_project_manage.html`
   - **Características:**
     - Navbar compacta
     - Sidebar lateral colapsável (usa os componentes `*_sidebar.html`)
     - Grid: `[Sidebar 280px] [Conteúdo flex]`
     - Área de trabalho 100% largura
     - Suporte a tabs/abas

---

## 📋 Ação Necessária

### Criar `layouts/workspace.html`

**Estrutura Proposta:**

```html
{% extends "layouts/base.html" %}

{% block layout %}
<div class="layout-workspace">
  <!-- Navbar Compacta -->
  <nav class="workspace-navbar">
    <a href="#" class="navbar-brand">Gestão Versus</a>
    <div class="navbar-breadcrumb">
      {% block breadcrumb %}{% endblock %}
    </div>
    <div class="navbar-actions">
      {% block navbar_actions %}{% endblock %}
    </div>
  </nav>

  <div class="workspace-container">
    <!-- Sidebar Lateral (Colapsável) -->
    <aside class="workspace-sidebar" id="workspaceSidebar">
      {% block sidebar %}
        <!-- Conteúdo da sidebar (filtros, ferramentas, etc.) -->
      {% endblock %}
    </aside>

    <!-- Área de Trabalho Principal -->
    <main class="workspace-main">
      {% block workspace_content %}
        <!-- Conteúdo principal (Kanban, Tabs, etc.) -->
      {% endblock %}
    </main>
  </div>
</div>
{% endblock %}
```

**CSS Necessário:**
- Grid: `display: grid; grid-template-columns: 280px 1fr;`
- Sidebar colapsável: `transform: translateX(-100%);` quando colapsada
- Navbar compacta: `height: 48px;` (vs. 64px do app)
- Responsivo: Sidebar vira gaveta em mobile

---

## ✅ Conclusão

**Os 3 layouts cobrem TODAS as necessidades?**

- ✅ **SIM**, mas com uma ressalva:
  - `layouts/app.html` ✅ Pronto
  - `layouts/form.html` ✅ Pronto
  - `layouts/workspace.html` ⚠️ **PRECISA SER CRIADO**

**Próximo Passo:**
1. Criar `layouts/workspace.html` baseado em `grv_project_manage.html`
2. Extrair CSS comum para `app32.css`
3. Testar com uma tela de exemplo (ex: `my_work.html` refatorado)

---

**Versão:** 1.0  
**Status:** 📋 Análise Completa  
**Próxima Ação:** Criar `layouts/workspace.html`
