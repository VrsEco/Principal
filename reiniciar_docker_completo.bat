@echo off
echo ================================================================================
echo   REINICIAR DOCKER COMPLETO - Limpar Cache
echo ================================================================================
echo.
echo Este script vai:
echo   1. Parar TODOS os containers
echo   2. Remover containers antigos
echo   3. Rebuild da imagem (para garantir codigo atualizado)
echo   4. Iniciar tudo novamente
echo.
echo ATENCAO: Isso pode demorar uns 2-3 minutos!
echo.
pause

echo.
echo [1/5] Parando containers...
docker-compose -f docker-compose.dev.yml down

echo.
echo [2/5] Removendo containers antigos...
docker-compose -f docker-compose.dev.yml rm -f

echo.
echo [3/5] Rebuild da imagem do app (garantir codigo atualizado)...
docker-compose -f docker-compose.dev.yml build app_dev

echo.
echo [4/5] Iniciando containers...
docker-compose -f docker-compose.dev.yml up -d

echo.
echo [5/5] Aguardando 10 segundos para containers iniciarem...
timeout /t 10 /nobreak

echo.
echo ================================================================================
echo   DOCKER REINICIADO COM SUCESSO!
echo ================================================================================
echo.
echo Agora teste novamente:
echo   http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=6
echo.
echo Para ver os logs em tempo real:
echo   docker-compose -f docker-compose.dev.yml logs -f app_dev
echo.
pause

