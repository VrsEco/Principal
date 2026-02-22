# 📋 Sistema de Atividades com Kanban - Projetos GRV

## 🎯 Visão Geral

Sistema completo de gerenciamento de atividades de projetos com interface Kanban, permitindo visualizar e organizar o fluxo de trabalho de cada projeto.

---

## ✨ Funcionalidades Implementadas

### 1. **Botão "Gerenciar" nos Cards de Projeto** ✅

**Localização:** Card de cada projeto em `/grv/company/<id>/projects/projects`

**Visual:**
```
┌─────────────────────────────────────────┐
│ Projeto Teste                           │
│ [GRV - Portfolio Teste] [Em andamento]  │
├─────────────────────────────────────────┤
│ ...informações do projeto...            │
├─────────────────────────────────────────┤
│ [📋 Gerenciar] [Editar] [Excluir]      │ ← NOVO!
└─────────────────────────────────────────┘
```

**Link:** `/grv/company/{company_id}/projects/{project_id}/manage`

---

### 2. **Página de Gerenciamento com Kanban** ✅

**URL:** `/grv/company/<company_id>/projects/<project_id>/manage`

**Estrutura:**

```
┌─────────────────────────────────────────────────────────┐
│ CABEÇALHO DO PROJETO (Gradiente azul/roxo)             │
│ Título do Projeto                                       │
│ Código: AA.J.12 | Responsável: João | Portfólio: ...  │
└─────────────────────────────────────────────────────────┘

[← Voltar]                      [➕ Nova Atividade]

┌───────────┬───────────┬───────────┬───────────┬───────────┬───────────┐
│ Caixa de  │ Aguardando│ Executando│ Pendências│ Suspensos │ Concluídos│
│ Entrada   │           │           │           │           │           │
│    (0)    │    (2)    │    (3)    │    (1)    │    (0)    │    (5)    │
├───────────┼───────────┼───────────┼───────────┼───────────┼───────────┤
│┌─────────┐│┌─────────┐│┌─────────┐│┌─────────┐│           │┌─────────┐│
││AA.J.12.01││AA.J.12.02││AA.J.12.04││AA.J.12.07││  Nenhuma  ││AA.J.12.03││
││─────────││─────────││─────────││─────────││ atividade ││─────────││
││Definir  ││Mapear   ││Executar ││Revisar  ││    aqui   ││Planejar ││
││escopo   ││processos││testes   ││docs     ││           ││reunião  ││
││         ││         ││         ││         ││           ││         ││
││Resp: Ana││Resp: José│Prazo:15/││Orç:5k   ││           ││✓ Concl. ││
││Prazo:30/││Prazo:30/││Orç: 10k ││         ││           ││01/10/25 ││
│└─────────┘│└─────────┘│└─────────┘│└─────────┘│           │└─────────┘│
│           │           │           │           │           │           │
│ [Arraste] │ [Arraste] │ [Arraste] │ [Arraste] │           │ [Arraste] │
└───────────┴───────────┴───────────┴───────────┴───────────┴───────────┘
```

---

### 3. **6 Colunas do Kanban** ✅

| Coluna | Slug | Cor | Descrição |
|--------|------|-----|-----------|
| **Caixa de Entrada** | `inbox` | Cinza | Novas atividades cadastradas |
| **Aguardando** | `waiting` | Amarelo | Aguardando dependências |
| **Executando** | `executing` | Azul | Em execução ativa |
| **Pendências** | `pending` | Laranja | Com bloqueios/pendências |
| **Suspensos** | `suspended` | Vermelho | Temporariamente pausados |
| **Concluídos** | `completed` | Verde | Finalizados |

**Comportamento:**
- ✅ Atividades novas vão automaticamente para "Caixa de Entrada"
- ✅ Drag and drop entre colunas
- ✅ Atualização em tempo real
- ✅ Contador de atividades por coluna

---

### 4. **Modal de Cadastro/Edição de Atividades** ✅

**Campos do Formulário:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| **O quê?** | Text | ✅ Sim | Descrição da atividade |
| **Quem?** | Text | ❌ Não | Responsável pela execução |
| **Quando?** | Date | ❌ Não | Prazo da atividade |
| **Como?** | Textarea | ❌ Não | Método/Processo de execução |
| **Orçamento** | Number | ❌ Não | Valor em R$ |
| **Observações** | Textarea | ❌ Não | Informações adicionais |

**Ações:**
- [Cancelar] [Salvar Atividade]

---

### 5. **Geração Automática de Código** ✅

**Formato:** `{PROJECT_CODE}.{SEQUENCE:02d}`

