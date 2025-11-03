@echo off
echo ============================================
echo   LIMPEZA COMPLETA DE SESSAO
echo   Solucao Definitiva
echo ============================================
echo.

echo [PASSO 1] Parando container da aplicacao...
docker-compose -f docker-compose.dev.yml stop app_dev
if %ERRORLEVEL% EQU 0 (
    echo ✅ Container parado
) else (
    echo ❌ Erro ao parar container
    pause
    exit /b 1
)
echo.

echo [PASSO 2] Limpando cache do Flask...
docker-compose -f docker-compose.dev.yml run --rm app_dev find /app -name "*.pyc" -delete 2>nul
docker-compose -f docker-compose.dev.yml run --rm app_dev find /app -name "__pycache__" -type d -exec rm -rf {} + 2>nul
echo ✅ Cache limpo
echo.

echo [PASSO 3] Iniciando container novamente...
docker-compose -f docker-compose.dev.yml start app_dev
echo ✅ Container iniciado
echo.

echo [PASSO 4] Aguardando aplicacao inicializar (10 segundos)...
timeout /t 10 /nobreak > nul
echo.

echo [PASSO 5] Verificando se aplicacao esta respondendo...
curl -s -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/
echo.

echo [PASSO 6] Testando rota de logout...
curl -s -L -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/auth/logout
echo.

echo ============================================
echo   LIMPEZA CONCLUIDA!
echo ============================================
echo.
echo AGORA FACA O SEGUINTE:
echo.
echo 1. FECHE COMPLETAMENTE O NAVEGADOR
echo    - Clique com botao direito no icone da barra
echo    - Escolha "Fechar todas as janelas"
echo    - OU pressione Alt+F4 em todas as janelas
echo.
echo 2. ABRA O NAVEGADOR NOVAMENTE
echo.
echo 3. ACESSE: http://127.0.0.1:5003/main
echo    ✅ Deve redirecionar para LOGIN
echo.
echo ============================================
echo.

pause

echo.
echo Quer que eu abra o navegador agora? (S/N)
set /p abrir=
if /i "%abrir%"=="S" (
    echo.
    echo ⚠️  IMPORTANTE: Fechando todas as janelas do navegador...
    taskkill /F /IM msedge.exe 2>nul
    taskkill /F /IM chrome.exe 2>nul
    taskkill /F /IM firefox.exe 2>nul
    
    echo Aguardando 2 segundos...
    timeout /t 2 /nobreak > nul
    
    echo Abrindo navegador limpo...
    start http://127.0.0.1:5003/main
    
    echo.
    echo ✅ Navegador aberto!
    echo    Se ainda assim for direto para /main:
    echo    - Pressione Ctrl+Shift+N (modo anonimo)
    echo    - Acesse novamente: http://127.0.0.1:5003/main
)

















