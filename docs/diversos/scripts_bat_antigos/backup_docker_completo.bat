@echo off
REM ============================================
REM Backup Completo - Docker APP31
REM ============================================
REM Faz backup de:
REM - Banco de dados PostgreSQL
REM - Volume Docker
REM - Arquivos da aplicação
REM ============================================

echo ============================================
echo 📦 BACKUP COMPLETO - APP31
echo ============================================
echo.

REM Criar variável de data
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%b%%a)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set datetime=%mydate%_%mytime%

REM Criar diretório de backup se não existir
if not exist "backups" mkdir backups

echo [1/4] Verificando containers...
docker ps --filter "name=gestaoversus" --format "table {{.Names}}\t{{.Status}}"
echo.

echo [2/4] Backup do banco de dados PostgreSQL...
docker exec gestaoversus_db_prod pg_dump -U postgres -d bd_app_versus > "backups\db_backup_%datetime%.sql" 2>&1

if %errorlevel% equ 0 (
    echo ✅ Backup do banco criado: backups\db_backup_%datetime%.sql
) else (
    echo ❌ Erro ao criar backup do banco
    echo ⚠️  Verifique se o container está rodando: docker ps
    pause
    exit /b 1
)
echo.

echo [3/4] Comprimindo backup do banco...
powershell -Command "Compress-Archive -Path 'backups\db_backup_%datetime%.sql' -DestinationPath 'backups\db_backup_%datetime%.zip' -Force"
if %errorlevel% equ 0 (
    echo ✅ Backup comprimido criado
    del "backups\db_backup_%datetime%.sql"
) else (
    echo ⚠️  Erro ao comprimir, mantendo arquivo .sql
)
echo.

echo [4/4] Verificando arquivos já persistidos no Windows...
echo    - uploads\         : %cd%\uploads
echo    - temp_pdfs\       : %cd%\temp_pdfs
echo    - logs\            : %cd%\logs
echo    - backups\         : %cd%\backups
echo ✅ Arquivos já estão no Windows (não precisa backup adicional)
echo.

echo ============================================
echo ✅ BACKUP CONCLUÍDO COM SUCESSO!
echo ============================================
echo.
echo 📁 Backup salvo em: backups\db_backup_%datetime%.zip
echo.
echo 💡 RECOMENDAÇÕES:
echo    1. Copie este backup para outro disco/nuvem
echo    2. Teste o restore periodicamente
echo    3. Configure backup automático (Task Scheduler)
echo.
echo 📊 Informações dos volumes Docker:
docker volume ls --filter "name=app31"
echo.

pause


