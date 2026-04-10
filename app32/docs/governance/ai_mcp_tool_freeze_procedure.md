# Procedimento de Congelamento de Tool Insegura IA/MCP — APP32

Documento operacional da **AA.J.31.1324 — Organização IA/MCP - Grupo 07 - Definir procedimento de congelamento de tool insegura**.

## Fonte canônica

- Manifesto: `src.intelligence.mcp_contracts.tool_freeze.APP32_TOOL_FREEZE_MANIFEST`
- Tool MCP: `describe_app32_tool_freeze_procedure_tool`
- Registrador: `src.core.mcp_tool_freeze_tools.register_tool_freeze_tools`

## Quando congelar

Congelar imediatamente a tool quando houver:

- `cross_tenant_risk`: suspeita/evidência de vazamento entre empresas;
- `rbac_bypass`: acesso por perfil/surface sem permissão;
- `unsafe_mutation`: mutação sem `company_id`, contrato ou confirmação;
- `financial_exposure`: exposição financeira ou mutação financeira pela `user`;
- `secret_exposure`: token, senha, cookie ou segredo em payload/metadata;
- `runtime_error`: erro 500 recorrente causado por tool alterada;
- `catalog_contract_drift`: divergência entre catálogo, contrato, playbook e policy.

## Procedimento de congelamento

1. Identificar `tool_name`, capability, domínio, surface, `company_id`, `user_id` e `trace_id`.
2. Classificar trigger e severidade.
3. Desabilitar capability, remover scope de surface ou forçar `human_gate`.
4. Executar testes IA/MCP impactados.
5. Fazer deploy oficial.
6. Executar smokes obrigatórios:
   - `AI_MCP_RELEASE_RUNTIME_OK True`;
   - `AI_MCP_RELEASE_SURFACES_OK True`;
   - `AI_MCP_RELEASE_CHECKLIST_OK 7 3`.
7. Registrar evidência no board/arquivo de resultado.

## Procedimento de descongelamento

1. Corrigir causa raiz.
2. Adicionar teste que reproduz e protege contra regressão.
3. Revisar multi-tenancy, RBAC, surface, domínio, risco e gate humano.
4. Reabilitar capability/scope.
5. Redeploy e smokes pós-deploy.
6. Registrar evidência de reabilitação segura.

## Critério de bloqueio

Nenhuma tool congelada pode ser reabilitada enquanto houver:

- risco cross-tenant aberto;
- teste de política falhando;
- contrato MCP divergente;
- smoke pós-deploy falhando;
- ausência de evidência de causa raiz.

## Uso via MCP

```text
describe_app32_tool_freeze_procedure_tool()
describe_app32_tool_freeze_procedure_tool(trigger='cross_tenant_risk')
```

## Smoke pós-deploy

```powershell
python -c "import app; from src.intelligence.mcp_contracts import APP32_TOOL_FREEZE_MANIFEST; print('AI_MCP_TOOL_FREEZE_OK', len(APP32_TOOL_FREEZE_MANIFEST.triggers), len(APP32_TOOL_FREEZE_MANIFEST.freeze_steps))"
```

Resultado esperado:

```text
AI_MCP_TOOL_FREEZE_OK 7 4
```
