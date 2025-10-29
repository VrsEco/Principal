@echo off
REM ============================================
REM Copiar Dados para C:\gestaoversus\referencias
REM ============================================

echo ============================================
echo Copiando dados para C:\gestaoversus\referencias
echo ============================================
echo.

REM Criar diretório
if not exist "C:\gestaoversus\referencias" mkdir "C:\gestaoversus\referencias"

echo [1/4] Copiando documentacao...
copy "ANALISE_PERSISTENCIA_DADOS_DOCKER.md" "C:\gestaoversus\referencias\" 2>nul
copy "DECISAO_PERSISTENCIA_DADOS.md" "C:\gestaoversus\referencias\" 2>nul
copy "ONDE_ESTAO_MEUS_DADOS.md" "C:\gestaoversus\referencias\" 2>nul
copy "LEIA_PRIMEIRO_DADOS.md" "C:\gestaoversus\referencias\" 2>nul
copy "_INDICE_PERSISTENCIA_DADOS.md" "C:\gestaoversus\referencias\" 2>nul
copy "RESPOSTA_SUA_PERGUNTA.md" "C:\gestaoversus\referencias\" 2>nul
echo OK - Documentacao copiada

echo.
echo [2/4] Copiando backups...
if exist "backups" (
    xcopy /E /I /Y "backups" "C:\gestaoversus\referencias\backups" >nul
    echo OK - Backups copiados
) else (
    echo Pasta backups nao encontrada
)

echo.
echo [3/4] Copiando uploads...
if exist "uploads" (
    xcopy /E /I /Y "uploads" "C:\gestaoversus\referencias\uploads" >nul
    echo OK - Uploads copiados
) else (
    echo Pasta uploads nao encontrada
)

echo.
echo [4/4] Copiando logs...
if exist "logs" (
    xcopy /E /I /Y "logs" "C:\gestaoversus\referencias\logs" >nul
    echo OK - Logs copiados
) else (
    echo Pasta logs nao encontrada
)

echo.
echo ============================================
echo CONCLUIDO!
echo ============================================
echo.
echo Dados copiados para: C:\gestaoversus\referencias
echo.
echo Abrindo pasta...
start explorer.exe "C:\gestaoversus\referencias"
echo.
pause


