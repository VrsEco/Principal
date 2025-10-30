@echo off
echo ================================================================================
echo   CONFIGURAR DOCKER PARA MODO DESENVOLVIMENTO
echo ================================================================================
echo.
echo Este script vai:
echo   1. Parar os containers atuais
echo   2. Iniciar com o docker-compose.override.yml (monta codigo como volume)
echo   3. Agora mudancas no codigo apareceram automaticamente!
echo.
pause

echo.
echo [1/3] Parando containers...
docker-compose down

echo.
echo [2/3] Iniciando em MODO DESENVOLVIMENTO (com volumes de codigo)...
docker-compose up -d

echo.
echo [3/3] Aguardando 10 segundos...
timeout /t 10 /nobreak

echo.
echo ================================================================================
echo   MODO DESENVOLVIMENTO ATIVADO!
echo ================================================================================
echo.
echo Agora:
echo   - Mudancas no codigo aparecem automaticamente
echo   - Nao precisa rebuild
echo   - Apenas reinicie: docker-compose restart app
echo.
echo Teste agora:
echo   http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=6
echo.
pause

