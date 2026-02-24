# 📋 Decision Log - Decisões Arquiteturais
- 2025-11-17 — Arthur  
  - Removido suporte a SQLite (arquivo `database/sqlite_db.py` e scripts legados)  
  - `PostgreSQLDatabase` passou a implementar `get_company_profile`, `update_company_profile`, `update_company_mvv`, `get_overdue_tasks`  
  - Rotinas/tarefas e integrações agora usam apenas o driver Postgres  
  - **Pendência registrada**: tabela `user_logs` está falhando por não ter coluna `id` com default/sequence → corrigir próximo
- 2025-11-17 — Equipe Governança  
  - Adicionada dependência `plotly` aos relatórios profissionais (gráficos gerados por `modules/gerador_relatorios.py`)  
  - Ajustados endpoints `/api/companies/<id>/routine-tasks/*` para usar colunas `TIMESTAMP` no PostgreSQL

**Projeto:** GestaoVersus  
**Última atualização:** 26/11/2025

---

## 🎯 Formato de Registro

Cada decisão deve conter:
- **Data:** Quando foi tomada
- **Contexto:** Por que foi necessária
- **Decisão:** O que foi decidido
- **Alternativas:** O que foi considerado
- **Consequências:** Impactos da decisão
- **Status:** Ativa, Superada, Cancelada

---

## 📚 Decisões Registradas

### **#001 - Uso de PostgreSQL como Banco Principal**

**Data:** 18/10/2025  
**Contexto:** Necessidade de suportar operações avançadas e escalabilidade  
**Decisão:** PostgreSQL como banco principal, SQLite apenas para testes locais  
**Alternativas:** MySQL, MongoDB  
**Consequências:** +Performance, +Features avançadas, -Simplicidade  
**Status:** ✅ Ativa

---

### **#002 - Arquitetura Modular com Blueprints**

**Data:** 18/10/2025  
**Contexto:** Separar módulos PEV, GRV, Meetings  
**Decisão:** Usar Flask Blueprints para modularização  
**Alternativas:** Monolito, Microserviços  
**Consequências:** +Organização, +Manutenibilidade, =Complexidade  
**Status:** ✅ Ativa

---

### **#003 - Database Abstraction Layer**

**Data:** 18/10/2025  
**Contexto:** Suportar PostgreSQL e SQLite simultaneamente  
**Decisão:** Criar `DatabaseInterface` com implementações específicas  
**Alternativas:** SQLAlchemy ORM completo  
**Consequências:** +Flexibilidade, +Controle, -Código boilerplate  
**Status:** ✅ Ativa

---

### **#004 - Soft Delete ao Invés de Hard Delete**

**Data:** 18/10/2025  
**Contexto:** Necessidade de auditoria e recuperação de dados  
**Decisão:** Usar `is_deleted=True` ao invés de DELETE real  
**Alternativas:** Hard delete, Archive table  
**Consequências:** +Auditoria, +Recuperação, -Complexidade queries  
**Status:** ✅ Ativa

---

### **#005 - Jinja2 Templates ao Invés de SPA**

**Data:** 18/10/2025  
**Contexto:** Simplicidade e manutenibilidade  
**Decisão:** Server-side rendering com Jinja2 + JavaScript Vanilla  
**Alternativas:** React, Vue, Angular  
**Consequências:** +Simplicidade, +SEO, -Interatividade  
**Status:** ✅ Ativa

---

### **#006 - Tipos de Planejamento (Evolução vs Implantação)**

**Data:** 23/10/2025  
**Contexto:** Diferentes fluxos para empresas existentes vs novos negócios  
**Decisão:** Campo `plan_mode` com valores 'evolucao' e 'implantacao'  
**Alternativas:** Dois módulos separados, Feature flags  
**Consequências:** +Flexibilidade, +Reutilização código, -Complexidade rotas  
**Status:** ✅ Ativa

---

### **#007 - Padrão PFPN para Formulários**

