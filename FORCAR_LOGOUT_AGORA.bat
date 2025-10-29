@echo off
echo ============================================
echo   FORCAR LOGOUT - SOLUCAO IMEDIATA
echo ============================================
echo.

echo [1] Reiniciando container da aplicacao...
docker-compose -f docker-compose.dev.yml restart app_dev
echo ✅ Container reiniciado
echo.

echo [2] Aguardando 3 segundos...
timeout /t 3 /nobreak > nul
echo.

echo [3] Abrindo navegador para fazer logout...
start http://127.0.0.1:5003/auth/logout
echo.

echo ============================================
echo   INSTRUCOES IMPORTANTES
echo ============================================
echo.
echo OPCAO 1: Se o navegador abriu:
echo   1. Aguarde carregar a pagina
echo   2. Voce deve ser redirecionado para login
echo   3. ✅ PRONTO! Agora teste: http://127.0.0.1:5003/main
echo.
echo OPCAO 2: Se nao funcionou:
echo   1. Pressione F12 no navegador
echo   2. Aba Application -^> Cookies
echo   3. Delete o cookie "session"
echo   4. Feche e reabra o navegador
echo.
echo OPCAO 3: Modo Anonimo (MAIS FACIL):
echo   1. Pressione Ctrl+Shift+N (Chrome/Edge)
echo   2. Acesse: http://127.0.0.1:5003/main
echo   3. Deve pedir login
echo.

pause

echo.
echo Quer abrir em modo anonimo agora? (S/N)
set /p resposta=
if /i "%resposta%"=="S" (
    echo.
    echo ============================================
    echo Instrucoes para modo anonimo:
    echo ============================================
    echo 1. Nova janela vai abrir
    echo 2. Pressione Ctrl+Shift+N 
    echo 3. Na janela anonima, acesse:
    echo    http://127.0.0.1:5003/main
    echo.
    start msedge.exe
)









