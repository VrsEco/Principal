# Matriz de Roteamento

## Tipo de pedido -> skill / especialista principal

| Tipo | Skill principal | Especialista líder | Apoio comum |
|---|---|---|---|
| Definir arquitetura, boundaries, refatoração estrutural | `gestao_versus_core` | `arquiteto.md` | `dba.md`, `backend_service.md` |
| Execução longa com 3+ etapas | `aa-j-31-card-execution` (obrigatória) | depende do domínio | `qa_automation.md`, `arquiteto.md` |
| Criar ou revisar workflow V3 | `workflow-factory-versus` | `backend_service.md` | `backend_api.md`, `qa_automation.md`, `ai_engineer.md` |
| Investigar bug, drift, permissão, tenant, produção | `gestao-versus-incident-response` | `qa_automation.md` | `arquiteto.md`, `backend_api.md`, `dba.md` |
| Deploy, produção, migração, restart | `deploy_gestao_versus` | `qa_automation.md` | `backend_api.md`, `dba.md` |
| Nova rota/API REST/MCP | nenhuma adicional obrigatória | `backend_api.md` | `backend_service.md`, `qa_automation.md` |
| Regra de negócio / service | nenhuma adicional obrigatória | `backend_service.md` | `arquiteto.md`, `dba.md` |
| Modelo, query, migração, performance SQL | nenhuma adicional obrigatória | `dba.md` | `backend_service.md` |
| UI, template, print, dashboard | nenhuma adicional obrigatória | `frontend.md` | `backend_api.md`, `qa_automation.md` |
| LangGraph, RAG, consumo MCP, agentes internos | nenhuma adicional obrigatória | `ai_engineer.md` | `backend_api.md`, `arquiteto.md` |

## Regra de contenção
Se o pedido couber em 1 skill + 1 especialista, não expandir para mais componentes.

## Regra de resposta
As respostas devem ser curtas e objetivas, com alvo de leitura entre 1 e 5 minutos, salvo quando o usuário pedir aprofundamento.

## Regra de resposta
As respostas devem ser curtas e objetivas, com alvo de leitura entre 1 e 5 minutos, salvo quando o usuário pedir aprofundamento.

## Regra mandatória
Se houver 3 ou mais etapas, a execução deve começar por `aa-j-31-card-execution`, com cards reais em `AA.J.1 (Produção)` e fechamento sequencial de cada passo.
