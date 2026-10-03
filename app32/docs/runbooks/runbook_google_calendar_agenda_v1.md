# Runbook — Agenda Unificada e sincronização com Google Calendar (v1)

Tipo: Runbook. Escopo: tela `/agenda` e envio app → Google (Fase 2). Leitura do Google e push webhook ficam para a Fase 3.

## Configuração (por ambiente)
1. Google Cloud Console: projeto → API **Google Calendar** ativada → tela de consentimento → credencial **OAuth Client (Web)**.
   Redirect URI autorizado: `https://<host>/agenda/google/callback`. Escopos: `calendar.events`, `openid`, `email`.
2. Variáveis de ambiente (nunca no Git):
   - `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`
   - `GOOGLE_CALENDAR_TOKEN_KEY` — chave Fernet: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   - `APP_PUBLIC_BASE_URL` — base HTTPS usada no link “Abrir no Versus” dentro do evento
   - `GOOGLE_CALENDAR_TIMEZONE` — opcional (padrão `America/Sao_Paulo`)
3. Migração `20261002_1000` (tabelas `google_calendar_connections` e `google_calendar_event_links`) segue o fluxo de deploy governado.
4. Sem as variáveis, a barra do Google não aparece na tela (integração desativada, nada quebra).

## Operação
- Cada usuário conecta a própria conta em `/agenda` **uma única vez, valendo para todas as empresas** (uma conexão por usuário). Tokens ficam criptografados; perder a chave exige reconectar.
- Dois botões: **“Sincronizar esta empresa”** (só a empresa ativa) e **“Sincronizar todas as empresas”** (todas em que o usuário atua como colaborador ativo). Cada empresa só remove do Google os eventos que ela mesma enviou. Cria/atualiza/remove eventos no calendário `primary`. Idempotente por hash de conteúdo; limite de 300 operações por clique.
- Atividades e instâncias viram eventos de dia inteiro; reuniões usam horário e duração planejada (padrão 60 min).
- Desconectar revoga o token e apaga os vínculos locais de todas as empresas; eventos já criados no Google permanecem.
- `status = revoked|error` na conexão indica reconexão necessária (mensagem em `last_error`).

## Conexão vencida e reconexão (v1.1)
- Ao abrir `/agenda`, o status valida o token; `invalid_grant` marca a conexão como `revoked` e exibe o aviso “Reconectar agora”. Falha de rede não revoga.
- `/agenda/google` é a tela de conexão/reconexão. Após reconectar, executa automaticamente a sincronização de -30 a +60 dias.
- Dois sentidos: Versus → Google grava eventos; Google → Versus é leitura ao vivo (somente consulta, sem armazenar), ignorando eventos criados pelo Versus e cancelados. Limite de 250 eventos por consulta.
- Em modo “Teste” do consentimento Google o refresh token expira em ~7 dias: este fluxo é o caminho esperado de reconexão.

## Agenda única (Fase 1 da SPEC `agenda_unificada_blocos_pessoa_v1.md`)
- Menu lateral: um único item **Agenda** (`/agenda`). O Calendário Operacional segue em `/calendar` e `/companies/<id>/calendar`,
  acessível pelo menu de três pontos da Agenda ("versão anterior") e por um botão "Ir para a nova Agenda" na tela antiga.
  O redirecionamento de `/calendar` para `/agenda` só será ativado ao fim da transição (RF-NAV-2).
- Visões Dia, Semana e Mês. Eventos avulsos (`work_calendar_events` com `source_type = manual`) aparecem na Agenda quando há colaborador definido
  (escopo "Somente meus" ou colaborador escolhido pelo gestor). **Não são enviados ao Google** (D9 da SPEC).
- Rotas novas (todas por empresa ativa, permissão `processes:view`): `GET /api/companies/<id>/agenda/late?sort=old|new|type|source&types=`,
  `POST /api/companies/<id>/agenda/telemetry`. Criar, editar e excluir evento avulso reutilizam
  `/api/companies/<id>/work-journey/calendar/events`.
