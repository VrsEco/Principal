@echo off
setlocal enabledelayedexpansion

REM ============================================
REM RECUPERACAO AUTOMATICA DE DADOS - APP31
REM ============================================

echo ============================================
echo RECUPERACAO AUTOMATICA DE DADOS
echo ============================================
echo.

echo [1/6] Verificando Docker...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Docker nao esta rodando!
    echo.
    echo Por favor:
    echo 1. Inicie o Docker Desktop
    echo 2. Aguarde ficar verde/azul
    echo 3. Execute este script novamente
    echo.
    pause
    exit /b 1
)
echo OK - Docker esta rodando

echo.
echo [2/6] Verificando volumes...
docker volume inspect app31_postgres_data_dev >nul 2>&1
if %errorlevel% neq 0 (
    echo AVISO: Volume nao encontrado, criando...
    docker volume create app31_postgres_data_dev
)
echo OK - Volume PostgreSQL existe

echo.
echo [3/6] Iniciando containers...
docker-compose -f docker-compose.dev.yml up -d
timeout /t 10 /nobreak >nul
echo OK - Containers iniciados

echo.
echo [4/6] Verificando se banco tem dados...
docker exec gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "\dt" >nul 2>&1

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo EXCELENTE! DADOS ESTAO NO BANCO!
    echo ============================================
    echo.
    echo Seus dados NAO foram perdidos!
    echo O banco esta funcionando normalmente.
    echo.
    echo Verificando tabelas...
    docker exec gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "\dt"
    echo.
    echo ============================================
    echo RECUPERACAO NAO NECESSARIA!
    echo ============================================
    echo.
    goto :success
)

echo AVISO: Banco vazio ou nao existe
echo.
echo [5/6] Criando banco se necessario...
docker exec gestaoversus_db_dev createdb -U postgres bd_app_versus_dev 2>nul
echo OK - Banco pronto

echo.
echo [6/6] Restaurando do backup mais recente...

REM Tentar backup mais recente primeiro
if exist "backups\backup_recuperacao_20251028_v2.sql" (
    echo Usando: backup_recuperacao_20251028_v2.sql
    type "backups\backup_recuperacao_20251028_v2.sql" | docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev >nul 2>&1
    goto :verify
)

if exist "backups\backup_recuperacao_20251028.sql" (
    echo Usando: backup_recuperacao_20251028.sql
    type "backups\backup_recuperacao_20251028.sql" | docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev >nul 2>&1
    goto :verify
)

if exist "backups\dump_bd_app_versus.sql" (
    echo Usando: dump_bd_app_versus.sql
    type "backups\dump_bd_app_versus.sql" | docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev >nul 2>&1
    goto :verify
)

if exist "backups\backup_pre_migracao_20251020_201337.sql" (
    echo Usando: backup_pre_migracao_20251020_201337.sql
    type "backups\backup_pre_migracao_20251020_201337.sql" | docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev >nul 2>&1
    goto :verify
)

echo ERRO: Nenhum backup SQL encontrado!
echo.
echo Backups disponiveis:
dir /b backups\*.sql
echo.
pause
exit /b 1

:verify
echo.
echo Verificando restauracao...
docker exec gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "\dt" >nul 2>&1

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo RECUPERACAO CONCLUIDA COM SUCESSO!
    echo ============================================
    echo.
    echo Tabelas restauradas:
    docker exec gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "\dt"
    echo.
    goto :success
) else (
    echo.
    echo ============================================
    echo ERRO NA RECUPERACAO
    echo ============================================
    echo.
    echo O restore nao funcionou.
    echo Leia: RECUPERAR_DADOS_AGORA.md para opcoes manuais
    echo.
    pause
    exit /b 1
)

:success
echo ============================================
echo PROXIMOS PASSOS
echo ============================================
echo.
echo 1. Fazer backup agora:
echo    backup_docker_completo.bat
echo.
echo 2. Testar aplicacao:
echo    http://localhost:5003
echo.
echo 3. Configurar backup automatico:
echo    Ler CONFIGURAR_BACKUP_AUTOMATICO.md
echo.
pause


