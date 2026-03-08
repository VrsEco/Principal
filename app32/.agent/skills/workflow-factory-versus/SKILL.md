---
name: workflow-factory-versus
description: Cria e evolui workflows conversacionais do Workflow Engine V3 no padrão Gestão Versus, com schemas Pydantic, handlers, presenters, testes, política, auditoria e integração MCP/API.
---

# Workflow Factory Versus

Use esta skill quando o pedido for **criar, evoluir, padronizar ou revisar workflows** do `Workflow Engine V3` do Gestão Versus.

## Objetivo
Entregar workflows no padrão Versus com:
- `schema` Pydantic rígido (`extra="forbid"`)
- `handler` determinístico
- `presenter` omnichannel
- testes mínimos
- documentação do fluxo
- integração com catálogo, usage e gap radar quando aplicável
- verificação de multi-tenancy, policy/HITL e paridade MCP/REST

## Quando usar
Acione esta skill para pedidos como:
- “crie um novo fluxo”
- “padronize este fluxo no V3”
- “extraia esse fluxo do menu_engine”
- “adicione um workflow determinístico para X”
- “construa o fluxo no padrão Versus”

## Sequência obrigatória
1. **Classificar o tipo do fluxo**
   - consulta/relatório
   - mutação operacional
   - fluxo assistido com wizard
   - ação sensível com HITL
2. **Escolher o módulo**
   - reaproveitar módulo existente em `src/intelligence/workflows/`
   - criar módulo novo apenas quando o domínio justificar
3. **Gerar a base**
   - preferir `scripts/init_workflow.py` desta skill para scaffolding inicial
4. **Completar a implementação**
   - schema
   - handler
   - presenter
   - testes
   - integração no runtime/dispatcher/menu adapter
5. **Auditar governança**
   - multi-tenancy
   - policy/HITL
   - observabilidade
   - catálogo / usage / gap
6. **Validar**
   - `py_compile`
   - pytest focado
   - se houver impacto aplicacional, seguir deploy conforme `deploy_gestao_versus`

## Scaffold mínimo obrigatório
Para um novo domínio ou fluxo relevante, criar ou evoluir:
- `src/intelligence/workflows/schemas/<modulo>.py`
- `src/intelligence/workflows/handlers/<modulo>_handler.py`
- `src/intelligence/workflows/presenters/<modulo>_presenter.py` (se houver saída própria)
- `tests/test_workflow_<modulo>_handler.py`
- `docs/specifications/workflow_<slug>.md` ou evolução da spec existente

## Regras de arquitetura
- Toda leitura e mutação deve respeitar `company_id`.
- Nunca colocar regra de negócio em rota.
- O presenter não consulta banco nem decide permissão.
- O handler recebe dependências explícitas e executa de forma determinística.
- Para canais `whatsapp`, `instagram` e `telegram`, o fluxo é o mesmo; muda só a apresentação.
- Para ações sensíveis, avaliar `policy.py` e approval/HITL antes da execução.
- Se o fluxo virar funcionalidade de negócio estável, planejar espelhamento REST + MCP.

## Integração obrigatória
Avalie e atualize quando fizer sentido:
- `src/intelligence/workflows/schemas/__init__.py`
- `src/intelligence/workflows/handlers/__init__.py`
- `src/intelligence/workflows/presenters/__init__.py`
- `src/intelligence/workflows/direct_execution.py`
- `src/intelligence/workflows/registry.py`
- `src/intelligence/workflows/contracts.py`
- `src/intelligence/menu_engine.py`
- `docs/specifications/workflow_engine_v3.md`

## Teste mínimo por fluxo
- sucesso principal
- erro de input/schema
- erro de escopo/empresa
- comportamento por canal quando houver presenter
- bloqueio por policy/HITL quando aplicável

## Referências desta skill
Leia conforme a necessidade:
- `references/workflow-checklist.md` para checklist de arquitetura e entrega
- `references/workflow-blueprint.md` para mapa de arquivos e decisões de integração

## Uso do script
Exemplo de scaffolding inicial:

```powershell
python .agent/skills/workflow-factory-versus/scripts/init_workflow.py --module occupancy --class-prefix Occupancy --action-key collaborator.occupancy --workflow-slug collaborator-occupancy --dry-run
```

Depois remova os placeholders e integre o fluxo ao runtime V3.
