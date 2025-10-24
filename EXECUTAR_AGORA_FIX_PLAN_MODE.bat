@echo off
echo ============================================
echo   CORRIGINDO COLUNA plan_mode
echo ============================================
echo.

echo Executando SQL no PostgreSQL do Docker...
echo.

docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < adicionar_coluna_plan_mode.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ COLUNA plan_mode ADICIONADA/VERIFICADA!
    echo.
    echo Agora teste criar um planejamento novamente.
    echo.
) else (
    echo.
    echo ❌ ERRO ao executar SQL!
    echo Verifique se o Docker está rodando.
    echo.
)

pause

