#!/bin/bash
# Script para configurar backup automático via CRON
# GestaoVersus (APP30)

set -e

echo "🕐 Configurando backup automático via CRON..."

# Variáveis
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_SCRIPT="$SCRIPT_DIR/backup_database.py"
LOG_FILE="$PROJECT_DIR/logs/backup_cron.log"

# Verificar se o script existe
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "❌ Script de backup não encontrado: $BACKUP_SCRIPT"
    exit 1
fi

# Criar diretório de logs se não existir
mkdir -p "$PROJECT_DIR/logs"

# Job do CRON (todos os dias às 3:00 AM)
CRON_JOB="0 3 * * * cd $PROJECT_DIR && python3 $BACKUP_SCRIPT >> $LOG_FILE 2>&1"

# Verificar se já existe
crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT" && {
    echo "⚠️  Job do CRON já existe. Removendo antiga..."
    crontab -l | grep -v "$BACKUP_SCRIPT" | crontab -
}

# Adicionar novo job
echo "Adicionando job do CRON..."
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Backup automático configurado!"
echo ""
echo "Agenda: Todos os dias às 3:00 AM"
echo "Script: $BACKUP_SCRIPT"
echo "Logs: $LOG_FILE"
echo ""
echo "Para verificar: crontab -l"
echo "Para remover: crontab -e (e remova a linha)"


