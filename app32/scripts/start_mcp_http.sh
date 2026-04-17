#!/bin/bash
set -euo pipefail

BASE="/srv/appgestaoversuscombr.45a4cd4b.configr.cloud"
APP_DIR="$BASE/www/app32"
PYTHON_BIN="${APP32_MCP_HTTP_PYTHON:-$BASE/.virtualenv/3.12/bin/python}"
HOST="${APP32_MCP_HTTP_HOST:-127.0.0.1}"
PORT="${APP32_MCP_HTTP_PORT:-8101}"
PUBLIC_BASE_URL="${APP32_MCP_PUBLIC_BASE_URL:-https://app.gestaoversus.com.br}"

cd "$APP_DIR"

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

export PYTHONPATH="$APP_DIR"
export APP32_MCP_HTTP_HOST="$HOST"
export APP32_MCP_HTTP_PORT="$PORT"
export APP32_MCP_PUBLIC_BASE_URL="$PUBLIC_BASE_URL"

exec "$PYTHON_BIN" -m app32.src.core.mcp_http_server
