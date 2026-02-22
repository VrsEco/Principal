@echo off
echo ================================================================================
echo   VER ERRO DO SERVIDOR
echo ================================================================================
echo.
echo Mostrando ultimas 50 linhas dos logs do Docker...
echo Procure por linhas com ERROR, Exception, Traceback
echo.
pause

docker-compose logs --tail=50 app

echo.
echo ================================================================================
echo.
echo Copie e cole aqui as linhas com erro (ERROR, Exception, Traceback)
echo.
pause

