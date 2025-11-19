@echo off
REM ============================================
REM Script: CRIAR_APP32.bat
REM Descrição: Cria pasta app32 para desenvolvimento
REM Uso: Execute quando quiser começar desenvolvimento
REM ============================================

echo ============================================
echo CRIAR APP32 (DESENVOLVIMENTO)
echo ============================================
echo.
echo Este script ira:
echo   1. Criar pasta app32
echo   2. Copiar codigo de app31 (exceto .git, logs, etc)
echo   3. Criar docker-compose.override.yml
echo   4. Criar .env.development
echo.
echo Deseja continuar? (S/N)
set /p confirmacao=

if /i not "%confirmacao%"=="S" (
    echo Cancelado.
    exit /b
)

echo.
echo Criando pasta app32...
cd ..
if not exist "app32" mkdir "app32"
cd app32

echo.
echo Criando arquivo de exclusao...
echo .git > exclude.txt
echo .venv >> exclude.txt
echo __pycache__ >> exclude.txt
echo instance >> exclude.txt
echo uploads >> exclude.txt
echo temp_pdfs >> exclude.txt
echo logs >> exclude.txt
echo backups >> exclude.txt
echo *.db >> exclude.txt
echo *.log >> exclude.txt
echo .env.production >> exclude.txt
echo docker-compose.override.yml >> exclude.txt

echo.
echo Copiando codigo de app31...
xcopy /E /I /EXCLUDE:exclude.txt ..\app31\* .

if %ERRORLEVEL% GEQ 8 (
    echo AVISO: Alguns arquivos podem nao ter sido copiados.
    echo Continue mesmo assim? (S/N)
    set /p continuar=
    if /i not "%continuar%"=="S" (
        del exclude.txt
        exit /b 1
    )
)

echo.
echo Removendo arquivo temporario...
del exclude.txt

echo.
echo Criando docker-compose.override.yml...
(
echo # ============================================
echo # Override para DESENVOLVIMENTO
echo # ============================================
echo.
echo services:
echo   app:
echo     volumes:
echo       - ./modules:/app/modules
echo       - ./templates:/app/templates
echo       - ./static:/app/static
echo       - ./models:/app/models
echo       - ./middleware:/app/middleware
echo       - ./database:/app/database
echo       - ./migrations:/app/migrations
echo       - ./utils:/app/utils
echo       - ./relatorios:/app/relatorios
echo       - ./services:/app/services
echo       - ./api:/app/api
echo       - ./config_database.py:/app/config_database.py
echo       - ./app_pev.py:/app/app_pev.py
echo     restart: "no"
echo     environment:
echo       FLASK_ENV: development
echo       FLASK_DEBUG: "1"
) > docker-compose.override.yml

echo.
echo Criando .env.development...
(
echo # ============================================
echo # Configuracao de DESENVOLVIMENTO
echo # ============================================
echo.
echo # Flask
echo FLASK_APP=app_pev.py
echo FLASK_ENV=development
echo FLASK_DEBUG=1
echo SECRET_KEY=dev-secret-key-change-in-production-2024
echo.
echo # Banco de dados ^(DEV^)
echo DATABASE_URL=postgresql://postgres:*Paraiso1978@localhost:5432/bd_app_versus_dev
echo POSTGRES_HOST=localhost
echo POSTGRES_PORT=5432
echo POSTGRES_USER=postgres
echo POSTGRES_PASSWORD=*Paraiso1978
echo POSTGRES_DB=bd_app_versus_dev
echo.
echo # Redis
echo REDIS_PASSWORD=dev_redis_password
echo REDIS_URL=redis://:dev_redis_password@localhost:6379/0
) > .env.development

echo.
echo Ajustando porta do docker-compose.yml...
echo (Alterando 5003 para 5004 para nao conflitar com app31)
powershell -Command "(Get-Content docker-compose.yml) -replace '5003:5002', '5004:5002' | Set-Content docker-compose.yml"

echo.
echo ============================================
echo APP32 CRIADO COM SUCESSO!
echo ============================================
echo.
echo Proximos passos:
echo   1. cd ..\app32
echo   2. docker-compose up
echo   3. Acesse: http://localhost:5004
echo   4. Comece a desenvolver!
echo.
echo IMPORTANTE:
echo   - app32 nao tem Git (e nao deve ter)
echo   - Use PROMOVER_DEV_PARA_PROD.bat quando estiver pronto
echo   - Sempre teste antes de promover
echo.
pause



