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
| `projects,operations,meetings,processes,routine,strategy,commercial` | liga exatamente os assuntos listados |

| Assunto | Ferramentas |
|---|---|
| `projects` | `create_project`, `update_project`, `update_project_task_secure` |
| `operations` | `request_engineering_suggestion`, `request_new_app32_integration` |
| `meetings` | `log_meeting_discussion` |
| `processes` | `create_process_bpmn_activity_tool`, `create_process_pop_step_for_bpmn_tool`, `draft_process_pop_step_description_tool`, `attach_process_pop_step_static_image_tool` (sub-onda 2B) |
| `routine` | 14 da jornada (sub-onda 2C): eventos de calendário, tarefa avulsa, solicitações de ausência e transferência, agenda (gerar, travar, destravar, mover), vínculos de rotina, blocos e regras. `delete_work_calendar_event_tool` exige aprovação |
| `strategy` | 17 de estratégia (sub-onda 2D): identidade e perfis estratégicos, vínculos de alinhamento, linha de visada, OKRs globais e de área, direcionador, participantes, seção do plano e revisão de maturação |
| `commercial` | 15 comerciais (sub-onda 2E): contratos (criar, editar, itens, encerrar), emissores, clientes, carteiras, catálogo, produtos e serviços e contrato da oferta. `close_commercial_contract` exige aprovação |

- Assunto fora da lista não é listado nem registrado. Mudou o valor: reiniciar o MCP pelo fluxo oficial (deploy `quick` com `restart_mcp=true`).
- Criar e editar não exigem aprovação (regra D6); excluir e encerrar exigem (2 ferramentas nas coortes `routine` e `commercial`). Aprovação e identidade seguem o contrato de mutações: só entra na coorte a ferramenta sem violação na linha de base.
- Reversão imediata: `MCP_VERSUS_WRITE_DOMAINS=none` e reinício.
- Validação após ligar: reconectar, listar as capacidades e chamar cada ferramenta na empresa de teste. Para escritas, usar registros de teste e conferir o ator gravado (deve ser o usuário da sessão).

## 7. Sonda de saúde do mcp-versus

`app32/scripts/qa/mcp_health_probe.py` checa, sem credenciais e só com leitura:
1. `/mcp/healthz` (200 e tempo);
2. descoberta OAuth em `/.well-known/oauth-protected-resource/mcp/pilot` (servidor de autorização e escopos base `mcp:access` e `mcp:user`);
3. descoberta do Keycloak (`token_endpoint`);
4. o endpoint MCP sem token deve responder 401.

Códigos de saída: 0 saudável, 1 degradado (lento ou sintomas no log), 2 falha. Opções: `--json` para um monitor externo e, no servidor, `--log logs/mcp_http_stderr.log --minutes 60` para contar `permission discovery failed`, `OperationalError` e `Traceback`.

Limites: não valida a lista de ferramentas (exige token). Para isso, chamar `list_user_app32_capabilities` autenticado e conferir a contagem esperada. Sintoma "0 ferramentas": olhar primeiro `permission discovery failed` no log.

## 8. Conector administrativo curado (`/mcp/pilot/admin`, escopo `mcp:admin`)

Segundo conector, só para administradores da plataforma. O conector comum (`/mcp/pilot`) **não muda** e nunca recebe `mcp:admin`.

**O que expõe (lista fechada, `src/core/mcp_admin_cohort.py`, 8 ferramentas):** aprovações de ausência e de transferência da jornada; exclusão de bloco, tarefa manual e regra da jornada; exclusão de linha de visada de indicador, de vínculo de alinhamento estratégico e de contrato comercial. Todas exigem aprovação humana persistida (regra D6) e permissão por empresa.

**O que não expõe:** diagnósticos do sistema (`get_database_schema`, `get_system_health`), cadastro de usuários, status de empresa, implantação de agentes, WhatsApp Status e as exclusões de projeto e reunião (dependem do adaptador do parâmetro de confirmação, M9).

