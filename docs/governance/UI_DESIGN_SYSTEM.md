# 🎨 Sistema de Design - GestaoVersus

**Versão:** 1.0  
**Data:** 30/10/2025  
**Status:** ✅ OBRIGATÓRIO para novas páginas

---

## 🎯 OBJETIVO

Estabelecer padrões visuais consistentes para criar interfaces profissionais, manuteníveis e com experiência do usuário uniforme.

---

## 📐 PÁGINA DE REFERÊNCIA

**Template Padrão:** GRV Process Map  
**URL Exemplo:** `/grv/company/{id}/process/map`  
**Arquivo:** `templates/grv_process_map.html`

### **Características:**
- Layout com sidebar + conteúdo
- Sistema de tabs
- Cards brancos (surface-card)
- Botões padronizados
- Variáveis CSS
- Responsivo

---

## 🏗️ ESTRUTURA DE LAYOUT PADRÃO

### **1. Layout Base**

```html
<div class="project-layout plan-layout" data-sidebar-toggle>
  
  <!-- Sidebar -->
  {% include 'sidebar_name.html' %}
  
  <!-- Conteúdo Principal -->
  <section class="project-content plan-content">
    
    <!-- Tabs (opcional) -->
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <button class="button" data-tab="tab1">Tab 1</button>
      <button class="button button-ghost" data-tab="tab2">Tab 2</button>
    </div>
    
    <!-- Cards de Conteúdo -->
    <div data-panel="tab1" class="surface-card" style="padding:20px;">
      <h3>Título</h3>
      <!-- Conteúdo -->
    </div>
    
  </section>
</div>
```

**CSS Obrigatório:**
```css
.app-main {
  padding: 40px 20px 64px !important;
}

.project-layout.plan-layout {
  max-width: 100% !important;
  width: 100% !important;
  grid-template-columns: 280px 1fr !important;
  gap: 16px !important;
}
```

---

## 🎨 COMPONENTES PADRÃO

### **1. BOTÕES**

#### **Botão Primário:**
```html
<button class="button button-primary">Ação Principal</button>
```

**Estilos:**
- Background: `#3b82f6`
- Hover: `#2563eb`
- Padding: `10px 20px`
- Border-radius: `8px`
- Font-weight: `500`

#### **Botão Secundário/Ghost:**
```html
<button class="button button-ghost">Ação Secundária</button>
```

**Estilos:**
- Background: Transparente
- Border: `1px solid rgba(148, 163, 184, 0.3)`
- Hover: Background leve

#### **Botão de Ação (Pequeno):**
```html
<button class="action-btn edit">✏️</button>
<button class="action-btn delete">🗑️</button>
```

---

### **2. CARDS**

#### **Surface Card (Padrão):**
```html
<div class="surface-card" style="padding:20px;">
  <h3>Título do Card</h3>
  <p>Conteúdo...</p>
</div>
```

**Estilos (atualizado):**
- Background: `#ffffff`
- Border: `1px solid #e5e7eb`
- Border-radius: `12px`
- Box-shadow: `0 1px 3px rgba(0,0,0,0.1)`
- Padding: `20-32px`
- Seções podem usar gradiente cinza claro no fundo externo

#### **Card com Gradiente (Destaque):**
```html
<div style="background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%); 
            border-radius: 12px; padding: 20px; color: white;">
  <h3>Título</h3>
  <div>Conteúdo...</div>
</div>
```

**Quando usar:**
- Resumos/Totalizadores
- Métricas importantes
- Call-to-action

---

### **3. TABELAS**

#### **Tabela Padrão:**
```html
<table class="data-table">
  <thead>
    <tr>
      <th>Coluna 1</th>
      <th>Coluna 2</th>
      <th style="width: 100px; text-align: center;">Ações</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Valor 1</td>
      <td>Valor 2</td>
      <td style="text-align: center;">
        <button class="action-btn edit">✏️</button>
        <button class="action-btn delete">🗑️</button>
      </td>
    </tr>
  </tbody>
</table>
```

**Estilos (atualizado):**
- Borda externa `1px #e5e7eb` e linhas de grade verticais/horizontais
- Títulos (thead/th): fundo `#e5e7eb`
- Subtítulos: linhas com fundo `#f1f5f9`
- Dados em zebra: ímpares `#ffffff`, pares `#f8fafc`
- Hover row: `#f8fafc`
- Padding cells: `12px`
- Sempre usar container com `overflow-x: auto` quando houver muitas colunas

#### **Tabela com Scroll:**
```html
<div style="overflow-x: auto; max-height: 600px; overflow-y: auto;">
  <table class="data-table">
    <thead style="position: sticky; top: 0; background: #f8fafc; z-index: 10;">
      <!-- Cabeçalhos -->
    </thead>
    <tbody>
      <!-- Linhas -->
    </tbody>
  </table>
</div>
```

