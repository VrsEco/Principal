---
name: workflow-factory-versus
description: Cria e evolui workflows conversacionais do Workflow Engine V3 no padrão Gestão Versus, com schemas Pydantic, handlers, presenters, testes, política, auditoria e integração MCP/API.
---

# Workflow Factory Versus

Use quando o pedido for criar, padronizar, revisar ou extrair workflows do Workflow Engine V3.

## Sequência curta
1. Classificar o tipo do fluxo
2. Reaproveitar módulo existente antes de criar outro
3. Se for fluxo do Sapiens/WhatsApp, aplicar também `../sapiens-workflow-first/SKILL.md`
4. Gerar base com `scripts/init_workflow.py` quando útil
5. Garantir coerencia com a arvore oficial do produto, com codigos sem ponto e com o dominio correto
6. Completar `schema`, `handler`, `presenter`, testes e integrações
7. Auditar multi-tenancy, policy/HITL, paridade REST/MCP e coerencia com os action keys existentes
8. Validar com compilação/teste focado

## Entrega mínima
- schema rígido
- handler determinístico
- presenter quando houver saída própria
- testes do caso principal e falhas críticas
- documentação/spec do fluxo
- coerencia com a arvore oficial do Sapiens quando o fluxo tocar chat/WhatsApp/menu

## Guardrails
- `company_id` obrigatório
- sem lógica de negócio em rota
- presenter não consulta banco
- ações sensíveis exigem avaliação de policy/HITL
- para fluxos conversacionais operacionais: workflow-first antes de LLM
- para fluxos do Sapiens: respeitar arvore oficial por dominio e codigos sem ponto
- para fluxos do Sapiens: explicitar se o fluxo pertence a escopo pessoal, equipe ou empresa
- evitar criar fluxo duplicado quando o comportamento puder ser encaixado em action key ou handler existente

## Quando combinar com `sapiens-workflow-first`
- criação/evolução de fluxo do WhatsApp ou chat do Sapiens
- intent routing, tool selection ou hidratação de contexto
- perguntas livres que devem cair em execução determinística
- fluxos com confirmação, sessão pendente, empresa explícita e fallback agentic
- fluxos que precisam respeitar a nova arvore `Gestao da Rotina`, `Gestao Estrategica`, `Gestao Financeira`, `Sapiens`, `Governanca`, `Implantacao` e `Sapiens Factory`

## Checklist extra para fluxos do Sapiens
- o fluxo está no dominio correto da arvore oficial?
- o codigo de menu previsto usa formato sem ponto?
- o escopo esta claro: pessoal, equipe ou empresa?
- no WhatsApp, existe regra de selecao de empresa antes da confirmacao quando necessario?
- existe action key reaproveitavel antes de criar um novo contrato?

## Referências
- `references/workflow-checklist.md`
- `references/workflow-blueprint.md`
- `references/first-workflow-example.md`
- `references/sapiens-workflow-extension.md`
- `../sapiens-workflow-first/references/deterministic-routing-checklist.md`
- `../../references/sapiens-official-tree.md`

## Script
- `scripts/init_workflow.py`
