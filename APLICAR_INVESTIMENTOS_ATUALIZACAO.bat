@echo off
chcp 65001 > nul
echo ============================================
echo   APLICAR ATUALIZAÇÃO DE INVESTIMENTOS
echo ============================================
echo.
echo Este script irá:
echo   1. Verificar e criar tabelas de investimento
echo   2. Aplicar migration com novos campos
echo   3. Popular categorias e itens padrão
echo.
echo Pressione qualquer tecla para continuar...
pause > nul

echo.
echo [1/4] Criando tabelas de investimento...
python -c "from config_database import get_db; db = get_db(); conn = db._get_connection(); cur = conn.cursor(); cur.execute(open('migrations/create_investment_contributions.sql', 'r', encoding='utf-8').read()); conn.commit(); print('✅ Tabelas criadas/verificadas!'); conn.close()"

if errorlevel 1 (
    echo ❌ Erro ao criar tabelas!
    pause
    exit /b 1
)

echo.
echo [2/4] Aplicando migration de novos campos...
python -c "from config_database import get_db; db = get_db(); conn = db._get_connection(); cur = conn.cursor(); cur.execute(open('migrations/20251028_update_investment_contributions.sql', 'r', encoding='utf-8').read()); conn.commit(); print('✅ Migration aplicada com sucesso!'); conn.close()"

if errorlevel 1 (
    echo ❌ Erro ao aplicar migration!
    pause
    exit /b 1
)

echo.
echo [3/4] Populando categorias e itens padrão...
python scripts/seed_investment_items.py

if errorlevel 1 (
    echo ❌ Erro ao popular dados!
    pause
    exit /b 1
)

echo.
echo [4/4] Verificando alterações...
python -c "from config_database import get_db; db = get_db(); conn = db._get_connection(); cur = conn.cursor(); cur.execute('SELECT column_name FROM information_schema.columns WHERE table_name = \'plan_finance_investment_contributions\' ORDER BY ordinal_position'); cols = [row[0] for row in cur.fetchall()]; print('Colunas da tabela:'); [print(f'  - {col}') for col in cols]; conn.close()"

echo.
echo ============================================
echo   ✅ ATUALIZAÇÃO CONCLUÍDA!
echo ============================================
echo.
echo Novos campos adicionados:
echo   - description (Descrição)
echo   - system_suggestion (Sugestão do sistema)
echo   - adjusted_value (Valor ajustado)
echo   - calculation_memo (Memória de cálculo)
echo.
echo Categorias e itens padrão criados:
echo   - Capital de Giro: Caixa, Recebíveis, Estoques
echo   - Imobilizado: Instalações, Máquinas, Outros
echo.
echo O sistema está pronto para uso!
echo.
pause