---

### **4. MODAIS**

#### **Modal Padrão (Padrão Obrigatório):**

**Ver:** `docs/governance/MODAL_STANDARDS.md`

```html
<div id="meuModal" class="modal">
  <div class="modal-content">
    <div class="modal-header">
      <h3>Título</h3>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    
    <div class="form-group">
      <label>Campo</label>
      <input type="text">
    </div>
    
    <div class="modal-actions">
      <button class="btn-secondary">Cancelar</button>
      <button class="btn-primary">Salvar</button>
    </div>
  </div>
</div>
```

**Regras:**
- ✅ Z-index: **25000** (SEMPRE)
- ✅ Remover classe ao abrir
- ✅ Forçar estilos com `cssText`
- ✅ Background: `rgba(0,0,0,0.6)`

---

### **5. FORMULÁRIOS**

#### **Campo de Formulário:**
```html
<div class="form-group">
  <label>Nome do Campo *</label>
  <input type="text" placeholder="Digite aqui...">
  <small>Texto de ajuda opcional</small>
</div>
```

**Estilos:**
- Label: `font-weight: 500, color: #334155`
- Input: `padding: 10px 12px, border: 1px solid #cbd5e1`
- Focus: `border-color: #3b82f6, box-shadow: 0 0 0 3px rgba(59,130,246,0.1)`
- Small: `color: #64748b, font-size: 12px`

#### **Select:**
```html
<select class="form-control">
  <option value="">Selecione...</option>
  <option value="1">Opção 1</option>
</select>
```

#### **Textarea:**
```html
<textarea rows="3" class="form-control"></textarea>
```

---

### **6. INFO BOXES**

#### **Info (Azul):**
```html
<div class="info-box info">
  ℹ️ <strong>Título:</strong> Texto informativo.
</div>
```

#### **Success (Verde):**
```html
<div class="info-box success">
  ✅ <strong>Sucesso:</strong> Operação concluída.
</div>
```

#### **Warning (Amarelo):**
```html
<div class="info-box warning">
  ⚠️ <strong>Atenção:</strong> Verificar antes de continuar.
</div>
```

#### **Error (Vermelho):**
```html
<div class="info-box error">
  ❌ <strong>Erro:</strong> Algo deu errado.
</div>
```

**Estilos:**
```css
.info-box {
  padding: 12px 16px;
  border-radius: 8px;
  border-left: 3px solid;
  font-size: 13px;
  line-height: 1.5;
}

.info-box.info {
  background: rgba(59, 130, 246, 0.1);
  color: #1e40af;
  border-color: #3b82f6;
}

.info-box.success {
  background: rgba(34, 197, 94, 0.1);
  color: #166534;
  border-color: #22c55e;
}

.info-box.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #92400e;
  border-color: #f59e0b;
}

.info-box.error {
  background: rgba(239, 68, 68, 0.1);
  color: #991b1b;
  border-color: #ef4444;
}
```

---

### **7. BADGES/TAGS**

```html
<span class="badge badge-primary">Status</span>
<span class="badge badge-success">Ativo</span>
<span class="badge badge-warning">Pendente</span>
```

**Estilos:**
```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.badge-primary { background: #dbeafe; color: #1e40af; }
.badge-success { background: #dcfce7; color: #166534; }
.badge-warning { background: #fef3c7; color: #92400e; }
.badge-danger { background: #fee2e2; color: #991b1b; }
```

---

## 🎨 CORES PADRÃO

### **Paleta Principal:**
```css
:root {
  /* Primárias */
  --color-primary: #3b82f6;
  --color-secondary: #8b5cf6;
  --color-accent: #3af1ae; /* Verde GRV */
  
  /* Semânticas */
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #3b82f6;
  
  /* Neutras */
  --color-text: #0f172a;
  --color-muted: #64748b;
  --color-border: #e2e8f0;
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
}
```

### **Gradientes Padrão:**
```css
/* Verde */
background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);

/* Azul */
background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);

/* Roxo */
background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);

/* Laranja */
background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
```

---

## 📏 ESPAÇAMENTOS PADRÃO

```css
/* Gap entre elementos */
--gap-xs: 4px;
--gap-sm: 8px;
--gap-md: 12px;
--gap-lg: 16px;
--gap-xl: 24px;
--gap-2xl: 32px;

/* Padding de cards */
--card-padding-sm: 16px;
--card-padding-md: 20px;
--card-padding-lg: 32px;

/* Border radius */
--radius-sm: 6px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-xl: 16px;
```

---

