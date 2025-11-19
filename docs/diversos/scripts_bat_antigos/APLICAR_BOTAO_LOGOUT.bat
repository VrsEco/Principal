@echo off
echo ============================================
echo   APLICAR BOTAO DE LOGOUT
echo   Menu de Usuario com Dropdown
echo ============================================
echo.

echo [INFO] Implementacao concluida:
echo   ✅ Menu dropdown ao clicar no usuario
echo   ✅ Botao de Logout elegante
echo   ✅ Botao de Perfil
echo   ✅ Botao de Configuracoes
echo   ✅ Animacao suave
echo   ✅ Fecha ao clicar fora
echo.

echo ============================================
echo   PASSO 1: Verificar container
echo ============================================
docker ps | findstr gestaoversus_app_dev
if %ERRORLEVEL% EQU 0 (
    echo ✅ Container rodando
) else (
    echo ❌ Container nao esta rodando!
    echo Execute: docker-compose -f docker-compose.dev.yml up -d
    pause
    exit /b 1
)
echo.

echo ============================================
echo   PASSO 2: Reiniciar container
echo ============================================
echo [INFO] Como usamos volumes montados, as mudancas
echo        ja estao disponiveis. Reiniciando para garantir...
docker-compose -f docker-compose.dev.yml restart app_dev
echo ✅ Container reiniciado
echo.

echo [INFO] Aguardando 5 segundos para app inicializar...
timeout /t 5 /nobreak > nul
echo.

echo ============================================
echo   PASSO 3: Testar se app responde
echo ============================================
curl -s -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/
echo.

echo ============================================
echo   TESTE MANUAL
echo ============================================
echo.
echo 1. Acesse: http://127.0.0.1:5003/main
echo.
echo 2. No canto superior direito, clique no USUARIO
echo.
echo 3. Deve aparecer um menu dropdown com:
echo    - Nome do usuario (AMARELO)
echo    - Email (AMARELO CLARO)
echo    - Botao "Meu Perfil" (AMARELO)
echo    - Botao "Configuracoes" (AMARELO)
echo    - Botao "Sair" (VERMELHO)
echo.
echo 4. Clique em "Sair"
echo    - Deve confirmar
echo    - Mostrar mensagem de sucesso
echo    - Redirecionar para login
echo.
echo ============================================
echo   RECURSOS DO MENU
echo ============================================
echo.
echo ✨ VISUAL:
echo    - Design moderno com gradiente
echo    - Animacao suave de abertura
echo    - Icones elegantes
echo    - Botao de logout em vermelho
echo.
echo 🎯 FUNCIONALIDADES:
echo    - Clique no usuario para abrir/fechar
echo    - Clique fora para fechar automaticamente
echo    - Confirmacao antes de sair
echo    - Mensagem de feedback
echo.
echo 📱 RESPONSIVO:
echo    - Funciona em todas as telas
echo    - Menu se posiciona automaticamente
echo.

echo ============================================
echo   ABRIR NAVEGADOR AGORA?
echo ============================================
set /p abrir=Digite S para abrir o navegador: 
if /i "%abrir%"=="S" (
    start http://127.0.0.1:5003/main
    echo.
    echo ✅ Navegador aberto!
    echo    Clique no usuario no canto superior direito
)

pause

