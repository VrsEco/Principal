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
- a rota de login usa `/auth/login`
- os artefatos são gravados em `app32/tests/e2e/outputs/`
- `PROD_SAFE` não pode operar com `E2E_DESTRUCTIVE_ACTIONS_ALLOWED=true`
- a Central de Testes E2E no app32 fica em `/qa/e2e`
