# Projeto: Sapiens - Agente Conversacional Inteligente
## Gestão Versus v2.0 — Roadmap de Implementação

---

## ⚖️ LEI DE CONFORMIDADE ARQUITETURAL — REGRA INQUEBRÁVEL

> **"O Sapiens é um usuário programático. Ele faz exatamente o que um usuário humano faria clicando nos botões do sistema — nem mais, nem menos."**

### CATEGORIA A — Mutação de Dados (INSERT / UPDATE / DELETE)
- ✅ **OBRIGATÓRIO**: Usar os mesmos Models SQLAlchemy (ORM) e Services que o Frontend usa.
- ✅ **OBRIGATÓRIO**: O resultado de qualquer ação do Sapiens DEVE ser visível, editável e continuável pelo usuário humano na interface do app.
- ❌ **PROIBIDO**: Executar INSERT/UPDATE/DELETE via SQL bruto (`text()`).
- ❌ **PROIBIDO**: Criar lógicas de negócio paralelas às do app (ex: gerar ATA em campo diferente de `meeting.meeting_notes`, criar projetos em tabelas alternativas, etc).

### CATEGORIA B — Análise de Dados (SELECT / Cruzamentos / Relatórios Analíticos)
- ✅ **PERMITIDO**: Usar `query_database()` com SQL SELECT customizado para análises livres.
- ✅ **PERMITIDO**: Cruzar múltiplas tabelas, calcular métricas e agregar dados.
- ✅ **PERMITIDO**: Gerar insights que um humano faria pegando 2-3 relatórios e analisando em planilha.
- ❌ **PROIBIDO**: SELECT em tabelas sensíveis: `users`, `roles`, `employees`, `companies`, `sessions`, `audit_log`.

### Checklist para Criar Novas Tools (@QA_AUTOMATION)
```
[ ] A tool escreve dados?    → Use Model SQLAlchemy da pasta /models.
[ ] A tool envia mensagem?   → Use services/email_service.py ou whatsapp_service.py.
[ ] A tool lê relatório?     → Chame a API REST existente ou query_database().
[ ] Resultado visível no app? → Sim = aprovado / Não = reprovar e refatorar.
```

**Onde esta lei está gravada:**
- `src/intelligence/tools.py` → Cabeçalho do arquivo (linha 1)
- `src/intelligence/agents/supervisor.py` → Prompt do Supervisor Central (injetado em todo LLM call)
- `ROADMAP_SAPIENS.md` → Este documento (fonte da verdade)

---


## ✅ FASE 1 — Sapiens Orientador (CONCLUÍDO)
**Objetivo:** Habilitar o Sapiens para educar, guiar e executar cadastros via chat.

### Entregáveis:
- [x] **Prompts Expandidos** (`src/intelligence/work_agents/agents.py`)
  - Todos os 7 agentes com papéis, limites de autorização e formato de resposta detalhados.
  - Sapiens com fluxo obrigatório: CONCEITO → MATERIAL RAG → OPÇÕES → PERGUNTA FINAL.

- [x] **RAG de Conhecimento** (`src/intelligence/seed_knowledge.py`)
  - 14 documentos vetorizados no ChromaDB cobrindo:
    - Mapa de Processos (conceito + boas práticas)
    - Planejamento Estratégico (PEV, OKRs)
    - Projetos e Gestão de Tarefas
    - Meu Trabalho
    - Reuniões
    - Indicadores (KPIs)
    - Usuários e Permissões
    - Regras de Aprovação Financeira
    - Conformidade Fiscal
    - Guia de Uso do Sapiens
    - Análise de Eficiência
    - Onboarding (Primeiros Passos)

- [x] **Tools MCP Completas** (`src/intelligence/tools.py`)
  - 15 ferramentas expostas: consult_rules, query_database, escalate_technical_issue,
    create_process_area, create_macro_process, create_process, update_company_status,
    list_process_hierarchy, list_plans, get_plan_diagnostics, update_plan_section,
    get_my_work, list_system_users, register_system_user, update_user_contacts.

- [x] **MCP Server Corrigido** (`src/core/mcp_server.py`)
  - FastMCP usando `tool.func` para introspecção real da assinatura Python.
  - Dependências `mcp` e `fastmcp` instaladas e no `requirements.txt`.

---