**Ativação (por ordem):**
1. Keycloak, realm `app32`: criar o client scope `mcp:admin` como **opcional** (nunca padrão) e restringi-lo por papel (Scope → desligar "Full scope allowed" e mapear só o papel de administrador da plataforma).
2. `.env` do servidor: `APP32_MCP_OIDC_ADMIN_ROUTE_ENABLED=1` e `bash scripts/manage_mcp_http.sh restart`.
3. Conferir: `/.well-known/oauth-protected-resource/mcp/pilot/admin` responde 200 com `scopes_supported` = `mcp:access`, `mcp:admin`.
4. Cadastrar o conector no cliente com `https://app.gestaoversus.com.br/mcp/pilot/admin` e autorizar com a conta de administrador.

**Desfazer:** remover a flag do `.env` e reiniciar (a rota some e a descoberta volta a 404).

### 8.1 Decisão (2026-10-11): as 8 ferramentas vão pelo conector comum (coorte `admin_ops`)
O desenho original prevalece: um único conector (`mcp-versus`), com a visibilidade filtrada pelo perfil do usuário. 7 das 8 ferramentas da seção 8 ganharam o escopo `mcp_user` e formam o assunto `admin_ops` das coortes de escrita (`MCP_VERSUS_WRITE_DOMAINS`, desligado por padrão). Cada uma exige permissão por empresa (`work_journey.approve`, `work_journey.delete`, `strategy.alignment.update`) e aprovação humana persistida (regra D6); quem não tem a permissão não as vê.

O conector `/mcp/pilot/admin` da seção 8 permanece no código, **desligado** (`APP32_MCP_OIDC_ADMIN_ROUTE_ENABLED` ausente), para o dia em que existir um caso de plataforma (usuários, empresas, agentes). Motivo da mudança: o Claude registra o cliente por cadastro dinâmico e pede a lista antiga de escopos, o que impedia obter `mcp:admin` sem alterar o provisionador de clientes do Keycloak (provedor próprio, sem código no repositório).

`delete_commercial_contract` **fica só no conector administrativo**: a governança vigente (teste de catálogo) mantém a exclusão de contrato fora do escopo `mcp_user` (suspender e encerrar contrato ficam no usuário). Mudar isso é decisão própria.

## 9. Coortes de escrita financeiras (sub-onda 2F): `finance_setup` e `finance_ledger`

Duas etapas, ligadas separadamente em `MCP_VERSUS_WRITE_DOMAINS`. A mutação financeira **nunca vai pela surface `user`**: as ferramentas só aparecem para token com o escopo `mcp:finance` e executam pela surface `finance`, como `create_financial_entry` e `create_financial_settlement` (já publicadas à parte).

| Assunto | Ferramentas | Observação |
|---|---|---|
| `finance_setup` (12) | catálogo, regra de classificação, regra de automação, orçamento (versão, linha, contrato, documento, agendamentos, matriz), habilitação de domínio, relatório | Cadastros e configuração; nenhuma lança nem baixa valor |
| `finance_ledger` (11) | lançamento direto, borderô e baixa de borderô, lançamento e casamento por conciliação, conciliação de lote, lote e registro de importação, rateio, agendamento, geração de agendamentos vencidos | As que lançam ou baixam valor exigem aprovação humana persistida (regra D6) |

Toda criação, geração, importação e conciliação exige `idempotency_key` (seção 10 do SPEC da onda 2); repetir a chamada com a mesma chave devolve o resultado guardado.

**Fora, de propósito:** `create_financial_closing` (o módulo `services.financial_closing_service` não existe: a ferramenta falharia sempre; precisa do serviço antes de entrar), faturamento e termos fiscais comerciais (`generate_commercial_billing_batch`, `generate_commercial_financial_titles_for_billing`, `upsert_commercial_contract_financial_terms`, `upsert_commercial_contract_fiscal_terms`), exclusões financeiras e qualquer movimentação fora do livro-razão (transferências, PIX).

**Ativação, em duas etapas:** primeiro `finance_setup`; só depois de validar numa empresa de teste, `finance_ledger`. Acrescente o assunto à linha existente e reinicie o MCP (`bash scripts/manage_mcp_http.sh restart`). Depois de ligar, reconecte o conector para a lista de ferramentas ser renovada.

