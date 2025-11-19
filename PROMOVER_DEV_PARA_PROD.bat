@echo off
REM ============================================
REM Script: PROMOVER_DEV_PARA_PROD.bat
REM Descrição: Copia código de app32 (dev) para app31 (prod)
REM Uso: Execute APENAS quando app32 estiver testado e estável
REM ============================================

echo ============================================
echo PROMOVER app32 (DEV) -^> app31 (PROD)
echo ============================================
echo.
echo AVISO: Este script ira:
echo   1. Fazer BACKUP de app31 antes de sobrescrever
echo   2. Copiar todo o codigo de app32 para app31
echo   3. Preservar arquivos de configuracao de producao
echo.
echo Deseja continuar? (S/N)
set /p confirmacao=

if /i not "%confirmacao%"=="S" (
    echo Cancelado.
    exit /b
)

echo.
echo Criando backup de app31...
set BACKUP_DIR=..\app31_backup_%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set BACKUP_DIR=%BACKUP_DIR: =0%

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
xcopy /E /I /Y "..\app31" "%BACKUP_DIR%"

echo Backup criado em: %BACKUP_DIR%
echo.

echo Copiando arquivos de app32 para app31...
echo.

REM Diretorios a copiar
robocopy "..\app32" "..\app31" /E /XD .venv __pycache__ .git instance uploads temp_pdfs logs backups node_modules .vscode .idea /XF *.db *.sqlite *.sqlite3 *.log .env.local .env.development

if %ERRORLEVEL% GEQ 8 (
    echo ERRO ao copiar arquivos!
    exit /b 1
)

echo.
echo Arquivos copiados com sucesso!
echo.

REM Preservar arquivos de producao
echo Preservando configuracoes de producao...
if exist "..\app31\.env.production" (
    echo Mantendo .env.production
)
if exist "..\app31\docker-compose.override.yml" (
    echo Mantendo docker-compose.override.yml
)

echo.
echo ============================================
echo PROMOCAO CONCLUIDA!
echo ============================================
echo.
echo Proximos passos:
echo   1. Navegue ate app31: cd ..\app31
echo   2. Revise as mudancas
echo   3. Teste localmente: docker-compose up
echo   4. Se tudo OK, faca commit: git add . ^&^& git commit -m "Promovido de app32"
echo   5. Faca deploy: git push
echo.
pause



