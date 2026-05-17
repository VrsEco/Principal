# Runbook — Implantação do Instruction Registry do Squad Cliente v1

Status: oficial

## 1. Objetivo

Implantar o instruction registry do `Sapiens Cliente` com risco controlado e rollout incremental.

## 2. Etapas

1. publicar docs canônicos
2. registrar tools MCP do instruction registry
3. adicionar `resolve_app32_instruction_bundle_tool` ao startup do `squad_cliente`
4. executar testes unitários
5. validar bootstrap em ambiente controlado
6. liberar rollout por canal `stable`

## 3. Smoke mínimo

- `describe_app32_instruction_registry_tool`
- `resolve_app32_instruction_bundle_tool(runtime_profile='squad_cliente')`
- `describe_app32_available_sapiens_squads_tool`
- `resolve_app32_sapiens_activation_tool`
- `describe_app32_squad_runtime_tool(runtime_profile='squad_cliente')`
- `list_user_app32_capabilities`

## 4. Sinais de erro

- runtime não suportado
- bundle sem `company_id` quando o contexto exigir
- drift entre `harness_key` do token e do bundle
- tentativa de injetar documentação longa na sessão

## 5. Rollback

Se houver anomalia:

1. retirar a tool do startup profile
2. manter apenas `describe_app32_squad_runtime_tool`
3. pausar canal `stable`
4. revisar bundle e testes
