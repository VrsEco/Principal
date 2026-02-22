@echo off
echo ============================================
echo   CRIANDO TABELAS NO POSTGRESQL DO DOCKER
echo ============================================
echo.

REM Executar SQL dentro do container do PostgreSQL
docker exec -i gestaoversos_db_prod psql -U postgres -d bd_app_versus < criar_tabelas_docker.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo ✅ TABELAS CRIADAS NO POSTGRESQL DO DOCKER!
    echo ============================================
    echo.
    echo Agora reinicie o container do Flask:
    echo   docker-compose restart app
    echo.
    echo E teste novamente!
    echo.
) else (
    echo.
    echo ❌ ERRO ao criar tabelas!
    echo Verifique se o container está rodando:
    echo   docker ps
    echo.
)

pause

