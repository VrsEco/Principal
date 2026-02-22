@echo off
chcp 65001 > nul
cls
echo ========================================
echo CRIAR TABELA CAPITAL DE GIRO
echo ========================================
echo.

docker-compose exec -T app python -c "from database.postgres_helper import get_engine; from sqlalchemy import text; e = get_engine(); c = e.connect(); c.execute(text('CREATE TABLE IF NOT EXISTS plan_finance_capital_giro (id SERIAL PRIMARY KEY, plan_id INTEGER NOT NULL, item_type VARCHAR(50) NOT NULL, contribution_date DATE NOT NULL, amount NUMERIC(15,2) NOT NULL, description TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_deleted BOOLEAN DEFAULT FALSE)')); c.commit(); c.close(); print('TABELA CRIADA!')"

echo.
echo ========================================
echo MIGRATION APLICADA!
echo ========================================
echo.
echo Agora teste salvar no modal!
echo.
pause

