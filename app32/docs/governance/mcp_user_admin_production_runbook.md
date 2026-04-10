# Runbook de Produção MCP User/Admin — APP32

Documento operacional da **AA.J.31.1321 — Organização IA/MCP - Grupo 07 - Criar runbook de produção MCP user/admin**.

## 1. Objetivo

Padronizar como agentes de IA e operadores técnicos devem publicar, validar, monitorar e congelar as surfaces MCP **user** e **admin** do APP32 em produção, preservando:

- isolamento multi-tenant por `company_id`;
- menor privilégio por perfil e surface;
- descoberta obrigatória de capabilities antes da execução;
- trilha auditável para mutações;
- compatibilidade com o runtime oficial do Sapiens.

## 2. Fontes canônicas

| Tema | Fonte |
|---|---|
| Catálogo único MCP/Sapiens | `src.intelligence.tool_catalog.catalog` |
| Registry de surfaces | `src.core.mcp_surface_registry` |
| Contratos por perfil | `src.intelligence.mcp_contracts.profiles` |
| Playbooks por surface | `src.intelligence.mcp_contracts.playbooks` |
| Playbooks por domínio | `src.intelligence.mcp_contracts.domain_playbooks` |
| Contratos CRUD | `src.intelligence.mcp_contracts.crud_domains` |
| Política RBAC/tool | `src.intelligence.security.tool_policy` |
| Runtime oficial | `src.intelligence.execution.run_agent_with_context` |

Fluxo oficial de runtime:

```text
execution -> menu_engine -> work_agents.graph -> tool_catalog
```

## 3. Surfaces cobertas

### 3.1 MCP User

Uso pretendido:

- colaborador, cliente e administrador em fluxos operacionais de menor privilégio;
- domínios permitidos: `routine`, `projects`, `meetings`, `strategy`;
- escopo padrão: empresa ativa (`active_company`);
- descoberta inicial: `list_user_app32_capabilities` e `describe_app32_crud_contracts_tool`.

Proibições:

- não acessar tools exclusivas de `admin`, `analytics` ou `ops`;
- não executar mutações financeiras sensíveis;
- não inferir `company_id` por nome parcial de empresa;
- não usar SQL livre.

### 3.2 MCP Admin

Uso pretendido:

- administrador e admin técnico em ações administrativas explícitas;
- domínios permitidos: `routine`, `projects`, `meetings`, `finance`, `strategy`, `governance`;
- escopo padrão: `company_id` explícito;
- descoberta inicial: `list_admin_app32_capabilities`, `describe_app32_profile_contracts_tool`, `describe_app32_crud_contracts_tool`.

Proibições:

- não assumir acesso global quando o contrato exigir escopo explícito;
- não usar admin para leitura analítica quando a surface `analytics` for suficiente;
- não elevar perfil ou permissão sem contrato e confirmação;
- não contornar gates humanos em risco `high` ou `critical`.

## 4. Checklist pré-release

Antes de publicar mudança MCP user/admin:

1. Confirmar que o runtime oficial continua apontando para:
   - `src.intelligence.execution.run_agent_with_context`;
   - `src.intelligence.menu_engine.handle_menu_message`;
   - `src.intelligence.work_agents.graph.create_work_agent_workflow`;
   - `src.intelligence.tool_catalog.catalog`.
2. Executar testes de contracts/smoke:
   - `tests/test_core_mcp_surface_registry.py`;
   - `tests/test_core_mcp_server_entrypoint.py`;
   - `tests/test_mcp_profile_contracts.py`;
   - `tests/test_mcp_surface_playbooks.py`;
   - `tests/test_mcp_domain_playbooks.py`;
   - `tests/test_official_runtime_smoke.py`;
   - `tests/test_tool_catalog_capabilities.py`.
3. Verificar que `user` não expõe `finance`.
4. Verificar que `admin` exige `company_id` explícito para ações sensíveis.
5. Verificar que discovery tools estão registradas para ambas as surfaces.
6. Confirmar que nenhuma nova tool ignora `company_id`, RBAC ou política de risco.

