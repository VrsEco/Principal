# SPEC - Auditoria Interna Fase 01 v1

**Classe documental:** SPEC  
**Status:** decisão oficial de implementação - Fase 01  
**Data:** 31/05/2026  
**Derivado de:** `C:\GestaoVersus\app32\app32\docs\papers\paper_auditoria_interna_integrada_versus_v1.md`  
**Especialista líder:** @ARQUITETO  
**Apoios:** @BACKEND_SERVICE, @BACKEND_API, @DBA, @FRONTEND, @QA_AUTOMATION

---

## 1. Decisão oficial

Implementar o módulo **Auditoria Interna Fase 01** como camada transversal de auditoria sobre Processos, Projetos, Reuniões, Financeiro e Indicadores.

Fluxo oficial da Fase 01:

```text
Checklist
→ execução
→ ponto de auditoria
→ papel de trabalho
→ achado
→ projeto/atividade
→ reunião de alinhamento
→ relatório
→ follow-up
```

---

## 2. Escopo da Fase 01

Incluído:

- cadastros de área/departamento e auditores;
- checklists vinculados a processo, projeto ou autônomos;
- itens de checklist com descrição para relatório;
- execução de checklist com status;
- pontos de auditoria manuais ou originados por checklist;
- papéis de trabalho com anexos, imagens, comentários e alertas;
- achados;
- vínculo com projeto existente ou criação de projeto/atividade corretiva;
- reunião de alinhamento vinculada ao achado/projeto;
- relatório web/PDF;
- registro de envio por e-mail/WhatsApp;
- follow-up de achados e ações corretivas.

Fora da Fase 01:

- motor avançado de anomalias;
- IA generativa;
- biblioteca completa COSO/COBIT;
- achado automático sem auditor;
- risk scoring sofisticado.

---

## 3. Guardrails técnicos

- Stack: Python, Flask, PostgreSQL, Jinja2/Tailwind.
- Toda tabela operacional deve possuir `company_id`.
- Toda query deve filtrar `company_id`.
- Rotas não podem conter regra de negócio.
- Serviços concentram regra de auditoria.
- Integração com Projetos/Reuniões deve ser por service/contrato, não SQL espalhado.
- Upload/evidência deve reaproveitar padrão existente de anexos quando disponível.

---

## 4. Modelo de dados mínimo

### 4.1 `audit_areas`

```text
id
company_id
name
description
manager_user_id
active
created_at
updated_at
```

### 4.2 `audit_auditors`

```text
id
company_id
user_id
employee_id
role                # auditor_admin, auditor, viewer_executivo
active
created_at
updated_at
```

### 4.3 `audit_checklists`

```text
id
company_id
title
description
checklist_type      # process, project, autonomous
linked_process_id
linked_project_id
linked_routine_id
area_id
owner_user_id
default_periodicity
active
metadata_json
created_at
updated_at
```

### 4.4 `audit_checklist_items`

```text
id
company_id
checklist_id
title
description_for_report
expected_evidence
criterion
weight
sort_order
active
metadata_json
created_at
updated_at
```

### 4.5 `audit_executions`

```text
id
company_id
checklist_id
schedule_id
area_id
auditor_user_id
period_label
planned_start_date
planned_end_date
started_at
completed_at
status              # planned, in_progress, completed, cancelled
created_at
updated_at
```

### 4.6 `audit_execution_items`

```text
id
company_id
execution_id
checklist_item_id
status              # conforming, qualified_conforming, non_conforming, not_applicable, not_tested
justification
comments
created_at
updated_at
```

### 4.7 `audit_points`

```text
id
company_id
title
description
origin_type         # manual, checklist, analyzer
source_module       # audit, processes, projects, meetings, finance, strategy
subject_type
subject_id
severity            # low, medium, high, critical
status              # open, in_review, converted_to_finding, dismissed, closed
assigned_to_user_id
detected_at
due_date
metadata_json
created_at
updated_at
```

### 4.8 `audit_workpapers`

```text
id
company_id
execution_id
execution_item_id
audit_point_id
auditor_user_id
comments
conclusion
alert_notes
evidence_summary
created_at
updated_at
```

### 4.9 `audit_evidence_links`

```text
id
company_id
workpaper_id
finding_id
evidence_type       # upload, image, process, project, task, meeting, finance_entry, indicator, comment
source_module
source_id
file_path
caption
created_by_user_id
created_at
```

### 4.10 `audit_findings`

```text
id
company_id
audit_point_id
execution_id
execution_item_id
title
condition_text
criterion_text
cause_text
effect_text
recommendation_text
severity            # low, medium, high, critical
status              # open, action_linked, awaiting_alignment, reported, in_followup, closed, reopened
responsible_user_id
due_date
project_id
task_id
alignment_meeting_id
created_at
updated_at
```