- Atrasadas: atividades e instâncias abertas com prazo anterior a hoje; ordem padrão mais antigas primeiro.
- Telemetria de uso: tabela `agenda_ui_events` (migração `20261003_1100`). Só nome da ação, detalhe curto de uma lista fixa, dispositivo,
  empresa e usuário. Nunca grava títulos nem dados dos itens. Consulta de adoção: `select event, detail, device, count(*) from agenda_ui_events group by 1,2,3`.
- Deploy: modo `full` (roda a migração). Os assets públicos da Agenda existem em `app32/static` e em `static/` (paridade obrigatória).

## Blocos, estimativas e mover (Fase 2 da SPEC)
- **Sem migração de banco.** Deploy pode ser `quick`. A Fase 2 só lê e grava tabelas existentes (`work_journey_*`, `project_tasks`, `process_instances`).
- **Interruptor "Blocos"** (Dia e Semana): sinais *Livre* (a partir de 30 min livres), *Completo* e *Acima* por bloco operacional, por dia. Somente leitura:
  não cria agenda e nunca bloqueia ação. Consumo = estimativa dos itens atribuídos ao bloco + duração de reuniões, eventos avulsos e eventos do Google
  com horário que **começam** no bloco. Concluídos, adiados, suspensos e cancelados não consomem. Item atrasado só consome depois que a **pessoa** o planeja
  (a sugestão automática do motor antigo não conta). O mesmo item em duas agendas (dia e semana) conta uma vez.
- **Estimativa:** atividades e instâncias **novas** sem tempo nascem com **30 min** (listener `models/estimate_defaults.py`, só no INSERT; registros existentes
  não mudam). O motor da agenda deixou de assumir 15 min: item sem estimativa fica fora da conta e o cartão mostra "Sem estimativa".
  **Estimar em lote** (aviso "N itens sem estimativa"): atalhos 30 min, 1 h, 2 h e 4 h; grava na origem (`estimated_hours`) e espelha em `work_journey_items`.
  Atividade: exige poder editar (responsável, dono do projeto ou `projects:edit`); instância: responsável/dono/executor ou `processes:edit`.
- **Mover para um bloco** (detalhe de atividade ou instância): até 5 destinos com o estado atual e o que ficaria. Mesmo dia não altera o prazo. Atividade em
  outro dia exige motivo e usa `ProjectTaskDueDateChangeService` (vale na hora ou vira pedido pendente; a tela avisa antes). Instância só no mesmo dia.
- **Sugerir distribuição** (Dia): o sistema aplica marcando `metadata_json.suggested_by = system`; **Aceitar** tira a marca; **Desfazer sugestão** remove só o marcado,
  nunca o que a pessoa atribuiu.
- Rotas novas (permissão `processes:view`): `GET .../agenda/blocks?start&end`, `GET|POST .../agenda/estimates`, `GET .../agenda/move-options?type&id`,
  `POST .../agenda/assign`, `GET|POST .../agenda/suggestions`.
- Telemetria nova: `blocks_toggle`, `estimate_open`, `estimate_save`, `move_open`, `move_confirm`, `suggest_open|apply|accept|undo`.
- Observação de dados: a produção tem itens duplicados entre agendas (dia e semana); a leitura de blocos os deduplica, mas as agendas antigas continuam como estão.

## Blocos da pessoa (Fase 3 da SPEC)
- **Exige migração** (`20261004_1000_person_work_blocks`, deploy `full`): cria `person_work_blocks` (por usuário, **sem `company_id`**, decisão D3) e as colunas nulas
  `person_block_id` em `work_journey_agenda_items`, `routine_journey_bindings` e `work_calendar_events` (FK `ON DELETE SET NULL`). Idempotente; downgrade remove tudo.
  Validada em PostgreSQL descartável (upgrade, repetição, restrição `end_time > start_time`, downgrade). **Antes do deploy: parecer do Arquiteto (exceção de isolamento
  da tabela sem `company_id`) e do DBA (migração e índice `(user_id, is_active)`), conforme SPEC seções 6.4 e 15.**
