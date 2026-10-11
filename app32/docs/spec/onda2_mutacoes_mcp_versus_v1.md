# SPEC — Levantamento da onda 2 do mcp-versus: mutações

**Classe:** SPEC (levantamento; nenhuma ferramenta é publicada por este documento)
**Data:** 2026-10-09
**Status:** proposta para decisão do responsável do produto
**Complementa:** [Classificação dos domínios publicados no mcp-versus](classificacao_dominios_mcp_versus_v1.md) (etapa E4) e [Glossário oficial do mcp-versus](glossario_mcp_versus_v1.md).

## 1. Por que este documento

A onda 1 publicou leituras por assunto (coortes), com um contrato automático que barra o que não é leitura de verdade. A onda 2 publica **mutações**. O erro mais caro da onda 1 foi achar que "parece leitura" bastava: a agenda da jornada e as ferramentas da Teia mostraram escrita escondida e identidade vinda do cliente. Por isso, antes de publicar qualquer mutação, este levantamento mede o que existe, aponta o que precisa ser corrigido e propõe um contrato automático para mutações, equivalente ao das leituras.

## 2. Números (catálogo na `main`, 2026-10-09)

| Medida | Valor |
|---|---:|
| Capacidades no catálogo | 353 |
| Escritas reais (verbo de mutação) | 171 |
| Escritas já publicadas no mcp-versus | 34 |
| **Escritas a publicar na onda 2** | **137** |
| A publicar com gate humano declarado | 36 |
| A publicar com parâmetro de identidade vindo do cliente | **32** |
| A publicar sem `company_id` explícito no esquema | **29** |
| A publicar, destrutivas (delete/remove/cancel) | 13, sendo 2 sem gate |

Fonte: catálogo de capacidades e esquemas reais registrados no servidor MCP (todas as 171 têm implementação MCP registrada). Classificação por verbo; exceções são conferidas tool a tool na migração de cada domínio.

### 2.1 A publicar, por domínio

| Domínio | A publicar | Com gate | `user_id` do cliente | Sem `company_id` | Destrutivas |
|---|---:|---:|---:|---:|---:|
| finance | 45 | 3 | 9 | 15 | 2 |
| governance (contratos comerciais, catálogo, deploy) | 27 | 6 | 4 | 7 | 1 |
| routine (jornada) | 21 | 5 | 5 | 2 | 4 |
| strategy | 19 | 15 | 12 | 0 | 2 |
| projects | 9 | 4 | 0 | 2 | 3 |
| processes | 7 | 1 | 0 | 0 | 0 |
| operations | 3 | 0 | 0 | 1 | 0 |
| identity_self_service | 2 | 0 | 1 | 1 | 0 |
| meetings | 2 | 1 | 0 | 0 | 1 |
| analytics | 1 | 0 | 1 | 0 | 0 |
| identity_admin | 1 | 1 | 0 | 1 | 0 |

## 3. Achados que bloqueiam a publicação

### B1. Identidade vinda do cliente (32 ferramentas)

O parâmetro de ator (`user_id`, `approver_user_id`) é aceito do cliente em 32 mutações. Em leitura isso só rotulava a resposta; em **escrita** decide quem consta como autor ou aprovador. Casos mais graves, por quebrarem separação de funções:

- `approve_work_journey_absence_request_tool` e `approve_work_journey_transfer_request_tool`: o cliente informa `approver_user_id`.
- `create_work_journey_absence_request_tool` e `create_work_journey_transfer_request_tool`: o solicitante vem do cliente.
- 12 de `strategy` (`upsert_organizational_identity_tool`, `upsert_strategy_identity_tool`, perfis e vínculos de processo, OKRs do plano, etc.) e 9 de `finance`/comercial (faturamento, fiscal, termos de contrato, cancelamento).

