# Runbook v1 — Infra: scheduler no boot, uwsgi e diagnóstico de requisições lentas

**Classe documental:** Runbook
**Status:** oficial
**Origem:** instabilidade de 13/10/2026 (card AA.J.29.35)
**Regra de ouro:** nenhuma mudança de infra pode reduzir a estabilidade. Uma fase por vez, com critério de sucesso e reversão, e deploy `quick` só em horário calmo, fora de 08:25 a 08:40 (rodada diária do WhatsApp Status) e sem `restart_mcp` quando o MCP não for tocado.

## 1. O que aconteceu em 13/10/2026

- O servidor reiniciou às 16:05. O MCP voltou sozinho (cron `monitor_mcp_http.sh` a cada 3 minutos); o scheduler dedicado **não voltou**, porque nada o sobe depois de um reinício. Ficou parado de 16:04 a 21:41.
- O app web travou em rotas diferentes (`/api/companies/{id}/employees`, `/api/process-routines`, `/api/processes`) até o HARAKIRI de 300 s. Banco saudável, worker dormindo. A causa ainda não foi achada.
- Depois do reinício o uwsgi voltou com **1 worker**, embora `deploy_configr.sh` configure 2. O `uwsgi.ini` só voltou a ter `workers = 2` quando um deploy o reescreveu (07:35 de 14/10). Suspeita: o host regenera o `.ini` no boot; não confirmado.
- Em 14/10 o host tinha **swap esgotado** (510 de 511 MB) com ~1,4 GB disponíveis; o host é de 4 GB e divide memória com Keycloak, MCP, scheduler, mariadb e outro app uwsgi. Não aumentar workers sem medir.

## 2. Fase 1 — monitor do scheduler (`scripts/monitor_scheduler.sh`)

Mesmo molde do monitor do MCP.

- Saudável (PID gerenciado e heartbeat com menos de 90 s): não faz nada e não escreve no log.
- Só age depois de **2 falhas consecutivas** (`APP32_SCHEDULER_MONITOR_FAIL_THRESHOLD`, padrão 2; cerca de 6 minutos), para não reagir a um deploy ou reinício em andamento.
- A única ação é `manage_scheduler.sh start`, idempotente, protegido pelo lock do manager (o mesmo do deploy) e pelo `flock` do `run_scheduler.py`. Nunca toca em uwsgi, MCP, nginx nem Keycloak.
- Limite conhecido: cobre processo morto e heartbeat parado; não detecta um job travado dentro de um scheduler vivo.

**Instalação (usuário `app`, depois do deploy que traz o script):**

```cron
*/3 * * * * cd /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32 && bash scripts/monitor_scheduler.sh >> logs/scheduler_monitor.log 2>&1
```

**Teste controlado (só depois das 21h):** `bash scripts/manage_scheduler.sh stop`; em até 6 a 9 minutos `logs/scheduler_monitor.log` deve registrar "Scheduler reparado com sucesso pelo monitor" e `manage_scheduler.sh health` voltar saudável. Custo: alguns minutos sem rotinas, com recuperação de atrasadas pelo próprio agendador.

**Reversão:** remover a linha do cron.

## 3. Fase 2 — causa das travadas (sem código novo)

O diagnóstico já existe em `utils/slow_request_probe.py`, desligado por padrão. Ligar pelo `.env` e reiniciar o web (deploy `quick`):

```
SLOW_REQUEST_STACK_ENABLED=1
SLOW_REQUEST_STACK_SECONDS=20
```

Quando uma requisição passar de 20 s, o app registra no log do uwsgi uma linha JSON `slow_request_stack` com a pilha da thread (arquivo, linha e função, sem caminho, query nem dados). No máximo 16 temporizadores simultâneos; não cancela a requisição. Ler com `grep -a slow_request_stack log/uwsgi/uwsgi.log`.

**Reversão:** remover as duas linhas do `.env` (ou `SLOW_REQUEST_STACK_ENABLED=0`) e reiniciar o web. Observação: o `uwsgi.ini` não define `enable-threads`; o temporizador roda enquanto a requisição está em chamada bloqueante, que é o caso das travadas observadas.

## 4. Fases seguintes (só com evidência das anteriores)

- **Fase 3, workers do uwsgi:** medir memória com 2 workers por alguns dias; descobrir o que reescreve o `uwsgi.ini` no boot; só então tornar o valor persistente, com backup do `.ini`. Não mexer no HARAKIRI antes de achar a causa.
- **Fase 4, rotação dos logs próprios:** ver a seção 4.1 (implementada em `scripts/rotate_app_logs.sh`).

### 4.1 Fase 4 — rotação dos logs do scheduler, do MCP e dos monitores

`logs/scheduler_stderr.log` chegou a 188 MB. O script `scripts/rotate_app_logs.sh` rotaciona **uma lista fixa** de arquivos de `logs/` (`scheduler_stderr.log`, `scheduler_stdout.log`, `mcp_http_stderr.log`, `mcp_http_stdout.log`, `mcp_http_monitor.log`, `scheduler_monitor.log`). Nunca toca em uwsgi, nginx, banco ou `.env`, e não reinicia nada.

- Só rotaciona arquivo acima de 50 MB (`APP32_LOG_ROTATE_MAX_BYTES`).
- Método copiar e truncar: o scheduler e o MCP gravam com `>>` (append), então continuam no fim do arquivo, sem buraco. A janela de perda é de milissegundos entre a cópia e o truncamento.
- Confere espaço livre (precisa de 2x o tamanho), compacta com `nice` e mantém só os 3 `.gz` mais recentes por log (`APP32_LOG_ROTATE_KEEP`).
- Lock próprio; `--dry-run` mostra o que faria sem alterar nada.

**Primeira vez, à mão, em horário calmo** (fora de 08:25 a 08:40 e dos backups das 03, 07, 12, 18 e 22 h):

```bash
cd /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32
bash scripts/rotate_app_logs.sh --dry-run        # só mostra o plano
nice -n 19 bash scripts/rotate_app_logs.sh       # rotaciona de verdade
ls -la logs/scheduler_stderr.log*                # o original zerado e o .gz
```

**Cron diário (depois da primeira execução bem-sucedida):**

```cron
10 4 * * * cd /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32 && bash scripts/rotate_app_logs.sh >> logs/rotate_app_logs.log 2>&1
```

**Reversão:** remover a linha do cron. Os `.gz` já gerados são só cópias e podem ser apagados quando quiser. Observação: os logs do nginx e do uwsgi pertencem ao host (root) e não são tratados aqui; a rotação do nginx sem reabrir o arquivo (o `access.log` fica vazio e o nginx grava em `access.log.1`) é um achado separado para o suporte do host.

## 5. Verificações rápidas

```bash
bash scripts/manage_scheduler.sh health        # PID gerenciado e heartbeat
tail -n 20 logs/scheduler_monitor.log          # só tem linhas quando houve falha
python3 - <<'PY'                               # workers do uwsgi
import socket, json
s = socket.socket(socket.AF_UNIX); s.connect("/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/etc/uwsgi/stats")
d = b""
while (c := s.recv(65536)): d += c
j = json.loads(d); print(len(j["workers"]), "workers, fila", j.get("listen_queue"))
PY
```
