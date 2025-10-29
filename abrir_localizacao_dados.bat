@echo off
REM ============================================
REM Abrir Localização dos Dados - APP31
REM ============================================

echo ============================================
echo 📍 ABRINDO LOCALIZAÇÕES DOS DADOS
echo ============================================
echo.

echo [1/6] Abrindo diretório de Uploads...
if exist "uploads" (
    start explorer.exe "%cd%\uploads"
    echo ✅ Uploads: %cd%\uploads
) else (
    echo ⚠️  Diretório não encontrado: uploads
)
echo.

echo [2/6] Abrindo diretório de Backups...
if exist "backups" (
    start explorer.exe "%cd%\backups"
    echo ✅ Backups: %cd%\backups
) else (
    echo ⚠️  Diretório não encontrado: backups
)
echo.

echo [3/6] Abrindo diretório de Logs...
if exist "logs" (
    start explorer.exe "%cd%\logs"
    echo ✅ Logs: %cd%\logs
) else (
    echo ⚠️  Diretório não encontrado: logs
)
echo.

echo [4/6] Abrindo diretório de PDFs Temporários...
if exist "temp_pdfs" (
    start explorer.exe "%cd%\temp_pdfs"
    echo ✅ PDFs Temp: %cd%\temp_pdfs
) else (
    echo ⚠️  Diretório não encontrado: temp_pdfs
)
echo.

echo [5/6] Tentando abrir Volume Docker do PostgreSQL...
echo ℹ️  Caminho WSL: \\wsl$\docker-desktop-data\data\docker\volumes\app31_postgres_data_dev\_data
start explorer.exe "\\wsl$\docker-desktop-data\data\docker\volumes\app31_postgres_data_dev\_data" 2>nul
if %errorlevel% equ 0 (
    echo ✅ Volume PostgreSQL aberto
) else (
    echo ⚠️  Volume não acessível (Docker Desktop precisa estar rodando)
)
echo.

echo [6/6] Tentando abrir raiz do WSL Docker...
echo ℹ️  Caminho WSL: \\wsl$\docker-desktop-data\data\docker\volumes
start explorer.exe "\\wsl$\docker-desktop-data\data\docker\volumes" 2>nul
if %errorlevel% equ 0 (
    echo ✅ Raiz dos volumes Docker aberto
) else (
    echo ⚠️  WSL não acessível (Docker Desktop precisa estar rodando)
)
echo.

echo ============================================
echo ✅ LOCALIZAÇÕES ABERTAS
echo ============================================
echo.
echo 💡 DICAS:
echo    - Volumes Docker (\\wsl$\...) só aparecem com Docker rodando
echo    - Arquivos locais estão sempre disponíveis
echo    - Não modifique diretamente os arquivos do volume Docker!
echo.
echo 📋 CAMINHOS COMPLETOS:
echo.
echo 📁 Windows (Sempre Acessíveis):
echo    %cd%\uploads
echo    %cd%\backups
echo    %cd%\logs
echo    %cd%\temp_pdfs
echo.
echo 🐳 Docker (Requer Docker Desktop Rodando):
echo    \\wsl$\docker-desktop-data\data\docker\volumes\app31_postgres_data_dev\_data
echo    \\wsl$\docker-desktop-data\data\docker\volumes\app31_redis_data_dev\_data
echo.

pause

