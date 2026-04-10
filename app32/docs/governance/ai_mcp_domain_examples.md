# Exemplos Oficiais de Fluxos IA/MCP por Domínio

A atividade **AA.J.31.1326** consolida um catálogo canônico de exemplos oficiais de fluxos MCP do APP32 para os domínios **Rotina**, **Estratégia** e **Finanças**.

## Objetivo

Dar às IAs/agentes um artefato único, consultável via MCP, mostrando **como interagir com o APP32** sem misturar conceitos de surface, domínio, contrato CRUD e análise permitida.

## Fonte canônica

- manifesto: `APP32_DOMAIN_EXAMPLES_MANIFEST`
- contrato Python: `src.intelligence.mcp_contracts.domain_examples`
- tool MCP: `describe_app32_domain_examples_tool`

## Regras obrigatórias

1. Todo exemplo é **tenant-safe** e exige `tenant_scope_required=True`.
2. Todo exemplo referencia, no mínimo:
   - `src.intelligence.mcp_contracts.domain_playbooks`
   - `src.intelligence.mcp_contracts.crud_domains`
3. SQL livre é proibido.
4. Finanças só pode aparecer em `admin` ou `analytics`.
5. Fluxos financeiros exigem `company_id` explícito.
6. Mutações financeiras exigem **gate humano**.
7. Estratégia analítica usa `strategy_plan_diagnostics` como análise canônica.

## Domínios cobertos

### 1. Rotina
Exemplos oficiais:
- `routine_create_work_item`
- `routine_list_processes`

Padrão esperado:
- surface principal: `user`
- escopo: `active_company`
- descoberta antes da execução
- validação do contrato CRUD antes da mutação

### 2. Estratégia
Exemplos oficiais:
- `strategy_plan_diagnostics_analysis`
- `strategy_analysis_to_mutation_redirect`

Padrão esperado:
- análise via `analytics`
- mutação via `admin`
- evidências e limitações explícitas
- separação entre insight e ação operacional

### 3. Finanças
Exemplos oficiais:
- `finance_cash_commitments_analysis`
- `finance_mutation_requires_gate`

Padrão esperado:
- surface: `analytics` ou `admin`
- somente `administrador` e `admin_tecnico`
- `company_id` explícito
- sem SQL livre
- gate humano para mutação e para leituras sensíveis quando a política exigir

## Uso via MCP

### Manifesto completo
- `describe_app32_domain_examples_tool()`

### Exemplos de um domínio
- `describe_app32_domain_examples_tool(domain="routine")`
- `describe_app32_domain_examples_tool(domain="strategy")`
- `describe_app32_domain_examples_tool(domain="finance")`

### Exemplo específico
- `describe_app32_domain_examples_tool(example_id="finance_mutation_requires_gate")`

## Smoke pós-deploy

Referência de validação esperada:

- `AI_MCP_DOMAIN_EXAMPLES_OK 6 3`

Interpretação:
- `6` exemplos oficiais cadastrados
- `3` domínios cobertos (`routine`, `strategy`, `finance`)

## Integração com o restante da estratégia IA/MCP

Este catálogo **não executa** fluxos reais por conta própria. Ele funciona como camada declarativa e auditável para orientar:

- Sapiens
- agentes externos via MCP
- onboarding de providers externos
- governança de prompts/playbooks
- futuras simulações/harnesses controlados

## Relações canônicas

- playbooks por domínio: `describe_app32_domain_playbooks_tool`
- contratos CRUD: `describe_app32_crud_contracts_tool`
- catálogo de análises permitidas: `describe_app32_allowed_analyses_tool`
- contratos de perfil: `describe_app32_profile_contracts_tool`
- onboarding de IA externa: `describe_app32_external_ai_onboarding_tool`

## Proibições explícitas

- Não usar esses exemplos para autorizar acesso fora do perfil/surface real.
- Não tratar exemplo como bypass de contrato CRUD.
- Não liberar SQL livre.
- Não usar surface `user` para finanças.
- Não executar mutação financeira sem gate humano.
