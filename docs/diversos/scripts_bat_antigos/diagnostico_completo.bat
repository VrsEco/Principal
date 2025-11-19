@echo off
echo ================================================================================
echo   DIAGNOSTICO COMPLETO - Verificar por que codigo nao atualizou
echo ================================================================================
echo.

echo [1] Verificando containers rodando...
docker ps --filter "name=app_dev"
echo.

echo [2] Verificando quando o container foi criado...
docker inspect --format='{{.Created}}' gestaoversus_app_dev_1 2>nul
if errorlevel 1 docker inspect --format='{{.Created}}' app31-app_dev-1 2>nul
if errorlevel 1 docker inspect --format='{{.Created}}' app31_app_dev_1 2>nul
echo.

echo [3] Listando arquivos Python modificados recentemente...
echo Verificando modules/pev/__init__.py
dir /T:W modules\pev\__init__.py
echo.

echo [4] Verificando se ha arquivos .pyc (cache do Python)...
dir /S /B *.pyc | find "modules\pev" 2>nul
echo.

echo ================================================================================
echo.
echo IMPORTANTE: Se o container foi criado ANTES de hoje, esta rodando codigo antigo!
echo.
echo SOLUCAO:
echo   1. Pare o Docker: docker-compose -f docker-compose.dev.yml down
echo   2. Rebuild forçado: docker-compose -f docker-compose.dev.yml build --no-cache app_dev
echo   3. Inicie: docker-compose -f docker-compose.dev.yml up -d
echo.
pause

