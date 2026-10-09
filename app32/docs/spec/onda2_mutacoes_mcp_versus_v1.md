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
