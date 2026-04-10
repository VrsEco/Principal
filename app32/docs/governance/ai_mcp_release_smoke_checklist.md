# Checklist de Release e Smoke Pós-Deploy IA/MCP — APP32

Documento operacional da **AA.J.31.1323 — Organização IA/MCP - Grupo 07 - Criar checklist de release e smoke pós-deploy IA/MCP**.

## 1. Objetivo

Criar um checklist executável e consultável via MCP para releases de IA/MCP no APP32, garantindo que alterações em Sapiens, MCP, tools, playbooks, analytics e superfícies de acesso só sejam encerradas com:

- testes de contrato passando;
- runtime oficial validado;
- boundaries de surface/perfil preservadas;
- deploy executado pelo fluxo oficial;
- smoke pós-deploy com marcador objetivo;
- rollback conhecido caso qualquer gate falhe.

## 2. Fonte canônica

- Manifesto: `src.intelligence.mcp_contracts.release_checklist.APP32_RELEASE_CHECKLIST_MANIFEST`
- Tool MCP: `describe_app32_release_checklist_tool`
- Registrador: `src.core.mcp_release_checklist_tools.register_release_checklist_tools`
- Catálogo: `src.intelligence.tool_catalog.catalog`

## 3. Gates obrigatórios

### 3.1 Pré-release

Executar antes do deploy:

```powershell
python -m pytest -q tests/test_mcp_* tests/test_core_mcp_* tests/test_official_runtime_smoke.py
python -m pytest -q tests/test_intelligence_runtime_classification.py tests/test_intelligence_runtime_guard.py
python -m pytest -q tests/test_core_mcp_surface_registry.py tests/test_mcp_surface_playbooks.py tests/test_mcp_profile_contracts.py
```

Evidência esperada:

- testes verdes;
- runtime oficial aponta para `execution -> menu_engine -> work_agents.graph -> tool_catalog`;
- legados continuam `allowed_for_new_work=False`;
- surface `user` sem `finance`;
- `admin` com escopo explícito;
- `analytics` sem mutação;
- `ops` restrita.

### 3.2 Deploy

Executar o deploy oficial:

```powershell
python C:\GestaoVersus\app32\scripts\elite_deploy_v3.py
```

Evidência esperada:

- código atualizado;
- dependências em conformidade;
- migrations aplicadas/verificadas;
- uWSGI reiniciado;
- sem erro crítico.

### 3.3 Pós-deploy

Executar smokes:

```powershell
python -c "import app; from src.intelligence.work_agents.graph import create_work_agent_workflow; print('AI_MCP_RELEASE_RUNTIME_OK', hasattr(create_work_agent_workflow(),'invoke'))"
python -c "import app; from src.core.mcp_surface_registry import get_surface_manifest; print('AI_MCP_RELEASE_SURFACES_OK', all(bool(get_surface_manifest(s)) for s in ['user','admin','analytics','ops']))"
python -c "import app; from src.intelligence.mcp_contracts import APP32_RELEASE_CHECKLIST_MANIFEST; print('AI_MCP_RELEASE_CHECKLIST_OK', len(APP32_RELEASE_CHECKLIST_MANIFEST.checklist), len(APP32_RELEASE_CHECKLIST_MANIFEST.smokes))"
```

Resultado esperado:

```text
AI_MCP_RELEASE_RUNTIME_OK True
AI_MCP_RELEASE_SURFACES_OK True
AI_MCP_RELEASE_CHECKLIST_OK 7 3
```

### 3.4 Rollback

Preparar rollback se:

- import do `app` falhar;
- runtime oficial não compilar;
- surface manifest falhar;
- boundary user/admin/analytics/ops for violada;
- erro 500 recorrente surgir em tool MCP afetada;
- houver evento crítico de tenant/security relacionado à release.

Procedimento:

1. Reverter commit ou congelar registrador/capability afetado.
2. Redeploy pelo fluxo oficial.
3. Reexecutar smokes pós-deploy.
4. Registrar evidência e causa raiz.

## 4. Uso via MCP

Para consultar checklist completo:

```text
describe_app32_release_checklist_tool()
```

Para consultar por gate:

```text
describe_app32_release_checklist_tool(gate='pre_release')
describe_app32_release_checklist_tool(gate='deploy')
describe_app32_release_checklist_tool(gate='post_deploy')
describe_app32_release_checklist_tool(gate='rollback')
```

Para consultar smoke específico:

```text
describe_app32_release_checklist_tool(smoke_id='official_runtime_import')
describe_app32_release_checklist_tool(smoke_id='mcp_surface_manifest')
describe_app32_release_checklist_tool(smoke_id='release_checklist_manifest')
```

## 5. Critérios de aceite

Uma release IA/MCP só pode ser encerrada quando:

- todos os checks `high` e `critical` passaram;
- o deploy oficial foi concluído;
- os três smokes pós-deploy retornaram os marcadores esperados;
- evidência foi registrada em arquivo de resultado;
- não há risco aberto de cross-tenant, bypass RBAC ou runtime legado não protegido.