**Data:** 23/10/2025  
**Contexto:** Necessidade de UX consistente em formulários de edição  
**Decisão:** Criar padrão PFPN (Visualização/Edição) para todos os formulários  
**Alternativas:** Edição inline sempre ativa, Modals para edição  
**Consequências:** +UX profissional, +Consistência, +Segurança (confirmações)  
**Implementação:** `docs/patterns/PFPN_PADRAO_FORMULARIO.md`  
**Status:** ✅ Ativa

**Detalhes da decisão #007:**
- Campos em modo visualização: fundo cinza (#f1f5f9), readonly
- Campos em modo edição: fundo branco, editável
- Botões: Editar, Cancelar, Salvar, Excluir
- Restauração de valores ao cancelar
- Notificações de sucesso/erro
- Implementado primeiro em: Canvas de Expectativas dos Sócios

---

### **#008 - Docker para Desenvolvimento e Produção**

**Data:** 20/10/2025  
**Contexto:** Consistência entre ambientes dev/prod  
**Decisão:** Docker Compose para orquestração de serviços  
**Alternativas:** Instalação local, Vagrant  
**Consequências:** +Consistência, +Isolamento, -Curva aprendizado  
**Status:** ✅ Ativa

---

### **#009 - Containers conectando ao PostgreSQL nativo do Windows**

**Data:** 28/10/2025  
**Contexto:** PostgreSQL 18 passou a operar instalado no host Windows, evitando duplicidade de dados entre containers e ambiente local  
**Decisão:** Remover o serviço `db` do `docker-compose.yml` e configurar `app`, `celery_worker`, `celery_beat` e `nginx` para usar `host.docker.internal` com as credenciais oficiais (`.env`)  
**Alternativas:** Manter PostgreSQL em container dedicado, usar serviço gerenciado na nuvem  
**Consequências:** +Simplicidade operacional, +Reuso da instância corporativa, -Dependência de disponibilidade do host  
**Status:** ✅ Ativa

---

### **#010 - Backups automatizados via Windows Task Scheduler**

**Data:** 28/10/2025  
**Contexto:** Garantir cópias consistentes do banco corporativo sem depender dos containers  
**Decisão:** Script `scripts/backup/run_pg_backup.ps1` executado às 12h, 18h e 22h via tarefa agendada `GestaoVersus_Postgres_Backup`  
**Alternativas:** Cron dentro do container, jobs no PostgreSQL, execuções manuais  
**Consequências:** +Confiabilidade, +Centralização dos artefatos em `backups/`, -Depende de usuário logado para Task Scheduler interativo  
**Status:** ❌ Superada (ver #016)

---

### **#011 - Publicação automática diária no GitHub**

**Data:** 28/10/2025  
**Contexto:** Reduzir risco de alterações locais ficarem fora do repositório oficial  
**Decisão:** Script `scripts/deploy/auto_git_push.ps1` executado diariamente às 18h pela tarefa `GestaoVersus_GitHub_Publish`  
**Alternativas:** Lembretes manuais, hooks externos  
**Consequências:** +Governança do versionamento, +Rastreabilidade de mudanças, -Exige credenciais Git configuradas no host  
**Status:** ✅ Ativa

---

### **#012 - Separação física entre ambientes Produção (APP31) e Desenvolvimento (APP32)**

**Data:** 12/11/2025  
**Contexto:** Necessidade de ter ambientes paralelos com os mesmos códigos para testar novas funcionalidades sem afetar usuários finais.  
**Decisão:** Manter o diretório `app31` como ambiente de produção, executado com `docker-compose.yml` apontando para o PostgreSQL oficial (`bd_app_versus`) e exposto na porta `5003`/Nginx `80/443`. Usar o diretório `app32` como ambiente de desenvolvimento com `docker-compose.yml` próprio (build via `Dockerfile.dev`), Redis isolado (`6380`), aplicação em `5004` e banco clonado (`bd_app_versus_dev`). O dump é armazenado em `app31/backups/`.  
**Alternativas:** Utilizar apenas um diretório alternando variáveis de ambiente; criar workspaces Git separados; usar ambientes em nuvem.  
**Consequências:** +Segurança (prod estável), +Rapidez para testar correções, +Padronização dos scripts de subida, -Duplicação de diretórios e necessidade de manter dumps atualizados.  
**Status:** ✅ Ativa

---

### **#013 - Plotly como dependência obrigatória dos relatórios profissionais**

**Data:** 17/11/2025  
**Contexto:** O gerador de relatórios (`modules/gerador_relatorios.py`) já utilizava Plotly para montar gráficos antes de exportar PDFs, mas a dependência não estava listada em `requirements.txt`, fazendo o endpoint `/api/relatorios/projetos/<company_id>` retornar 500 por `ModuleNotFoundError`.  
**Decisão:** Adicionar `plotly==5.24.0` às dependências oficiais e documentar a obrigatoriedade da biblioteca para geração dos gráficos usados nos relatórios corporativos.  
**Alternativas:** Remover os gráficos dos relatórios ou reimplementar usando apenas ReportLab. Ambas foram descartadas por reduzir valor visual do documento e já existir código estável com Plotly.  
**Consequências:** +Confiabilidade dos relatórios (sem 500), +Consistência entre ambientes, -Aumento mínimo no tempo de build (pacote adicional).  
**Status:** ✅ Ativa

---

### **#014 - Reorganização do Sistema de Usuários e Empresas (User-Employee-Company)**

**Data:** 26/11/2025  
**Contexto:** O sistema original tinha relação direta User ↔ Company, limitando a flexibilidade. Consultores que atendem múltiplas empresas precisavam de múltiplos logins. Atividades eram atribuídas por nome (texto), impossibilitando agregação eficiente. Necessidade de implementar "Minhas Atividades" agregadas de todas as empresas.  
**Decisão:** Implementar arquitetura de três camadas com entidade intermediária `Employee` (Colaborador): `USER ←→ EMPLOYEE ←→ COMPANY`. Criados modelos `Employee` e `Role` (com campo `permissions` JSON). Adicionado campo `employee_id` em `project_tasks`. Criado serviço `UserEmployeeService` e API REST completa (`/api/user-employee/*`).  
**Alternativas:** Manter estrutura atual (não resolve múltiplas empresas), Tabela de associação simples N:M (não suporta funcionários sem acesso), Duplicar usuários (má UX).  
**Consequências:** +Flexibilidade total (usuário em múltiplas empresas), +Atividades agregadas eficientes, +Permissões granulares por empresa, +Rastreabilidade completa, -Complexidade adicional (mais joins), -Migração de dados necessária, -Mudança de paradigma para desenvolvedores.  
**Implementação:** Ver `docs/governance/DECISION_LOG_ADR008.md` para detalhes completos.  
**Status:** ✅ Ativa

---

### **#015 - Normalização das Atividades do My Work**

**Data:** 28/11/2025  
**Contexto:** As atividades de projetos estavam armazenadas em JSON dentro de `company_projects.activities` e as instâncias de processo usavam `assigned_collaborators` também em JSON. Isso impedia o My Work de aplicar filtros por responsável/executor, quebrava o controle de permissões e dificultava auditoria.  
**Decisão:** Criar tabelas normalizadas `project_activities` e `process_instance_collaborators`, adicionar colunas `responsible_id`/`executor_id`/`owner_employee_id` em `processes` e `process_instances`, migrar os dados existentes e atualizar o serviço `my_work_service` para consumir apenas essas estruturas relacionais (com fallback legado).  
**Alternativas:** Continuar no JSON e interpretar dinamicamente (não resolve permissões), reaproveitar `project_tasks` (não cobre processos, exigiria ajustes maiores nos módulos legados).  
**Consequências:** +Consistência dos vínculos User → Employee → Atividade, +Filtros confiáveis, +Auditoria, +Base para RBAC por papel (dono/responsável/executor), -Migração de dados e scripts adicionais, -Atualizações em serviços e páginas que ainda consumiam o JSON.  
**Status:** ✅ Ativa

---

### **#016 - Suspensão da tarefa automática de backup no Windows**

**Data:** 29/11/2025  
**Contexto:** Solicitado cancelar a execução periódica `GestaoVersus_Postgres_Backup` e concentrar os disparos de backup apenas quando houver demanda operacional específica.  
**Decisão:** remover a tarefa agendada do Windows Task Scheduler utilizando `scripts/backup/unregister_postgres_backup_tasks.ps1` e manter apenas execuções manuais do `scripts/backup/run_pg_backup.ps1` (ou reativar conscientemente via `register_postgres_backup_tasks.ps1`, se necessário).  
**Alternativas:** Manter a tarefa ativa, migrar o agendamento para cron em containers, mover a responsabilidade para jobs do PostgreSQL.  
**Consequências:** +Evita execuções automáticas duplicadas, +Controle explícito sobre quando gerar dumps, -Backups passam a depender de acionamento manual, -Requer disciplina operacional até definição de nova política.  
**Status:** ✅ Ativa

---

### **#017 - Arquitetura AI-Readable e Primazia da Layer 3 (PlanService)**

**Data:** 19/02/2026  
**Contexto:** Necessidade de expor regras de negócio para agentes de IA (MCP) e evitar lógica duplicada entre rotas e ferramentas. Além disso, padronizar modais e relatórios para alta fidelidade.  
**Decisão:** Centralizar toda a lógica de planejamento no `PlanService`. Refatorar ferramentas MCP (`src/intelligence/tools.py`) para serem context-aware (híbridas) e sanitizadas. Padronizar `z-index: 25000` para modais.  
**Alternativas:** Manter lógica em rotas Flask, criar serviços separados para IA.  
**Consequências:** +Reuso de código, +Segurança (multi-tenant centralizado), +AI-Readable por padrão, -Aumento da dependência do Service Layer.  
**Status:** ✅ Ativa

---

### **#018 - Padronização da Versão do PostgreSQL (PostgreSQL 14)**

**Data:** 22/02/2026  
**Contexto:** Divergência entre ambientes de desenvolvimento (rodando PG 18) e produção (rodando PG 14). Necessidade de paridade de ambiente para evitar bugs de incompatibilidade e garantir que scripts de migração funcionem em ambos.  
**Decisão:** Fixar o PostgreSQL versão 14 como padrão oficial do projeto Gestão Versus. Todos os ambientes locais (APP32) devem migrar para o binário da versão 14.  
**Alternativas:** Atualizar a produção para a versão 18 (descartado por estabilidade do ambiente atual).  
**Consequências:** +Paridade entre Dev e Prod, +Confiabilidade nas migrações, -Necessidade de reconfigurar serviços locais que apontavam para PG 18.  
**Status:** ✅ Ativa

---

## 📝 Como Adicionar Nova Decisão

1. Copie o template abaixo
2. Preencha todos os campos
3. Adicione na seção "Decisões Registradas"
4. Atualize a data de última atualização

```markdown
### **#XXX - Título da Decisão**

**Data:** DD/MM/YYYY  
**Contexto:** [Por que foi necessária]  
**Decisão:** [O que foi decidido]  
**Alternativas:** [O que foi considerado]  
**Consequências:** [Impactos esperados]  
**Status:** ✅ Ativa / ⚠️ Em Revisão / ❌ Superada
```

---

## 🔍 Revisão de Decisões

Decisões devem ser revisadas:
- Trimestralmente (verificar se ainda fazem sentido)
- Quando aparecer problema relacionado
- Ao adicionar nova feature que conflite

---

**Mantenha este arquivo atualizado!**  
**Decisões arquiteturais impactam todo o time.**
