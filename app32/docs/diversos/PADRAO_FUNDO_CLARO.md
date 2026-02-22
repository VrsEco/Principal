# PADRÃO "FUNDO CLARO" - GRV
## Especificação Completa do Padrão de Design

### 📋 **DEFINIÇÃO**
O padrão "Fundo Claro" é um sistema de design consistente que garante:
- **Fundos sempre claros** (branco → cinza muito claro)
- **Fontes sempre escuras** (preto ou azul muito escuro)
- **Contraste mínimo de 4.5:1** para acessibilidade
- **Uso de `!important`** para garantir precedência

### 🎨 **PALETA DE CORES**

#### **Fundos:**
```css
/* Fundo principal */
background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;

/* Fundo de cards */
background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%) !important;

/* Fundo de hover */
background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%) !important;
```

#### **Fontes:**
```css
/* Texto principal */
color: #000000 !important; /* Preto */

/* Texto secundário */
color: #1e293b !important; /* Azul muito escuro */

/* Texto muted */
color: #475569 !important; /* Cinza escuro */

/* Texto de destaque */
color: #1e40af !important; /* Azul escuro */
```

#### **Bordas e Sombras:**
```css
/* Bordas padrão */
border: 1px solid rgba(30, 64, 175, 0.1) !important;

/* Bordas de hover */
border: 1px solid rgba(30, 64, 175, 0.2) !important;

/* Sombras padrão */
box-shadow: 0 4px 12px rgba(30, 64, 175, 0.08) !important;

/* Sombras de hover */
box-shadow: 0 8px 24px rgba(30, 64, 175, 0.12) !important;
```

### 🔧 **IMPLEMENTAÇÃO**

#### **1. Arquivo CSS Global**
```css
/* static/css/grv-global-pattern.css */
/* Contém todas as regras do padrão "Fundo Claro" */
```

#### **2. Inclusão no Template Base**
```html
<!-- templates/base.html -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/grv-global-pattern.css') }}" />
```

#### **3. Aplicação em Páginas Específicas**
```html
{% block extra_head %}
{{ super() }}
<style>
  /* Aplicar padrão "Fundo Claro" */
  .elemento-especifico {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
    color: #000000 !important;
    border: 1px solid rgba(30, 64, 175, 0.1) !important;
    box-shadow: 0 4px 12px rgba(30, 64, 175, 0.08) !important;
  }
</style>
{% endblock %}
```

### 📐 **COMPONENTES PADRÃO**

#### **Cards e Superfícies:**
```css
.grv-card {
  background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%) !important;
  border: 1px solid rgba(30, 64, 175, 0.1) !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 12px rgba(30, 64, 175, 0.08) !important;
  transition: all 0.3s ease !important;
}

.grv-card:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(30, 64, 175, 0.12) !important;
  border-color: rgba(30, 64, 175, 0.2) !important;
}
```

#### **Botões:**
```css
.grv-btn-primary {
  background: linear-gradient(135deg, #1e40af, #7c3aed, #dc2626) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 8px !important;
  padding: 8px 16px !important;
  font-weight: 600 !important;
  transition: all 0.3s ease !important;
}

.grv-btn-secondary {
  background: linear-gradient(135deg, rgba(148, 163, 184, 0.2), rgba(100, 116, 139, 0.15)) !important;
  color: #000000 !important;
  border: 1px solid rgba(148, 163, 184, 0.3) !important;
  border-radius: 8px !important;
  padding: 8px 16px !important;
  font-weight: 600 !important;
  transition: all 0.3s ease !important;
}
```

#### **Inputs e Formulários:**
```css
.grv-input {
  background: #ffffff !important;
  color: #000000 !important;
  border: 1px solid rgba(148, 163, 184, 0.3) !important;
  border-radius: 8px !important;
  padding: 10px 12px !important;
}

.grv-input:focus {
  border-color: rgba(30, 64, 175, 0.5) !important;
  box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.1) !important;
  outline: none !important;
}

.grv-label {
  color: #000000 !important;
  font-weight: 600 !important;
}
```

