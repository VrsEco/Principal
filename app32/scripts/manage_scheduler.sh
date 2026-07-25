#!/bin/bash
# Gerenciador idempotente do scheduler dedicado do APP32.
# Uso: scripts/manage_scheduler.sh start|stop|restart|status|health

set -euo pipefail

BASE="${APP32_BASE_DIR:-/srv/appgestaoversuscombr.45a4cd4b.configr.cloud}"
APP="${APP32_APP_DIR:-$BASE/www/app32}"
PYTHON="${APP32_PYTHON:-$BASE/.virtualenv/3.12/bin/python}"
LOG_DIR="$APP/logs"
TMP_DIR="$APP/tmp"
PID_FILE="$TMP_DIR/scheduler_runtime.pid"
MANAGER_LOCK_DIR="$TMP_DIR/scheduler_manager.lock"
HEARTBEAT_FILE="$TMP_DIR/scheduler_heartbeat.json"
STDOUT_LOG="$LOG_DIR/scheduler_stdout.log"
STDERR_LOG="$LOG_DIR/scheduler_stderr.log"
RUNNER="$APP/scripts/run_scheduler.py"

mkdir -p "$LOG_DIR" "$TMP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

managed_pid() {
    local pid
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        if tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q "run_scheduler.py"; then
            echo "$pid"
        fi
    fi
}

heartbeat_ok() {
    [ -s "$HEARTBEAT_FILE" ] || return 1
    local modified now
    modified="$(stat -c %Y "$HEARTBEAT_FILE" 2>/dev/null || echo 0)"
    now="$(date +%s)"
    [ $((now - modified)) -le 90 ]
}

wait_for_health() {
    local attempts="${1:-20}"
    for _ in $(seq 1 "$attempts"); do
        if [ -n "$(managed_pid)" ] && heartbeat_ok; then
            return 0
        fi
        sleep 1
    done
    return 1
}

acquire_lock() {
    local attempts=30
    for _ in $(seq 1 "$attempts"); do
        if mkdir "$MANAGER_LOCK_DIR" 2>/dev/null; then
            trap 'rm -rf "$MANAGER_LOCK_DIR"' EXIT
            return 0
        fi
        sleep 1
    done
    log "ERRO: não foi possível adquirir lock do gerenciador do scheduler."
    return 1
}

stop_scheduler() {
    local pid
    pid="$(managed_pid)"
    if [ -n "$pid" ]; then
        log "Encerrando scheduler dedicado: PID $pid"
        kill -TERM "$pid" 2>/dev/null || true
        for _ in $(seq 1 20); do
            if ! kill -0 "$pid" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        if kill -0 "$pid" 2>/dev/null; then
            log "Scheduler não encerrou no prazo; forçando PID $pid"
            kill -KILL "$pid" 2>/dev/null || true
        fi
    else
        log "Nenhum scheduler dedicado gerenciado está ativo."
    fi
    rm -f "$PID_FILE" "$HEARTBEAT_FILE"
}

start_scheduler() {
    local pid
    pid="$(managed_pid)"
    if [ -n "$pid" ] && heartbeat_ok; then
        log "Scheduler já está saudável. PID $pid"
        return 0
    fi
    if [ -n "$pid" ]; then
        stop_scheduler
    fi

    log "Iniciando scheduler dedicado do APP32."
    nohup env \
        APP_BOOTSTRAP_DB_SCHEMA=0 \
        APP_BOOTSTRAP_RUNTIME_SERVICES=0 \
        FLASK_CONFIG=production \
        "$PYTHON" "$RUNNER" \
        >> "$STDOUT_LOG" 2>> "$STDERR_LOG" < /dev/null &
    echo "$!" > "$PID_FILE"

    if ! wait_for_health 30; then
        log "ERRO: scheduler não publicou heartbeat após a inicialização."
        tail -n 60 "$STDERR_LOG" 2>/dev/null || true
        return 1
    fi
    log "Scheduler dedicado saudável. PID $(managed_pid)"
}

status_scheduler() {
    local pid
    pid="$(managed_pid)"
    echo "pid_file=$(cat "$PID_FILE" 2>/dev/null || true)"
    echo "managed_pid=${pid:-}"
    if heartbeat_ok; then
        echo "heartbeat=ok"
        cat "$HEARTBEAT_FILE"
        echo
    else
        echo "heartbeat=fail"
    fi
}

ACTION="${1:-status}"
case "$ACTION" in
    start)
        acquire_lock
        start_scheduler
        ;;
    stop)
        acquire_lock
        stop_scheduler
        ;;
    restart)
        acquire_lock
        stop_scheduler
        start_scheduler
        ;;
    health)
        if [ -n "$(managed_pid)" ] && heartbeat_ok; then
            cat "$HEARTBEAT_FILE"
            echo
        else
            exit 1
        fi
        ;;
    status)
        status_scheduler
        ;;
    *)
        echo "Uso: $0 start|stop|restart|status|health" >&2
        exit 2
        ;;
esac