### 4.11 `audit_schedules`

```text
id
company_id
title
process_id
routine_id
checklist_id
area_id
auditor_user_id
planned_start_date
planned_end_date
recurrence_rule
status              # active, paused, completed, cancelled
metadata_json
created_at
updated_at
```

### 4.12 `audit_reports`

```text
id
company_id
execution_id
title
version
status              # draft, issued, sent
html_snapshot
pdf_path
issued_by_user_id
issued_at
created_at
updated_at
```

### 4.13 `audit_report_deliveries`

```text
id
company_id
report_id
channel             # email, whatsapp
recipient
status              # pending, sent, failed
sent_by_user_id
sent_at
error_message
created_at
```

---

## 5. Serviços obrigatórios

```text
InternalAuditAreaService
InternalAuditChecklistService
InternalAuditExecutionService
InternalAuditPointService
InternalAuditWorkpaperService
InternalAuditFindingService
InternalAuditRemediationBridgeService
InternalAuditScheduleService
InternalAuditReportService
InternalAuditDeliveryService
```

Responsabilidades principais:

- `ChecklistService`: CRUD de checklists e itens.
- `ExecutionService`: abrir, preencher e concluir execução.
- `PointService`: criar/triagem/fechar pontos de auditoria.
- `WorkpaperService`: comentários, conclusões, anexos e evidências.
- `FindingService`: criar achados e controlar ciclo de vida.
- `RemediationBridgeService`: criar/vincular projeto/atividade.
- `ScheduleService`: cronogramas e recorrência.
- `ReportService`: gerar relatório web/PDF.
- `DeliveryService`: registrar/envio e-mail/WhatsApp.

---

## 6. Workflow de status

### 6.1 Item de checklist

```text
not_tested
→ conforming
→ qualified_conforming
→ non_conforming
→ not_applicable
```

Regras:

- `not_applicable` exige justificativa.
- `qualified_conforming` pode gerar ponto de auditoria.
- `non_conforming` deve gerar ponto/achado ou justificativa formal.

### 6.2 Ponto de auditoria

```text
open
→ in_review
→ converted_to_finding
→ dismissed
→ closed
```

### 6.3 Achado

```text
open
→ action_linked
→ awaiting_alignment
→ reported
→ in_followup
→ closed
→ reopened
```

Regra: achado não pode ser `closed` sem evidência ou justificativa do auditor.

---

## 7. Rotas/telas Fase 01

Prefixo sugerido: `/internal-audit`.

Telas:

```text
/internal-audit                         Dashboard
/internal-audit/areas                   Áreas/departamentos
/internal-audit/auditors                Auditores
/internal-audit/checklists              Checklists
/internal-audit/checklists/<id>         Detalhe e itens
/internal-audit/schedules               Cronograma
/internal-audit/executions              Execuções
/internal-audit/executions/<id>         Execução do checklist
/internal-audit/points                  Pontos de auditoria
/internal-audit/workpapers/<id>         Papel de trabalho
/internal-audit/findings                Achados
/internal-audit/findings/<id>           Detalhe/remediação/follow-up
/internal-audit/reports/<id>            Relatório
```

Menu preliminar:

```text
Auditoria Interna
├── Dashboard
├── Checklists
├── Pontos de Auditoria
├── Execuções
├── Achados
├── Cronograma
├── Relatórios
└── Cadastros
```

---

## 8. Contratos de integração

### 8.1 Projetos/atividades

Entrada mínima para criar atividade corretiva:

```text
company_id
audit_finding_id
project_id opcional
title
description
responsible_user_id
due_date
priority
```

Saída mínima:

```text
project_id
task_id
status
url
```

### 8.2 Reuniões

Entrada mínima para reunião de alinhamento:

```text
company_id
audit_finding_id
title
participants
planned_at
agenda
```

Saída mínima:

```text
meeting_id
status
url
```

### 8.3 Processos/rotinas

Checklists podem referenciar `process_id`, `routine_id` e instâncias futuras, mas não devem copiar o processo.

### 8.4 Financeiro/Indicadores

Na Fase 01, vínculos são evidências. Cruzamentos automáticos ficam para fase posterior.

---

## 9. RBAC mínimo

```text
auditor_admin
- gerencia cadastros, checklists, cronogramas e relatórios.

auditor
- executa checklists, cria pontos, papéis de trabalho e achados.

responsavel_auditado
- visualiza achados atribuídos, responde ações e anexa evidências.

viewer_executivo
- consulta dashboards e relatórios emitidos.
```

Todos os checks de permissão devem considerar `company_id`.

---

## 10. Relatório

O relatório deve consolidar:

- dados da execução;
- área/processo/projeto auditado;
- checklist e itens;
- descrição de cada item para relatório;
- status;
- pontos de auditoria;
- papéis de trabalho relevantes;
- evidências;
- achados;
- projeto/atividade corretiva;
- reunião de alinhamento;
- conclusão do auditor;
- plano de follow-up.

