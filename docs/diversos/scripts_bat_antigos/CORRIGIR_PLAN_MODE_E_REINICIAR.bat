@echo off
echo ============================================
echo   CORRECAO COMPLETA - plan_mode
echo ============================================
echo.

echo PASSO 1: Adicionando coluna plan_mode...
echo.

docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < adicionar_coluna_plan_mode.sql

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ ERRO ao adicionar coluna!
    pause
    exit /b 1
)

echo.
echo ✅ Coluna plan_mode verificada/adicionada!
echo.

echo PASSO 2: Reiniciando servidor Flask...
echo.

docker restart gestaoversus_app_dev

echo.
echo ✅ Servidor reiniciado!
echo.
echo Aguardando servidor iniciar (10 segundos)...
timeout /t 10 /nobreak >nul

echo.
echo ============================================
echo   TESTE AGORA:
echo ============================================
echo.
echo 1. Acesse: http://127.0.0.1:5003/pev/dashboard
echo 2. Crie um novo planejamento
echo 3. Se der erro, execute: VER_LOGS_SERVIDOR.bat
echo.
pause

