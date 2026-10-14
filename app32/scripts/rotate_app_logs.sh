#!/bin/bash
# Rotação segura dos logs próprios do APP32 (scheduler, MCP e monitores), sem reiniciar nada.
# Uso (cron diário em horário calmo, fora de 08:25-08:40 e dos backups 03/07/12/18/22h):
#   10 4 * * * cd /srv/.../www/app32 && bash scripts/rotate_app_logs.sh >> logs/rotate_app_logs.log 2>&1
# Teste sem efeito:  bash scripts/rotate_app_logs.sh --dry-run
#
# Como é seguro:
# - só mexe numa lista fixa de arquivos de logs/ (nunca uwsgi, nginx, banco ou .env);
# - só rotaciona arquivo acima do limite (padrão 50 MB);
# - método "copiar e truncar": os processos gravam com ">>" (append), então continuam no fim do arquivo,
#   sem buraco; a janela de perda é de milissegundos entre a cópia e o truncamento;
# - confere espaço livre antes (precisa de 2x o tamanho) e usa nice para não competir com o web;
# - mantém só os N arquivos .gz mais recentes por log (padrão 3);
# - lock próprio: duas execuções não se atropelam.

set -euo pipefail

BASE="${APP32_BASE_DIR:-/srv/appgestaoversuscombr.45a4cd4b.configr.cloud}"
APP="${APP32_APP_DIR:-$BASE/www/app32}"
LOG_DIR="${APP32_LOG_DIR:-$APP/logs}"
TMP_DIR="$APP/tmp"
LOCK_DIR="$TMP_DIR/rotate_app_logs.lock"
MAX_BYTES="${APP32_LOG_ROTATE_MAX_BYTES:-52428800}"
KEEP="${APP32_LOG_ROTATE_KEEP:-3}"
FILES=(
    scheduler_stderr.log
    scheduler_stdout.log
    mcp_http_stderr.log
    mcp_http_stdout.log
    mcp_http_monitor.log
    scheduler_monitor.log
)
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

mkdir -p "$TMP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log "Rotação já em execução; saindo sem ação."
    exit 0
fi
trap 'rm -rf "$LOCK_DIR"' EXIT

low_priority() {
    if command -v nice >/dev/null 2>&1; then nice -n 19 "$@"; else "$@"; fi
}

rotated=0
for name in "${FILES[@]}"; do
    file="$LOG_DIR/$name"
    [ -f "$file" ] || continue
    size="$(stat -c %s "$file")"
    [ "$size" -gt "$MAX_BYTES" ] || continue

    avail_kb="$(df -Pk "$LOG_DIR" | awk 'NR==2 {print $4}')"
    need_kb=$(( (size * 2) / 1024 + 1 ))
    if [ "$avail_kb" -lt "$need_kb" ]; then
        log "ESPAÇO insuficiente para rotacionar $name (precisa ${need_kb} KB, livre ${avail_kb} KB); pulando."
        continue
    fi

    if [ "$DRY_RUN" -eq 1 ]; then
        log "[dry-run] rotacionaria $name (${size} bytes > ${MAX_BYTES})."
        continue
    fi

    stamp="$(date +%Y%m%d_%H%M%S)"
    tmp="$file.rotating.$stamp"
    cp "$file" "$tmp"          # cópia rápida do conteúdo atual
    : > "$file"                # trunca; quem grava em append segue no fim do arquivo
    low_priority gzip -f "$tmp"
    mv "$tmp.gz" "$file.$stamp.gz"
    log "Rotacionado $name: ${size} bytes -> $(stat -c %s "$file.$stamp.gz") bytes compactados ($name.$stamp.gz)."
    rotated=$((rotated + 1))

    # Mantém só os KEEP arquivos compactados mais recentes deste log.
    # shellcheck disable=SC2012
    ls -1t "$file".*.gz 2>/dev/null | tail -n "+$((KEEP + 1))" | while read -r old; do
        rm -f -- "$old"
        log "Removido arquivo antigo $(basename "$old")."
    done
done

[ "$rotated" -eq 0 ] && [ "$DRY_RUN" -eq 0 ] && log "Nada a rotacionar (todos abaixo de ${MAX_BYTES} bytes)."
exit 0
