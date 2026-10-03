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
