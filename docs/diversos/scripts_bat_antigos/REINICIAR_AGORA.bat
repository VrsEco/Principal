@echo off
echo ============================================
echo   REINICIANDO SERVIDOR FLASK
echo ============================================
echo.
echo Correcao aplicada no codigo.
echo Reiniciando para aplicar...
echo.

docker restart gestaoversus_app_dev

echo.
echo Aguardando servidor iniciar...
timeout /t 10 /nobreak

echo.
echo ============================================
echo   PRONTO PARA TESTAR!
echo ============================================
echo.
echo Acesse: http://127.0.0.1:5003/grv/company/5/projects/projects
echo.
echo Deve aparecer:
echo   - PEV Plans
echo   - GRV Portfolios
echo   - Projetos (incluindo "Teste 500 (Projeto)")
echo.
pause

