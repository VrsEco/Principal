# Suíte E2E do Gestão Versus

## Objetivo
Base inicial do projeto `AA.J.18` para suportar:

- `DEV_FULL`
- `PROD_SAFE`
- evidências automáticas
- smoke de autenticação e chegada ao workspace

## Variáveis esperadas

- `E2E_ENV_NAME`
- `E2E_BASE_URL`
- `E2E_USERNAME`
- `E2E_PASSWORD`
- `E2E_COMPANY_ID`
- `E2E_HEADLESS` (opcional)
- `E2E_DESTRUCTIVE_ACTIONS_ALLOWED`
- `E2E_REQUIRES_ISOLATED_TENANT`
- `E2E_REQUIRE_EXPLICIT_COMPANY`

## Perfis oficiais

### DEV_FULL
- destrutivo permitido
- tenant isolado obrigatório
- `company_id` explícito obrigatório
- base sugerida: clone local / homologação

Exemplo:
- `C:\GestaoVersus\app32\app32\tests\e2e\config\.env.dev_full.example`

### PROD_SAFE
- destrutivo proibido
- tenant isolado obrigatório
- `company_id` explícito obrigatório
- rota pós-login controlada

Exemplo:
- `C:\GestaoVersus\app32\app32\tests\e2e\config\.env.prod_safe.example`

## Execução inicial

```bash
pytest app32/tests/e2e/journeys/smoke/test_login_and_navigation.py -m smoke
```

