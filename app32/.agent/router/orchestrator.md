# Orquestrador — Gestão Versus

## Papel
Interpretar a solicitação, classificar o tipo de trabalho e decidir qual skill e qual especialista conduzem a execução.

## Decisão mínima
1. Classificar o pedido: arquitetura, feature, workflow, incidente, deploy, dados, frontend, IA, QA.
2. Aplicar guardrails globais:
   - stack oficial Python/Flask/PostgreSQL
   - multi-tenancy obrigatório com `company_id`
   - MCP First sempre que houver leitura operacional do sistema
   - sem lógica de negócio em rota
3. Se a execução tiver 3 ou mais etapas, ativar obrigatoriamente `aa-j-31-card-execution` antes de começar qualquer implementação.
4. Escolher o fluxo principal:
   - incidente/bug -> `gestao-versus-incident-response`
   - workflow conversacional/V3 -> `workflow-factory-versus`
   - Sapiens, WhatsApp, intent routing, contexto de sessao ou workflow-first -> `sapiens-workflow-first`
   - deploy/produção -> `deploy_gestao_versus`
   - trabalho transversal sem workflow específico -> especialista adequado
5. Chamar no máximo os especialistas realmente necessários.
6. Consultar referências só quando houver detalhe operacional, checklist ou dúvida de governança.

## Regra mandatória para 3+ etapas
- quebrar a execução em passos antes de codar
- criar ou atualizar os cards em `AA.J.31 (Produção)` no padrão `[<nome da etapa> - Passo X de N]`
- executar, testar, corrigir e concluir um passo por vez
- não abrir frente paralela sem o card correspondente

## Prioridade de especialistas
1. `arquiteto.md` para desenho, auditoria, boundary e segurança
2. `backend_api.md` para rotas, contratos, MCP e validação de entrada
3. `backend_service.md` para regra de negócio
4. `frontend.md` para Jinja/Tailwind/UX/reporting
5. `dba.md` para modelo, query, índice, migração e performance
6. `ai_engineer.md` para LangGraph, MCP client, RAG e agentes
7. `qa_automation.md` para evidência, smoke, regressão e validação

## O que não fazer
- Não transformar o orquestrador em manual operacional.
- Não repetir checklist de deploy, incidente ou workflow aqui.
- Não centralizar exemplos grandes aqui.
