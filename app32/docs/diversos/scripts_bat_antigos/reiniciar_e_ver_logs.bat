@echo off
echo ================================================================================
echo   REINICIAR SERVIDOR E VER LOGS
echo ================================================================================
echo.
echo Este script vai:
echo   1. Reiniciar o container app_dev
echo   2. Mostrar os logs em tempo real
echo.
echo Pressione Ctrl+C para parar de ver os logs
echo.
pause

echo.
echo [1/2] Reiniciando container...
docker-compose -f docker-compose.dev.yml restart app_dev

echo.
echo [2/2] Aguardando 3 segundos...
timeout /t 3 /nobreak >nul

echo.
echo ================================================================================
echo   LOGS EM TEMPO REAL
echo ================================================================================
echo.
echo Agora abra o navegador e acesse:
echo   http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=6
echo.
echo Os logs aparecerao aqui abaixo!
echo Pressione Ctrl+C quando quiser parar
echo.
echo ================================================================================
echo.

docker-compose -f docker-compose.dev.yml logs -f app_dev

