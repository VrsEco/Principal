@echo off
echo ================================================================================
echo   VER ERRO COMPLETO DO SERVIDOR
echo ================================================================================
echo.
echo Reiniciando container para aplicar mudancas...
docker-compose restart app

echo.
echo Aguardando 5 segundos...
timeout /t 5 /nobreak >nul

echo.
echo Agora acesse a pagina no navegador:
echo http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=6
echo.
echo Pressione qualquer tecla DEPOIS de acessar a pagina e ver o erro...
pause >nul

echo.
echo ================================================================================
echo LOGS DO ERRO:
echo ================================================================================
echo.
docker-compose logs --tail=100 app | findstr /I "error exception traceback DEBUG"

echo.
echo ================================================================================
echo.
echo Copie TUDO que apareceu acima e cole aqui!
echo Especialmente linhas com: Error, Exception, Traceback, File "/app/
echo.
pause

