# Matriz Canônica de Permissões IA/MCP por Perfil

A atividade **AA.J.31.1328** consolida a matriz canônica de permissões por perfil para uso de IA/MCP no APP32.

## Objetivo

Formalizar, em um artefato único e consultável, **o que cada perfil pode descobrir, ler, criar, atualizar, excluir, analisar e auditar** por surface MCP.

## Fonte canônica

- manifesto: `APP32_PERMISSION_MATRIX_MANIFEST`
- contrato Python: `src.intelligence.mcp_contracts.permission_matrix`
- tool MCP: `describe_app32_permission_matrix_tool`

## Perfis cobertos

Perfis principais:
- `colaborador`
- `cliente`
- `administrador`

Extensão técnica necessária para a arquitetura atual:
- `admin_tecnico`

## Superfícies cobertas

- `user`
- `admin`
- `analytics`
- `ops`

## Princípios da matriz

1. `tenant_scope_required=True` em toda a matriz.
2. SQL livre é proibido.
3. A matriz não substitui a `tool_policy`; ela **consolida governança**.
4. A decisão operacional final continua dependendo de:
   - tenant válido
   - surface permitida
   - domínio permitido
   - tool presente no manifest da surface
   - policy de risco/confirmacão

## Regras de alto nível

### Colaborador
- somente `user`
- sem finanças
- sem governança/admin/ops
- pode operar rotina, projetos e reuniões
- estratégia restrita a leitura/análise

### Cliente
- somente `user`
- leitura guiada
- sem mutações
- sem finanças/governança/admin/ops

### Administrador
- `user`, `admin`, `analytics`
- sem `ops`
- finanças somente em `admin` e `analytics`
- `analytics` permanece read-only
- `admin` exige `company_id` explícito

### Admin técnico
- `admin`, `analytics`, `ops`
- responsável por incidentes, diagnóstico técnico e intervenções auditáveis
- `ops` é exclusivo deste perfil

## Regras críticas por domínio

### Finanças
- sem surface `user`
- `company_id` explícito obrigatório
- mutações exigem gate humano
- sem SQL livre

### Analytics
- somente leitura/análise
- nunca mutar dados
- exige escopo explícito quando aplicável

### Operations
- exclusivo de `admin_tecnico`
- toda intervenção deve preservar trilha auditável

## Uso via MCP

### Manifesto completo
- `describe_app32_permission_matrix_tool()`

### Filtrar por perfil
- `describe_app32_permission_matrix_tool(profile="colaborador")`
- `describe_app32_permission_matrix_tool(profile="cliente")`
- `describe_app32_permission_matrix_tool(profile="administrador")`
- `describe_app32_permission_matrix_tool(profile="admin_tecnico")`

### Filtrar por surface
- `describe_app32_permission_matrix_tool(surface="user")`
- `describe_app32_permission_matrix_tool(surface="admin")`
- `describe_app32_permission_matrix_tool(surface="analytics")`
- `describe_app32_permission_matrix_tool(surface="ops")`

## Relação com contratos já existentes

A matriz consolida e cruza:

- `APP32_PROFILE_CONTRACTS_MANIFEST`
- `APP32_SURFACE_PLAYBOOKS_MANIFEST`
- `APP32_DOMAIN_PLAYBOOKS_MANIFEST`
- `evaluate_tool_policy(...)`
- `get_surface_manifest(...)`

## Smoke pós-deploy

Referência esperada:
- `AI_MCP_PERMISSION_MATRIX_OK 7 4`

Interpretação:
- `7` matrizes profile/surface publicadas
- `4` surfaces cobertas


## Drifts conhecidos preservados como observação

A 1328 consolida a matriz com base no canon atual, mas registra drifts que devem virar evolução posterior:

- `finance` ainda aparece mais permissivo em `src.intelligence.security.tenant_rbac` do que nos contratos MCP canônicos.
- `identity` possui exceções de self-service em capabilities `user`, embora o playbook de domínio privilegie `admin`/`ops`.
- `workload` aparece na surface analytics, mas não está formalizado em todos os contratos de perfil; por isso não foi promovido nesta matriz canônica.

## Observação arquitetural

A matriz foi mantida **declarativa e auditável**. Ela serve para:
- onboarding de agentes externos;
- runbooks de operação;
- alinhamento de produto e engenharia;
- validação futura de perfis customizados.