## 5. Smoke pós-deploy

Executar após deploy:

```powershell
python -c "import app; from src.core.mcp_surface_registry import get_surface_manifest; print('MCP_USER_ADMIN_RUNBOOK_SMOKE_OK', bool(get_surface_manifest('user')), bool(get_surface_manifest('admin')))"
```

Resultado esperado:

```text
MCP_USER_ADMIN_RUNBOOK_SMOKE_OK True True
```

Validações mínimas em produção:

- `get_surface_manifest('user')` retorna manifesto não vazio;
- `get_surface_manifest('admin')` retorna manifesto não vazio;
- `describe_app32_surface_playbooks_tool` segue disponível via registradores compartilhados;
- `describe_app32_domain_playbooks_tool` segue disponível via registradores compartilhados;
- import de `app` e registry MCP não falha após migrations/restart uWSGI.

## 6. Fluxo operacional de agente externo

### 6.1 Fluxo user

1. Descobrir surface: `list_user_app32_capabilities`.
2. Consultar playbook da surface: `describe_app32_surface_playbooks_tool(surface='user')`.
3. Consultar playbook do domínio: `describe_app32_domain_playbooks_tool(domain='<domínio>')`.
4. Consultar contrato CRUD quando houver mutação: `describe_app32_crud_contracts_tool`.
5. Validar `company_id` ativo.
6. Executar tool operacional permitida.
7. Responder com ação executada, filtros, IDs e pendências.

### 6.2 Fluxo admin

1. Descobrir surface: `list_admin_app32_capabilities`.
2. Consultar perfil: `describe_app32_profile_contracts_tool(profile='<perfil>')`.
3. Consultar playbook da surface: `describe_app32_surface_playbooks_tool(surface='admin')`.
4. Consultar playbook do domínio: `describe_app32_domain_playbooks_tool(domain='<domínio>')`.
5. Exigir `company_id` explícito.
6. Classificar risco da operação.
7. Para risco `high` ou `critical`, registrar intenção e pedir confirmação humana.
8. Executar tool somente se contrato e perfil permitirem.
9. Responder com trilha de decisão, parâmetros, resultado e próximo passo.

## 7. Critérios de congelamento de tool

Congelar uma tool user/admin quando qualquer condição ocorrer:

- evidência ou suspeita de vazamento cross-tenant;
- execução sem `company_id` quando obrigatório;
- mutação financeira acessível pela surface `user`;
- bypass de RBAC/profile/surface;
- erro 500 recorrente após chamada MCP;
- divergência entre capability manifest e contrato CRUD;
- retorno de dados sensíveis não previstos pelo domínio.

Procedimento de congelamento:

1. Remover ou bloquear a capability no catálogo/registrador aplicável.
2. Registrar atividade de incidente no AA.J.31 ou backlog de segurança.
3. Executar suíte MCP afetada.
4. Realizar deploy e smoke pós-deploy.
5. Reabilitar apenas com teste de regressão e evidência de correção.

## 8. Rollback

Se o deploy quebrar surfaces user/admin:

1. Interromper evolução de novas tools MCP.
2. Reverter o commit ou desabilitar o registrador/capability afetado.
3. Executar:
   - import de `app`;
   - smoke de `get_surface_manifest('user')`;
   - smoke de `get_surface_manifest('admin')`.
4. Confirmar que o runtime oficial Sapiens ainda compila.
5. Registrar evidência de rollback e causa raiz.

## 9. Gates de aceite

A surface MCP user/admin só deve ser considerada apta quando:

- testes de contracts e smoke passam;
- deploy conclui sem erro de migration/restart;
- smoke pós-deploy retorna `MCP_USER_ADMIN_RUNBOOK_SMOKE_OK True True`;
- não há rota alternativa usando runtime legado;
- não há acesso user a `finance`;
- ações admin sensíveis exigem `company_id` e confirmação quando aplicável.
