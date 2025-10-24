@echo off
cls
echo ========================================
echo   CADASTRAR USUARIO - ATALHO DIRETO
echo ========================================
echo.
echo IMPORTANTE: Voce precisa fazer LOGIN primeiro!
echo.
echo ========================================
echo PASSO 1: FAZER LOGIN
echo ========================================
echo.
echo Credenciais:
echo   Email: admin@versus.com.br
echo   Senha: 123456
echo.
echo Pressione qualquer tecla para abrir a pagina de login...
pause >nul
start http://127.0.0.1:5003/login
echo.
echo ========================================
echo Aguarde fazer o login...
echo ========================================
echo.
echo Apos fazer login, pressione qualquer tecla para continuar...
pause >nul
echo.
echo ========================================
echo PASSO 2: ABRIR CADASTRO DE USUARIO
echo ========================================
echo.
echo Abrindo formulario de cadastro...
start http://127.0.0.1:5003/auth/register
echo.
echo ========================================
echo VOCE DEVERIA VER:
echo ========================================
echo.
echo - Formulario com campos:
echo   * Nome completo
echo   * Email
echo   * Senha
echo   * Confirmar senha
echo   * Perfil (Admin/Consultor/Cliente)
echo.
echo - Botoes:
echo   * Cancelar
echo   * Cadastrar Usuario
echo.
echo ========================================
echo PARA RESOLVER O PROBLEMA DO BOTAO:
echo ========================================
echo.
echo 1. Abra a pagina de usuarios
echo 2. Pressione F12
echo 3. Va em Console
echo 4. Abra o arquivo: TESTE_CONSOLE_NAVEGADOR.md
echo 5. Execute os testes no console
echo.
echo ========================================
echo.
pause

