@echo off
echo.
echo ============================================================
echo   TESTE DO FAVICON - Gestao Versus App28
echo ============================================================
echo.
echo Verificando arquivos...
python verificar_favicon.py
echo.
echo ============================================================
echo.
echo Para testar no navegador:
echo   1. Execute: python app_pev.py
echo   2. Acesse: http://localhost:5002
echo   3. Verifique a aba do navegador (deve mostrar o logo Versus)
echo   4. Verifique o console (nao deve ter erro 404 do favicon)
echo.
echo ============================================================
pause

