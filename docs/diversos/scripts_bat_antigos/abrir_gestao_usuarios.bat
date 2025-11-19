@echo off
echo ========================================
echo GESTAO DE USUARIOS - GUIA DE ACESSO
echo ========================================
echo.
echo IMPORTANTE: Voce precisa fazer LOGIN primeiro!
echo.
echo ========================================
echo PASSO 1: FAZER LOGIN
echo ========================================
echo.
echo Abrindo pagina de login...
echo.
echo Credenciais:
echo Email: admin@versus.com.br
echo Senha: 123456
echo.
pause
start http://127.0.0.1:5003/login
echo.
echo ========================================
echo AGUARDE fazer o login...
echo ========================================
echo.
echo Pressione qualquer tecla APOS fazer login
pause
echo.
echo ========================================
echo PASSO 2: ABRIR GESTAO DE USUARIOS
echo ========================================
echo.
echo Abrindo pagina de gestao de usuarios...
start http://127.0.0.1:5003/auth/users/page
echo.
echo ========================================
echo VOCE DEVERIA VER:
echo ========================================
echo 1. Botao "Novo Usuario" no topo
echo 2. Tabela com lista de usuarios
echo 3. Botoes "Ativar/Desativar" para cada usuario
echo.
echo ========================================
echo SE NAO VE OS BOTOES:
echo ========================================
echo 1. Verifique se fez login corretamente
echo 2. Pressione Ctrl+F5 para forcar recarga
echo 3. Verifique se o usuario e admin
echo.
echo ========================================
echo TESTE VISUAL INTERATIVO:
echo ========================================
echo.
echo Deseja abrir o guia visual interativo? (S/N)
set /p resposta=
if /i "%resposta%"=="S" (
    echo Abrindo guia visual...
    start test_login_and_users.html
)
echo.
echo ========================================
echo FIM
echo ========================================
pause


