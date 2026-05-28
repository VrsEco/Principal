# Runbook — Robô E2E `AA.J.18` Sprint 2

## Classe
Runbook

## Objetivo
Operar a expansão da suíte E2E para navegação real supervisionada, CRUD inicial por domínio e preparação para alto volume, concorrência multiusuário e múltiplas sessões MCP.

## Escopo da Sprint 2
- smoke browser real em módulos críticos
- page objects e task objects iniciais
- builders e perfis de massa controlada
- CRUD inicial no domínio `meetings`
- relatório de falha por jornada
- perfis de volume e concorrência

## Artefatos principais
- `app32/tests/e2e/pages/`
- `app32/tests/e2e/tasks/`
- `app32/tests/e2e/journeys/smoke/`
- `app32/tests/e2e/journeys/crud/`
- `app32/tests/e2e/data/profiles.py`
- `app32/tests/e2e/load/concurrency_profiles.py`
- `app32/tests/e2e/load/mcp_session_plan.py`

## Comandos principais
### Contratos e fundação atual
```bash
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
pytest app32/tests/e2e/test_execution_contract.py app32/tests/e2e/test_tenant_context.py app32/tests/e2e/test_evidence_collection.py app32/tests/e2e/test_inventory_contract.py app32/tests/e2e/test_journey_report.py app32/tests/e2e/journeys/smoke/test_navigation_targets.py -q
```

### Smoke supervisionado real
```bash
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
pytest app32/tests/e2e/journeys/smoke/test_real_navigation_smoke.py -q
```

### CRUD inicial de meetings
```bash
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
pytest app32/tests/e2e/journeys/crud/test_meetings_crud_contract.py app32/tests/e2e/journeys/crud/test_meetings_crud_e2e.py -q
```

### Perfis de volume e concorrência
```bash
python app32/tests/e2e/scripts/print_load_profiles.py
```

## Critérios de expansão por domínio
Um domínio novo só entra quando tiver:
1. page object com seletor de prontidão estável
2. task object com rotas/ações mínimas
3. builder de massa dedicado se houver mutação
4. jornada smoke ou CRUD associada ao inventário
5. evidência por jornada com `failed_step` e `failure_type`
6. validação explícita de `company_id`

## Critérios para alto volume
- usar perfis `large` e `huge` somente em ambiente controlado
- manter `run_marker` e `company_id` explícitos
- registrar perfil usado no metadata da jornada
- validar paginação, filtro, renderização e emissão de relatório

## Critérios para multiusuário e MCP concorrente
- autenticação por sessão isolada
- contexto explícito de `company_id`
- sem compartilhamento de storage state entre usuários diferentes
- validar ausência de tenant crossing
- registrar `user_label`, surface e perfil de concorrência no relatório da jornada

## Próximos passos
1. fechar documentação executiva da Sprint 2
2. conectar o CRUD de meetings ao backend real DEV_FULL
3. ampliar smoke real para `/channels`
4. iniciar harness real de concorrência multiusuário
5. iniciar harness real de concorrência MCP
