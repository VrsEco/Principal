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

echo "----------------------------------------------------"
echo "🚀 INICIANDO ATUALIZAÇÃO: $(date)"
echo "----------------------------------------------------"

# 1. Sincronia Git
echo "📂 Sincronizando código com repositório central..."
cd $APP
git fetch origin main
git reset --hard origin/main
echo "✅ Código atualizado com sucesso."

# 2. Dependências
echo "📦 Atualizando dependências Python..."
$PIP install -r requirements.txt --quiet
echo "✅ Dependências em conformidade."

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
if [ -f "passenger_wsgi.py" ]; then
    touch passenger_wsgi.py
fi
if [ -f "$WWW/passenger_wsgi.py" ]; then
    touch "$WWW/passenger_wsgi.py"
fi

echo "----------------------------------------------------"
echo "✨ DEPLOY CONCLUÍDO COM SUCESSO!"
echo "----------------------------------------------------"