## Execução recomendada no Windows

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
pytest app32/tests/e2e/journeys/smoke/test_login_and_navigation.py -q
```

## Inspecionar contrato efetivo

```bash
python app32/tests/e2e/scripts/print_effective_config.py
```

## Gerar sessão autenticada reutilizável

```bash
python app32/tests/e2e/scripts/bootstrap_auth_state.py
```

O script:
- autentica na tela real
- resolve o tenant/contexto
- persiste `storage_state.json` para reuso nas próximas execuções

## Evidências geradas por execução

Cada execução grava em `outputs/<modo>/<run_id>/`:

- `traces/`
- `screenshots/`
- `videos/`
- `reports/manifest.json`
- `reports/junit.xml` (reservado para pipeline)

O `manifest.json` registra:
- artefatos produzidos
- eventos da execução
- trilha mínima da jornada

## Inventário funcional inicial

Arquivo canônico:
- `C:\GestaoVersus\app32\app32\tests\e2e\catalog\inventory.yaml`

Cobertura inicial da Sprint 1:
- autenticação
- seleção de empresa
- workspace `/my-work`
- entrada de reuniões `/meetings/`
- integrações `/api-mcp`
- canais `/channels`

Smoke mínimo da Sprint 1:
- login + chegada ao workspace
- contrato dos alvos de navegação críticos

Smoke supervisionado da Sprint 2:
- login real
- navegação real em `/my-work`
- redirecionamento real em `/meetings/`
- navegação real em `/api-mcp`
- navegação real em `/channels`

Modelagem funcional inicial da Sprint 2:
- `pages/workspace_page.py`
- `pages/meetings_page.py`
- `pages/integrations_page.py`
- `pages/channels_page.py`
- `pages/work_journey_page.py`
- `tasks/navigation_tasks.py`

Perfis de volume e concorrência:
- `data/profiles.py`
- `data/builders.py`
- `load/concurrency_profiles.py`
- `load/mcp_session_plan.py`
- `load/user_concurrency_harness.py`
- `load/mcp_concurrency_harness.py`
- `scripts/print_load_profiles.py`
- `scripts/run_user_concurrency_probe.py`
- `scripts/run_mcp_concurrency_probe.py`

Esses artefatos são a base para:
- alto volume de dados
- muitos usuários simultâneos
- múltiplas sessões MCP autenticadas em paralelo

CRUD inicial priorizado:
- `data/meeting_builders.py`
- `tasks/meetings_tasks.py`
- `journeys/crud/test_meetings_crud_contract.py`
- `journeys/crud/test_meetings_crud_e2e.py`
- `core/http_session.py`
- `scripts/run_meetings_devfull_crud.py`

CRUD adicional da Sprint 4:
- `data/work_journey_builders.py`
- `tasks/work_journey_tasks.py`
- `journeys/crud/test_work_journey_crud_contract.py`
- `journeys/crud/test_work_journey_crud_e2e.py`

Catálogo de suítes e execução supervisionada:
- `catalog/suite_catalog.py`
- `core/e2e_supervised_execution_service.py`
- tela no app32: `/qa/e2e`
- API: `/api/configs/qa/e2e/frontend-state`
- execuções supervisionadas: `/api/configs/qa/e2e/executions`
- detalhes/downloads de run: `/api/configs/qa/e2e/runs/<run_id>`
- manifesto: `/api/configs/qa/e2e/runs/<run_id>/manifest`
- backlog candidates: `/api/configs/qa/e2e/runs/<run_id>/backlog-candidates`
- sync de backlog: `/api/configs/qa/e2e/runs/<run_id>/backlog-sync`

Relatórios por jornada:
- cada jornada crítica registra `steps`, `artifacts`, `status`, `failed_step` e `failure_type`
- o manifesto consolidado continua em `reports/manifest.json`
- isso vale para smoke, CRUD, alto volume, multiusuário e sessões MCP concorrentes

Relatórios operacionais de volume/concorrência:
- `core/operational_report.py`
- `scripts/build_operational_load_reports.py`
- saída consolidada em JSON para:
  - volume de dados
  - multiusuário
  - concorrência MCP
  - filtros e relatórios críticos
- esses relatórios também entram como artefato no `manifest.json`

Probe de filtros e relatórios:
- `load/report_filter_volume_harness.py`
- `scripts/run_report_filter_volume_probe.py`

Probe de download e governança:
- `load/report_download_harness.py`
- `scripts/run_report_download_probe.py`
- `catalog/drift_detector.py`
- `catalog/drift_baseline.yaml`
- `scripts/run_drift_detection.py`
- `core/execution_history.py`
- `scripts/build_execution_diff.py`
- `core/failure_governance.py`
- `scripts/render_e2e_center_visual_audit.py`

## Cobertura reforçada para erros funcionais semelhantes

Fluxos especiais agora seguem um padrão comum:

- abrir a tela ou endpoint principal
- executar a ação principal do usuário
- validar ausência de erro público renderizado
- validar persistência/retorno funcional

Helper canônico:

- `core/functional_guards.py`

Fluxos já adaptados a esse padrão:

- `workspace_functional_probe`
- `meetings_functional_probe`
- `work_journey_functional_probe`
- `integrations_functional_probe`
- `reports_functional_probe`
- `financial_functional_probe`
- `processes_functional_probe` incluindo **save draft** do BPMN Modeler

## Pipeline oficial Sprint 5

Workflow canônico:
- `C:\GestaoVersus\app32\.github\workflows\e2e-governance.yml`

Gates principais:
- contrato do inventário e catálogo de suítes
- detector de drift funcional com baseline versionado
- histórico/diff entre execuções
- governança de falhas e candidatos de backlog
- UI/API da Central E2E

## Próximos passos imediatos

1. expandir baseline de drift à medida que novos domínios entrarem no catálogo
2. acoplar upload dos artefatos do workflow ao histórico operacional
3. ampliar downloads reais por módulo crítico
4. consolidar abertura automática de backlog a partir dos candidatos gerados

## Esteira oficial de completude

Documento canônico:
- `C:\GestaoVersus\app32\app32\docs\spec\esteira_oficial_completude_testes_e2e_v1.md`

Essa esteira formaliza que a suíte só evolui para completude real quando cobre:
- inventário de superfícies
- ação principal do usuário
- falha observável
- evidência técnica
- produção segura em `PROD_SAFE`

Também estabelece que erro real observado e ainda não coberto passa a alimentar a fila oficial de expansão da automação.

Backlog prático derivado:
- `C:\GestaoVersus\app32\app32\docs\playbooks\backlog_pratico_expansao_e2e_por_dominio_v1.md`

## Regra reforçada de autenticação em PROD_SAFE

A suíte não pode mais aceitar como sucesso um estado em que:

- a URL continue em `/login?next=...`
- a seleção de empresa permaneça em `/portal`
- o fluxo pós-login não chegue ao destino esperado

Para sessões HTTP, respostas não JSON na seleção de empresa agora devem falhar com diagnóstico explícito em vez de erro genérico de decode.

## Onda 1 — ações principais de workspace e integrations

Novos probes funcionais:

- `workspace_functional_probe`
  - filtros do My Work
  - listagem de atividades
  - exportação printável
- `integrations_functional_probe`
  - catálogo de integrações
  - fila de pedidos
  - página API / MCP

Esses probes agora falham explicitamente quando houver:

- redirect para `/login`
- HTML onde era esperado JSON
- mensagem pública de erro no conteúdo funcional

## Onda 1 — ações principais de meetings e work_journey

Novos probes funcionais:

- `meetings_functional_probe`
  - abertura autenticada de `/meetings/`
  - redirecionamento para `/meetings/company/<company_id>`
  - presença da ação principal `novaReuniao`
- `work_journey_functional_probe`
  - board da jornada
  - listagem de tarefas manuais
  - página principal `/companies/<company_id>/work-journey`

Esses probes falham explicitamente quando houver:

- redirect para `/login`
- erro público no HTML renderizado
- ausência da ação principal ou da região principal da tela
- payload funcional sem `success=true`

## Onda 2 — processes, BPMN, canvas e save assíncrono

Novo probe funcional:

- `processes_functional_probe`
  - lista de processos por empresa
  - detalhe do processo
  - abertura do BPMN Modeler
  - leitura do diagrama BPMN
  - save de rascunho em `DEV_FULL`

Esse probe falha explicitamente quando houver:

- redirect para `/login`
- erro público no modeler
- ausência do botão `Salvar rascunho`
- falha no payload do diagrama
- falha no save do rascunho em ambiente controlado

## Onda 3 — financial, reports e admin

Novos probes funcionais:

- `financial_functional_probe`
  - páginas principais do financeiro
  - exportações PDF/XLSX
- `reports_functional_probe`
  - relatório gerencial da jornada
  - exportação printável da jornada
  - print do workspace
- `admin_functional_probe`
  - leitura de parametrização
  - estado da Central E2E
  - save seguro de parametrização em `DEV_FULL`

Esses probes falham explicitamente quando houver:

- redirect para `/login`
- exportação com content-type incorreto
- payload administrativo inválido
- erro público em páginas ou relatórios

Runbook canônico:
- `C:\GestaoVersus\app32\app32\docs\runbooks\robot_e2e_aa_j18_sprint1_runbook.md`
- `C:\GestaoVersus\app32\app32\docs\runbooks\robot_e2e_aa_j18_sprint2_runbook.md`
- `C:\GestaoVersus\app32\app32\docs\runbooks\robot_e2e_aa_j18_sprint3_runbook.md`
- `C:\GestaoVersus\app32\app32\docs\runbooks\robot_e2e_aa_j18_sprint4_runbook.md`
- `C:\GestaoVersus\app32\app32\docs\runbooks\robot_e2e_aa_j18_sprint5_runbook.md`
- `C:\GestaoVersus\app32\app32\docs\runbooks\robot_e2e_aa_j18_sprint6_runbook.md`
- `C:\GestaoVersus\app32\app32\docs\harnesses\robot_e2e_operations_center_harness.md`

## Observações

- a seleção de empresa usa `data-portal-company-id`
- a rota de login usa `/login`
- os artefatos são gravados em `app32/tests/e2e/outputs/`
- `PROD_SAFE` não pode operar com `E2E_DESTRUCTIVE_ACTIONS_ALLOWED=true`
- a Central de Testes E2E no app32 fica em `/qa/e2e`
