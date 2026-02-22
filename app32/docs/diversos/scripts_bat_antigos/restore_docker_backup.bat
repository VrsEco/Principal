@echo off
REM ============================================
REM Restore de Backup - Docker APP31
REM ============================================
REM Restaura backup do banco de dados
REM ============================================

echo ============================================
echo 🔄 RESTORE DE BACKUP - APP31
echo ============================================
echo.

REM Verificar se foi passado um arquivo de backup
if "%~1"=="" (
    echo ❌ Erro: Arquivo de backup não especificado
    echo.
    echo 📖 USO:
    echo    restore_docker_backup.bat [arquivo_backup]
    echo.
    echo 📝 EXEMPLO:
    echo    restore_docker_backup.bat backups\db_backup_20251028_1430.sql
    echo    restore_docker_backup.bat backups\db_backup_20251028_1430.zip
    echo.
    echo 📁 Backups disponíveis:
    dir /b backups\db_backup_*.sql 2>nul
    dir /b backups\db_backup_*.zip 2>nul
    echo.
    pause
    exit /b 1
)

set BACKUP_FILE=%~1

REM Verificar se arquivo existe
if not exist "%BACKUP_FILE%" (
    echo ❌ Erro: Arquivo não encontrado: %BACKUP_FILE%
    echo.
    pause
    exit /b 1
)

echo 📂 Arquivo de backup: %BACKUP_FILE%
echo.

echo ⚠️  ATENÇÃO: Esta operação vai SOBRESCREVER os dados atuais!
echo.
set /p confirm="Tem certeza que deseja continuar? (S/N): "

if /i not "%confirm%"=="S" (
    echo ❌ Operação cancelada pelo usuário
    pause
    exit /b 0
)

echo.
echo [1/4] Verificando containers...
docker ps --filter "name=gestaoversus_db" --format "table {{.Names}}\t{{.Status}}"
echo.

REM Verificar extensão do arquivo
echo %BACKUP_FILE% | findstr /i "\.zip$" >nul
if %errorlevel% equ 0 (
    echo [2/4] Descompactando arquivo ZIP...
    set TEMP_SQL=%BACKUP_FILE:.zip=.sql%
    powershell -Command "Expand-Archive -Path '%BACKUP_FILE%' -DestinationPath 'backups\temp_restore' -Force"
    
    REM Procurar arquivo .sql no diretório descompactado
    for /f "delims=" %%i in ('dir /b /s backups\temp_restore\*.sql 2^>nul') do set TEMP_SQL=%%i
    
    if not exist "%TEMP_SQL%" (
        echo ❌ Erro: Arquivo SQL não encontrado no ZIP
        rmdir /s /q backups\temp_restore 2>nul
        pause
        exit /b 1
    )
) else (
    set TEMP_SQL=%BACKUP_FILE%
)

echo [3/4] Criando backup de segurança antes do restore...
set datetime=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%
docker exec gestaoversus_db_prod pg_dump -U postgres -d bd_app_versus > "backups\pre_restore_backup_%datetime%.sql" 2>&1
echo ✅ Backup de segurança criado
echo.

echo [4/4] Restaurando banco de dados...
type "%TEMP_SQL%" | docker exec -i gestaoversus_db_prod psql -U postgres -d bd_app_versus 2>&1

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo ✅ RESTORE CONCLUÍDO COM SUCESSO!
    echo ============================================
    echo.
    echo 📊 Verificando banco restaurado...
    docker exec gestaoversus_db_prod psql -U postgres -d bd_app_versus -c "\dt" 2>&1
) else (
    echo.
    echo ============================================
    echo ❌ ERRO AO RESTAURAR BACKUP
    echo ============================================
    echo.
    echo 🔄 Um backup de segurança foi criado em:
    echo    backups\pre_restore_backup_%datetime%.sql
    echo.
)

REM Limpar arquivos temporários
if exist "backups\temp_restore" (
    rmdir /s /q backups\temp_restore 2>nul
)

echo.
pause