## ✅ FASE 2 — Braços Executivos de Reunião + Tarefas (CONCLUÍDO)
**Objetivo:** O Sapiens pode criar/gerenciar reuniões e registrar trabalho via chat.

### Entregáveis:
- [x] **Tools MCP de Reunião** (`src/intelligence/tools.py`)
  - `schedule_meeting`, `start_meeting`, `log_meeting_discussion`, `finish_meeting`, `send_meeting_minutes`.
- [x] **Tools MCP de Gestão de Tarefas** (`src/intelligence/tools.py`)
  - `get_tasks_today`, `complete_task`, `log_work_hours`, `request_deadline_extension`, `list_team_workload`.
- [x] **Consolidação**: Total de 25 tools MCP operacionais e validadas via ORM.
- [x] **RAG** — Adicionados documentos de Reuniões e Guia Sapiens.

---

## ✅ FASE 3 — Webhook Telegram (CONCLUÍDO)
**Objetivo:** O Sapiens opera fora do sistema, diretamente no Telegram dos usuários.

### Entregáveis:
- [x] **Bot Telegram** (`api/webhooks/telegram_webhook.py`)
  - Webhook endpoint Flask: `POST /webhook/telegram`.
  - Tunelamento automático via Ngrok (`run_dev.py`).
  - Autenticação por `telegram_id` vinculado ao `User.telegram`.
- [x] **Arquitetura de Mensageria**
  - Processamento assíncrono (Threads) para evitar timeout no Telegram.
  - Normalização de mensagens (Tuplas vs BaseMessage) no Supervisor e Grafo.
  - Segurança: Filtro de usuários não vinculados ("Human-in-the-loop" de Identidade).

---

## 🔧 FASE 4 — Proatividade e Aprovação Hierárquica (PENDENTE)
**Objetivo:** O Sapiens age sem ser chamado (Cron) e gerencia aprovações entre superiores e subordinados.

### Entregáveis pendentes:
- [ ] **Cron Scheduler Matinal** (`services/scheduler_service.py`)
  - Job diário (08:00h): analisa tarefas vencendo nos próximos 3 dias.
  - Envia mensagem personalizada no Telegram de cada colaborador.
  - Mensagens segmentadas: 🔴 Atrasadas | 🟡 Vencendo Esta Semana | 💡 Semana Leve.

- [ ] **Fluxo Human-in-the-Loop** (LangGraph Checkpoints)
  - Colaborador pede extensão de prazo → Sapiens PAUSA o grafo (checkpoint no PostgreSQL).
  - Sapiens envia mensagem ao supervisor no Telegram: "Aprovar ou Recusar?"
  - Supervisor responde → LangGraph RETOMA o estado → executa ação ou notifica recusa.

- [ ] **Notificações de Entrega Concluída**
  - Quando uma tarefa é concluída via chat, notificar o supervisor automaticamente.

---

## 📐 Arquitetura de Referência

```
[Usuário - Telegram/WhatsApp]
         │
         ▼
[Webhook Flask - /webhook/telegram]
         │  autentica por telegram_id
         ▼
[LangGraph - work_agent_graph]
         │
    ┌────┴────┐
    │ Supervisor (gpt-4o-mini - Roteador) │
    └────┬────┘
         │ roteia para o agente certo
    ┌────▼────────────────────────────────┐
    │ Agentes: sapiens | operations | ... │
    └────┬────────────────────────────────┘
         │ invoca ferramentas se necessário
    ┌────▼────┐
    │ ToolNode (MCP Tools - 15 ferramentas) │
    └────┬────┘
         │ lê/escreve no PostgreSQL
    ┌────▼────┐
    │ PostgreSQL (app32 - Multi-tenant) │
    └─────────┘
```

---

## 📋 Status Atual do MCP Server
- **25 Tools Ativas:** consult_rules, query_database, schedule_meeting, start_meeting, log_meeting_discussion, finish_meeting, send_meeting_minutes, get_tasks_today, complete_task, log_work_hours, request_deadline_extension, list_team_workload, e ferramentas de cadastro (area, macro, process).
- **RAG:** 14 documentos vetorizados (ChromaDB local em `./data/chroma_db`).
- **LangGraph:** Grafo compilado com 8 agentes + ToolNode + Supervisor.
- **Modelos:** `gpt-4o` (especialistas) + `gpt-4o-mini` (roteador/supervisor).