Envios por e-mail/WhatsApp devem registrar entrega em `audit_report_deliveries`.

---

## 11. Índices mínimos

```text
(company_id, active)
(company_id, checklist_id)
(company_id, execution_id)
(company_id, status)
(company_id, severity)
(company_id, due_date)
(company_id, project_id)
(company_id, task_id)
(company_id, alignment_meeting_id)
```

---

## 12. Critérios de aceite

A Fase 01 estará aceita quando:

1. usuário autorizado criar checklist vinculado a processo, projeto ou autônomo;
2. checklist possuir itens com `description_for_report`;
3. auditor executar checklist e marcar status;
4. item não conforme gerar ponto de auditoria/achado;
5. achado criar ou vincular projeto/atividade;
6. achado vincular reunião de alinhamento;
7. papel de trabalho aceitar comentários e evidências;
8. relatório web/PDF for gerado;
9. envio por e-mail/WhatsApp registrar delivery;
10. todas as consultas respeitarem `company_id`;
11. testes validarem fluxo principal e isolamento multi-tenant.

---

## 13. Plano de testes

Testes mínimos:

- unitários de services;
- integração de models/queries por `company_id`;
- contrato de criação de atividade/projeto;
- contrato de vínculo com reunião;
- renderização de relatório;
- permissão por perfil;
- regressão do sidebar/menu;
- smoke do fluxo completo.

Fluxo smoke:

```text
criar checklist
→ criar item
→ abrir execução
→ marcar não conforme
→ criar ponto
→ criar achado
→ vincular projeto/atividade
→ vincular reunião
→ gerar relatório
→ registrar envio
→ iniciar follow-up
```

---

## 14. Próxima etapa implementável

Implementar em três ondas:

1. **Base e cadastros:** tabelas, services, RBAC, menu, checklists, áreas e auditores.
2. **Execução e achados:** execução de checklist, pontos, papéis de trabalho, evidências e achados.
3. **Integrações e relatório:** projeto/atividade, reunião de alinhamento, relatório, envio e follow-up.

### Contrato implementado da Onda 4

- `audit_reports`: relatório versionado por `company_id + execution_id + version`;
- emissão exige aprovação humana e conclusão do auditor;
- emissão grava `snapshot_json` e torna a versão imutável;
- correções posteriores criam nova versão e preservam a anterior como `superseded`;
- `audit_follow_ups`: trilha append-only de acompanhamento por achado e empresa;
- resolução e encerramento exigem validação textual do auditor;
- saída A4 permite impressão ou salvamento em PDF;
- entrega auditável por e-mail/WhatsApp permanece evolução subsequente.

## 15. Incremento P0 IA/OAuth/CLI — 16/09/2026

Arquitetura-alvo preservada: plataforma única para auditoria sistêmica/interna e trabalho externo; `AuditEngagement` delimita empresa custodiante (`company_id`), auditado, objetivo, período, programa e equipe. `AuditRun` registra execução e linhagem; candidato gerado por IA/analyzer exige triagem humana antes do ponto. Estes agregados ainda são evolução planejada, não implementação desta entrega.

Contrato do incremento local:

- capability ausente é negada; não há inferência financeira por nome;
- aprovação é um registro persistido, nunca um booleano do payload;
- `ToolApprovalService` revalida status, tipo, tenant e usuário do registro, além de principal/tool/digest e expiração;
- `mcp.tool_policy.allowed/blocked` usa identidade resolvida pelo servidor e metadata estruturada, sem copiar payload ou subject;
- metadata contém principal, auth_method, client_id, scopes, surface, motivo, approval_request_id e payload_digest;
- mutação autorizada exige persistência durável antes do callback; falha produz `AIExecutionAuditPersistenceError`;
- leituras e eventos negados permanecem best-effort;
- logger, retorno e persistência redigem segredos recursivamente, inclusive arrays.

Aceite desse incremento local: 27 testes focados aprovados, incluindo callback não executado sem trilha durável. Naquele estágio, permaneciam pendentes smoke OAuth autenticado end-to-end, concorrência e replay em PostgreSQL, migração da tabela de eventos e rollout. As subseções seguintes registram o fechamento técnico dos três primeiros itens; o rollout continua pendente. Metadata JSONB não equivale a novos campos/indexes estruturados no banco.

### 15.1 Schema de auditoria v2 — implementação local

