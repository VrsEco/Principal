@echo off
echo ============================================
echo   CRIANDO TABELAS PARA CANVAS EXPECTATIVAS
echo ============================================
echo.

echo Executando script SQL...
echo.

REM Executar o script SQL no PostgreSQL
psql -h localhost -p 5432 -U postgres -d gestao_versus -f CRIAR_TABELAS_ALIGNMENT.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ TABELAS CRIADAS COM SUCESSO!
    echo.
    echo Agora você pode testar o Canvas de Expectativas:
    echo http://127.0.0.1:5003/pev/implantacao/alinhamento/canvas-expectativas?plan_id=8
    echo.
) else (
    echo.
    echo ❌ ERRO ao criar tabelas!
    echo Verifique a conexão com PostgreSQL.
    echo.
)

pause
