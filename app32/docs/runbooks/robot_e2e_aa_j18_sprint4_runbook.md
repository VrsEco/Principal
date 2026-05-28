# Runbook — AA.J.18 Sprint 4

## Objetivo
Expandir a operação do robô E2E com:
- segundo domínio CRUD real
- execução supervisionada a partir da Central E2E
- catálogo de suítes por domínio e ambiente
- probe de filtros e relatórios críticos
- smokes recorrentes de `DEV_FULL` e `PROD_SAFE`

## Entradas
- `E2E_ENV_NAME`
- `E2E_BASE_URL`
- `E2E_USERNAME`
- `E2E_PASSWORD`
- `E2E_COMPANY_ID`

## Catálogo de suítes
- arquivo: `C:\GestaoVersus\app32\app32\tests\e2e\catalog\suite_catalog.py`
- tela: `/qa/e2e`
- API: `/api/configs/qa/e2e/frontend-state`

## Execução supervisionada
- listar execuções: `GET /api/configs/qa/e2e/executions`
- iniciar execução: `POST /api/configs/qa/e2e/executions`
- detalhe: `GET /api/configs/qa/e2e/executions/<execution_id>`

## Comandos principais
- `python app32/tests/e2e/scripts/run_report_filter_volume_probe.py`
- `python app32/tests/e2e/scripts/run_user_concurrency_probe.py`
- `python app32/tests/e2e/scripts/run_mcp_concurrency_probe.py`
- `python app32/tests/e2e/scripts/build_operational_load_reports.py`

## Readiness
- smoke real precisa gerar manifesto
- probes de concorrência precisam consolidar JSON operacional
- execuções supervisionadas só podem disparar suítes whitelisted
- `PROD_SAFE` continua sem destrutivo