**Exemplos:**
- Projeto `AA.J.12` tem atividades:
  - `AA.J.12.01`
  - `AA.J.12.02`
  - `AA.J.12.03`
  - ...
  - `AA.J.12.99`

**Função Backend:**
```python
def _generate_activity_code(cursor, company_id: int, project_id: int) -> tuple:
    # Busca código do projeto (ex: AA.J.12)
    # Analisa atividades existentes
    # Encontra maior sequência (ex: 05)
    # Incrementa e formata com 2 dígitos (ex: 06)
    # Retorna: ('AA.J.12.06', 6)
```

**Características:**
- ✅ Sempre 2 dígitos (01-99)
- ✅ Sequencial automático
- ✅ Imutável após criação
- ✅ Hierárquico: Projeto → Atividade

---

### 6. **Drag and Drop no Kanban** ✅

**Funcionalidade:**
- ✅ Arrastar card de uma coluna para outra
- ✅ Efeito visual durante arrasto
- ✅ Destaque da coluna ao passar por cima
- ✅ Atualização automática no servidor
- ✅ Rollback automático em caso de erro

**Implementação:**
```javascript
// 1. Usuário arrasta card
card.addEventListener('dragstart', () => {
  draggedCard = card;
  originColumn = card.closest('[data-kanban-column]');
  card.classList.add('dragging');
});

// 2. Solta em nova coluna
column.addEventListener('drop', async (event) => {
  const targetStage = column.dataset.stage;
  const activityId = draggedCard.dataset.activityId;
  
  // Move visualmente
  dropzone.appendChild(draggedCard);
  
  // Atualiza no servidor
  await fetch(`/api/.../activities/${activityId}/stage`, {
    method: 'PATCH',
    body: JSON.stringify({ stage: targetStage })
  });
});
```

**Comportamentos Especiais:**
- Quando movida para "Concluídos":
  - `status` → `'completed'`
  - `completion_date` → data atual
- Demais colunas:
  - `status` → slug da coluna

---

## 🔌 APIs Implementadas

### GET - Listar Atividades
```
GET /api/companies/{company_id}/projects/{project_id}/activities
```

**Response:**
```json
{
  "success": true,
  "activities": [
    {
      "id": 1,
      "code": "AA.J.12.01",
      "what": "Definir escopo",
      "who": "João Silva",
      "when": "2025-12-31",
      "how": "Reunião com stakeholders",
      "amount": "5000",
      "observations": "Prioritário",
      "stage": "executing",
      "status": "executing",
      "completion_date": null
    }
  ]
}
```

### POST - Criar Atividade
```
POST /api/companies/{company_id}/projects/{project_id}/activities
Content-Type: application/json

{
  "what": "Definir escopo",
  "who": "João Silva",
  "when": "2025-12-31",
  "how": "Reunião",
  "amount": 5000,
  "observations": "Urgente"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Atividade criada com sucesso.",
  "activity": {
    "id": 2,
    "code": "AA.J.12.02",
    "what": "Definir escopo",
    "stage": "inbox",
    "status": "pending",
    ...
  }
}
```

### PUT - Atualizar Atividade
```
PUT /api/companies/{company_id}/projects/{project_id}/activities/{activity_id}
Content-Type: application/json

{
  "what": "Definir escopo (atualizado)",
  "who": "Maria Santos",
  ...
}
```

### DELETE - Excluir Atividade
```
DELETE /api/companies/{company_id}/projects/{project_id}/activities/{activity_id}
```

### PATCH - Mover no Kanban
```
PATCH /api/companies/{company_id}/projects/{project_id}/activities/{activity_id}/stage
Content-Type: application/json

{
  "stage": "executing"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Atividade movida com sucesso.",
  "stage": "executing"
}
```

---

## 💾 Estrutura de Dados

### Armazenamento

Atividades são armazenadas como JSON no campo `activities` da tabela `company_projects`:

```json
[
  {
    "id": 1,
    "code": "AA.J.12.01",
    "what": "Definir escopo do projeto",
    "who": "João Silva",
    "when": "2025-12-31",
    "how": "Reunião com stakeholders",
    "amount": "5000",
    "observations": "Prioritário",
    "stage": "executing",
    "status": "executing",
    "completion_date": null
  },
  {
    "id": 2,
    "code": "AA.J.12.02",
    "what": "Mapear processos atuais",
    "who": "Maria Santos",
    "when": "2025-11-15",
    "how": "Entrevistas e documentação",
    "amount": "8000",
    "observations": null,
    "stage": "waiting",
    "status": "waiting",
    "completion_date": null
  }
]
```

