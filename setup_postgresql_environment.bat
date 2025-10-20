@echo off
echo ========================================
echo    CONFIGURACAO POSTGRESQL - APP29
echo    Banco: bd_app_versus
echo ========================================
echo.

echo 1. Verificando PostgreSQL...
psql --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ PostgreSQL nao encontrado!
    echo    Instale o PostgreSQL primeiro
    echo    Download: https://www.postgresql.org/download/
    pause
    exit /b 1
)

echo ✅ PostgreSQL encontrado
echo.

echo 2. Configurando variaveis de ambiente...
echo    POSTGRES_HOST=localhost
echo    POSTGRES_PORT=5432
echo    POSTGRES_DB=bd_app_versus
echo    POSTGRES_USER=postgres
echo.

set POSTGRES_HOST=localhost
set POSTGRES_PORT=5432
set POSTGRES_DB=bd_app_versus
set POSTGRES_USER=postgres

echo Digite a senha do PostgreSQL:
set /p POSTGRES_PASSWORD=

if "%POSTGRES_PASSWORD%"=="" (
    echo ❌ Senha nao pode estar vazia!
    pause
    exit /b 1
)

echo.
echo 3. Testando conexao com PostgreSQL...
psql -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U %POSTGRES_USER% -d postgres -c "SELECT version();" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Erro ao conectar PostgreSQL!
    echo    Verifique:
    echo    - Se o PostgreSQL esta rodando
    echo    - Se a senha esta correta
    echo    - Se o usuario 'postgres' existe
    pause
    exit /b 1
)

echo ✅ Conexao com PostgreSQL OK
echo.

echo 4. Criando banco de dados 'bd_app_versus'...
psql -h %POSTGRES_HOST% -p %POSTGRES_PORT% -U %POSTGRES_USER% -d postgres -c "CREATE DATABASE bd_app_versus;" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Banco 'bd_app_versus' ja existe ou erro ao criar
) else (
    echo ✅ Banco 'bd_app_versus' criado com sucesso
)

echo.
echo 5. Executando migracao de dados...
python migrate_to_postgresql.py
if %errorlevel% neq 0 (
    echo ❌ Erro na migracao!
    pause
    exit /b 1
)

echo.
echo 6. Verificando migracao...
python verify_postgresql_migration.py
if %errorlevel% neq 0 (
    echo ❌ Erro na verificacao!
    pause
    exit /b 1
)

echo.
echo ========================================
echo    MIGRACAO CONCLUIDA COM SUCESSO!
echo ========================================
echo.
echo Para usar PostgreSQL, configure o arquivo .env:
echo.
echo DB_TYPE=postgresql
echo POSTGRES_HOST=localhost
echo POSTGRES_PORT=5432
echo POSTGRES_DB=bd_app_versus
echo POSTGRES_USER=postgres
echo POSTGRES_PASSWORD=%POSTGRES_PASSWORD%
echo.
echo DATABASE_URL=postgresql://postgres:%POSTGRES_PASSWORD%@localhost:5432/bd_app_versus
echo.
pause
