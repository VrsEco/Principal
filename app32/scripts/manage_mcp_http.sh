#!/bin/bash
# Gerenciador idempotente do runtime MCP HTTP remoto do APP32.
# Uso:
#   scripts/manage_mcp_http.sh start|stop|restart|status|health

set -euo pipefail

BASE="${APP32_BASE_DIR:-/srv/appgestaoversuscombr.45a4cd4b.configr.cloud}"
APP="${APP32_APP_DIR:-$BASE/www/app32}"
PORT="${APP32_MCP_HTTP_PORT:-8101}"
HOST="${APP32_MCP_HTTP_HOST:-127.0.0.1}"
PUBLIC_BASE="${APP32_MCP_PUBLIC_BASE_URL:-https://app.gestaoversus.com.br}"
HEALTH_ATTEMPTS="${APP32_MCP_HEALTH_ATTEMPTS:-240}"

LOG_DIR="$APP/logs"
TMP_DIR="$APP/tmp"
PID_FILE="$TMP_DIR/mcp_http.pid"
LOCK_DIR="$TMP_DIR/mcp_http.lock"
STDOUT_LOG="$LOG_DIR/mcp_http_stdout.log"
STDERR_LOG="$LOG_DIR/mcp_http_stderr.log"
HEALTH_URL="http://$HOST:$PORT/healthz"
PUBLIC_HEALTH_URL="$PUBLIC_BASE/mcp/healthz"
START_SCRIPT="$APP/scripts/start_mcp_http.sh"

mkdir -p "$LOG_DIR" "$TMP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

port_pids() {
    lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true
}

health_ok() {
    curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null 2>&1
}

public_health_ok() {
    curl -k -fsS --max-time 8 "$PUBLIC_HEALTH_URL" >/dev/null 2>&1
}

wait_for_no_port() {
    local attempts="${1:-20}"
    for _ in $(seq 1 "$attempts"); do
        if [ -z "$(port_pids)" ]; then
            return 0
        fi
        sleep 1
    done
    return 1
}

wait_for_health() {
    local attempts="${1:-30}"
    for _ in $(seq 1 "$attempts"); do
        if health_ok; then
            return 0
        fi
        sleep 1
    done
    return 1
}

acquire_lock() {
    local attempts=30
    for _ in $(seq 1 "$attempts"); do
        if mkdir "$LOCK_DIR" 2>/dev/null; then
            trap 'rm -rf "$LOCK_DIR"' EXIT
            return 0
        fi
        sleep 1
    done
    log "ERRO: não foi possível adquirir lock MCP: $LOCK_DIR"
    return 1
}

stop_mcp() {
    local pids
    pids="$(port_pids)"
    if [ -n "$pids" ]; then
        log "Encerrando listener MCP na porta $PORT: $pids"
        kill -TERM $pids 2>/dev/null || true
        if ! wait_for_no_port 20; then
            pids="$(port_pids)"
            if [ -n "$pids" ]; then
                log "Listener MCP ainda ativo; forçando parada: $pids"
                kill -KILL $pids 2>/dev/null || true
                wait_for_no_port 5 || true
            fi
        fi
    else
        log "Nenhum listener MCP ativo na porta $PORT."
    fi
    rm -f "$PID_FILE"
}

start_mcp() {
    chmod +x "$START_SCRIPT"
    if health_ok; then
        local existing
        existing="$(port_pids)"
        log "MCP já saudável em $HEALTH_URL. PID(s): ${existing:-desconhecido}"
        return 0
    fi

    local stale
    stale="$(port_pids)"
    if [ -n "$stale" ]; then
        log "Porta $PORT ocupada, mas health falhou; reiniciando listener: $stale"
        stop_mcp
    fi

    log "Iniciando MCP HTTP em $HOST:$PORT"
    nohup env \
        APP32_MCP_PUBLIC_BASE_URL="$PUBLIC_BASE" \
        APP32_MCP_HTTP_HOST="$HOST" \
        APP32_MCP_HTTP_PORT="$PORT" \
        "$START_SCRIPT" \
        >> "$STDOUT_LOG" 2>> "$STDERR_LOG" < /dev/null &

    echo "$!" > "$PID_FILE"

    if ! wait_for_health "$HEALTH_ATTEMPTS"; then
        log "ERRO: MCP não respondeu ao health local após start."
        tail -n 40 "$STDERR_LOG" 2>/dev/null || true
        return 1
    fi

    local final_pids
    final_pids="$(port_pids)"
    log "MCP ativo em $HEALTH_URL. PID(s): ${final_pids:-desconhecido}"
}

status_mcp() {
    local pids
    pids="$(port_pids)"
    echo "port=$PORT"
    echo "pid_file=$(cat "$PID_FILE" 2>/dev/null || true)"
    echo "listener_pids=${pids:-}"
    if health_ok; then
        echo "local_health=ok"
    else
        echo "local_health=fail"
    fi
    if public_health_ok; then
        echo "public_health=ok"
    else
        echo "public_health=fail"
    fi
}

ACTION="${1:-status}"

case "$ACTION" in
    start)
        acquire_lock
        start_mcp
        ;;
    stop)
        acquire_lock
        stop_mcp
        ;;
    restart)
        acquire_lock
        stop_mcp
        start_mcp
        ;;
    health)
        if health_ok; then
            curl -fsS --max-time 5 "$HEALTH_URL"
            echo
        else
            exit 1
        fi
        ;;
    status)
        status_mcp
        ;;
    *)
        echo "Uso: $0 start|stop|restart|status|health" >&2
        exit 2
        ;;
esac
