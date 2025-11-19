@echo off
setlocal enabledelayedexpansion
REM ============================================
REM Copiar Dados para C:\gestaoversus\referencias
REM ============================================
REM Exporta dados do Docker para pasta acessível
REM ============================================

echo ============================================
echo 📦 EXPORTANDO DADOS PARA REFERENCIAS
echo ============================================
echo.

REM Criar diretório se não existir
if not exist "C:\gestaoversus\referencias" (
    mkdir "C:\gestaoversus\referencias"
    echo ✅ Diretório criado: C:\gestaoversus\referencias
)

REM Data/hora para nome dos arquivos
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%b%%a)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set datetime=%mydate%_%mytime%

echo.
echo [1/5] Exportando banco de dados PostgreSQL...
echo ============================================

REM Verificar se Docker está rodando
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker não está rodando!
    echo.
    echo 💡 Para exportar dados do PostgreSQL:
    echo    1. Inicie o Docker Desktop
    echo    2. Execute este script novamente
    echo.
    echo ⏭️  Continuando com cópia de arquivos locais...
    goto :copy_local_files
)

REM Tentar exportar do container de produção
docker exec gestaoversus_db_prod pg_dump -U postgres -d bd_app_versus > "C:\gestaoversus\referencias\postgres_export_%datetime%.sql" 2>nul
if %errorlevel% equ 0 (
    echo ✅ PostgreSQL (PROD) exportado: postgres_export_%datetime%.sql
    goto :copy_local_files
)

REM Se não deu certo, tentar container de desenvolvimento
docker exec gestaoversus_db_dev pg_dump -U postgres -d bd_app_versus_dev > "C:\gestaoversus\referencias\postgres_export_%datetime%.sql" 2>nul
if %errorlevel% equ 0 (
    echo ✅ PostgreSQL (DEV) exportado: postgres_export_%datetime%.sql
    goto :copy_local_files
)

REM Se não deu certo, tentar container sem sufixo
docker ps --format "{{.Names}}" | findstr "db" > temp_containers.txt
for /f "delims=" %%c in (temp_containers.txt) do (
    docker exec %%c pg_dump -U postgres -d bd_app_versus > "C:\gestaoversus\referencias\postgres_export_%datetime%.sql" 2>nul
    if !errorlevel! equ 0 (
        echo ✅ PostgreSQL exportado de %%c: postgres_export_%datetime%.sql
        del temp_containers.txt
        goto :copy_local_files
    )
)

echo ⚠️  Nenhum container PostgreSQL encontrado
echo    Os dados do banco não foram exportados
del temp_containers.txt 2>nul

:copy_local_files

echo.
echo [2/5] Copiando Uploads (arquivos de usuários)...
echo ============================================
if exist "uploads" (
    xcopy /E /I /Y "uploads" "C:\gestaoversus\referencias\uploads" >nul
    echo ✅ Uploads copiados para: C:\gestaoversus\referencias\uploads
) else (
    echo ⚠️  Pasta uploads não encontrada
)

echo.
echo [3/5] Copiando Backups...
echo ============================================
if exist "backups" (
    xcopy /E /I /Y "backups" "C:\gestaoversus\referencias\backups" >nul
    echo ✅ Backups copiados para: C:\gestaoversus\referencias\backups
) else (
    echo ⚠️  Pasta backups não encontrada
)

echo.
echo [4/5] Copiando Logs...
echo ============================================
if exist "logs" (
    xcopy /E /I /Y "logs" "C:\gestaoversus\referencias\logs" >nul
    echo ✅ Logs copiados para: C:\gestaoversus\referencias\logs
) else (
    echo ⚠️  Pasta logs não encontrada
)

echo.
echo [5/5] Copiando Documentação...
echo ============================================

REM Copiar documentos de persistência
copy "ANALISE_PERSISTENCIA_DADOS_DOCKER.md" "C:\gestaoversus\referencias\" >nul 2>&1
copy "DECISAO_PERSISTENCIA_DADOS.md" "C:\gestaoversus\referencias\" >nul 2>&1
copy "ONDE_ESTAO_MEUS_DADOS.md" "C:\gestaoversus\referencias\" >nul 2>&1
copy "LEIA_PRIMEIRO_DADOS.md" "C:\gestaoversus\referencias\" >nul 2>&1
copy "_INDICE_PERSISTENCIA_DADOS.md" "C:\gestaoversus\referencias\" >nul 2>&1
copy "CONFIGURAR_BACKUP_AUTOMATICO.md" "C:\gestaoversus\referencias\" >nul 2>&1
copy "RESUMO_ANALISE_PERSISTENCIA.md" "C:\gestaoversus\referencias\" >nul 2>&1
copy "RESPOSTA_SUA_PERGUNTA.md" "C:\gestaoversus\referencias\" >nul 2>&1

echo ✅ Documentação copiada

echo.
echo ============================================
echo ✅ EXPORTAÇÃO CONCLUÍDA
echo ============================================
echo.
echo 📂 Todos os dados foram copiados para:
echo    C:\gestaoversus\referencias\
echo.
echo 📁 Estrutura criada:
dir /b "C:\gestaoversus\referencias"
echo.
echo 💡 COMO ACESSAR:
echo    1. Abra o Explorador de Arquivos (Windows + E)
echo    2. Cole na barra: C:\gestaoversus\referencias
echo    3. Pressione Enter
echo.
echo 🚀 OU execute: start explorer.exe "C:\gestaoversus\referencias"
echo.

set /p abrir="Deseja abrir a pasta agora? (S/N): "
if /i "%abrir%"=="S" (
    start explorer.exe "C:\gestaoversus\referencias"
    echo ✅ Pasta aberta!
)

echo.
pause

