# Runbook — AA.J.18 Sprint 5

## Objetivo
Industrializar o robô E2E com:
- cobertura crítica adicional
- downloads e relatórios emitidos
- detector de drift funcional
- diff entre execuções
- classificação de falhas e candidatos de backlog
- pipeline oficial com gates de cobertura

## Entradas
- `E2E_ENV_NAME`
- `E2E_BASE_URL`
- `E2E_USERNAME`
- `E2E_PASSWORD`
- `E2E_COMPANY_ID`

## Comandos principais
- `python app32/tests/e2e/scripts/run_report_download_probe.py`
- `python app32/tests/e2e/scripts/run_drift_detection.py`
- `python app32/tests/e2e/scripts/build_execution_diff.py`
- `python app32/tests/e2e/scripts/build_operational_load_reports.py`

## Governança de drift
- inventário canônico: `C:\GestaoVersuspp32pp32	ests\e2e\catalog\inventory.yaml`
- baseline aceito: `C:\GestaoVersuspp32pp32	ests\e2e\catalog\drift_baseline.yaml`
- o gate falha quando surgir rota crítica nova fora do inventário e fora do baseline versionado

## Histórico e falhas
- diff entre execuções: `C:\GestaoVersuspp32pp32	ests\e2e\core\execution_history.py`
- governança de falhas: `C:\GestaoVersuspp32pp32	ests\e2e\coreailure_governance.py`
- a Central E2E continua em `/qa/e2e`

## Pipeline oficial
- workflow: `C:\GestaoVersuspp32\.github\workflows\e2e-governance.yml`
- gatilhos: `pull_request`, `workflow_dispatch`
- gates:
  - inventário/catálogo
  - drift funcional
  - histórico/diff
  - governança de falhas
  - Central E2E

## Readiness
- `run_drift_detection.py` precisa retornar `aligned`
- candidatos de backlog precisam ser gerados a partir do manifesto quando houver falha
- downloads críticos precisam registrar `content_type`, `status_code` e tamanho da resposta
- pipeline oficial não pode liberar merge se os gates de cobertura falharem
