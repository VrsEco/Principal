@echo off
REM ============================================
REM Verificar Volumes Docker - APP31
REM ============================================
REM Mostra informações sobre volumes e dados
REM ============================================

echo ============================================
echo 🔍 VERIFICAÇÃO DE VOLUMES - APP31
echo ============================================
echo.

echo [1/5] Status dos containers...
echo ============================================
docker ps --filter "name=gestaoversus" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.

echo [2/5] Volumes Docker existentes...
echo ============================================
docker volume ls --filter "name=app31"
echo.

echo [3/5] Detalhes do volume PostgreSQL...
echo ============================================
docker volume inspect app31_postgres_data_dev 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  Volume app31_postgres_data_dev não encontrado
    echo.
    echo 💡 Procurando outros volumes PostgreSQL...
    docker volume ls --filter "name=postgres"
)
echo.

echo [4/5] Tamanho dos volumes...
echo ============================================
docker system df -v | findstr "app31"
echo.

echo [5/5] Verificando banco de dados...
echo ============================================
echo Tamanho do banco:
docker exec gestaoversus_db_prod psql -U postgres -d bd_app_versus -c "SELECT pg_size_pretty(pg_database_size('bd_app_versus'));" 2>nul
if %errorlevel% equ 0 (
    echo.
    echo Tabelas no banco:
    docker exec gestaoversus_db_prod psql -U postgres -d bd_app_versus -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;" 2>nul
) else (
    echo ⚠️  Não foi possível conectar ao banco
    echo    Verifique se o container está rodando: docker ps
)
echo.

echo [EXTRA] Arquivos locais mapeados no Windows...
echo ============================================
echo 📁 Uploads:      %cd%\uploads
if exist "uploads" (
    dir /a-d /s uploads 2>nul | find "File(s)"
) else (
    echo    ⚠️  Diretório não encontrado
)

echo.
echo 📁 Backups:      %cd%\backups  
if exist "backups" (
    dir /a-d /s backups 2>nul | find "File(s)"
) else (
    echo    ⚠️  Diretório não encontrado
)

echo.
echo 📁 Logs:         %cd%\logs
if exist "logs" (
    dir /a-d /s logs 2>nul | find "File(s)"
) else (
    echo    ⚠️  Diretório não encontrado
)

echo.
echo 📁 PDFs Temp:    %cd%\temp_pdfs
if exist "temp_pdfs" (
    dir /a-d /s temp_pdfs 2>nul | find "File(s)"
) else (
    echo    ⚠️  Diretório não encontrado
)

echo.
echo ============================================
echo ✅ VERIFICAÇÃO CONCLUÍDA
echo ============================================
echo.
echo 💡 DICAS:
echo    - Volumes Docker persistem dados entre reinicializações
echo    - Arquivos mapeados ficam direto no Windows
echo    - Para backup completo, execute: backup_docker_completo.bat
echo.

pause


