---
name: workflow-factory-versus
description: Cria e evolui workflows conversacionais do Workflow Engine V3 no padrão Gestão Versus, com schemas Pydantic, handlers, presenters, testes, política, auditoria e integração MCP/API.
---

# Workflow Factory Versus

Use quando o pedido for criar, padronizar, revisar ou extrair workflows do Workflow Engine V3.

## Sequência curta
1. Classificar o tipo do fluxo
2. Reaproveitar módulo existente antes de criar outro
3. Gerar base com `scripts/init_workflow.py` quando útil
4. Completar `schema`, `handler`, `presenter`, testes e integrações
5. Auditar multi-tenancy, policy/HITL e paridade REST/MCP
6. Validar com compilação/teste focado

## Entrega mínima
- schema rígido
- handler determinístico
- presenter quando houver saída própria
- testes do caso principal e falhas críticas
- documentação/spec do fluxo

## Guardrails
- `company_id` obrigatório
- sem lógica de negócio em rota
- presenter não consulta banco
- ações sensíveis exigem avaliação de policy/HITL

## Referências
- `references/workflow-checklist.md`
- `references/workflow-blueprint.md`
- `references/first-workflow-example.md`

## Script
- `scripts/init_workflow.py`
