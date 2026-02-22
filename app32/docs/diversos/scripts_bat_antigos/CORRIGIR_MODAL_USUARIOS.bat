@echo off
echo ============================================
echo   CORRIGIR MODAL DE USUARIOS
echo   Diagnostico e Correcao Completa
echo ============================================
echo.

echo [PASSO 1] Limpando cache do navegador...
echo.
echo IMPORTANTE: Voce precisa fazer isso manualmente!
echo.
echo 1. No navegador, pressione: Ctrl + Shift + Delete
echo 2. Marque: "Imagens e arquivos em cache"
echo 3. Periodo: "Todo o periodo"
echo 4. Clique em "Limpar dados"
echo.
pause

echo.
echo [PASSO 2] Reiniciando container...
docker-compose -f docker-compose.dev.yml restart app_dev
echo.
timeout /t 5 /nobreak > nul

echo.
echo [PASSO 3] Abrindo em modo anonimo...
echo.
echo ABRA EM MODO ANONIMO/PRIVADO:
echo - Edge/Chrome: Ctrl + Shift + N
echo - Firefox: Ctrl + Shift + P
echo.
echo Depois acesse: http://127.0.0.1:5003/login
echo.
pause

echo.
echo [PASSO 4] Testando acesso...
start http://127.0.0.1:5003/login
echo.

echo ============================================
echo   INSTRUCOES DE TESTE
echo ============================================
echo.
echo 1. Faca login:
echo    Email: admin@versus.com.br
echo    Senha: 123456
echo.
echo 2. Acesse: http://127.0.0.1:5003/auth/users/page
echo.
echo 3. Pressione F12 e va na aba Console
echo.
echo 4. Digite este comando no console:
echo    console.log('Modal:', document.getElementById('editModal'));
echo.
echo 5. Verifique se o modal existe
echo.
pause