- Ninguém muda sozinho: o usuário só "vira" pessoa ao confirmar o assistente (menu ⋮ > **Meus blocos**). Quem não migra segue exatamente como hoje.
- **Assistente** (`GET /api/agenda/person-blocks/migration`, `POST .../migration/apply`, `POST .../migration/revert`): monta uma proposta a partir dos blocos ativos de todas as
  empresas do usuário; junta blocos de mesmo nome e modo que se sobrepõem em dias comuns (janela mais ampla); nada é criado sem confirmação bloco a bloco; vínculos de
  rotina dos blocos aceitos são reapontados (`person_block_id`). **Reverter** apaga os blocos da pessoa; os blocos por empresa nunca são alterados; itens que a pessoa
  colocou nos blocos da pessoa voltam a ser sugeridos pelo motor.
- **Editor** (`/api/agenda/person-blocks`, só o próprio usuário): nome, início, fim, modo, dias, tipos preferidos (só sugestão). Sobreposição gera **aviso** e não impede.
  Toda gravação grava `user_logs` (`entity_type = person_work_block`, antes e depois).
- **Adaptador** `get_effective_blocks(company_id, employee_id)`: blocos da pessoa se o dono do colaborador tem blocos ativos; senão, legados. Na Agenda, o **dia único**
  (itens e eventos de todas as empresas do próprio usuário, capacidade do dia pela **união** dos intervalos) só vale quando a pessoa olha a **própria** agenda. O gestor
  (escopo "Toda a empresa") continua vendo cada empresa isolada: sem itens de outras empresas.
- Atribuir/mover/sugerir em modo pessoa grava `person_block_id` (e `block_id` fica nulo). **Limite conhecido até a Fase 4:** o Calendário Operacional antigo, o motor de agendas,
  relatório e PDF ainda leem só `block_id`; itens colocados em bloco da pessoa aparecem como "sem bloco" naquela tela até esses consumidores usarem o adaptador.
- Telemetria nova: `blocks_edit_open`, `blocks_edit_save` (create/update/delete), `migration_open`, `migration_apply`, `migration_revert`.

## Equipe (Fase 4 da SPEC)
- **Sem migração. Pode ser deploy `quick`.** Mas o valor real depende da Fase 3 estar no ar (sem ela, a tela Equipe só mostra os blocos por empresa).
- Visão **Equipe** (botão ao lado de Dia, Semana e Mês; só aparece para quem vê a empresa toda, `has_company_full_access`). Rota: `GET /api/companies/<id>/agenda/team?start&end` (403 para os demais).
- Para cada colaborador ativo da empresa: sinal do dia e de cada bloco (Livre, Completo, Acima), ocupação total e consumo dividido em **"desta empresa"** e **"outras empresas"**.
- **Privacidade (por construção, coberta por teste que procura títulos sentinela na resposta):** itens desta empresa saem com título; itens e reuniões de **outras** empresas e eventos avulsos
  saem **somente como minutos**; eventos do Google nunca entram; a soma entre empresas só vale para quem migrou para blocos da pessoa; quem não migrou aparece com os blocos legados desta
  empresa, sem soma. Campos de bloco permitidos: id, nome, início, fim, modo, capacidade, consumo, minutos desta/outras empresas, sem estimativa, sinal e itens desta empresa (tipo, título, minutos).
- Carga em lote: o número de consultas não cresce com a equipe (teste com 60 colaboradores). Limite de 300 colaboradores e de 14 dias por consulta.
- Telemetria: `view_change = team`, `team_filter`.
- **Fora desta entrega (decisão consciente):** motor de agendas, apresentador do Calendário Operacional antigo, relatório/PDF, mapa de incentivos e ferramentas MCP **ainda leem só os blocos por empresa**.
  São 13 arquivos e cerca de 50 pontos que dependem de `block_id`; migrá-los antes de haver usuários com blocos da pessoa em produção só aumentaria o risco. Fica como etapa 4c, a medir pelo uso real.

