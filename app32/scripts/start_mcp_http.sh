#!/bin/bash
set -euo pipefail

BASE="/srv/appgestaoversuscombr.45a4cd4b.configr.cloud"
APP_DIR="$BASE/www/app32"
PYTHON_BIN="${APP32_MCP_HTTP_PYTHON:-$BASE/.virtualenv/3.12/bin/python}"
cd "$APP_DIR"

export PYTHONPATH="$APP_DIR"
export APP32_MCP_HTTP_APP_DIR="$APP_DIR"

exec "$PYTHON_BIN" - <<'PY'
import os
import runpy
import sys

app_dir = os.path.abspath(os.environ["APP32_MCP_HTTP_APP_DIR"])
shadow_path = os.path.join(app_dir, "src", "core")

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(os.path.join(app_dir, ".env"), override=False)

normalized_sys_path = []
for entry in sys.path:
    resolved = os.path.abspath(entry or os.getcwd())
    if resolved == shadow_path:
        continue
    if resolved == app_dir:
        continue
    normalized_sys_path.append(entry)

sys.path[:] = [app_dir, *normalized_sys_path]
os.environ.setdefault("APP32_MCP_HTTP_HOST", "127.0.0.1")
os.environ.setdefault("APP32_MCP_HTTP_PORT", "8101")
os.environ.setdefault("APP32_MCP_PUBLIC_BASE_URL", "https://app.gestaoversus.com.br")
os.environ.setdefault("APP32_MCP_CLIENT", "claude_remote_connector")
os.environ.setdefault("APP32_MCP_CONNECTOR", "claude_remote_connector")
runpy.run_module("src.core.mcp_http_server", run_name="__main__")
PY
