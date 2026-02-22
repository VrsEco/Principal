@echo off
echo ============================================
echo   CORRIGIR CORES DO MENU - FINAL
echo ============================================
echo.

echo [INFO] Configuracao de cores:
echo   🟡 TEXTOS EM AMARELO:
echo      - Administrador
echo      - admin@versus.com.br
echo      - Meu Perfil
echo      - Configuracoes
echo.
echo   ⚪ ICONES EM BRANCO:
echo      - Todos os icones (pessoa, engrenagem, porta)
echo.
echo   🔴 BOTAO SAIR:
echo      - Texto: Vermelho
echo      - Icone: Branco
echo.

echo ============================================
echo   APLICANDO NO DOCKER
echo ============================================
echo.

echo [1/4] Verificando container...
docker ps | findstr gestaoversus_app_dev
if %ERRORLEVEL% EQU 0 (
    echo ✅ Container rodando
) else (
    echo ❌ Container nao esta rodando!
    echo.
    echo Iniciando container...
    docker-compose -f docker-compose.dev.yml up -d
    timeout /t 5 /nobreak > nul
)
echo.

echo [2/4] Reiniciando container da aplicacao...
docker-compose -f docker-compose.dev.yml restart app_dev
echo ✅ Container reiniciado
echo.

echo [3/4] Aguardando aplicacao inicializar (8 segundos)...
timeout /t 8 /nobreak > nul
echo.

echo [4/4] Testando se aplicacao responde...
curl -s -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/
echo.

echo ============================================
echo   RESULTADO ESPERADO
echo ============================================
echo.
echo Ao clicar no usuario, o menu deve mostrar:
echo.
echo ┌─────────────────────────────────┐
echo │ ⚪👤 🟡 Administrador            │
echo │ ⚪📧 🟡 admin@versus.com.br      │
echo ├─────────────────────────────────┤
echo │ ⚪👤 🟡 Meu Perfil              │
echo │ ⚪⚙️  🟡 Configuracoes           │
echo ├─────────────────────────────────┤
echo │ ⚪🚪 🔴 Sair                    │
echo └─────────────────────────────────┘
echo.
echo ⚪ = Icone BRANCO
echo 🟡 = Texto AMARELO
echo 🔴 = Texto VERMELHO (apenas "Sair")
echo.

echo ============================================
echo   TESTE AGORA
echo ============================================
echo.
echo 1. Acesse: http://127.0.0.1:5003/main
echo 2. Clique no usuario (canto superior direito)
echo 3. Verifique:
echo    ✅ Nome em AMARELO
echo    ✅ Email em AMARELO
echo    ✅ "Meu Perfil" em AMARELO
echo    ✅ "Configuracoes" em AMARELO
echo    ✅ Todos os ICONES em BRANCO
echo    ✅ "Sair" em VERMELHO (texto)
echo    ✅ Icone "Sair" em BRANCO
echo.

set /p abrir=Abrir navegador agora? (S/N): 
if /i "%abrir%"=="S" (
    start http://127.0.0.1:5003/main
    echo.
    echo ✅ Navegador aberto!
    echo.
    echo 📌 INSTRUCOES:
    echo    1. Faca login se necessario
    echo    2. Clique no nome do usuario (canto superior direito)
    echo    3. Menu aparece com cores corretas!
)

echo.
pause




















