**Correção:** remover o parâmetro e derivar o ator da sessão autenticada, como feito nas leituras da Teia (#131).

### B2. Sem `company_id` explícito (29 ferramentas)

O glossário exige `company_id` explícito em mutação, para o grant ser validado antes do serviço. Hoje 29 recebem a empresa dentro do `payload` ou nem a recebem: quase todo o cadastro financeiro (15), catálogo e produtos comerciais, `request_agent_deployment`/`approve_agent_deployment`, `update_user_contacts`, `escalate_technical_issue`, `register_system_user` e as ferramentas legadas do chat (`create_project_task`, `complete_task`, `log_work_hours`, `request_deadline_extension`).

**Correção:** `company_id` como parâmetro de primeiro nível, conferido com o do `payload`, como já é em `create_financial_entry`.

### B3. Destrutivas sem gate

- A publicar: `remove_commercial_fiscal_batch` e `delete_work_calendar_event_tool`.
- **Já publicadas hoje:** `delete_meeting_activity`, `delete_meeting_decision` e `delete_meeting_topic` (risco médio, sem gate). Decisão necessária: aceitar ou exigir gate.

### B4. Risco declarado baixo em ferramenta que escreve

| Ferramenta | Situação |
|---|---|
| `create_whatsapp_status_schedule`, `update_whatsapp_status_schedule`, `pause_whatsapp_status_schedule` | **Publicadas.** Mudam a agenda de publicação externa; deveriam ter gate (retomar já tem). |
| `dispatch_financial_process_trigger`, `process_financial_import_batch`, `toggle_financial_catalog_item`, `log_meeting_discussion`, `generate_strategic_connection_summary` | A publicar. Escrevem e estão como risco baixo. |

### B5. Duplicatas legadas: não publicar, substituir

Há versões antigas do chat ao lado de variantes `_secure` com contrato correto (`create_project_task`/`create_project_task_secure`, `delete_project_task`/`..._secure`, `complete_task`, `log_work_hours`, `request_deadline_extension`). A regra da onda 1 vale aqui: publicar a `_secure` e **não** a legada. Quando falta a `_secure` (concluir tarefa, apontar horas), criá-la.

### B6. Mutações financeiras e idempotência

45 mutações de finance estão em risco médio e só 3 têm gate. A regra vigente exige idempotência nas financeiras. É preciso medir quais têm `idempotency_key` antes de publicar (o `create_project_task_secure` é o modelo).

### B7. Itens que ficam fora

- `query_database` (SQL livre) e `register_system_user`: **fora do MCP** (já decidido em D3 para o segundo).
- `approve_agent_deployment` e `request_agent_deployment`: ficam no mcp-versus (D1), mas só depois do contrato de deploy; agente nunca aprova.
- `update_company_status`: alto risco, administrativo; avaliar depois.

## 4. Contrato automático para mutações (proposta)

Equivalente ao contrato das leituras, aplicado a toda mutação antes de entrar numa coorte. Falha de qualquer item barra a publicação:

1. `company_id` de primeiro nível; sem parâmetro de identidade do cliente (`user_id`, `approver_*`, `actor_*`, `request_id`, `trace_id`).
2. Risco coerente com o efeito: verbo de escrita nunca é `low`.
3. Gate humano obrigatório para: destrutivas, aprovações, publicação externa, qualquer financeira que lance ou baixe valor, e alto/crítico.
4. Financeira com `idempotency_key`.
5. Não engole exceção de permissão; a negação do grant chega ao cliente.
6. Imports do código existem (catraca já criada no #135).
7. Escopo alcançável pelo token e permissão declarada e resolvida por empresa.
8. Teste por ferramenta: negativa de empresa sem grant, gate recusado sem aprovação, e (financeira) repetição idempotente.

## 5. Ordem proposta

Critério: valor diário, menor raio de dano, menos correções prévias.

| Sub-onda | Domínio | Itens | Pré-requisito principal |
|---|---|---:|---|
| 2A | projects, meetings (restante), operations | 14 | B3 nas reuniões; `_secure` para tarefas |
| 2B | processes (modelagem BPMN/POP) | 7 | gate na publicação do pacote já existe |
| 2C | routine (jornada) | 21 | B1 (aprovações), B3, B5 |
| 2D | strategy | 19 | B1 (12 com `user_id`); quase todas já têm gate |
| 2E | governance comercial (contratos, catálogo) | ~23 | B1, B2, B3 |
| 2F | finance | 45 | B1, B2, B6, contrato de mutações completo |
| — | deploy de agentes, `update_company_status`, `apply_app32_implantation_persona_profile_update_tool` | 4 | contrato de deploy; decisão própria |
| — | `identity_self_service` (2), `analytics` (1), `register_system_user` (1, fora) | 4 | caso a caso |

## 6. Decisões necessárias

| # | Pergunta | Recomendação |
|---|---|---|
| D6 | Mutação de risco médio sem gate (hoje: reuniões e processos) segue sem aprovação, só com RBAC e auditoria? | Sim para criar/editar; **exigir gate** para destrutiva, aprovação, publicação externa e financeira. |
| D7 | Corrigir já as 3 exclusões de reunião publicadas sem gate e as 3 agendas de WhatsApp Status em risco baixo? | Sim, em PR próprio, antes da sub-onda 2A. |
| D8 | Financeiro entra por último e só com idempotência e gate? | Sim. |
| D9 | Ordem 2A a 2F? | Sim. |

## 7. Próximos passos (sem publicar nada)

1. Implementar o **contrato de mutações** (seção 4) como teste em modo "relatório": lista as violações por ferramenta sem barrar a CI, para medir o tamanho do trabalho. Depois vira regra.
2. PR de correção B1 (identidade do cliente) por domínio, começando por `routine` (aprovações) e `strategy`.
3. PR de B3/B4 nas ferramentas já publicadas, conforme D7.
4. Só então a sub-onda 2A, em coorte com variável de ambiente, no mesmo molde da onda 1.

Não altera autorização, identidade nem dados persistidos.

## 8. Decisão D6 aplicada (2026-10-09): aprovação aplicada pelo runtime

Medição de 2026-10-09: o flag `human_gate` do catálogo era só declarativo no mcp-versus. Das 66 capacidades com `human_gate=True`, 39 passavam pela política sem aprovação persistida (confirmado ao vivo com `finish_meeting`). O runtime só pedia aprovação quando a política negava (risco alto ou crítico, ação destrutiva, matriz do overlay).

Opção B aprovada pelo responsável. A regra agora é única e vive em `src/core/mcp_gate_policy.py`:

| Exige aprovação humana persistida | Não exige |
|---|---|
| Destrutivas (`delete`, `remove`, `cancel`, `reset`, `archive`) | Criar e editar de risco médio (RBAC por empresa e auditoria) |
| Aprovações e rejeições (`approve`, `reject`) | Iniciar, encerrar e agendar reunião |
| Publicação e envio a terceiros (`publish`, `resume`, `send`) | Pausar agenda do WhatsApp Status (parada de emergência) |
| Financeiras que lançam ou baixam valor, e fim de vida de contrato (lista `APPROVAL_TOOLS`) | Leituras |
| Risco alto ou crítico com gate declarado | |

- O runtime aplica a regra mesmo quando a política aprovaria; a aprovação é um registro persistido, vinculado a principal, empresa, ferramenta e payload exato, consumido uma vez.
- O manifesto do mcp-versus (`list_user_app32_capabilities`) passa a informar `human_gate` conforme a regra, não conforme o flag.
- Contrato de mutações: M4 mede o que o runtime realmente aplica; nova regra **M9** barra booleano de confirmação vindo do cliente (`confirm`, `confirmed_mutation`, `human_gate_confirmed`).
- Removido o booleano do cliente nas ferramentas registradoras de plano (5), `publish_approved_process_modeling_package_tool` e `update_commercial_offer_contract`.
- **Ficam como estão, por serem atestação e não autorização:** `strategic_tree_add_contribution` e `submit_process_improvement_analysis_tool` (o booleano atesta que um humano confirmou o conteúdo). Ficam na base do M9 as ferramentas LangChain compartilhadas com o chat (`delete_project`, `delete_project_task(_secure)`, `restore_project_task_secure`, `delete_meeting_secure`) e `request_agent_deployment`, para a sub-onda de cada domínio.

## 9. Quadro da sub-onda 2A (projetos, reuniões e operações) — 2026-10-09

Medido com o contrato de mutações (M1-M9) e a regra de aprovação (seção 8). "Livre" = sem aprovação pela regra D6.

### 9.1 Já publicadas (17): sem pendência de contrato
Reuniões (16): `create/update_meeting`, `create/update/delete_meeting_topic`, `..._decision`, `..._activity`, `start/finish/schedule_meeting`, `send_meeting_minutes`, `sync_meeting_activities_to_project`; projetos: `create_project_task_secure`. Aprovação aplicada pelo runtime nas 4 que a regra exige (3 exclusões e `send_meeting_minutes`).

### 9.2 Prontas para publicar, sem correção de contrato (3)
| Ferramenta | Risco | Aprovação | Observação |
|---|---|---|---|
| `create_project` | médio | livre | `company_id` explícito, permissão `project.create` |
| `update_project` | médio | livre | `project_id` ou `project_code`; `changes` livre |
| `update_project_task_secure` | médio | livre | `task_id` + `changes` |

### 9.3 Publicáveis após correção pequena (3)
| Ferramenta | Violação | Correção |
|---|---|---|
| `request_engineering_suggestion` | `requester_name` vem do cliente (rótulo do solicitante) | derivar o nome da sessão |
| `log_meeting_discussion` | M3: escrita declarada como risco baixo | elevar para médio |
| `request_new_app32_integration` | M7: sem escopo alcançável (`mcp_user` ausente) | incluir `mcp_user` nos escopos |

### 9.4 Exigem adaptação antes (5 destrutivas/restauração, com aprovação do runtime)
`delete_project`, `delete_project_task_secure`, `restore_project_task_secure`, `delete_meeting_secure`, mais a legada `delete_project_task`. Pendências: M9 (`confirm` do cliente; as ferramentas são compartilhadas com o chat, então a solução é um adaptador MCP que oculta o parâmetro e injeta a confirmação só depois da aprovação) e M7 (escopo só `mcp_admin`/`sapiens`; decidir se entram para `mcp:user`). Proposta: **ficam fora da 2A**, entram em 2A-bis.

### 9.5 Não publicar (substituídas ou legadas do chat)
`create_project_task` (usar a `_secure`), `delete_project_task` (usar a `_secure`), `request_deadline_extension` e `escalate_technical_issue` (sem `company_id`, escopos do chat; substituir por variantes `_secure` ou pelo pedido de sugestão à Engenharia).

### 9.6 Mecanismo de publicação
As mutações já publicadas são listas fixas no registro. Para as novas, proposta: coorte de escrita no mesmo molde das leituras, com `MCP_VERSUS_WRITE_DOMAINS` (desligada por padrão), registro condicionado à variável e o contrato de mutações como porta: só entra na coorte a ferramenta sem violação na linha de base.

### 9.7 Resultado esperado da 2A
Publicáveis: 3 prontas + 3 corrigidas = **6 mutações novas** (criar e editar projeto, editar tarefa, pedir sugestão à Engenharia, registrar discussão de reunião, pedir integração). Nenhuma exige aprovação nova. O uso diário que muda: passar a criar e editar projetos e tarefas pelo mcp-versus, além de registrar sugestões e integrações.

## 10. Sub-onda 2F (financeiro): desenho da idempotência — 2026-10-11

Documento de desenho, sem código. Pede decisão antes de implementar (seção 10.7).

### 10.1 Problema
- 30 ferramentas financeiras de escrita têm M5 (sem `idempotency_key`) e 17 delas têm M1 (sem `company_id` de primeiro nível).
- Não existe idempotência financeira genérica. O que há é local: faturamento de contratos (`contract_native_billings`), execuções de automação (`financial_automation_executions`), tarefas de projeto e árvore estratégica. Nenhuma cobre lançamento, baixa, borderô, importação ou conciliação.
- Risco concreto: o cliente MCP repete a chamada (tempo esgotado, nova tentativa automática) e o lançamento ou a baixa é gravado duas vezes. No financeiro isso é valor duplicado no caixa.

### 10.2 Princípio: uma camada única no runtime, não 30 correções
A idempotência vive em `mcp_runtime`, ao lado da aprovação persistida, e vale para toda ferramenta que a declarar. As ferramentas não mudam de corpo; ganham só o parâmetro opcional `idempotency_key` (injetado pelo adaptador `mcp_param_hiding`, sem editar as 30 assinaturas).

### 10.3 Tabela nova `mcp_idempotency_keys`
| Coluna | Uso |
|---|---|
| `id` | chave primária |
| `company_id` | empresa (isolamento) |
| `principal_id` | quem chamou (a chave de um usuário não vale para outro) |
| `tool_name` | ferramenta |
| `idempotency_key` | texto do cliente, até 128 caracteres |
| `payload_digest` | resumo canônico do payload (o mesmo `canonical_payload_digest` da aprovação) |
| `status` | `in_progress`, `succeeded`, `failed` |
| `result` | JSON do envelope devolvido (limitado; só o necessário para repetir a resposta) |
| `created_at`, `expires_at` | validade de 24 horas |

Restrição única: `(company_id, principal_id, tool_name, idempotency_key)`.

### 10.4 Comportamento
1. Sem chave: a chamada segue como hoje, mas a ferramenta financeira **de criação** passa a exigir a chave quando a coorte finance de escrita estiver ligada (decisão D10 abaixo).
2. Primeira chamada: grava a linha `in_progress` **antes** de executar, em transação própria (a restrição única barra a corrida entre duas chamadas simultâneas).
3. Mesma chave e mesmo `payload_digest`: devolve o resultado guardado, sem executar de novo (`replayed: true`).
4. Mesma chave e payload diferente: erro `idempotency_key_reuse`, sem executar.
5. Chamada anterior ainda `in_progress`: erro `request_in_progress` (o cliente tenta de novo depois).
6. Falha na execução: a linha vira `failed` e a chave pode ser reutilizada com o mesmo payload.
7. Combinação com aprovação (financeiras que lançam ou baixam valor): a aprovação é consumida **uma vez**; a repetição com a mesma chave devolve o resultado guardado sem pedir nova aprovação.

### 10.5 `company_id` de primeiro nível (M1)
17 ferramentas recebem `company_id` explícito na assinatura, no molde de `create_financial_entry` (que já confere o payload contra o tenant). É mudança mecânica, com teste por ferramenta, e pode sair antes da idempotência em PR próprio.

### 10.6 Migração e implantação
- A tabela exige migração Alembic: o deploy `quick` não a roda; o 2F pede **deploy completo** (`deployment_id` informado) e é o motivo de despachar o lote atual antes.
- A migração só cria tabela nova (sem alterar dados existentes). Rollback: remover a tabela; o runtime sem a tabela ignora a camada (fail-open **somente** para ferramentas sem a flag de exigência; nas financeiras exigidas, fail-closed).
- Limpeza: tarefa agendada apaga linhas expiradas.

### 10.7 Decisões necessárias
| # | Pergunta | Recomendação |
|---|---|---|
| D10 | A chave passa a ser **obrigatória** nas ferramentas financeiras de criação? | Sim em `create_*`, `generate_*`, `import_*`, `reconcile_*`, `match_*`; opcional em `upsert_*` e `replace_*`, que já são idempotentes por natureza. |
| D11 | Validade da chave | 24 horas. |
| D12 | Ordem | 1) M1 financeiro (PR pequeno, sem migração); 2) camada de idempotência + migração (deploy completo); 3) ligar a coorte `finance` de escrita em duas etapas: cadastros (catálogo, regras, orçamento) e depois lançamento/baixa/conciliação. |
| D13 | Quem pode ligar | Só `MCP_VERSUS_WRITE_DOMAINS=...,finance` após validação em empresa de teste da AA. |

### 10.8 Fora desta sub-onda
Fiscal (`list_commercial_fiscal_workspace` e emissão), exclusões financeiras e qualquer ferramenta que mova dinheiro fora do ledger (transferências bancárias, PIX). Seguem sem publicação.