### 9.1 Pré-validação antes da aprovação, autor e resposta compacta (validação de 12/10/2026)
- **Pré-validação (`src/core/mcp_prevalidation.py`):** a aprovação vale só para o conteúdo exato da chamada. Antes, se o serviço recusava o conteúdo depois (conta bancária ou rateio ausentes), a aprovação já tinha sido consumida e se perdia (duas aprovações gastas na validação do lançamento direto). Agora o runtime roda o pré-validador da ferramenta, sem gravar nada, **antes de abrir ou consumir a aprovação** e devolve o erro de negócio na primeira chamada. Hoje cobre `create_financial_direct_entry`; novas ferramentas entram acrescentando uma linha em `PREVALIDATORS`. O pré-validador é consultivo: se ele falhar por exceção, a chamada segue o fluxo normal.
- **Autor e aprovação no lançamento direto:** `created_by_*` vêm da sessão (valores enviados pelo cliente são descartados) e a aprovação humana consumida grava `approved_by_user_id` e `approved_at` no lançamento, com o número da solicitação em `metadata_json.human_approval`.
- **Resposta compacta:** `create_financial_direct_entry` devolve só identificação e situação do agendamento, do lançamento e da baixa (antes eram cerca de 15 mil tokens); o detalhe sai de `get_financial_entry`.

### 9.2 Rateio obrigatório nos títulos a pagar e a receber (regra de negócio, 13/10/2026)
Todo título a pagar ou a receber criado via MCP exige rateio: a soma fecha em 100% (ou, se por valor, no valor do título) e cada linha traz **plano de contas e centro de resultado analíticos**. A regra é a mesma do agendamento e do lançamento direto e vive em `services/financial_title_rules.py`.

| Para inserir... | Ferramenta | Conta bancária | Rateio | Aprovação |
|---|---|---|---|---|
| Conta a pagar ou a receber em aberto | `create_financial_entry` | opcional | **obrigatório**, em `allocations` na mesma chamada | sim |
| Título como agendamento | `create_financial_schedule` | opcional | obrigatório, em `metadata_json.allocations` | não |
| Lançamento já pago ou recebido | `create_financial_direct_entry` | obrigatória | obrigatório, em `allocations` | sim |

`create_financial_entry` grava lançamento e rateio **juntos** (se o rateio falhar, o lançamento recém-criado é desfeito) e o erro de rateio aparece antes de pedir a aprovação (pré-validação). Exemplo de `allocations`: `[{"allocation_type": "percentage", "percentage": 100, "chart_account_id": 217, "cost_center_id": 24}]`. Tipos diferentes de `payable` e `receivable` (por exemplo `bank_movement`) não exigem rateio.

### 9.3 Pré-validação em todas as financeiras com aprovação (13/10/2026)
Cobertura de `src/core/mcp_prevalidation.py`, rodando antes de pedir ou consumir a aprovação humana:

| Ferramenta | O que é conferido antes da aprovação |
|---|---|
| `create_financial_entry` | Formato do lançamento, referências, código duplicado e rateio obrigatório de 100% |
| `create_financial_direct_entry` | Conta bancária, rateio, referências e domínios habilitados |
| `replace_financial_allocations` | Lançamento da empresa, bloqueio de borderô, tipos do rateio e soma (100% ou valor) |
| `create_financial_settlement` | Campos obrigatórios, lançamento da empresa, bloqueio de borderô, banco e saldo (baixa não excede o principal) |
| `create_financial_bordero_settlement` | Borderô existe na empresa |
| `reconcile_financial_import_batch` | Lote de importação existe na empresa |
| `match_financial_bank_reconciliation_row` | Linha do extrato e lançamento existem na empresa |
| `create_financial_entry_from_bank_reconciliation_row` | Linha do extrato existe na empresa |
| `generate_due_financial_schedules` | Data `run_until` válida e agendamento (se informado) existe |

As verificações são somente leitura, sem bloqueio de linhas. São consultivas: o serviço real valida de novo e decide. Um teste (`test_every_published_financial_tool_that_needs_approval_has_a_prevalidator`) falha se uma financeira nova com aprovação for publicada sem pré-validador. As regras vivem em `services/financial_prevalidation_rules.py`.