- merge migration `20260917_1000`, sobre os heads `20260913_1500` e `20260916_1000`, assume a tabela legada sem apagar histórico;
- colunas: `principal_id`, `auth_method`, `client_id`, `surface`, `token_scopes` (JSONB), `policy_allowed`, `policy_reason`, `approval_request_id`, `payload_digest`;
- índices novos iniciam por `company_id` e cobrem principal/tempo, policy/tempo e aprovação;
- eventos legados não são reinterpretados a partir de metadata livre; campos novos podem permanecer nulos;
- schema version: `2026-09-16.v2`;
- writer faz apenas INSERT em transação própria de `db.engine.begin()`, sem DDL e sem commit/rollback da sessão da tool;
- downgrade preserva tabela, colunas e índices por serem aditivos e conterem evidência; remoção exige decisão específica de retenção;
- aplicar migration antes de promover o writer; schema ausente/incompatível bloqueia mutação pela regra fail-closed;
- contrato daquele estágio: 30 testes aprovados; PostgreSQL real, concorrência/replay e OAuth ponta a ponta ainda eram pendentes e foram tratados nas subseções seguintes.

### 15.2 Homologação PostgreSQL isolada

Em 16/09/2026, 11 testes reais em PostgreSQL 16.15 passaram: schema novo/idempotência, schema legado/histórico/downgrade preservador, campos v2/segredos redigidos, consumo concorrente com exatamente um vencedor, replay, tenant/usuário/digest/expiração e transação independente. A consulta exige `payload.approval_key` exata no banco antes de `FOR UPDATE`; validações de binding permanecem no service.

O smoke OAuth local usa JWT RS256 assinado e valida de forma integrada issuer, audience, client allowlist, scopes, vínculo persistido `issuer/sub`, grant explícito de `company_id`, negação cross-tenant, principal revogado e evento `ai_mcp_audit_events` com identidade/policy estruturadas. Tokens inválidos ou principals revogados falham sem fallback para bearer legado.

A evidência aplica a revision diretamente com Operations Alembic em schemas descartáveis. Complementarmente, o comando real `flask db upgrade`, com bootstrap de schema/runtime desligado e banco sintético marcado nos heads `20260913_1500` e `20260916_1000`, carregou o APP32, executou `20260917_1000` e alcançou o head esperado. O ORM concorrente do ensaio representa a fronteira de AgentAction usada pelo service.

Banco totalmente vazio não é um gate válido deste incremento: a cadeia histórica falha antes do P0 em `20260205_2000`, pois `portfolios.company_id` referencia `companies` sem revision baseline que crie essa tabela. Corrigir o bootstrap integral é dívida arquitetural separada e não autoriza alterar ou mascarar migrations históricas durante o rollout do P0. A homologação posterior com IdP externo/redirect real está registrada em 15.4; ainda falta rollout controlado, portanto o P0 não está encerrado.

### 15.3 Gate de rollout OAuth

`services/oauth_mcp_rollout_readiness_service.py` é a decisão pura e `scripts/qa/check_oauth_mcp_rollout_readiness.py` é o adaptador operacional read-only. O modo `pilot` exige grants ativos e rota piloto, preserva a surface `user` legada e rejeita issuer/JWKS/base pública sem HTTPS. O modo `cohort` exige ativação global e lista explícita de surfaces. Ambos exigem algoritmo assimétrico e `mcp:access`; CA customizada precisa existir. Ausência de allowlist de clients gera alerta explícito, aceitável apenas para Dynamic Client Registration aprovado.

Com `--live`, o preflight consulta apenas endpoints públicos, sem bearer: discovery deve devolver issuer/JWKS idênticos à configuração; JWKS deve conter chaves com `kid` e `kty`; metadata RFC 9728 deve apontar para `/mcp/pilot/user` e para o authorization server contratado. Resposta acima de 1 MiB, TLS inválido, drift ou indisponibilidade bloqueiam a promoção.

Sem configuração explícita, o gate retorna `ready=false`. Em 17/09/2026, as configurações públicas foram injetadas apenas no processo read-only e `--live` retornou `ready=true`: discovery, JWKS e metadata RFC 9728 corresponderam ao contrato. A rota piloto anônima respondeu `401` com `WWW-Authenticate` apontando para o metadata correto. Não houve alteração de flags, credenciais ou dados em produção.

### 15.4 Smoke autenticado Codex CLI

O cliente `mcp-versus` concluiu Authorization Code com PKCE e Dynamic Client Registration no IdP público. Em seguida, o Codex CLI executou exclusivamente `list_user_app32_capabilities`, após aprovação humana limitada à chamada, sem acesso a shell, arquivos ou mutações. Resultado: 4 capabilities, 3 domínios e scope efetivo `mcp_user`.

Critério comprovado: login interativo, emissão/uso de bearer pelo cliente sem revelar credencial, sessão MCP remota e catálogo autenticado de leitura. Critério ainda pendente: rollout do writer/schema v2 e comprovação em produção da trilha `ai_mcp_audit_events`; portanto, a evidência não encerra o P0 nem autoriza ampliar a coorte.
