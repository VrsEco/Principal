@echo off
echo ========================================
echo    INICIANDO APP29 COM POSTGRESQL
echo ========================================
echo.

echo Configurando variaveis de ambiente...
set DB_TYPE=postgresql
set POSTGRES_HOST=localhost
set POSTGRES_PORT=5432
set POSTGRES_DB=bd_app_versus
set POSTGRES_USER=postgres
set POSTGRES_PASSWORD=*Paraiso1978
set DATABASE_URL=postgresql://postgres:*Paraiso1978@localhost:5432/bd_app_versus

echo.
echo Iniciando aplicacao...
python app_pev.py

pause
