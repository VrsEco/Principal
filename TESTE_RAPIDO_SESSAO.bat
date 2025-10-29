@echo off
echo ============================================
echo   TESTE RAPIDO - STATUS DA SESSAO
echo ============================================
echo.

echo [1] Container esta rodando?
docker ps | findstr gestaoversus_app_dev
if %ERRORLEVEL% EQU 0 (
    echo ✅ SIM - Container esta rodando
) else (
    echo ❌ NAO - Container nao esta rodando!
    echo.
    echo Execute: docker-compose -f docker-compose.dev.yml up -d
    pause
    exit /b 1
)
echo.

echo [2] Aplicacao responde na porta 5003?
curl -s -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/
echo.

echo [3] Rota /main esta protegida?
echo (Se voce NAO estiver logado, deve retornar 302 redirect)
curl -s -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/main
echo.

echo [4] Logout via GET funciona?
curl -s -L -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/auth/logout
echo.

echo [5] Verificando configuracao de sessao no container...
echo.
echo --- config.py - SESSION_COOKIE_HTTPONLY ---
docker exec gestaoversus_app_dev grep "SESSION_COOKIE_HTTPONLY" config.py
echo.
echo --- config.py - REMEMBER_COOKIE_DURATION ---
docker exec gestaoversus_app_dev grep "REMEMBER_COOKIE_DURATION" config.py
echo.

echo ============================================
echo   DIAGNOSTICO
echo ============================================
echo.
echo Se os testes acima mostrarem:
echo   - Container rodando: ✅
echo   - Porta 5003 respondendo (200 ou 302): ✅
echo   - SESSION_COOKIE_HTTPONLY = True: ✅
echo   - REMEMBER_COOKIE_DURATION = days=7: ✅
echo.
echo Entao o problema e que VOCE TEM UMA SESSAO ATIVA!
echo.
echo ============================================
echo   SOLUCAO IMEDIATA
echo ============================================
echo.
echo Execute UM dos seguintes:
echo.
echo A) FORCAR_LOGOUT_AGORA.bat
echo    (Reinicia container e abre logout)
echo.
echo B) LIMPAR_SESSAO_COMPLETO.bat  
echo    (Limpeza completa + fecha navegador)
echo.
echo C) Modo Anonimo Manual:
echo    1. Ctrl+Shift+N no navegador
echo    2. Acesse: http://127.0.0.1:5003/main
echo    3. Deve pedir login
echo.

pause









