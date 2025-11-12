@echo off
echo ============================================
echo   APLICAR COR AMARELA AO MENU
echo ============================================
echo.

echo [INFO] Textos em AMARELO:
echo   ✅ Nome do usuario (Administrador)
echo   ✅ Email (admin@versus.com.br)
echo   ✅ Meu Perfil
echo   ✅ Configuracoes
echo   ✅ Icones dos itens
echo.
echo   ❌ Botao "Sair" permanece VERMELHO
echo.

echo ============================================
echo   REINICIANDO CONTAINER
echo ============================================
docker-compose -f docker-compose.dev.yml restart app_dev
echo ✅ Container reiniciado
echo.

echo ⏳ Aguardando 5 segundos...
timeout /t 5 /nobreak > nul
echo.

echo ============================================
echo   TESTE AGORA
echo ============================================
echo.
echo 1. Acesse: http://127.0.0.1:5003/main
echo 2. Clique no usuario (canto superior direito)
echo 3. Verifique as cores:
echo    - Nome em AMARELO ✨
echo    - Email em AMARELO CLARO ✨
echo    - "Meu Perfil" em AMARELO ✨
echo    - "Configuracoes" em AMARELO ✨
echo    - "Sair" em VERMELHO 🔴
echo.

set /p abrir=Abrir navegador agora? (S/N): 
if /i "%abrir%"=="S" (
    start http://127.0.0.1:5003/main
    echo.
    echo ✅ Navegador aberto!
    echo    Clique no usuario para ver o menu amarelo!
)

pause





































