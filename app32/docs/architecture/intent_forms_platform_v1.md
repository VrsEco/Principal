# Intent Forms Platform v1

## Objetivo
Criar uma camada canônica entre linguagem natural e execução determinística para consultas, ações, análises e aprovações do Sapiens.

## Pipeline
1. Entrada livre do usuário
2. Construção de `IntentDraft`
3. Normalização para `OperationalIntentForm`
4. Resolução de tenant/entidades/datas
5. Validação e desambiguação
6. Confirmação baseada no formulário
7. Execução determinística
8. Resposta formatada

## Contrato canônico
Arquivo-base:
- `src/intelligence/intents/schemas/operational_form.py`

Subescopos:
- `CompanyScopeForm`
- `SubjectScopeForm`
- `FilterScopeForm`
- `ActionScopeForm`
- `OutputScopeForm`
- `ConfirmationScopeForm`
- `ResolutionScopeForm`
- `SourceScopeForm`

## Primeira vertical conectada
`my_work` já começou a usar a plataforma via:
- `src/intelligence/intents/builders/my_work_form_builder.py`
- `src/intelligence/workflows/handlers/my_work_handler.py`

## Benefícios esperados
- unificação entre frontend, REST, MCP e Sapiens
- multi-tenancy explícita no contrato
- confirmação previsível antes da execução
- menor taxa de Flow Gap
- maior testabilidade

## Roadmap
### Fase 1
- `query.my_work`
- `action.project_task.complete`
- `action.project_task.update_due_date`
- `analysis.project_task.audit`

### Fase 2
- compartilhar contrato com filtros do frontend/API

### Fase 3
- ações em lote
- aprovações HITL
- análises transversais
