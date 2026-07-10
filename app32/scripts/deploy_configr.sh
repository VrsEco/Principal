#!/bin/bash
# =================================================================
# SQUAD DE ENGENHARIA DE ELITE: Script de Deploy Configr
# Missão: Sincronia Total (Git -> Servidor)
# =================================================================

set -e

# Configurações de Caminho (Padrão Configr)
BASE="/srv/appgestaoversuscombr.45a4cd4b.configr.cloud"
WWW="$BASE/www"
APP="$WWW/app32"
PYTHON="$BASE/.virtualenv/3.12/bin/python"
PIP="$BASE/.virtualenv/3.12/bin/pip"
DEPLOY_STDOUT_LOG="$APP/deploy_stdout.txt"
DEPLOY_STDERR_LOG="$APP/deploy_stderr.txt"
WEB_HEALTH_URL="http://127.0.0.1/healthz"
WEB_HEALTH_HOST="app.gestaoversus.com.br"

mkdir -p "$APP"
: > "$DEPLOY_STDOUT_LOG"
: > "$DEPLOY_STDERR_LOG"
exec > >(tee "$DEPLOY_STDOUT_LOG") 2> >(tee "$DEPLOY_STDERR_LOG" >&2)

echo "----------------------------------------------------"
echo "🚀 INICIANDO ATUALIZAÇÃO: $(date)"
echo "----------------------------------------------------"

# 1. Sincronia Git
echo "📂 Sincronizando código com repositório central..."
cd $APP
git fetch origin +refs/heads/main:refs/remotes/origin/main
git reset --hard origin/main
echo "✅ Código atualizado com sucesso."

# 2. Dependências
echo "📦 Atualizando dependências Python..."
$PIP install -r requirements.txt --quiet
echo "✅ Dependências em conformidade."

# 2.1 Assets canônicos de portfólio de processos
echo "🖼️  Sincronizando assets canônicos do portfólio de processos..."
$PYTHON scripts/sync_process_portfolio_assets.py
echo "✅ Assets de portfólio sincronizados."

# 3. Migrações de Banco (Alembic)
echo "🗃️  Verificando migrações de banco de dados..."
set +e
$PYTHON -c "
import sys, os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
os.environ.setdefault('FLASK_CONFIG', 'production')
os.environ['APP_BOOTSTRAP_DB_SCHEMA'] = '0'
os.environ['APP_BOOTSTRAP_RUNTIME_SERVICES'] = '0'
from flask_migrate import upgrade
from app import create_app
app = create_app('production')
with app.app_context():
    upgrade(revision='heads')
" 2>&1
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Migrations aplicadas/verificadas com sucesso."
else
    echo "⚠️  Nota: Migrations falharam ou não há mudanças pendentes."
fi

# 3.1 Runtime uWSGI: buffering de POST + resiliência básica
# - Evita que requisições POST pequenas (/login, /portal, APIs JSON) prendam o
#   worker quando o upstream repassa corpo sem buffering.
# - Sobe 2 workers para reduzir indisponibilidade total durante reciclagem.
# - Aplica reciclagem preventiva de workers para reduzir degradação acumulada.
echo "🛡️  Garantindo parâmetros de resiliência do uWSGI..."
mkdir -p "$BASE/etc/uwsgi/conf.d"
cat > "$BASE/etc/uwsgi/conf.d/app32_post_buffering.ini" <<'EOF'
post-buffering = 65536
workers = 2
max-requests = 1000
max-worker-lifetime = 3600
reload-on-rss = 768
thunder-lock = true
env = APP_BOOTSTRAP_RUNTIME_SERVICES=0
EOF
UWSGI_INI="$BASE/etc/uwsgi/uwsgi.ini"
if [ -f "$UWSGI_INI" ] && ! grep -qE '^[[:space:]]*post-buffering[[:space:]]*=' "$UWSGI_INI"; then
    "$PYTHON" - "$UWSGI_INI" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
lines = path.read_text().splitlines()
out = []
inserted = False
for line in lines:
    out.append(line)
    if not inserted and line.strip().startswith("harakiri"):
        out.append("post-buffering  = 65536")
        inserted = True
if not inserted:
    out.append("post-buffering  = 65536")
path.write_text("\n".join(out) + "\n")
PY
fi
echo "✅ parâmetros de resiliência do uWSGI configurados."

check_web_readiness() {
    curl -fsS --max-time 5 -H "Host: $WEB_HEALTH_HOST" "$WEB_HEALTH_URL" >/dev/null
}

# 4. Reinício da Aplicação
echo "🔄 Reiniciando servidor uWSGI (Configr)..."
UWSGI_APP_INI="appgestaoversuscombr.45a4cd4b.configr.cloud.ini"
set +e
UWSGI_PIDS=$(pgrep -f "uwsgi --ini $UWSGI_APP_INI")
set -e

if [ -n "$UWSGI_PIDS" ]; then
    echo "   - Encerrando workers/vassal atuais: $UWSGI_PIDS"
    set +e
    pkill -TERM -f "uwsgi --ini $UWSGI_APP_INI"
    set -e

    echo "   - Aguardando Emperor recriar o vassal..."
    RESTART_OK=0
    for i in {1..20}; do
        set +e
        NEW_UWSGI_PIDS=$(pgrep -f "uwsgi --ini $UWSGI_APP_INI")
        set -e
        if [ -n "$NEW_UWSGI_PIDS" ]; then
            echo "   - uWSGI ativo novamente com PID(s): $NEW_UWSGI_PIDS"
            RESTART_OK=1
            break
        fi
        sleep 1
    done

    if [ "$RESTART_OK" -ne 1 ]; then
        echo "⚠️  Aviso: não foi possível confirmar restart do uWSGI por PID."
    fi
