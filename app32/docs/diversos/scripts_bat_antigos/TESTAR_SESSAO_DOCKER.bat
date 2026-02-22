@echo off
echo ============================================
echo   TESTE DE SESSAO E AUTENTICACAO - DOCKER
echo   GestaoVersus - Porta 5003 (Dev)
echo ============================================
echo.

echo [TESTE 1] Verificar se container esta rodando...
docker ps | findstr gestaoversus_app_dev
if %ERRORLEVEL% EQU 0 (
    echo ✅ Container app_dev esta rodando
) else (
    echo ❌ Container nao esta rodando! Execute: docker-compose -f docker-compose.dev.yml up -d
    pause
    exit /b 1
)
echo.

echo [TESTE 2] Verificar porta 5003...
curl -s -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/
echo.

echo [TESTE 3] Acessar rota protegida /main...
echo (Deve redirecionar para login se nao autenticado)
curl -s -L -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/main
echo.

echo [TESTE 4] Testar logout via GET...
curl -s -L -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/auth/logout
echo.

echo ============================================
echo   TESTE MANUAL AGORA
echo ============================================
echo.
echo 1. Abra o navegador em MODO ANONIMO (Ctrl+Shift+N)
echo.
echo 2. Acesse: http://127.0.0.1:5003/main
echo    ✅ ESPERADO: Redirecionar para /login
echo.
echo 3. Acesse: http://127.0.0.1:5003/
echo    ✅ ESPERADO: Redirecionar para /login
echo.
echo 4. Faca login:
echo    - Email: admin@versus.com.br
echo    - Senha: 123456
echo.
echo 5. Apos login, acesse: http://127.0.0.1:5003/main
echo    ✅ ESPERADO: Mostrar pagina principal
echo.
echo 6. Teste logout: http://127.0.0.1:5003/auth/logout
echo    ✅ ESPERADO: Redirecionar para /login com mensagem
echo.
echo 7. Pressione F12 - Aba Application - Cookies
echo    Verifique cookie "session":
echo    ✅ HttpOnly deve ser true
echo    ✅ SameSite deve ser Lax
echo.

echo ============================================
echo   VERIFICAR LOGS EM TEMPO REAL
echo ============================================
echo.
echo Execute em outro terminal:
echo   docker logs -f gestaoversus_app_dev
echo.

pause

echo.
echo Abrir logs agora? (S/N)
set /p resposta=
if /i "%resposta%"=="S" (
    start cmd /k "docker logs -f gestaoversus_app_dev"
)


