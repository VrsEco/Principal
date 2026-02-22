@echo off
echo ================================================================================
echo   VER LOGS COMPLETOS (SEM FILTRO)
echo ================================================================================
echo.
echo Mostrando ultimas 80 linhas...
echo.
docker-compose logs --tail=80 app

echo.
echo ================================================================================
echo.
pause

