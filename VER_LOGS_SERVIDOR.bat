@echo off
echo ============================================
echo   LOGS DO SERVIDOR FLASK (DOCKER)
echo ============================================
echo.
echo Mostrando ultimas 100 linhas de log...
echo.
echo ============================================
echo.

docker logs gestaoversus_app_dev --tail 100

echo.
echo ============================================
echo   FIM DOS LOGS
echo ============================================
echo.
pause

