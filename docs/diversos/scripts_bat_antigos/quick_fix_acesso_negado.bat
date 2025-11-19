@echo off
cls
echo ========================================
echo   RESOLVER "ACESSO NEGADO"
echo ========================================
echo.
echo Problema: Voce recebe "Acesso negado"
echo mesmo sendo administrador.
echo.
echo ========================================
echo SOLUCAO RAPIDA:
echo ========================================
echo.
echo 1. FECHE TODAS as abas do navegador
echo 2. Pressione Ctrl+Shift+Delete
echo 3. Marque: Cache e Cookies
echo 4. Clique em Limpar
echo 5. FECHE o navegador completamente
echo 6. Abra novamente
echo.
echo ========================================
echo.
echo Pressione qualquer tecla para abrir o login...
pause >nul
echo.
echo Abrindo pagina de login...
start http://127.0.0.1:5003/login
echo.
echo ========================================
echo CREDENCIAIS:
echo ========================================
echo.
echo Email: admin@versus.com.br
echo Senha: 123456
echo.
echo ========================================
echo.
echo Apos fazer login, pressione qualquer tecla...
pause >nul
echo.
echo Abrindo cadastro de usuario...
start http://127.0.0.1:5003/auth/register
echo.
echo ========================================
echo VOCE DEVE VER:
echo ========================================
echo.
echo - Formulario de cadastro de usuario
echo - Campos: Nome, Email, Senha, Perfil
echo - Botoes: Cancelar, Cadastrar
echo.
echo ========================================
echo SE AINDA DA ACESSO NEGADO:
echo ========================================
echo.
echo 1. Abra o arquivo: RESOLVER_ACESSO_NEGADO.md
echo 2. Siga as instrucoes detalhadas
echo 3. Execute o diagnostico no console (F12)
echo.
echo ========================================
echo.
pause


