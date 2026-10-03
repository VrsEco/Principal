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

