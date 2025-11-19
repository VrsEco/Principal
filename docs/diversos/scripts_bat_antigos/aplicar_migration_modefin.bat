@echo off
chcp 65001 > nul
echo ========================================
echo APLICAR MIGRATION MODEFIN
echo ========================================
echo.

echo Criando tabela plan_finance_capital_giro...
echo.

docker-compose exec -T app python -c "from database.postgres_helper import get_engine; from sqlalchemy import text; engine = get_engine(); conn = engine.begin(); conn.execute(text('CREATE TABLE IF NOT EXISTS plan_finance_capital_giro (id SERIAL PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE, item_type VARCHAR(50) NOT NULL, contribution_date DATE NOT NULL, amount NUMERIC(15, 2) NOT NULL DEFAULT 0, description TEXT, notes TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_deleted BOOLEAN DEFAULT FALSE)')); conn.commit(); print('Tabela criada!')"

echo.
echo Criando indices...
echo.

docker-compose exec -T app python -c "from database.postgres_helper import get_engine; from sqlalchemy import text; engine = get_engine(); conn = engine.begin(); conn.execute(text('CREATE INDEX IF NOT EXISTS idx_capital_giro_plan_id ON plan_finance_capital_giro(plan_id)')); conn.commit(); print('Indices criados!')"

echo.
echo Adicionando coluna executive_summary...
echo.

docker-compose exec -T app python -c "from database.postgres_helper import get_engine; from sqlalchemy import text; engine = get_engine(); conn = engine.begin(); conn.execute(text('ALTER TABLE plan_finance_metrics ADD COLUMN IF NOT EXISTS executive_summary TEXT')); conn.commit(); print('Coluna adicionada!')"

echo.
echo ========================================
echo MIGRATION APLICADA COM SUCESSO!
echo ========================================
echo.
echo Agora teste salvar no modal novamente!
echo.
pause

