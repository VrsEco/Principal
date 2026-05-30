# Runbook — Robô E2E `AA.J.18` Sprint 1

## Classe
Runbook

## Objetivo
Operar a fundação inicial do robô E2E do Gestão Versus em `DEV_FULL` e `PROD_SAFE`.

## Escopo atual
- contrato de ambientes
- autenticação real
- seleção de tenant
- persistência de `storage_state.json`
- manifesto de evidências
- smoke mínimo por contrato

## Entradas obrigatórias
- `E2E_ENV_NAME`
- `E2E_BASE_URL`
- `E2E_USERNAME`
- `E2E_PASSWORD`
- `E2E_COMPANY_ID`

## Perfis
### `DEV_FULL`
- destrutivo permitido
- usar apenas clone local/homologação/laboratório

### `PROD_SAFE`
- destrutivo proibido
- usar tenant isolado
- não operar sem `company_id` explícito

## Comandos principais
### Inspecionar configuração efetiva
```bash
python app32/tests/e2e/scripts/print_effective_config.py
```

### Gerar sessão autenticada reutilizável
```bash
python app32/tests/e2e/scripts/bootstrap_auth_state.py
```

### Rodar smoke base
```bash
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
pytest app32/tests/e2e/journeys/smoke/test_login_and_navigation.py -q
```

### Rodar contratos da fundação
```bash
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
pytest app32/tests/e2e/test_execution_contract.py app32/tests/e2e/test_tenant_context.py app32/tests/e2e/test_evidence_collection.py app32/tests/e2e/test_inventory_contract.py app32/tests/e2e/journeys/smoke/test_navigation_targets.py -q
```

## Saídas esperadas
- `app32/tests/e2e/outputs/<modo>/<run_id>/traces/`
- `app32/tests/e2e/outputs/<modo>/<run_id>/screenshots/`
- `app32/tests/e2e/outputs/<modo>/<run_id>/videos/`
- `app32/tests/e2e/outputs/<modo>/<run_id>/reports/manifest.json`

## Smoke mínimo da Sprint 1
- login `/login`
- seleção de empresa `/portal`
- workspace `/my-work`
- contratos de navegação para `/meetings/` e `/api-mcp`

## Próximos passos
1. fechar a documentação final curta da Sprint 1
2. ampliar smoke para navegação real supervisionada
3. iniciar CRUD por domínio
4. desenhar a Central de Testes E2E no app32 (`AA.J.18.13`)
