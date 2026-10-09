# Runbook — Coortes de leitura do mcp-versus

**Classe:** Runbook
**Data:** 2026-10-08
**Complementa:** [SPEC de classificação dos domínios](../spec/classificacao_dominios_mcp_versus_v1.md) e [Glossário do mcp-versus](../spec/glossario_mcp_versus_v1.md).

## 1. O que existe

Leituras do mcp-versus publicadas por **assunto**, cada uma validada pelo contrato automático
(`src/core/mcp_cohort_contract.py`, teste `test_mcp_read_cohort_contract.py`): risco baixo, sem gate,
verbo de leitura, `company_id` explícito, sem parâmetro de escrita, escopo alcançável pelo token,
permissão declarada e sem escrita no código da tool. Todas passam pelo limitador de tamanho de resposta.

| Assunto | Ferramentas | Padrão |
|---|---:|---|
| `strategy` | 13 | **ligado** |
| `processes` | 4 | **ligado** |
| `platform` | 3 | **ligado** |
| `knowledge` | 2 | **ligado** (variantes `*_secure`, `company_id` validado pelo grant; SPEC RAG 16.10) |
| `commercial` | 14 | desligado (dados sensíveis) |
| `finance` | 24 | desligado (dados sensíveis); `list_financial_closings` fica fora até existir `services.financial_closing_service` |
| `routine` | 16 | flag própria `MCP_VERSUS_ROUTINE_READ_ENABLED` |

## 2. Como ligar e desligar

Variável `MCP_VERSUS_READ_DOMAINS` no `.env` do servidor (`app32/.env`), lida ao iniciar o MCP:

| Valor | Efeito |
|---|---|
| ausente | `strategy`, `processes`, `platform`, `knowledge` |
| `strategy,processes,platform,commercial,finance` | exatamente a lista (acrescente os sensíveis) |
| `none` ou vazia | **interruptor de emergência**: nenhuma coorte nova |

Mudou o valor: reiniciar o runtime MCP pelo fluxo oficial (deploy `quick` com `restart_mcp=true`).
Assuntos fora da lista não são listados **nem registrados**.

## 3. Validação após o deploy

1. Confirmar no log do run: SHA esperado, `restart_mcp=true`, MCP ativo.
2. Reconectar o cliente e listar as capacidades (`list_user_app32_capabilities`): devem aparecer 49 + 14 (`routine`) + as coortes ligadas.
3. Chamar cada ferramenta nova na empresa de teste (somente leitura) e conferir: resposta estruturada, `_truncation` quando grande, negativa em empresa sem grant.
4. Ligar `commercial`/`finance` só depois de revisar amostras de dados reais com o responsável.

## 4. Reversão

- Imediata: `MCP_VERSUS_READ_DOMAINS=none` e reinício do MCP.
- Definitiva: reverter o PR e novo deploy aprovado.

## 5. Fora das coortes, por design

`get_my_work`, `get_tasks_today`, `search_organizational_knowledge`, `answer_organizational_question`
e `list_team_workload` (usam a "empresa ativa" da sessão; o conhecimento por empresa é atendido pelas
variantes `*_secure`, e as atividades pessoais por `list_my_work_secure`); a agenda da jornada
(`force_regenerate`); `get_project_task_analytics_report` (`include_deleted`); as 18
`describe_app32_*` de metadados internos; as ferramentas de deploy e **todas as mutações**
(onda 2, com gate humano).

## 6. Coortes de ESCRITA (sub-onda 2A)

Mutações novas entram por coorte própria, desligada por padrão. Variável `MCP_VERSUS_WRITE_DOMAINS` no `.env` do servidor (`app32/.env`), lida ao iniciar o MCP:

| Valor | Efeito |
|---|---|
| ausente, vazia ou `none` | nenhuma coorte de escrita (padrão) |
| `projects,operations,meetings` | liga exatamente os assuntos listados |

| Assunto | Ferramentas |
|---|---|
| `projects` | `create_project`, `update_project`, `update_project_task_secure` |
| `operations` | `request_engineering_suggestion`, `request_new_app32_integration` |
| `meetings` | `log_meeting_discussion` |

- Assunto fora da lista não é listado nem registrado. Mudou o valor: reiniciar o MCP pelo fluxo oficial (deploy `quick` com `restart_mcp=true`).
- Nenhuma delas exige aprovação (regra D6). Aprovação e identidade seguem o contrato de mutações: só entra na coorte a ferramenta sem violação na linha de base.
- Reversão imediata: `MCP_VERSUS_WRITE_DOMAINS=none` e reinício.
- Validação após ligar: reconectar, listar as capacidades e chamar cada ferramenta na empresa de teste. Para escritas, usar registros de teste e conferir o ator gravado (deve ser o usuário da sessão).
