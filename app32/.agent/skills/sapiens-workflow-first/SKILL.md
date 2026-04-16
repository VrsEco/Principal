---
name: sapiens-workflow-first
description: Projeta e evolui fluxos do Sapiens com entrada em linguagem natural e execucao workflow-first, cobrindo intencao, roteamento, contexto, permissoes, confirmacao, canais e fallback controlado de LLM.
---

# Sapiens Workflow First

Use quando o pedido envolver Sapiens, WhatsApp, chat operacional, roteamento por intencao, tool selection, contexto de sessao ou migracao de fluxos agentic para deterministico.

## Sequência curta
1. Classificar a entrada: saudacao, menu, pergunta livre operacional ou caso realmente aberto
2. Extrair intencao, entidade, escopo, periodo, status e empresa citada
3. Mapear a entrada para a arvore oficial do Sapiens por dominio e codigo sem ponto
4. Selecionar workflow/tool deterministico antes de considerar LLM
5. Validar permissao, multi-tenancy e contexto de canal/sessao
6. Resolver se a empresa precisa ser escolhida antes da confirmacao
7. Confirmar com o usuario quando houver risco, ambiguidade ou acao sensivel
8. Preencher payload com dados de sessao e perguntar so o indispensavel
9. Executar e responder com saida curta, operacional e auditavel

## Regras-mãe
- pergunta livre nao significa execucao por LLM
- workflow-first e LLM-last para consultas e operacoes repetitivas
- linguagem natural e interface de entrada, nao estrategia obrigatoria de execucao
- a arvore oficial do Sapiens e orientada por dominio, nao pela arvore legada de projetos/processos/consultas
- os codigos de menu do Sapiens usam formato sem ponto, ex: `111`, `122`, `145`
- empresa explicita na mensagem tem prioridade sobre empresa ativa da sessao
- canais externos nao podem depender de `current_user`
- desambiguacao de contexto so quando houver conflito real
- perguntar apenas o que for indispensavel
- no WhatsApp, quando houver multiplas empresas elegiveis para uma operacao, selecionar empresa antes da confirmacao final

## Arvore oficial de referencia
- `1` Gestao da Rotina
  - `11` Minhas Tarefas
  - `12` Atividades de Projetos
  - `13` Instancias de Processos
  - `14` Reunioes
  - `15` Tarefas da Equipe
  - `16` Tarefas da Empresa
  - `17` Resumos Operacionais
  - `18` Capacidade Operacional
- `2` Gestao Estrategica
- `3` Gestao Financeira
- `4` Sapiens
- `5` Governanca e Aprovacoes
- `6` Implantacao e Funcionamento
- `7` Sapiens Factory

## Escopos operacionais canonicos
- pessoal: `11x`
- equipe: `15x`
- empresa: `16x`
- capacidade: `18x`

## Pipeline canonico
1. Identificar workflow
2. Validar permissoes
3. Resolver empresa/escopo quando necessario
4. Confirmar com o usuario quando necessario
5. Hidratar contexto
6. Executar
7. Devolver resultado

## Agentes especializados
- `../../agents/sapiens_intent_router.md`
- `../../agents/sapiens_context_resolver.md`
- `../../agents/sapiens_workflow_executor.md`

## Intencoes prioritarias para determinismo
- consultar atividades / instancias / reunioes / processos
- criar atividades / instancias
- concluir atividades / instancias
- consultas pessoais com periodo e status
- consultas de equipe com periodo e status
- consultas de empresa com periodo e status
- encerrar reuniao
- enviar resumo de reuniao por e-mail
- enviar resumo de reuniao por WhatsApp

## Heuristicas obrigatorias
- saudacao pura oferece `menu` ou pergunta direta
- pedido operacional claro nao passa por pergunta de menu
- pedido que cite explicitamente codigo numerico como `111`, `145` ou `183` deve tentar roteamento direto
- se houver sessao pendente:
  - continuar automaticamente quando a resposta casar com o estado atual
  - resetar automaticamente quando o novo comando estiver claro
  - perguntar `nova conversa` x `continuar` apenas em ambiguidade real
- no WhatsApp aceitar formatos numerados naturais como `1`, `1: valor`, `1 - valor`
- no WhatsApp, para operacoes com multiplas empresas acessiveis, perguntar a empresa antes de exibir confirmacao de execucao

## Workflows novos ou destacados
- `meeting.close`
- `meeting.send_summary_email`
- `meeting.send_summary_whatsapp`
- consultas por escopo `my_tasks.*`, `team_tasks.*`, `company_tasks.*` como modelo de intencao canonica, ainda que parte da execucao reutilize action keys legadas internamente

## Especialistas líderes
- `backend_service.md` para regras de fluxo e determinismo
- `backend_api.md` para contratos, schema e surface MCP/REST
- `ai_engineer.md` para intent routing, fallback agentic e telemetria LLM
- `qa_automation.md` para regressao conversacional e validacao por canal

## Entrega mínima
- regra de roteamento explicita
- payload canonico do workflow
- politica de contexto/permissao
- regras de confirmacao
- testes de conversa feliz + ambiguidades + canal externo

## Referências
- `references/deterministic-routing-checklist.md`
- `references/routine-consult-pilot.md`
- `../../references/sapiens-official-tree.md`
