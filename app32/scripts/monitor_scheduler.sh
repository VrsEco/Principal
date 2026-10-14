#!/bin/bash
# Monitor leve do scheduler dedicado do APP32 (mesmo molde de monitor_mcp_http.sh).
# Uso recomendado via cron do usuário app:
#   */3 * * * * cd /srv/.../www/app32 && bash scripts/monitor_scheduler.sh >> logs/scheduler_monitor.log 2>&1
#
# Regras de segurança (o monitor nunca pode piorar a estabilidade):
# - só olha o health do manager (PID gerenciado + heartbeat com menos de 90 s);
# - saudável: não faz nada e não escreve no log;
# - só age depois de FAIL_THRESHOLD falhas consecutivas (padrão 2, cerca de 6 minutos);
# - a única ação é "manage_scheduler.sh start", que é idempotente e usa o lock do manager e o flock do runner;
# - nunca reinicia uwsgi, MCP, nginx nem Keycloak.

set -euo pipefail

BASE="${APP32_BASE_DIR:-/srv/appgestaoversuscombr.45a4cd4b.configr.cloud}"
APP="${APP32_APP_DIR:-$BASE/www/app32}"
FAIL_THRESHOLD="${APP32_SCHEDULER_MONITOR_FAIL_THRESHOLD:-2}"

LOG_DIR="$APP/logs"
TMP_DIR="$APP/tmp"
MANAGER="$APP/scripts/manage_scheduler.sh"
STATE_FILE="$TMP_DIR/scheduler_monitor.failures"
LOCK_DIR="$TMP_DIR/scheduler_monitor.lock"

mkdir -p "$LOG_DIR" "$TMP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

acquire_lock() {
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        trap 'rm -rf "$LOCK_DIR"' EXIT
        return 0
    fi
    log "Monitor do scheduler já em execução; saindo sem ação."
    exit 0
}

health_ok() {
    bash "$MANAGER" health >/dev/null 2>&1
}

read_failures() {
    cat "$STATE_FILE" 2>/dev/null || echo "0"
}

write_failures() {
    echo "$1" > "$STATE_FILE"
}

acquire_lock

failures="$(read_failures)"
case "$failures" in
    ''|*[!0-9]*) failures=0 ;;
esac

if health_ok; then
    if [ "$failures" -gt 0 ]; then
        log "Scheduler saudável novamente; zerando falhas (eram $failures)."
    fi
    write_failures 0
    exit 0
fi

failures=$((failures + 1))
write_failures "$failures"
log "Scheduler sem heartbeat saudável. falhas_consecutivas=$failures threshold=$FAIL_THRESHOLD"

if [ "$failures" -lt "$FAIL_THRESHOLD" ]; then
    log "Aguardando nova falha antes de agir, para evitar falso positivo (deploy, reinício em andamento)."
    exit 0
fi

log "Threshold atingido; iniciando o scheduler pelo manager idempotente (start)."
if bash "$MANAGER" start; then
    if health_ok; then
        write_failures 0
        log "Scheduler reparado com sucesso pelo monitor."
        exit 0
    fi
    log "start executado, mas o health ainda falha."
    exit 1
fi

log "Falha ao executar start do scheduler."
exit 1
