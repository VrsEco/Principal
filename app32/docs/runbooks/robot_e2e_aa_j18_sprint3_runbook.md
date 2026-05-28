# Runbook — AA.J.18 Sprint 3

## Objetivo
Operar a suíte E2E com:
- CRUD real em `DEV_FULL`
- smoke real ampliado
- concorrência multiusuário
- concorrência MCP autenticada
- central operacional inicial no app32

## Entradas
- `E2E_ENV_NAME`
- `E2E_BASE_URL`
- `E2E_USERNAME`
- `E2E_PASSWORD`
- `E2E_COMPANY_ID`

## Comandos principais
- `python app32/tests/e2e/scripts/run_meetings_devfull_crud.py`
- `python app32/tests/e2e/scripts/run_user_concurrency_probe.py`
- `python app32/tests/e2e/scripts/run_mcp_concurrency_probe.py`
- `python app32/tests/e2e/scripts/build_operational_load_reports.py`

## UI operacional
- tela inicial: `/qa/e2e`
- estado frontend: `/api/configs/qa/e2e/frontend-state`

## Saídas esperadas
- `manifest.json`
- relatórios operacionais em JSON
- trilhas por jornada
- visão consolidada na Central de Testes E2E
