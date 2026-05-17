# Readiness Operacional para Abertura Controlada IA/MCP — APP32

Documento operacional da **AA.J.31.1345 — Organização IA/MCP - Grupo 09 - Consolidar readiness operacional para abertura controlada de uso IA/MCP**.

## Objetivo

Consolidar, em um artefato único e consultável, os gates mínimos para abrir o uso de IA/MCP no APP32 de forma **controlada**, preservando:

- runtime oficial;
- menor privilégio por perfil/surface;
- onboarding de agentes externos;
- checklist de release e smoke;
- monitoramento, freeze e rollback;
- coerência entre contratos MCP, catálogo e enforcement.

## Fonte canônica

- Manifesto: `src.intelligence.mcp_contracts.operational_readiness.APP32_OPERATIONAL_READINESS_MANIFEST`
- Tool MCP: `describe_app32_operational_readiness_tool`
- Registrador: `src.core.mcp_operational_readiness_tools.register_operational_readiness_tools`

## Artefatos que compõem a readiness

- `docs/governance/mcp_user_admin_production_runbook.md`
- `docs/governance/external_ai_mcp_onboarding_manual.md`
- `docs/governance/ai_mcp_release_smoke_checklist.md`
- `docs/governance/ai_mcp_tool_freeze_procedure.md`
- `docs/governance/ai_mcp_permission_matrix.md`
- `docs/governance/ai_mcp_usage_dashboard_spec.md`
- `tests/test_ai_mcp_contract_drift_suite.py`

## Fases obrigatórias

### 1. Contracts
- profiles, playbooks, permission matrix, catálogo e policy sem drift aberto;
- suíte de drift e contratos verde.

### 2. Release
- checklist oficial de release executado;
- deploy concluído;
- smoke pós-deploy validado;
- health do MCP HTTP remoto validado externamente.

### 3. Onboarding
- intake, desenho de acesso, registro e validação de IA externa prontos;
- discovery obrigatório ativo.

### 4. Operations
- dashboard/relatório disponível;
- procedimento de freeze e rollback conhecido;
- surfaces monitoráveis por operação.

### 5. Go-live
- abertura apenas controlada:
  - homologação interna;
  - piloto;
  - uso assistido.

## Smokes obrigatórios

Resultado esperado:

```text
MCP_USER_ADMIN_RUNBOOK_SMOKE_OK True True
AI_MCP_RELEASE_CHECKLIST_OK 7 3
AI_MCP_TOOL_FREEZE_OK 7 4
AI_MCP_EXTERNAL_ONBOARDING_OK 4 5
AI_MCP_CONTRACT_DRIFT_SUITE_OK 6 True
AI_MCP_OPERATIONAL_READINESS_OK 5 5
```

## Critérios de abertura controlada

- usar somente surfaces e perfis já canonizados;
- exigir `company_id` explícito quando o contrato exigir;
- bloquear liberação irrestrita enquanto houver drift aberto;
- congelar tool ao primeiro sinal de risco cross-tenant/RBAC;
- manter rollback validado;
- validar o caminho canônico do Claude em **Claude Code / aba Code**.

## Condições de bloqueio

- drift entre contrato, catálogo e policy;
- smoke pós-deploy falhando;
- tool sensível sem freeze/rollback operacionalizado;
- risco cross-tenant;
- abertura geral sem onboarding e readiness documental;
- regressão no runtime MCP HTTP (ex.: `502`, listener morto, bootstrap FastMCP quebrado).

## Lições aprendidas incorporadas à readiness

- `surface=user` deve ser **permission-aware** e refletir a permissão real da senha do APP32;
- health `200` em `/mcp/healthz` é gate mínimo obrigatório, não opcional;
- wrappers MCP precisam preservar assinatura tipada para não quebrar o bootstrap do FastMCP;
- Claude Chat e Claude Code são superfícies diferentes e não devem ser misturados no onboarding canônico.

## Uso via MCP

```text
describe_app32_operational_readiness_tool()
describe_app32_operational_readiness_tool(phase='release')
describe_app32_operational_readiness_tool(gate_id='controlled_go_live')
```

## Smoke pós-deploy

```powershell
python -c "import app; from src.intelligence.mcp_contracts import APP32_OPERATIONAL_READINESS_MANIFEST; print('AI_MCP_OPERATIONAL_READINESS_OK', len(APP32_OPERATIONAL_READINESS_MANIFEST.gates), len(APP32_OPERATIONAL_READINESS_MANIFEST.required_smokes))"
```

Resultado esperado:

```text
AI_MCP_OPERATIONAL_READINESS_OK 5 5
```
