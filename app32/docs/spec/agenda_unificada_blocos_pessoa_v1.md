# SPEC — Agenda unificada e blocos de jornada da pessoa

Status: aprovada para execução (v1.2, 2026-10-03). Decisões D10 e D11 e as 9 recomendações da seção 15.2
foram confirmadas pelo responsável de produto. Fase 1 autorizada a iniciar; Fase 3 depende dos pareceres da
seção 15.3. Sem implementação concluída desta SPEC. A Agenda Unificada
(`/agenda`) e a sincronização com o Google Calendar já estão em produção (PR #86);
esta SPEC define o que vem depois: unificar com o Calendário Operacional
(`/calendar`) e mover os blocos de horário da empresa para a pessoa.

Protótipo de referência (privado): https://claude.ai/artifact/REcHTjGEo1dS8ZH71gxdVL

## Entrega e checklist

- [x] Diagnóstico do Calendário Operacional e da Agenda Unificada (código da `main` e produção).
- [x] Levantamento de uso e de dependências dos blocos.
- [x] Protótipo de UI/UX para celular e computador, validado pelo responsável de produto.
- [x] Decisões de produto registradas (seção 3).
- [x] Validação das premissas no código: estimativas, mudança de prazo, sobreposição de blocos e
      precedente de tabelas por usuário (achados nas seções 1.4, 5.5, 5.9 e 6.4).
- [x] D10 e D11 aprovadas.
- [x] Decisões da seção 15.2 confirmadas (2026-10-03).
- [ ] Parecer do Arquiteto sobre o modelo de dados e o isolamento (seção 6.4).
- [ ] Parecer do DBA sobre migração e índices.
- [x] Aprovação para iniciar a Fase 1 (2026-10-03).
- [ ] Fase 1 entregue e validada com colaboradores (seção 9.1).
- [ ] Card de execução por entrega (`aa-j-31-card-execution`), quando houver 3 ou mais etapas.

## 1. Contexto e problema

Hoje há duas telas para a mesma pergunta, "o que tenho para fazer e quando":

- **Calendário Operacional** (`/calendar`, módulo `work_journey`): planejamento semanal por
  capacidade. Tem blocos de horário, regras de recorrência, itens sincronizados a partir de
  instâncias, atividades e reuniões, agenda sugerida (gerar, travar, PDF), eventos avulsos,
  ausências e transferências com aprovação, relatório gerencial e ferramentas MCP.
- **Agenda Unificada** (`/agenda`): visão por data de reuniões, atividades e instâncias, criar
  a partir do dia, abrir a página de gestão de cada registro, sincronização nos dois sentidos
  com o Google Calendar e layout responsivo.

O Portal (`/portal`) e o Meu Trabalho (`/my-work`) também listam atividades por data. Eles estão
**fora do escopo** desta SPEC e serão avaliados depois.

### 1.1 Problema dos blocos

O bloco (`work_journey_blocks`) tem `company_id` e `employee_id` obrigatórios. O colaborador
existe uma vez por empresa (`UNIQUE(user_id, company_id)` em `employees`). Quem atua em
várias empresas recebe um conjunto de blocos por empresa, todos sobre as mesmas horas.

Retrato do clone do banco de produção (dados de meados de agosto de 2026, com ressalvas na
seção 1.3), segunda-feira de um usuário que atua em 3 empresas reais:

| Medida | Valor |
|---|---|
| Blocos somados (operacional + buffer) | 25 h |
| Janela do dia (primeiro ao último horário) | 10,5 h |
| Tempo com 2 ou mais empresas no mesmo horário | 9 h |
| Almoço cadastrado | 3 vezes, em horários diferentes |

Alcance: 7 dos 29 usuários ativos vinculados atuam em mais de uma empresa. Para quem atua em
uma só, o comportamento atual não muda.

### 1.2 Uso das funções avançadas

No mesmo clone: 26 blocos em 4 empresas (o último criado em maio), 1 regra, 1 ausência,
0 transferências, 2 eventos avulsos, 178 itens sincronizados em 8 empresas e 60 agendas, todas
em status sugerido (nenhuma travada). Os itens e as agendas sugeridas são o uso real; regras,
ausências, transferências e travamento são pouco usados.

### 1.3 Ressalvas dos números

O clone é anterior à produção atual e parte das agendas foi gerada por consultas durante este
trabalho. O retrato serve para dimensionar, não para medir adoção. A Fase 1 deve incluir
telemetria (seção 13) para medir uso real antes de decidir cortes.

### 1.4 Achado de validação: estimativas

Medido no clone (mesmas ressalvas da seção 1.3):

| Universo | Total | Sem estimativa (0) |
|---|---|---|
| Atividades de projeto abertas | 848 | 767 (90%) |
| Instâncias de processo abertas | 274 | 273 |
| Itens de jornada ativos | 109 | 70 |

No código da `main`: `ProjectTask.estimated_hours` começa em 0, o sync de jornada converte 0 em 0
minutos para atividades e instâncias, e o **motor da agenda assume 15 minutos** quando a estimativa é 0.
Ou seja, o padrão de 30 min no cadastro **não existe hoje**, e as duas telas mostram valores diferentes
para o mesmo item. Sem tratar isso, os sinais por bloco nasceriam quase todos vazios. Ver 5.9.

## 2. Objetivos e não objetivos

### 2.1 Objetivos

1. Uma única tela, **Agenda**, para consultar, criar, planejar e agir, no celular e no computador.
2. O bloco de horário pertence à **pessoa** (usuário) e recebe atividades, instâncias,
   reuniões e eventos avulsos de qualquer empresa em que a pessoa atua.
3. O sistema **sinaliza** capacidade livre e itens acima da capacidade por bloco, em cada dia.
   Nunca bloqueia.
4. O gestor enxerga a ocupação **por bloco** de cada colaborador, sem expor itens de outras empresas.
5. Preservar todas as funções existentes (ausências e transferências com aprovação, regras,
   agenda sugerida, relatório, PDF, MCP) e o histórico.

### 2.2 Não objetivos

- Remover tabelas ou migrar dados históricos de agendas.
- Criar recuperação automática de atrasadas. A área de atrasadas já existe e continua.
- Travar ou impedir a pessoa de planejar acima da capacidade.
- Alterar as regras de aprovação de ausências, transferências e mudança de prazo.
- Unificar Portal e Meu Trabalho (avaliar depois).
- Calcular incentivos a partir dos blocos (o mapa de incentivos só desenha o bloco como nó).

## 3. Decisões de produto já tomadas

| # | Decisão |
|---|---|
| D1 | Um único item de menu, **Agenda**. `/calendar` passa a redirecionar. |
| D2 | Ausências e transferências continuam existindo, com aprovação. |
| D3 | O bloco é da pessoa. A pessoa coloca nele itens de várias empresas. |
| D4 | O sistema sinaliza livre, completo e acima. Não trava. A pessoa decide o que realocar. |
| D5 | Estimativa padrão de **30 min nos novos cadastros** (a implementar; ver D10). Item que chega sem tempo fica "sem estimativa" e fora da conta. |
| D6 | Não há "recuperação". A área de atrasadas ordena da mais antiga para a mais nova por padrão, com outras ordenações e filtros. |
| D7 | O gestor vê a ocupação também **por bloco**. |
| D8 | Celular e computador são requisitos de primeira classe. |
| D9 | O Google Calendar segue como entregue (conexão por usuário, envio por empresa ou global, leitura somente consulta). |
| D10 | **Política de estimativa:** padrão de 30 min só em novos cadastros; itens antigos sem estimativa ficam marcados e fora da conta, sem preenchimento em massa; o motor deixa de assumir 15 min; tela de estimar em lote na Fase 2. |
| D11 | **Mover para outro dia:** atividades usam o fluxo existente de mudança de prazo (com motivo); instâncias, na Fase 2, só se movem entre blocos do mesmo dia. |

## 4. Princípios

1. **Sinalizar, não bloquear.** Toda regra de capacidade produz aviso e ação sugerida, nunca impedimento.
2. **Isolamento por empresa nos dados.** Itens são sempre lidos por `company_id`, com o acesso
   que a pessoa tem em cada empresa. A visão da pessoa é uma agregação de leituras por empresa,
   nunca uma leitura sem escopo.
3. **Blocos são preferência pessoal.** Não são dado da empresa; não aparecem para o gestor
   além do que a seção 8.3 permite.
4. **Rota fina, regra em service.** Rotas validam e adaptam. Regras vivem em services.
5. **Compatibilidade.** Contratos MCP, relatórios e PDF continuam funcionando durante toda a migração.
6. **Migração com confirmação humana.** Nada é fundido nem apagado sozinho.
7. **Texto e cor.** Todo sinal tem texto, não só cor.

## 5. Requisitos funcionais

### 5.1 Navegação

- **RF-NAV-1.** Um item "Agenda" no menu lateral substitui "Calendário" e "Agenda Unificada".
- **RF-NAV-2.** `/calendar` e `/companies/<id>/calendar` redirecionam para a Agenda, preservando
  `date` e `employee_id` quando existirem. As URLs antigas de API continuam válidas.
- **RF-NAV-3.** Visões **Dia**, **Semana** e **Mês**. Abre no Dia no celular e na Semana no computador.
- **RF-NAV-4.** Interruptor **Blocos** liga os blocos, a capacidade e os sinais. Desligado, não há
  barras nem minutos.
- **RF-NAV-5.** Menu de três pontos: Blocos de horário, Regras de recorrência, Ausências,
  Transferências, Relatório gerencial, Conexão com o Google. Itens de gestão só para quem tem permissão.
- **RF-NAV-6.** Telas "Blocos de horário" e "Equipe" acessíveis por esse menu e por atalhos na Agenda.

### 5.2 Criar

- **RF-CRI-1.** Um botão (Criar no computador; + no celular) abre as quatro opções: Reunião,
  Atividade, Instância e Evento avulso, já com a data do dia selecionado e, no computador, com o
  horário clicado.
- **RF-CRI-2.** Reunião abre o editor existente (`/meetings/company/<id>?new=1&date=`). Atividade e
  Instância usam o formulário rápido atual. Evento avulso usa o cadastro existente de eventos avulsos.
- **RF-CRI-3.** Atividade nova sem tempo informado nasce com 30 min (RF-EST-1). Um item que chegue sem
  tempo por outro caminho é tratado por RF-SIN-5.

### 5.3 Blocos da pessoa

- **RF-BLO-1.** O usuário cadastra, edita, ordena e exclui os próprios blocos.
- **RF-BLO-2.** Campos: nome, início, fim, modo, tipos preferidos, dias da semana, ativo.
- **RF-BLO-3.** Modos, com os rótulos atuais: **Operacional** (recebe tarefas), **Capacidade
  ocupada** (bloqueia o período, sem sinal) e **Vazio / Buffer** (janela livre para urgências, sem sinal).
- **RF-BLO-4.** Tipos preferidos (atividade, instância, reunião, evento avulso) servem de sugestão.
  O bloco aceita qualquer item.
- **RF-BLO-5.** Blocos da mesma pessoa que se sobrepõem no mesmo dia da semana geram **aviso** no editor,
  mas **não são impedidos**: hoje não existe essa validação e os dados reais já têm sobreposição. A
  capacidade é calculada pela **união dos intervalos**, sem contar a mesma hora duas vezes. A migração
  tolera sobreposições existentes.
- **RF-BLO-6.** Cada alteração de bloco gera registro de auditoria (quem, quando, antes e depois).
- **RF-BLO-7.** A tela "Blocos" tem duas visões: **Como está hoje** (blocos atuais por empresa, com
  as disputas) enquanto houver blocos legados, e **Como ficaria** (os blocos da pessoa).

### 5.4 Sinais por bloco

Definições, por pessoa e por data:

- **Capacidade do bloco** = (fim − início) em minutos, apenas para modo Operacional.
- **Consumo do bloco** = soma da **estimativa** dos itens atribuídos ao bloco + soma da **duração**
  dos eventos com horário que **começam** dentro do bloco (reuniões, eventos avulsos com horário e
  eventos do Google).
- **Sinal** (somente blocos Operacionais):
  - **Acima**: consumo > capacidade. Texto: "Acima 1h30".
  - **Livre**: capacidade − consumo ≥ **limite de ocioso** (padrão 30 min). Texto: "Livre 1h30".
  - **Completo**: os demais casos.
- **Capacidade do dia** = soma das capacidades dos blocos Operacionais do dia. Dias sem blocos
  operacionais mostram "Sem expediente".

Requisitos:

- **RF-SIN-1.** Os sinais aparecem em cada bloco, no Dia, na Semana (resumo por dia) e no celular
  (cada bloco da lista). A barra do dia mostra consumo × capacidade.
- **RF-SIN-2.** Itens concluídos não consomem capacidade.
- **RF-SIN-3.** Itens atrasados só consomem capacidade depois de planejados em um bloco e dia.
- **RF-SIN-4.** O limite de ocioso é configurável (padrão 30 min).
- **RF-SIN-5.** Item sem estimativa fica **fora da conta** e recebe o marcador "Sem estimativa".
  Nunca recebe valor inventado. O motor da agenda deixa de assumir 15 minutos (RF-EST-3).
- **RF-SIN-6.** Os sinais não bloqueiam nenhuma ação.

### 5.5 Atribuir e mover itens

- **RF-MOV-1.** Atribuir um item a um bloco, em um dia, é uma ação da pessoa. O sistema pode
  **sugerir** distribuição, respeitando preferência de tipo e capacidade, e a pessoa aceita,
  recusa ou ajusta. Itens que não cabem ficam "sem bloco", nunca são forçados.
- **RF-MOV-2.** A ação **Mover para um bloco** lista até 5 opções, com o estado atual do bloco
  e o estado que ficaria. A ordem é: opções que cabem primeiro, depois as do mesmo dia, depois a
  data mais próxima.
- **RF-MOV-3.** Mover entre blocos do **mesmo dia** não altera o prazo e vale para atividades e instâncias.
  Mover uma **atividade** para **outro dia** altera o prazo e usa o **fluxo existente de mudança de prazo**
  (`ProjectTaskDueDateChangeService`): o motivo é obrigatório; a mudança é efetivada na hora quando a pessoa
  é a responsável pela atividade, dona do projeto ou tem permissão de editar projetos; caso contrário, vira
  solicitação pendente de aprovação. A tela avisa qual dos dois casos vai ocorrer antes de confirmar.
  **Instâncias** não têm fluxo equivalente: na Fase 2 só podem ser movidas entre blocos do mesmo dia;
  o outro dia fica para quando houver um fluxo definido (seção 15).
- **RF-MOV-4.** Reuniões e eventos do Google não são movidos pela Agenda (têm horário próprio).
- **RF-MOV-5.** "Desfazer sugestão" remove só o que foi sugerido pelo sistema, nunca o que a pessoa atribuiu.

### 5.6 Atrasadas

- **RF-ATR-1.** Faixa "Atrasadas" no topo, recolhida por padrão, com contagem e horas estimadas.
- **RF-ATR-2.** Ordem padrão: **mais antigas primeiro** (por data de prazo).
- **RF-ATR-3.** Ordenações disponíveis: mais recentes primeiro, empresa, tipo. Filtro por atividades e instâncias.
- **RF-ATR-4.** Cada atrasada abre os detalhes e permite **Mover para um bloco** (RF-MOV-2). Não há
  recuperação automática.

### 5.7 Equipe (gestor)

- **RF-EQP-1.** Tela "Equipe": para cada colaborador, ocupação da semana e, por dia, o sinal de cada
  bloco operacional (acima, livre ou completo), somando **todas as empresas** da pessoa.
- **RF-EQP-2.** O detalhe de um dia mostra cada bloco com consumo × capacidade e a divisão
  "desta empresa" e "outras empresas". **Não mostra títulos nem dados dos itens das outras empresas.**
- **RF-EQP-3.** Quem pode ver: perfis que já podem gerenciar o colaborador na empresa
  (mesma regra de `_can_manage_employee` do módulo atual).
- **RF-EQP-4.** A tela só informa. Não há ação de bloqueio ou de reatribuição forçada.

### 5.8 Google Calendar

- **RF-GOO-1.** Mantém o comportamento entregue (SPEC/runbook `runbook_google_calendar_agenda_v1.md`).
- **RF-GOO-2.** Opcional, decisão pendente (seção 15): enviar a agenda travada ao Google como
  blocos de horário.

### 5.9 Estimativas

- **RF-EST-1.** Atividade criada **a partir da entrega** desta funcionalidade, sem tempo informado, nasce
  com 30 min de estimativa. Para instâncias, usar a estimativa do processo quando houver; sem ela, 30 min
  (confirmar na seção 15).
- **RF-EST-2.** Itens existentes sem estimativa **não são preenchidos em massa**. Ficam marcados "Sem
  estimativa" e fora da conta dos sinais.
- **RF-EST-3.** O motor da agenda deixa de assumir 15 minutos para estimativa 0. A mudança é visível:
  cartões que mostravam "15 min" passam a mostrar "Sem estimativa". Comunicar na liberação.
- **RF-EST-4.** Tela **Estimar em lote**: lista os itens sem estimativa, ordenados por prazo (mais próximo
  primeiro), com filtro por tipo e empresa e atalhos de 30 min, 1 h, 2 h e 4 h. Salva em lote respeitando a
  permissão de edição de cada item. Acessível pelo aviso "N itens sem estimativa" na Agenda.
- **RF-EST-5.** Telemetria: percentual de itens com estimativa, antes e depois (meta: crescer a cada semana).

## 6. Modelo de dados

### 6.1 Tabela nova: `person_work_blocks`

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | int PK | |
| `user_id` | int FK `users.id` | dono do bloco; `ON DELETE CASCADE` |
| `name` | varchar(160) | |
| `description` | text | opcional |
| `start_time`, `end_time` | time | `end_time > start_time` |
| `block_mode` | varchar(30) | `operational`, `reserved_full`, `buffer` (mesmos valores atuais) |
| `weekdays_json` | json | lista 0–6, como hoje |
| `preferred_item_types` | json | subconjunto de `manual`, `process_instance`, `project_task`, `meeting` |
| `order_index` | int | |
| `is_active` | bool | |
| `created_at`, `updated_at` | datetime | |

Índice: `(user_id, is_active)`. Sem `company_id` por decisão D3.

### 6.2 Colunas novas, nulas e retrocompatíveis

- `work_journey_agenda_items.person_block_id` → `person_work_blocks.id`, `ON DELETE SET NULL`.
- `routine_journey_bindings.person_block_id` → `person_work_blocks.id`, `ON DELETE SET NULL`.
- `work_calendar_events.person_block_id` → `person_work_blocks.id`, `ON DELETE SET NULL`.

As colunas `block_id` legadas permanecem e continuam válidas. Nada histórico é reescrito.

### 6.3 Tabelas existentes que permanecem

`work_journey_blocks`, `work_journey_rules`, `work_journey_items`, `work_journey_agendas`,
`work_journey_agenda_items`, `work_journey_absence_requests`, `work_journey_transfer_requests`,
`work_calendar_events`, `routine_journey_bindings`.

A agenda (`work_journey_agendas`) continua por empresa e colaborador. A visão da pessoa **agrega**
as agendas de todos os colaboradores do mesmo usuário (o usuário acessa só as empresas em que
tem acesso). Isso evita criar uma segunda estrutura de agenda.

### 6.4 Adaptador de blocos efetivos

`get_effective_blocks(company_id, employee_id)`:

1. Se o `Employee` tem `user_id` e esse usuário tem ao menos um `person_work_blocks` ativo,
   devolve os blocos da pessoa.
2. Caso contrário, devolve os blocos legados de `work_journey_blocks` (comportamento de hoje).

Quem consome blocos (motor da agenda, apresentador, relatórios, PDF, serviço de rotinas, ferramentas
MCP, mapa de incentivos) passa a chamar o adaptador. O usuário só "vira" pessoa depois de migrar
(seção 10). Não há chave global.

**Precedente verificado:** já existem tabelas por usuário, sem `company_id`: `notes`, `user_mcp_tokens`,
`identity_principals`, `user_employee_assignments`, `password_reset_tokens` e `google_calendar_connections`.

**Ponto para parecer do Arquiteto:** `person_work_blocks` não tem `company_id`. É preferência
pessoal do usuário, não dado de empresa, e só é lido (a) pelo próprio usuário e (b) por serviços
que devolvem resultados agregados e filtrados (seção 8.3). Validar que isso é compatível com a
regra "toda leitura e escrita isola `company_id`", ou definir a exceção formal. Condições propostas para a exceção: (1) o bloco é preferência pessoal; (2) nenhuma
junção com tabelas de dados de empresa; (3) leitura de terceiros só por serviço agregado; (4) auditoria de gravação.

## 7. Contratos de API, serviços e MCP

### 7.1 Serviços (regra de negócio)

- `person_work_block_service`: CRUD, validação de sobreposição, auditoria.
- `block_signal_service`: cálculo de capacidade, consumo e sinal por pessoa, dia e bloco. Função pura
  sobre dados já carregados, testável sem banco.
- `block_assignment_service`: atribuir, sugerir, desfazer e mover itens, integrando com o serviço de
  mudança de prazo existente.
- `team_block_signal_service`: agrega sinais por colaborador para o gestor, aplicando a regra de privacidade.
- Camada de adaptação `get_effective_blocks` (seção 6.4).

### 7.2 Rotas HTTP (propostas, finas)

| Rota | Uso |
|---|---|
| `GET/POST /api/agenda/blocks`, `PUT/DELETE /api/agenda/blocks/<id>` | blocos da pessoa (usuário autenticado) |
| `GET /api/agenda/signals?start=&end=` | sinais por bloco e dia da pessoa (todas as empresas com acesso) |
| `POST /api/agenda/assignments`, `DELETE /api/agenda/assignments/<id>` | atribuir, mover e desfazer |
| `POST /api/agenda/assignments/suggest` | sugestão de distribuição |
| `GET /api/companies/<id>/agenda/late?sort=&types=` | atrasadas ordenadas e filtradas |
| `GET /api/companies/<id>/agenda/team-signals?start=&end=` | visão do gestor |

Payloads validados por schema rigoroso. Toda rota de empresa usa `active_company_permission_required`.

### 7.3 MCP

- As ferramentas atuais **mantêm nomes e contratos**: `list_work_journey_blocks_tool`,
  `save_work_journey_block_tool`, `get_work_journey_board_tool`, `get_work_journey_agenda_tool`,
  `generate_work_journey_agenda_tool`, `lock_work_journey_agenda_tool`,
  `unlock_work_journey_agenda_tool`, `move_work_journey_agenda_item_tool`,
  `get_work_journey_capacity_report_tool` e as demais de jornada. Passam a operar pelo adaptador.
- Nenhuma mudança de permissão ou superfície nas ferramentas existentes.
- Opcional na Fase 4: `get_agenda_block_signals_tool` (leitura, `tenant_safe`).
- A SPEC de skills/playbooks MCP dependente deve ser atualizada (seção 16).

## 8. Regras de negócio e privacidade

### 8.1 Exemplo numérico

Bloco 10:00–12:00 (2 h de capacidade) com uma reunião de 1 h 30 min que começa às 10:00 e uma
atividade estimada em 2 h: consumo 3 h 30 min, sinal **Acima 1h30**. O bloco 07:30–10:00
(2 h 30 min), sem nada, mostra **Livre 2h30**. Mover a atividade de 2 h para esse bloco
deixa o primeiro em **Livre 30min** e o segundo em **Livre 30min**.

### 8.2 Itens sem estimativa

Fora do consumo e marcados. Contam nos totais "sem estimativa" da bandeja de planejamento, mas
nunca nos sinais.

### 8.3 Privacidade do gestor

O gestor de uma empresa vê, para cada colaborador: a ocupação total (todas as empresas), o sinal de
cada bloco e, no detalhe, o consumo dividido em "desta empresa" e "outras empresas". Os itens das outras
empresas não são identificados (sem título, projeto, processo ou reunião). Quem ainda não migrou para
blocos da pessoa aparece com os blocos legados da empresa, sem soma entre empresas.

### 8.4 Permissões

Reutiliza `processes` (`view`) para leitura da agenda e as regras atuais de gestão de colaborador.
Blocos da pessoa: o próprio usuário lê e grava; o gestor não edita blocos de outra pessoa.
Auditoria obrigatória em toda gravação de bloco.

## 9. Requisitos de UX/UI

Referência visual: o protótipo (link no topo). Requisitos obrigatórios:

- **Responsivo.** Sem rolagem horizontal da página em largura de celular (cerca de 360 px). Alvos de
  toque com pelo menos 44 px. Painéis de detalhe e criação como folha que sobe da base no celular,
  e como painel lateral no computador.
- **Cores por tipo, com texto:** Reunião (roxo), Atividade (azul), Instância (verde), Evento avulso
  (rosa), Google (âmbar). Cor nunca é o único indicador.
- **Sinais:** acima (vermelho + "Acima Xh"), livre (azul-petróleo + "Livre Xh"), completo (verde + "Completo").
- **Tema claro e escuro**, com contraste adequado.
- **Estados:** vazio ("Nada marcado… toque em Criar"), carregando, erro com ação, Google vencido
  (faixa amarela com "Reconectar").
- **Teclado e foco** visíveis em todos os controles; `Esc` fecha painéis.
- **Idioma:** PT-BR, voz ativa, rótulos pelo que a pessoa reconhece ("Blocos", "Equipe", "Atrasadas").
- A Semana mostra o resumo dos sinais por bloco; os itens aparecem dentro dos blocos na visão **Dia**.

### 9.1 Plano de validação de UX e adesão

A adesão depende mais da usabilidade que das funções. Por isso a UX tem critérios de aceite próprios, por fase.

**Critérios de aceite de UX (toda fase):**

- Larguras testadas: 360, 768 e 1280 px, em tema claro e escuro, sem rolagem horizontal da página.
- Alvos de toque de pelo menos 44 px; contraste mínimo AA; foco visível; navegação completa por teclado.
- Tarefas-chave em poucos toques no celular: criar um item (até 3 toques), mover um item sinalizado
  (até 3 toques), reconectar o Google (1 toque a partir do aviso).
- Orçamento de desempenho: primeira renderização da Agenda em até 2 s em rede 4G; mês carregado em uma
  chamada; sem recarregar a página ao trocar de visão.
- Estados completos: vazio, carregando, erro com ação, offline do Google, sem permissão.
- Texto claro, em PT-BR, sem jargão técnico. Cada sinal com texto e cor.

**Validação com pessoas reais, antes de cada liberação ampla:**

1. Teste de uso com 3 a 5 colaboradores (pelo menos 2 só no celular), com 4 tarefas: ver o dia, criar uma atividade,
   mover um item acima da capacidade, achar uma atrasada antiga. Medir tempo, erros e hesitações.
2. Liberação gradual: opt-in "Nova Agenda" com atalho para voltar à tela antiga durante a transição
   (RF-NAV, Fase 1), e canal de feedback dentro da tela.
3. Revisão do protótipo e da tela real lado a lado antes de cada fase: o protótipo é a referência visual.

**Métricas de adesão (seção 13):** usuários ativos por semana na Agenda, uso do interruptor Blocos, itens
movidos após um sinal, percentual de itens com estimativa e quantos voltaram à tela antiga.

## 10. Migração dos blocos

1. **Assistente por usuário**, iniciado pelo próprio usuário (ou convite), nunca em lote automático.
2. Lê os blocos legados de todos os colaboradores do usuário e propõe uma lista única: blocos
   repetidos ou sobrepostos (por exemplo, "Almoço" em três empresas) são agrupados em um só, com
   horário sugerido.
3. O usuário **confirma, ajusta ou recusa cada proposta**. Nada é criado sem confirmação.
4. Ao confirmar, cria os `person_work_blocks`, reaponta vínculos de rotina por sobreposição de horário
   e nome (`routine_journey_bindings.person_block_id`) e passa o adaptador a usar os blocos da pessoa.
5. **Reversível:** os blocos legados ficam intactos. Excluir os blocos da pessoa devolve o usuário ao
   comportamento anterior.
6. Agendas já geradas e itens de agenda mantêm `block_id` legado.
7. Quem não tem usuário vinculado segue com blocos por empresa.

Escala de referência (clone): 26 blocos legados em 4 empresas; 19 deles de um único usuário em 4 empresas;
6 vínculos de rotina a blocos.

## 11. Faseamento, critérios de aceite e testes

Cada fase é entregável e reversível. Nenhuma fase altera dados históricos.

### Fase 1 — Agenda única (sem mudar blocos)

Escopo: menu "Agenda" único; visões Dia e Semana (além do Mês); Evento avulso como quarta opção do Criar,
e exibido na Agenda; faixa Atrasadas com ordenação e filtro; telemetria básica; atalhos de ida e volta entre a
Agenda e o Calendário Operacional. O redirecionamento de `/calendar` (RF-NAV-2) é ativado ao fim do período de
transição, por configuração, depois do teste com colaboradores (seção 9.1).

Aceite: um item de menu; redirecionamento preserva `date` e `employee_id`; atrasadas ordenadas
da mais antiga para a mais nova por padrão; sem rolagem horizontal em 360 px; o Calendário Operacional
continua acessível pelo menu de três pontos durante a transição.
Testes: contrato de rotas e redirecionamentos; ordenação e filtro de atrasadas; teste visual
responsivo; regressão do Google.

### Fase 2 — Sinais e mover sobre os blocos existentes

Escopo: `block_signal_service` e `block_assignment_service`; sinais por bloco na Agenda, usando os
blocos legados de cada empresa e colaborador; Mover para um bloco; sugestão de distribuição; política de
estimativa (RF-EST-1 a RF-EST-5), com a tela Estimar em lote e a remoção do fallback de 15 minutos.

Aceite: os exemplos numéricos da seção 8.1 reproduzidos em testes; nenhum bloqueio de ação; mover para
outro dia aciona o fluxo de mudança de prazo; item sem estimativa fora da conta; "Desfazer sugestão"
remove só o sugerido; atividade movida para outro dia aciona o fluxo de prazo com motivo; instância só se
move dentro do mesmo dia; novas atividades nascem com 30 min; cartões sem estimativa mostram o marcador, e o motor
não assume mais 15 minutos.
Testes: unitários do cálculo (função pura), incluindo limites (exatamente 30 min livres, consumo igual
à capacidade, evento que cruza dois blocos), tenancy (nenhum dado de outra empresa), integração do mover.

### Fase 3 — Blocos da pessoa

Escopo: `person_work_blocks`, colunas `person_block_id`, `person_work_block_service`, adaptador
`get_effective_blocks`, editor de blocos, assistente de migração, reapontamento de rotinas, auditoria.

Aceite: usuário migrado passa a ter um dia único; usuário não migrado não muda; reverter funciona;
nenhuma ferramenta MCP existente muda de contrato; relatórios e PDF seguem funcionando.
Testes: migração em PostgreSQL descartável com dados sintéticos; adaptador nos dois modos; validação de
sobreposição; auditoria; compatibilidade de contratos MCP.

### Fase 4 — Leitura unificada e Equipe

Escopo: motor da agenda, apresentador, relatório e PDF, mapa de incentivos e MCP consumindo o adaptador;
tela Equipe; sinais agregados entre empresas.

Aceite: o gestor vê o sinal por bloco e a divisão "desta empresa" e "outras empresas" sem identificar itens
alheios; a soma entre empresas só ocorre para usuários migrados; sem vazamento entre tenants.
Testes: privacidade (nenhum campo de item de outra empresa na resposta), permissões, desempenho com
dezenas de colaboradores.

### Fase 5 — Configurar e acabamento

Escopo: reorganizar Regras, Ausências e Transferências no menu de configuração, mantendo aprovações;
opcional: agenda travada como blocos de horário no Google; decisão sobre desligar a tela legada.

## 12. Segurança, privacidade e LGPD

- A visão da pessoa nunca lê dado de empresa sem o acesso que a pessoa tem naquela empresa.
- O gestor não acessa blocos nem itens de outras empresas (seção 8.3).
- Blocos são dados pessoais de rotina de trabalho: auditoria de gravação, retenção alinhada à política
  vigente, exclusão do usuário apaga os blocos (`ON DELETE CASCADE`).
- Logs e telemetria não registram títulos de itens.
- Nenhuma credencial, token ou segredo é manuseado por esta funcionalidade.

## 13. Observabilidade e métricas de sucesso

Eventos (sem conteúdo dos itens): abertura da Agenda por visão, uso do interruptor Blocos, abertura de
bloco, mover (mesmo dia e outro dia), aceite e recusa de sugestão, uso de filtros de atrasadas, abertura
da tela Equipe.

Métricas:

- Adoção: usuários que ligam o interruptor Blocos ao menos 1 vez por semana.
- Qualidade dos dados: percentual de itens com estimativa e de itens "sem estimativa".
- Efeito: dias por usuário com ao menos um bloco acima, e tempo médio até mover um item sinalizado.
- Migração: usuários migrados e blocos unidos pelo assistente.
- Meta de usabilidade: tarefas de criar e mover concluídas em até 3 toques no celular.

## 14. Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Estimativas ruins distorcem os sinais | Marcar "sem estimativa"; telemetria de qualidade; sem valor inventado |
| Pessoa ignora sinais e vive acima da capacidade | Resumo da semana e visão do gestor, apenas informativos |
| Quebra de contrato MCP | Adaptador, nomes e contratos preservados, testes de contrato |
| Vazamento entre empresas na visão da pessoa | Agregação por leitura com acesso por empresa; testes de privacidade |
| Mudar o dia contorna a aprovação de prazo | Reutilizar o fluxo existente e avisar antes de confirmar |
| Migração fundindo blocos indevidamente | Confirmação item a item e reversão |
| Quadro semanal ruim no celular | Lista por bloco no celular; Semana resumida |
| Adoção baixa do planejamento | Interruptor Blocos desligável; telemetria antes de investir mais |
| 90% dos itens sem estimativa: sinais quase vazios no início | Padrão de 30 min só em novos cadastros, tela Estimar em lote, marcador "Sem estimativa" e meta semanal de cobertura |
| Usabilidade ruim derruba a adesão | Critérios de UX por fase, teste com colaboradores reais e liberação gradual com volta à tela antiga |

## 15. Decisões

### 15.1 Aprovadas

- **D10** Política de estimativa (RF-EST-1 a RF-EST-5).
- **D11** Mover para outro dia: atividades pelo fluxo existente; instâncias só no mesmo dia na Fase 2.

### 15.2 Confirmadas em 2026-10-03

| # | Tema | Recomendação |
|---|---|---|
| 1 | Limite de "Livre" | 30 min, configurável |
| 2 | Reuniões e Google consomem a capacidade | Sim, quando têm horário; eventos de dia inteiro do Google não consomem |
| 3 | Visão do gestor | Só os totais das outras empresas, sem os itens |
| 4 | Sobreposição de blocos | Avisar, não impedir; capacidade pela união dos intervalos |
| 5 | Agenda travada no Google como blocos | Adiar; sem escopo na Fase 5 |
| 6 | Nome "Evento avulso" | Manter |
| 7 | Portal e Meu Trabalho | Avaliar depois da Fase 2, com telemetria |
| 8 | Padrão de 30 min para instâncias | Usar a estimativa do processo quando houver; sem ela, 30 min (decisão do usuário em 03/10/2026, no lugar de 1 h) |
| 9 | Início da Fase 1 | Aprovado (não toca em blocos nem em dados) |

### 15.3 Pendências de parecer

- **Arquiteto:** exceção de `company_id` para `person_work_blocks`, com as condições da seção 6.4. Bloqueia a Fase 3.
- **DBA:** migração e índices. Bloqueia a Fase 3.
- **Produto:** fluxo de mudança de prazo para instâncias, quando se quiser mover instâncias para outro dia.

## 16. Documentação dependente a atualizar após aprovação

Ordem oficial: Paper → SPEC → Manifesto → Playbook → Runbook → Harness.

- Runbook `runbook_google_calendar_agenda_v1.md`: rotas e menu da Agenda única.
- Playbooks e descrições das ferramentas MCP de jornada (nomes mantidos; semântica dos blocos).
- Harness de QA da Agenda: casos de sinais, mover, privacidade do gestor e responsividade.

## 17. Referências

- Protótipo: https://claude.ai/artifact/REcHTjGEo1dS8ZH71gxdVL
- PR da Agenda Unificada e do Google Calendar: VrsEco/Principal#86.
- Código atual: `api/routes/work_journey.py`, `services/work_journey_*`, `models/work_journey.py`,
  `models/routine.py` (`RoutineJourneyBinding`), `services/unified_calendar_service.py`,
  `services/google_calendar_service.py`, `src/core/mcp_work_journey_tools.py`,
  `src/intelligence/tooling/capabilities.py`.
- `docs/spec/controle_deploy_agentes_squad_v1.md` para a esteira de publicação.
