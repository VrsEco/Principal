@echo off
echo ============================================
echo   VALIDACAO DO SETUP DOCKER
echo   Modelagem Financeira
echo ============================================
echo.

echo [1/6] Verificando containers...
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr gestaoversos
echo.

echo [2/6] Verificando arquivo no container...
docker exec gestaoversos_app_prod ls -lh templates/implantacao/modelo_modelagem_financeira.html
echo.

echo [3/6] Verificando migration aplicada...
docker exec gestaoversos_db_prod psql -U postgres -d bd_app_versus -c "\d plan_finance_metrics" | findstr notes
if %ERRORLEVEL% EQU 0 (
    echo ✅ Campo 'notes' existe!
) else (
    echo ❌ Campo 'notes' NAO existe! Execute: aplicar_migration_modelagem_financeira.bat
)
echo.

echo [4/6] Verificando variavel FLASK_ENV...
docker exec gestaoversos_app_prod env | findstr FLASK
echo.

echo [5/6] Verificando porta 5003...
docker ps | findstr 5003
echo.

echo [6/6] Testando se app responde...
curl -s -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/main
echo.

echo ============================================
echo   INSTRUCOES
echo ============================================
echo.
echo 1. Se todos os checks passaram:
echo    - Acesse: http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=45
echo    - Abra F12 ^(Console^)
echo    - Procure por mensagens: 🔵 Script carregado
echo    - Teste: openPremiseModal^(^)
echo.
echo 2. Se algo falhou:
echo    - Veja: DEBUG_MODELAGEM_FINANCEIRA.md
echo    - Execute: docker-compose restart app
echo    - Tente novamente
echo.

pause




























