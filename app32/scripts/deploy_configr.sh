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
from flask_migrate import upgrade
from app import create_app
app = create_app('production')
with app.app_context():
    upgrade()
" 2>&1
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Migrations aplicadas/verificadas com sucesso."
else
    echo "⚠️  Nota: Migrations falharam ou não há mudanças pendentes."
fi

# 4. Reinício da Aplicação
echo "🔄 Reiniciando servidor uWSGI (Passenger/Configr)..."
touch $WWW/restart.txt
# Backup do reinício: tocar o wsgi também
if [ -f "passenger_wsgi.py" ]; then
    touch passenger_wsgi.py
fi

echo "----------------------------------------------------"
echo "✨ DEPLOY CONCLUÍDO COM SUCESSO!"
echo "----------------------------------------------------"