else
    echo "⚠️  Aviso: PIDs do uWSGI não encontrados; aplicando fallback por toque de arquivos."
fi

# Fallback/pass-through para ambientes que ainda respeitam restart por arquivo.
touch $WWW/restart.txt
mkdir -p $WWW/tmp && touch $WWW/tmp/restart.txt
mkdir -p $APP/tmp && touch $APP/tmp/restart.txt
touch $APP/restart.txt
if [ -f "passenger_wsgi.py" ]; then
    touch passenger_wsgi.py
fi
if [ -f "$WWW/passenger_wsgi.py" ]; then
    touch "$WWW/passenger_wsgi.py"
fi

echo "🌐 Validando readiness HTTP do app web..."
WEB_READY=0
for i in {1..60}; do
    set +e
    check_web_readiness
    WEB_HEALTH_CODE=$?
    set -e
    if [ "$WEB_HEALTH_CODE" -eq 0 ]; then
        WEB_READY=1
        echo "✅ App web respondeu ao healthcheck em ${i}s."
        break
    fi
    sleep 1
done

if [ "$WEB_READY" -ne 1 ]; then
    echo "❌ ERRO: app web não respondeu ao healthcheck local após restart."
    echo "   URL: $WEB_HEALTH_URL (Host: $WEB_HEALTH_HOST)"
    exit 1
fi

# 5. MCP HTTP remoto (reinício controlado para refletir novas tools/contratos após deploy)
echo "🧠 Reiniciando runtime MCP HTTP remoto para refletir o código recém-publicado..."
MCP_HEALTH_URL="http://127.0.0.1:8101/healthz"
MCP_PUBLIC_HEALTH_URL="https://app.gestaoversus.com.br/mcp/healthz"
MCP_STDOUT_LOG="$APP/logs/mcp_http_stdout.log"
MCP_STDERR_LOG="$APP/logs/mcp_http_stderr.log"

if [ -f "$APP/scripts/start_mcp_http.sh" ]; then
    mkdir -p "$APP/logs"
    chmod +x "$APP/scripts/start_mcp_http.sh"
    if [ -f "$APP/scripts/manage_mcp_http.sh" ]; then
        echo "   - Usando gerenciador MCP idempotente: scripts/manage_mcp_http.sh restart"
        chmod +x "$APP/scripts/manage_mcp_http.sh"
        APP32_MCP_PUBLIC_BASE_URL="https://app.gestaoversus.com.br" \
        APP32_MCP_HTTP_PORT="8101" \
        bash "$APP/scripts/manage_mcp_http.sh" restart
    else
        echo "⚠️  Aviso: manage_mcp_http.sh não encontrado; usando start direto legado."
        MCP_LEGACY_PIDS=$(lsof -tiTCP:8101 -sTCP:LISTEN 2>/dev/null || true)
        if [ -n "$MCP_LEGACY_PIDS" ]; then
            echo "   - Encerrando listener MCP legado na porta 8101: $MCP_LEGACY_PIDS"
            kill -TERM $MCP_LEGACY_PIDS 2>/dev/null || true
            sleep 3
        fi
        nohup env \
            APP32_MCP_PUBLIC_BASE_URL="https://app.gestaoversus.com.br" \
            APP32_MCP_HTTP_PORT="8101" \
            "$APP/scripts/start_mcp_http.sh" \
            >> "$MCP_STDOUT_LOG" 2>> "$MCP_STDERR_LOG" < /dev/null &
    fi

    MCP_LOCAL_OK=0
    for i in {1..30}; do
        set +e
        curl -fsS --max-time 5 "$MCP_HEALTH_URL" >/dev/null
        MCP_HEALTH_CODE=$?
        set -e
        if [ "$MCP_HEALTH_CODE" -eq 0 ]; then
            MCP_LOCAL_OK=1
            break
        fi
        sleep 1
    done

    MCP_FINAL_PIDS=$(lsof -tiTCP:8101 -sTCP:LISTEN 2>/dev/null || true)
    if [ -n "$MCP_FINAL_PIDS" ]; then
        echo "   - Listener MCP HTTP ativo na porta 8101 com PID(s): $MCP_FINAL_PIDS"
    else
        echo "⚠️  Aviso: nenhum PID do listener MCP HTTP foi encontrado na porta 8101 após o restart."
    fi

    MCP_PUBLIC_OK=0
    if [ "$MCP_LOCAL_OK" -eq 1 ]; then
        for i in {1..20}; do
            set +e
            curl -k -fsS --max-time 8 "$MCP_PUBLIC_HEALTH_URL" >/dev/null
            MCP_PUBLIC_HEALTH_CODE=$?
            set -e
            if [ "$MCP_PUBLIC_HEALTH_CODE" -eq 0 ]; then
                MCP_PUBLIC_OK=1
                break
            fi
            sleep 1
        done
    fi

    if [ "$MCP_LOCAL_OK" -eq 1 ]; then
        echo "✅ MCP HTTP remoto ativo em 127.0.0.1:8101 com código atualizado."
    else
        echo "⚠️  Aviso: MCP HTTP remoto não respondeu ao health local após restart."
    fi

    if [ "$MCP_PUBLIC_OK" -eq 1 ]; then
        echo "✅ MCP HTTP remoto respondeu também no health público /mcp/healthz."
    else
        echo "⚠️  Aviso: MCP HTTP remoto não respondeu ao health público /mcp/healthz após restart."
    fi
else
    echo "⚠️  Aviso: script start_mcp_http.sh não encontrado; pulando MCP HTTP remoto."
fi

echo "----------------------------------------------------"
echo "✨ DEPLOY CONCLUÍDO COM SUCESSO!"
echo "----------------------------------------------------"
