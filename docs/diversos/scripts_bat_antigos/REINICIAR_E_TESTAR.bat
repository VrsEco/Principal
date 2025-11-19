@echo off
echo ============================================
echo   REINICIANDO SERVIDOR FLASK
echo ============================================
echo.

docker restart gestaoversus_app_dev

echo.
echo Aguardando servidor iniciar (10 segundos)...
timeout /t 10 /nobreak

echo.
echo ============================================
echo   TESTE AGORA:
echo ============================================
echo.
echo 1. Acesse: http://127.0.0.1:5003/grv/company/5/projects/projects
echo.
echo 2. Deve aparecer:
echo    - PEV Plans
echo    - GRV Portfolios  
echo    - Projetos (incluindo "Teste 500 (Projeto)")
echo.
echo 3. Se nao aparecer, execute: VER_LOGS_SERVIDOR.bat
echo.
pause

