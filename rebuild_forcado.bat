@echo off
echo ================================================================================
echo   REBUILD FORCADO - SEM CACHE
echo ================================================================================
echo.
echo Este script vai fazer um rebuild COMPLETO sem usar cache.
echo Isso GARANTE que o codigo mais recente sera usado.
echo.
echo Vai demorar 3-5 minutos!
echo.
pause

echo.
echo [1/4] Parando todos os containers...
docker-compose -f docker-compose.dev.yml down

echo.
echo [2/4] Removendo imagens antigas do app...
docker rmi app31-app_dev 2>nul
docker rmi app31_app_dev 2>nul
docker rmi gestaoversus_app_dev 2>nul

echo.
echo [3/4] Rebuild SEM CACHE (pode demorar)...
docker-compose -f docker-compose.dev.yml build --no-cache app_dev

echo.
echo [4/4] Iniciando containers...
docker-compose -f docker-compose.dev.yml up -d

echo.
echo Aguardando 15 segundos para containers iniciarem completamente...
timeout /t 15 /nobreak

echo.
echo ================================================================================
echo   REBUILD COMPLETO FINALIZADO!
echo ================================================================================
echo.
echo Agora teste novamente:
echo   http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=6
echo.
echo Cole no console:
echo   fetch('/pev/api/implantacao/6/products/totals').then(r =^> r.json()).then(data =^> console.log('TOTALS:', data.totals));
echo.
echo DEVE aparecer: faturamento: {valor: ..., percentual: ...}
echo.
pause

