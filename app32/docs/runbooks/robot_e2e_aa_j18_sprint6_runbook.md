# Runbook — AA.J.18 Sprint 6

## Objetivo
Expandir a Central E2E com:
- histórico e diff entre execuções
- download direto de manifesto e artefatos
- candidatos de backlog e sync assistido
- filtros operacionais por ambiente, suíte e status
- auditoria visual supervisionada

## Entradas
- `E2E_ENV_NAME`
- `E2E_BASE_URL`
- `E2E_USERNAME`
- `E2E_PASSWORD`
- `E2E_COMPANY_ID`

## Endpoints principais
- tela: `/qa/e2e`
- frontend state: `/api/configs/qa/e2e/frontend-state`
- detalhe do run: `/api/configs/qa/e2e/runs/<run_id>`
- manifesto: `/api/configs/qa/e2e/runs/<run_id>/manifest`
- backlog candidates: `/api/configs/qa/e2e/runs/<run_id>/backlog-candidates`
- sync backlog: `POST /api/configs/qa/e2e/runs/<run_id>/backlog-sync`

## Scripts principais
- `python app32/tests/e2e/scripts/build_execution_diff.py`
- `python app32/tests/e2e/scripts/run_drift_detection.py`
- `python app32/tests/e2e/scripts/render_e2e_center_visual_audit.py`

## Readiness
- diff precisa estar disponível na Central
- runs precisam expor manifesto e primeiro artefato por download
- falhas precisam gerar `backlog_candidates.json`
- auditoria visual precisa gerar HTML e screenshot em `outputs/visual_audit/`
