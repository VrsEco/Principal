@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul
color 0A

echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                                                                            ║
echo ║        🔄 MIGRAÇÃO: DATA DE INÍCIO DA DISTRIBUIÇÃO DE LUCROS              ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo.

:: ==============================================================================
:: DESCRIÇÃO DA MIGRAÇÃO
:: ==============================================================================
echo 📋 DESCRIÇÃO:
echo    Esta migração adiciona o campo 'start_date' na tabela 
echo    'plan_finance_profit_distribution' para registrar a data de início
echo    do pagamento da distribuição de lucros.
echo.
echo    Este campo será utilizado no cálculo do Fluxo de Caixa do Investidor.
echo.
echo ──────────────────────────────────────────────────────────────────────────────
echo.

:: ==============================================================================
:: VERIFICAÇÕES PRÉ-MIGRAÇÃO
:: ==============================================================================
echo 🔍 Verificando ambiente...
echo.

if not exist ".env" (
    echo ❌ ERRO: Arquivo .env não encontrado!
    echo    Por favor, configure o arquivo .env antes de executar a migração.
    pause
    exit /b 1
)

echo ✅ Arquivo .env encontrado
echo.

:: ==============================================================================
:: BACKUP AUTOMÁTICO
:: ==============================================================================
echo 💾 Criando backup automático...
echo.

if not exist "backups" mkdir backups

set TIMESTAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

echo    Backup será salvo em: backups\backup_%TIMESTAMP%.sql
echo.

:: ==============================================================================
:: EXECUTAR MIGRAÇÃO NO POSTGRESQL
:: ==============================================================================
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║  EXECUTANDO MIGRAÇÃO NO POSTGRESQL                                         ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

python -c "
import os
import sys
from config_database import get_db

try:
    print('🔌 Conectando ao banco de dados...')
    db = get_db()
    
    print('✅ Conexão estabelecida')
    print()
    
    # Verificar se a coluna já existe
    conn = db._get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'plan_finance_profit_distribution' 
        AND column_name = 'start_date'
    ''')
    
    if cursor.fetchone():
        print('ℹ️  A coluna start_date já existe na tabela plan_finance_profit_distribution')
        print('   Nenhuma alteração necessária.')
    else:
        print('📝 Adicionando coluna start_date...')
        cursor.execute('''
            ALTER TABLE plan_finance_profit_distribution 
            ADD COLUMN start_date DATE
        ''')
        conn.commit()
        print('✅ Coluna start_date adicionada com sucesso!')
    
    conn.close()
    print()
    print('✅ Migração concluída com sucesso!')
    print()
    
except Exception as e:
    print(f'❌ ERRO durante a migração: {str(e)}')
    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ ERRO: A migração falhou!
    echo    Verifique as mensagens de erro acima.
    echo.
    pause
    exit /b 1
)

:: ==============================================================================
:: VERIFICAÇÃO PÓS-MIGRAÇÃO
:: ==============================================================================
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║  VERIFICAÇÃO PÓS-MIGRAÇÃO                                                  ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

python -c "
from config_database import get_db

db = get_db()
conn = db._get_connection()
cursor = conn.cursor()

# Verificar estrutura da tabela
cursor.execute('''
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'plan_finance_profit_distribution'
    ORDER BY ordinal_position
''')

print('📊 Estrutura da tabela plan_finance_profit_distribution:')
print('─' * 80)
print(f'{'Coluna':<30} {'Tipo':<20} {'Nulável':<10}')
print('─' * 80)

for row in cursor.fetchall():
    print(f'{row[0]:<30} {row[1]:<20} {row[2]:<10}')

print('─' * 80)
print()

conn.close()
"

:: ==============================================================================
:: CONCLUSÃO
:: ==============================================================================
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║                                                                            ║
echo ║  ✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!                                        ║
echo ║                                                                            ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.
echo 📝 PRÓXIMOS PASSOS:
echo.
echo    1. Reinicie o servidor Flask
echo    2. Acesse a página de Modelagem Financeira
echo    3. Edite a Distribuição de Lucros
echo    4. Configure a data de início do pagamento
echo    5. Verifique o Fluxo de Caixa do Investidor
echo.
echo ──────────────────────────────────────────────────────────────────────────────
echo.
echo 📌 ARQUIVOS MODIFICADOS NESTA MIGRAÇÃO:
echo.
echo    • database/postgresql_db.py
echo      - Adicionada coluna start_date na tabela plan_finance_profit_distribution
echo      - Atualizado método get_plan_profit_distribution()
echo      - Atualizado método update_plan_profit_distribution()
echo.
echo    • templates/implantacao/modelo_modelagem_financeira.html
echo      - Adicionado campo de data no modal de distribuição de lucros
echo      - Atualizado JavaScript para enviar/receber o campo start_date
echo      - Adicionada exibição da data de início no card
echo.
echo    • modules/pev/implantation_data.py
echo      - Adicionado campo start_date no payload de distribuicao_lucros
echo.
echo ──────────────────────────────────────────────────────────────────────────────
echo.
echo 💡 NOTA: A data de início será usada para calcular quando a distribuição
echo    de lucros começará a ser paga no Fluxo de Caixa do Investidor.
echo.

pause