## 10. Exclusões de projeto, atividade e reunião (coorte `deletions`, 13/10/2026)

**Decisão do responsável:** as exclusões passam a ser alcançáveis pelo conector comum. Isso **reverte** a decisão anterior de manter `delete_project`, `delete_project_task_secure`, `restore_project_task_secure` e `delete_meeting_secure` só na superfície administrativa (os testes de governança correspondentes foram atualizados). `delete_commercial_contract` e o alias legado `delete_project_task` continuam só na superfície administrativa.

| Ferramenta | Permissão exigida | Aprovação humana |
|---|---|---|
| `delete_project` | `project.delete` | sim |
| `delete_project_task_secure` | `project.task.delete` | sim |
| `restore_project_task_secure` | `project.task.restore` | sim |
| `delete_meeting_secure` | `meeting.delete` | sim |

- **O parâmetro `confirm` não existe para o cliente** (`mcp_param_hiding`): a confirmação é a **aprovação humana persistida** (regra D6), vinculada a principal, empresa, ferramenta e conteúdo exato. O valor fixo só satisfaz a confirmação interna da ferramenta, que é compartilhada com o chat. Um teste-guarda falha se alguma ferramenta com confirmação injetada não exigir aprovação persistida.
- **Visibilidade:** só aparecem para quem tem a permissão na empresa (e o perfil comum de colaborador não tem `delete` no domínio). Matriz de papéis: administrador tem exclusão; colaborador e cliente não.
- **Pré-validação** (antes de pedir a aprovação): o alvo existe na empresa e está no estado certo (não removido, para excluir; removido, para restaurar).
- **Ativar:** acrescentar `deletions` a `MCP_VERSUS_WRITE_DOMAINS`, reiniciar o MCP e reconectar o conector. Desfazer: tirar o assunto da linha e reiniciar.

## 11. Diagnóstico: por que uma ferramenta não aparece para um usuário
Depois de ligar uma coorte, a ferramenta só aparece para o cliente se **quatro** condições valerem. Na ordem:
1. A flag do assunto está em `MCP_VERSUS_WRITE_DOMAINS` no `.env`.
2. O processo do MCP foi **reiniciado** depois da edição (`bash scripts/manage_mcp_http.sh restart`); ele só lê o `.env` ao iniciar.
3. O perfil do usuário no APP32 tem a **permissão** da ferramenta na empresa (ou permissão total), e o grant não tem teto que a exclua.
4. O **conector foi reconectado**: o cliente guarda a lista de ferramentas da conexão.

`python scripts/qa/mcp_tool_visibility.py "Nome" --cohort deletions` (no servidor, com o Python do ambiente virtual 3.12, somente leitura) imprime a flag e, por empresa, o teto do grant e se o perfil tem a permissão, para cada ferramenta da coorte. Caso real de 13/10/2026: a flag estava no `.env` e o perfil era administrador, mas o MCP não tinha sido reiniciado.

## 12. Limpeza das chaves de idempotência (tabela `mcp_idempotency_keys`)
- **Automática:** tarefa diária `mcp_idempotency_purge` no agendador do APP32, às **03:30** (horário de São Paulo). Remove as chaves vencidas há mais de **7 dias** (a chave vale 24 h; os 7 dias extras ficam só como rastro de diagnóstico). Roda em lotes de 1000, com teto de 50 lotes por execução, e é idempotente. Aparece no console de automações (`kind: maintenance`).
- **Configuração:** `MCP_IDEMPOTENCY_PURGE_ENABLED` (padrão ligado) e `MCP_IDEMPOTENCY_RETENTION_DAYS` (padrão 7).
- **Manual:** `python scripts/purge_mcp_idempotency_keys.py` (por padrão só **conta**; `--apply` remove; `--days N` muda a retenção), com o Python do ambiente virtual 3.12 do servidor.
- **O que nunca é removido:** chave ainda válida (não vencida) e qualquer dado de negócio.
- **Como confirmar que rodou:** o log da aplicação registra "Chaves de idempotência do MCP removidas: N".