## 🔤 TIPOGRAFIA PADRÃO

```css
/* Tamanhos de fonte */
--text-xs: 11px;
--text-sm: 12px;
--text-base: 14px;
--text-lg: 16px;
--text-xl: 18px;
--text-2xl: 20px;
--text-3xl: 24px;
--text-4xl: 32px;

/* Pesos */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;

/* Família */
font-family: "Inter", "Segoe UI", Arial, sans-serif;
```

---

## 📚 CATÁLOGO DE COMPONENTES (Proposta)

Sugiro documentar estes componentes:

### **1. Pop-ups/Modais:**
- ✅ Modal de CRUD (formulário)
- ✅ Modal de confirmação (sim/não)
- ✅ Modal de visualização (read-only)
- ✅ Modal de configuração (parâmetros)

### **2. Formulários:**
- Input text
- Select dropdown
- Textarea
- Date picker
- Number input
- Checkbox/Radio
- File upload

### **3. Tabelas:**
- Tabela simples
- Tabela com ações (edit/delete)
- Tabela com scroll (horizontal/vertical)
- Tabela com cabeçalho fixo
- Tabela com rodapé (totais)
- Tabela responsiva

### **4. Cards:**
- Card padrão (branco)
- Card com gradiente (destaque)
- Card de métrica (número grande)
- Card de resumo (vários valores)
- Card colapsável

### **5. Navegação:**
- Tabs horizontais
- Sidebar de navegação
- Breadcrumbs
- Paginação

### **6. Feedback:**
- Info boxes (info, success, warning, error)
- Toasts/Notifications
- Loading states
- Empty states
- Error states

### **7. Ações:**
- Botões (primary, secondary, ghost, danger)
- Dropdown de ações
- Botões de edição inline
- Botões flutuantes (FAB)

---

## 📋 PROCESSO DE ADIÇÃO DE PADRÕES

### **Quando você encontrar um padrão que gosta:**

**PASSO 1: Me envie**
- URL da página
- Screenshot (opcional)
- Descrição: "Gostei do estilo dos botões/cards/etc"

**PASSO 2: Eu analiso**
- Extraio CSS e HTML
- Documento o componente
- Adiciono no catálogo

**PASSO 3: Aplico**
- Crio template reutilizável
- Adiciono na governança
- Atualizo páginas existentes (se quiser)

---

## 🎯 CATEGORIAS DE PADRÕES

Vou documentar padrões nestas categorias:

### **A) Layout & Estrutura**
- Grid systems
- Sidebar patterns
- Header/Footer
- Spacing systems

### **B) Componentes de Input**
- Forms
- Modals
- Dropdowns
- Date pickers

### **C) Componentes de Output**
- Tables
- Cards
- Charts/Graphs
- Lists

### **D) Navegação**
- Tabs
- Breadcrumbs
- Pagination
- Sidebars

### **E) Feedback & Estados**
- Alerts
- Toasts
- Loading
- Empty states
- Errors

### **F) Cores & Tipografia**
- Color palettes
- Gradients
- Font sizes
- Font weights

---

## ✅ PRÓXIMOS PASSOS

### **AGORA:**

**1. Aplicar padrão GRV ao ModeFin:**
- Layout: .project-layout
- Cards: .surface-card
- Botões: .button classes
- Espaçamento: 40px/20px

**2. Criar arquivo:**
`docs/governance/UI_COMPONENTS.md` com catálogo

**3. Extrair componentes:**
Criar arquivos de exemplo reutilizáveis

---

## 🚀 VOCÊ DECIDE

**Opção A - Aplicar Padrão Agora:**
- Adapto ModeFin para usar layout GRV
- Surface cards brancos
- Botões padronizados
- **Tempo:** 30-45 min

**Opção B - Documentar Primeiro:**
- Crio catálogo completo de componentes
- Você revisa e aprova
- Depois aplicamos
- **Tempo:** 1-2h documentação + aplicação

**Opção C - Híbrido:**
- Aplico padrão básico no ModeFin
- Vamos documentando à medida que você encontra padrões que gosta
- **Tempo:** Incremental

---

## 💡 MINHA RECOMENDAÇÃO

**OPÇÃO C (Híbrido)**

**Porque:**
1. ✅ Você já tem ModeFin funcionando
2. ✅ Podemos melhorar incrementalmente
3. ✅ Você define prioridades
4. ✅ Documentamos o que realmente usa

**Como:**
- Aplico padrão básico GRV no ModeFin (30 min)
- Você me manda outros exemplos que gosta
- Vou documentando e criando catálogo
- Governança cresce organicamente

---

**O que você prefere: A, B ou C?**

Ou me diga especificamente o que quer ajustar primeiro no ModeFin! 🎨
