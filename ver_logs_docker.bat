@echo off
echo ============================================
echo   LOGS DO DOCKER - Ultimas 100 linhas
echo ============================================
echo.

docker logs gestaoversus_app_dev --tail 100

echo.
echo ============================================
pause