---

## 🎨 Cards de Atividade

### Informações Exibidas:

```
┌─────────────────────────────────┐
│ AA.J.12.01      [Editar] [Excluir]│
├─────────────────────────────────┤
│ Definir escopo do projeto        │
├─────────────────────────────────┤
│ Responsável: João Silva          │
│ Prazo: 31/12/2025               │
│ Orçamento: R$ 5.000,00          │
└─────────────────────────────────┘
```

**Interações:**
- ✅ **Arrastar** - Move entre colunas
- ✅ **Editar** - Abre modal de edição
- ✅ **Excluir** - Remove a atividade (com confirmação)

---

## 🔄 Fluxo de Trabalho

### Criar Nova Atividade:

1. **Usuário clica** em "➕ Nova Atividade"
2. **Modal abre** com formulário vazio
3. **Usuário preenche:**
   - O quê? (obrigatório)
   - Quem? Quando? Como? Orçamento? Observações?
4. **Clica em "Salvar Atividade"**
5. **Sistema:**
   - Gera código automático (ex: `AA.J.12.05`)
   - Define `stage = 'inbox'`
   - Define `status = 'pending'`
   - Salva no JSON de atividades
6. **Card aparece** na coluna "Caixa de Entrada"

### Mover Atividade:

1. **Usuário arrasta** card da "Caixa de Entrada"
2. **Solta** na coluna "Executando"
3. **Sistema:**
   - Move visualmente o card
   - Chama API PATCH para atualizar `stage`
   - Atualiza `status` da atividade
   - Mostra notificação de sucesso
4. **Card permanece** na nova coluna
5. **Se erro:**
   - Card volta para coluna original
   - Mostra mensagem de erro

### Editar Atividade:

1. **Usuário clica** em "Editar" no card
2. **Modal abre** com dados preenchidos
3. **Usuário modifica** campos
4. **Clica em "Salvar Atividade"**
5. **Sistema:**
   - Atualiza dados da atividade
   - Mantém código e stage
   - Atualiza timestamp
6. **Card atualiza** com novos dados

### Excluir Atividade:

1. **Usuário clica** em "Excluir" no card
2. **Confirmação:** "Confirmar exclusão da atividade 'X'?"
3. **Se confirmar:**
   - Remove do array de atividades
   - Atualiza banco de dados
   - Remove card do Kanban
   - Mostra notificação

---

## 📊 Cálculos Dinâmicos no Card do Projeto

Os campos dinâmicos do card de projeto são calculados das atividades:

### Status do Projeto:
```javascript
if (todas as atividades concluídas) {
  status = 'Concluído';
} else if (alguma atividade concluída) {
  status = 'Em andamento';
} else if (tem atividades) {
  status = 'Iniciado';
} else {
  status = 'Planejado';
}
```

### Orçamento Total:
```javascript
orçamento_total = soma(atividade.amount) para todas as atividades
```

### Prazo Previsto:
```javascript
prazo_previsto = maior(atividade.when) entre todas as atividades
```

### Atividades Atrasadas:
```javascript
atrasadas = atividades com status in ['delayed', 'overdue', 'late', 'atrasado']
```

---

## 🎨 Estilo Visual

### Cores das Colunas:

| Coluna | Cor | Hex |
|--------|-----|-----|
| Caixa de Entrada | Cinza | `#94a3b8` |
| Aguardando | Amarelo | `#fbbf24` |
| Executando | Azul | `#3b82f6` |
| Pendências | Laranja | `#f59e0b` |
| Suspensos | Vermelho | `#ef4444` |
| Concluídos | Verde | `#10b981` |

### Efeitos Visuais:

**Card Normal:**
- Border: `1px solid rgba(15, 23, 42, 0.08)`
- Shadow: `0 6px 16px rgba(15, 23, 42, 0.06)`

**Card Hover:**
- Shadow: `0 12px 28px rgba(15, 23, 42, 0.12)`
- Border: `rgba(37, 99, 235, 0.35)`

**Card Arrastando:**
- Opacity: `0.75`
- Transform: `scale(0.98)`
- Shadow: `0 14px 32px rgba(15, 23, 42, 0.18)`
- Cursor: `grabbing`

**Coluna Drop Target:**
- Border: `#2563eb`
- Box Shadow: `0 0 0 2px rgba(37, 99, 235, 0.18)`

---

## 🧪 Casos de Teste

