---
name: gestao_versus_core
description: Plano de controle do Gestão Versus. Use para aplicar governança global, escolher skill/especialista e manter a arquitetura enxuta e modular.
---

# Gestão Versus Core

Skill obrigatória de governança do projeto.

## Use para
- aplicar as regras globais do Gestão Versus
- decidir qual skill principal deve conduzir o trabalho
- escolher o especialista líder
- manter economia de contexto e separação correta entre agente, skill, referência e script

## Sequência curta
1. Ler `../../router/orchestrator.md`
2. Aplicar guardrails globais de `../../references/constitution.md`
3. Se houver 3 ou mais etapas, ativar obrigatoriamente `aa-j-31-card-execution` e materializar os cards antes da execução
4. Selecionar a skill principal, se existir:
   - incidente -> `gestao-versus-incident-response`
   - workflow V3 -> `workflow-factory-versus`
   - deploy/produção -> `deploy_gestao_versus`
5. Selecionar o especialista líder em `../../router/routing-matrix.md`
6. Consultar referências só se o detalhe for realmente necessário

## Guardrails inegociáveis
- stack oficial Python/Flask/PostgreSQL
- multi-tenancy com `company_id`
- MCP First quando houver estado operacional
- sem lógica de negócio em rota
- sem documentação longa dentro desta skill
- sem execução 3+ etapas sem cards reais em `AA.J.31`

## Referências
- `../../router/orchestrator.md`
- `../../router/routing-matrix.md`
- `../../references/constitution.md`
- `../../references/personas.md`
- `../../references/component-boundaries.md`
