@echo off
echo ================================================================================
echo   COPIAR CODIGO ATUALIZADO PARA DENTRO DO CONTAINER
echo ================================================================================
echo.
echo Se o volume nao estiver funcionando, vamos copiar manualmente!
echo.
pause

echo.
echo [1] Identificando nome do container...
for /f "tokens=*" %%i in ('docker ps --filter "name=app_dev" --format "{{.Names}}"') do set CONTAINER=%%i

if "%CONTAINER%"=="" (
    echo ERRO: Container app_dev nao encontrado!
    echo Verifique se o Docker esta rodando: docker ps
    pause
    exit /b 1
)

echo Container encontrado: %CONTAINER%
echo.

echo [2] Copiando products_service.py...
docker cp modules\pev\products_service.py %CONTAINER%:/app/modules/pev/products_service.py

echo.
echo [3] Copiando __init__.py do pev...
docker cp modules\pev\__init__.py %CONTAINER%:/app/modules/pev/__init__.py

echo.
echo [4] Removendo arquivos .pyc (cache Python)...
docker exec %CONTAINER% find /app -name "*.pyc" -delete
docker exec %CONTAINER% find /app -name "__pycache__" -type d -exec rm -rf {} + 2>nul

echo.
echo [5] Reiniciando container...
docker restart %CONTAINER%

echo.
echo Aguardando 10 segundos...
timeout /t 10 /nobreak

echo.
echo ================================================================================
echo   CODIGO COPIADO E CONTAINER REINICIADO!
echo ================================================================================
echo.
echo Agora teste novamente:
echo   http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=6
echo.
pause

