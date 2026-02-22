@echo off
chcp 65001 > nul
echo ========================================
echo APLICAR MODEFIN - Modelagem Financeira
echo ========================================
echo.

echo [1/3] Aplicando migration no banco de dados...
docker-compose exec app python -c "from database.postgres_helper import get_connection; conn = get_connection(); cursor = conn.cursor(); cursor.execute(open('migrations/create_modefin_tables.sql').read()); conn.commit(); conn.close(); print('Migration aplicada com sucesso!')"

echo.
echo [2/3] Reiniciando container Docker...
docker-compose restart app

echo.
echo [3/3] Aguardando 5 segundos...
timeout /t 5 /nobreak > nul

echo.
echo ========================================
echo MODEFIN APLICADO COM SUCESSO!
echo ========================================
echo.
echo Acesse: http://localhost:5000/pev/implantacao/modelo/modefin?plan_id=1
echo.
pause