### Teste 1: Criar Primeira Atividade
```
1. Acesse: /grv/company/5/projects/26/manage
2. Clique "➕ Nova Atividade"
3. Preencha: "Definir escopo inicial"
4. Salve

Resultado Esperado:
✅ Card aparece na "Caixa de Entrada"
✅ Código: AA.J.26.01
✅ Stage: inbox
✅ Status: pending
```

### Teste 2: Criar Segunda Atividade
```
1. Clique "➕ Nova Atividade" novamente
2. Preencha: "Mapear processos"
3. Salve

Resultado Esperado:
✅ Card aparece na "Caixa de Entrada"
✅ Código: AA.J.26.02 (sequencial)
```

### Teste 3: Mover Atividade
```
1. Arraste card "AA.J.26.01" da "Caixa de Entrada"
2. Solte em "Executando"

Resultado Esperado:
✅ Card move visualmente
✅ Contador atualiza: Inbox (1) → (0), Executando (0) → (1)
✅ Notificação: "Atividade movida para Executando"
✅ Ao recarregar, atividade permanece em "Executando"
```

### Teste 4: Completar Atividade
```
1. Arraste card para "Concluídos"

Resultado Esperado:
✅ Status → 'completed'
✅ completion_date → data atual
✅ Card na coluna verde
```

### Teste 5: Editar Atividade
```
1. Clique "Editar" em um card
2. Modifique campos
3. Salve

Resultado Esperado:
✅ Dados atualizados no card
✅ Código mantido (não muda)
✅ Stage mantida (não volta para inbox)
```

### Teste 6: Excluir Atividade
```
1. Clique "Excluir" em um card
2. Confirme

Resultado Esperado:
✅ Card removido do Kanban
✅ Contador atualizado
✅ Notificação de sucesso
```

---

## 📁 Arquivos Criados/Modificados

### Novos Arquivos:
1. ✅ `templates/grv_project_manage.html` - Página Kanban completa

### Arquivos Modificados:
1. ✅ `templates/grv_projects_projects.html`
   - Botão "📋 Gerenciar" adicionado

2. ✅ `modules/grv/__init__.py`
   - Rota `grv_project_manage()` criada

3. ✅ `app_pev.py`
   - Função `_generate_activity_code()`
   - API GET/POST `/api/companies/<id>/projects/<id>/activities`
   - API PUT/DELETE `/api/companies/<id>/projects/<id>/activities/<id>`
   - API PATCH `/api/companies/<id>/projects/<id>/activities/<id>/stage`

---

## 🔗 Integração com Sistema Existente

### Cards de Projeto:
```javascript
// Orçamento total vem das atividades
budget_total = activities.reduce((sum, act) => 
  sum + (parseFloat(act.amount) || 0), 0
);

// Prazo previsto vem da maior data
predicted_deadline = max(activities.map(act => act.when));

// Status calculado das atividades
if (todas completed) → 'Concluído'
else if (alguma completed) → 'Em andamento'
```

### Link no Card:
```html
<a href="/grv/company/5/projects/26/manage">
  📋 Gerenciar
</a>
```

---

## ✅ Checklist de Validação

- [x] Botão "Gerenciar" aparece nos cards de projeto
- [x] Link leva para página de gerenciamento
- [x] Página exibe informações do projeto no cabeçalho
- [x] Kanban com 6 colunas renderiza
- [x] Botão "Nova Atividade" abre modal
- [x] Modal permite criar atividade
- [x] Código gerado automaticamente (2 dígitos)
- [x] Atividade aparece na "Caixa de Entrada"
- [x] Drag and drop funciona entre colunas
- [x] API PATCH atualiza stage
- [x] Editar atividade funciona
- [x] Excluir atividade funciona
- [x] Contadores atualizam corretamente
- [x] Notificações aparecem
- [x] Sem erros no console

---

## 🚀 Próximos Passos (Futuro)

### Melhorias Planejadas:

1. **Select de Responsável:**
   - Campo "Quem?" como select de colaboradores
   - Em vez de texto livre

2. **Filtros e Busca:**
   - Filtrar por responsável
   - Buscar por descrição
   - Filtrar por prazo

3. **Indicadores Visuais:**
   - Badge de prioridade
   - Ícone de anexos
   - Badge de atraso (prazo vencido)

4. **Relatórios:**
   - Tempo médio por coluna
   - Taxa de conclusão
   - Distribuição de orçamento

5. **Comentários:**
   - Adicionar comentários nas atividades
   - Histórico de alterações

---

**Data de Implementação:** 11/10/2025  
**Versão:** APP27  
**Módulo:** GRV - Gestão de Projetos  
**Status:** ✅ Funcional

