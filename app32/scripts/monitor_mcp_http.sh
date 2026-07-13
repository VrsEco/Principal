#!/bin/bash
# Monitor leve do runtime MCP HTTP remoto do APP32.
# Uso recomendado via cron:
#   */3 * * * * cd /srv/.../www/app32 && bash scripts/monitor_mcp_http.sh >> logs/mcp_http_monitor.log 2>&1

set -euo pipefail

BASE="${APP32_BASE_DIR:-/srv/appgestaoversuscombr.45a4cd4b.configr.cloud}"
APP="${APP32_APP_DIR:-$BASE/www/app32}"
PORT="${APP32_MCP_HTTP_PORT:-8101}"
HOST="${APP32_MCP_HTTP_HOST:-127.0.0.1}"
PUBLIC_BASE="${APP32_MCP_PUBLIC_BASE_URL:-https://app.gestaoversus.com.br}"
FAIL_THRESHOLD="${APP32_MCP_MONITOR_FAIL_THRESHOLD:-3}"

LOG_DIR="$APP/logs"
TMP_DIR="$APP/tmp"
MANAGER="$APP/scripts/manage_mcp_http.sh"
STATE_FILE="$TMP_DIR/mcp_http_monitor.failures"
LOCK_DIR="$TMP_DIR/mcp_http_monitor.lock"
LOCAL_HEALTH_URL="http://$HOST:$PORT/healthz"
PUBLIC_HEALTH_URL="$PUBLIC_BASE/mcp/healthz"

mkdir -p "$LOG_DIR" "$TMP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

acquire_lock() {
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        trap 'rm -rf "$LOCK_DIR"' EXIT
        return 0
    fi
    log "Monitor MCP já em execução; saindo sem ação."
    exit 0
}

health_ok() {
    curl -fsS --max-time 5 "$LOCAL_HEALTH_URL" >/dev/null 2>&1 \
        && curl -k -fsS --max-time 8 "$PUBLIC_HEALTH_URL" >/dev/null 2>&1
}

read_failures() {
    cat "$STATE_FILE" 2>/dev/null || echo "0"
}

write_failures() {
    echo "$1" > "$STATE_FILE"
}

acquire_lock

if health_ok; then
    write_failures 0
    log "MCP saudável. local=ok public=ok"
    exit 0
fi

failures="$(read_failures)"
case "$failures" in
    ''|*[!0-9]*) failures=0 ;;
esac
failures=$((failures + 1))
write_failures "$failures"

log "MCP health falhou. falhas_consecutivas=$failures threshold=$FAIL_THRESHOLD"

if [ "$failures" -lt "$FAIL_THRESHOLD" ]; then
    log "Aguardando nova falha antes de reiniciar para evitar falso positivo."
    exit 0
fi

log "Threshold atingido; reiniciando runtime MCP via manager idempotente."
if bash "$MANAGER" restart; then
    if health_ok; then
        write_failures 0
        log "MCP reparado com sucesso pelo monitor."
        exit 0
    fi
    log "Restart executado, mas health ainda falha."
    exit 1
fi

log "Falha ao executar restart do MCP."
exit 1