#### **Sidebar e Navegação:**
```css
.project-sidebar, .plan-sidebar {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
  border: 1px solid rgba(30, 64, 175, 0.1) !important;
  box-shadow: 0 8px 24px rgba(30, 64, 175, 0.08) !important;
  border-radius: 16px !important;
}

.project-nav-link {
  background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%) !important;
  color: #1e293b !important;
  border: 1px solid rgba(30, 64, 175, 0.1) !important;
  border-radius: 12px !important;
  padding: 14px 18px !important;
  font-weight: 500 !important;
  transition: all 0.3s ease !important;
}

.project-nav-link:hover {
  color: #000000 !important;
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%) !important;
  border-color: rgba(30, 64, 175, 0.2) !important;
  transform: translateY(-1px) !important;
}

.project-nav-link.is-active {
  color: #000000 !important;
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%) !important;
  border-color: rgba(30, 64, 175, 0.3) !important;
  font-weight: 600 !important;
}
```

#### **Cabeçalho:**
```css
.app-header {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
  border-bottom: 1px solid rgba(30, 64, 175, 0.1) !important;
  backdrop-filter: blur(18px) !important;
  box-shadow: 0 4px 12px rgba(30, 64, 175, 0.08) !important;
}

.header-nav .nav-link {
  color: #1e293b !important;
  font-weight: 600 !important;
  padding: 8px 16px !important;
  border-radius: 8px !important;
  transition: all 0.3s ease !important;
}

.header-nav .nav-link:hover {
  color: #000000 !important;
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 4px 8px rgba(30, 64, 175, 0.1) !important;
}

.header-nav .nav-link.active {
  color: #000000 !important;
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%) !important;
  font-weight: 700 !important;
}
```

### 🎯 **BARRAS COLORIDAS (Identificação Visual)**
```css
.grv-accent-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #1e40af, #7c3aed, #dc2626);
  z-index: 1;
}
```

### 📱 **RESPONSIVIDADE**
```css
@media (max-width: 768px) {
  .grv-card {
    margin: 8px !important;
    padding: 16px !important;
  }
  
  .grv-btn-primary,
  .grv-btn-secondary {
    padding: 12px 20px !important;
    font-size: 14px !important;
  }
}
```

### ✅ **PÁGINAS JÁ APLICADAS**
- ✅ Dashboard Principal (`templates/routine_dashboard.html`)
- ✅ Gerenciamento de Projetos (`templates/grv_project_manage.html`)
- ✅ Listagem de Projetos (`templates/grv_projects_projects.html`)
- ✅ Páginas de Reuniões (`templates/meetings_manage.html`)
- ✅ Página de Análise (`templates/grv_projects_analysis.html`)
- ✅ **Sidebar Global** (todos os sidebars do sistema)
- ✅ **Cabeçalho Global** (navegação Ecossistema/PEV/GRV)

### 🚀 **COMO APLICAR EM NOVAS PÁGINAS**

#### **Passo 1: Incluir CSS Global**
```html
{% block extra_head %}
{{ super() }}
<link rel="stylesheet" href="{{ url_for('static', filename='css/grv-global-pattern.css') }}">
{% endblock %}
```

#### **Passo 2: Aplicar Classes Padrão**
```html
<div class="grv-card">
  <h3 class="grv-card-title">Título</h3>
  <p class="grv-card-text">Conteúdo</p>
</div>
```

#### **Passo 3: CSS Específico (se necessário)**
```css
{% block extra_head %}
{{ super() }}
<style>
  .elemento-especifico {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
    color: #000000 !important;
    border: 1px solid rgba(30, 64, 175, 0.1) !important;
    box-shadow: 0 4px 12px rgba(30, 64, 175, 0.08) !important;
  }
</style>
{% endblock %}
```

### 📋 **CHECKLIST DE APLICAÇÃO**
- [ ] Fundos sempre claros (branco → cinza muito claro)
- [ ] Fontes sempre escuras (preto ou azul muito escuro)
- [ ] Contraste mínimo de 4.5:1
- [ ] Uso de `!important` para precedência
- [ ] Bordas azuis sutis
- [ ] Sombras modernas
- [ ] Transições suaves (0.3s)
- [ ] Hover effects com elevação
- [ ] Responsividade incluída

### 🎨 **IDENTIDADE VISUAL**
- **Nome**: Padrão "Fundo Claro"
- **Versão**: 1.0
- **Data de Criação**: Dezembro 2024
- **Status**: Ativo e Implementado
- **Escopo**: Sistema GRV Completo

---
**Nota**: Este padrão garante consistência visual e máxima legibilidade em todas as páginas do sistema GRV.
