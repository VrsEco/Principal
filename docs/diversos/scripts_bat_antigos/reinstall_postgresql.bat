@echo off
echo ========================================
echo    REINSTALACAO POSTGRESQL - APP29
echo    Banco: bd_app_versus
echo ========================================
echo.
echo IMPORTANTE: Execute este script como ADMINISTRADOR!
echo Pressione Ctrl+C para cancelar se nao for administrador.
echo.
pause

echo 1. Parando servicos PostgreSQL...
sc stop postgresql-x64-16 >nul 2>&1
sc stop postgresql-x64-17 >nul 2>&1
echo ✅ Servicos parados

echo.
echo 2. Removendo servicos PostgreSQL...
sc delete postgresql-x64-16 >nul 2>&1
sc delete postgresql-x64-17 >nul 2>&1
echo ✅ Servicos removidos

echo.
echo 3. Desinstalando PostgreSQL 16...
"C:\Program Files\PostgreSQL\16\uninstall-postgresql.exe" --mode unattended >nul 2>&1
echo ✅ PostgreSQL 16 desinstalado

echo.
echo 4. Desinstalando PostgreSQL 17...
"C:\Program Files\PostgreSQL\17\uninstall-postgresql.exe" --mode unattended >nul 2>&1
echo ✅ PostgreSQL 17 desinstalado

echo.
echo 5. Removendo diretorios restantes...
rmdir /s /q "C:\Program Files\PostgreSQL" >nul 2>&1
rmdir /s /q "C:\ProgramData\PostgreSQL" >nul 2>&1
echo ✅ Diretorios removidos

echo.
echo 6. Baixando PostgreSQL 16...
echo    Aguarde o download...
powershell -Command "Invoke-WebRequest -Uri 'https://get.enterprisedb.com/postgresql/postgresql-16.3-1-windows-x64.exe' -OutFile 'postgresql-installer.exe'"
if %errorlevel% neq 0 (
    echo ❌ Erro ao baixar PostgreSQL
    echo    Baixe manualmente de: https://www.postgresql.org/download/windows/
    pause
    exit /b 1
)
echo ✅ Download concluido

echo.
echo 7. Instalando PostgreSQL 16...
echo    Configuracoes:
echo    - Usuario: postgres
echo    - Senha: postgres123
echo    - Porta: 5432
echo    - Encoding: UTF8
echo.
postgresql-installer.exe --mode unattended --superpassword postgres123 --servicename postgresql-x64-16 --serviceaccount postgres --servicepassword postgres123 --serverport 5432 --locale C
if %errorlevel% neq 0 (
    echo ❌ Erro na instalacao
    pause
    exit /b 1
)
echo ✅ PostgreSQL 16 instalado

echo.
echo 8. Configurando PostgreSQL...
set PGPASSWORD=postgres123
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "ALTER USER postgres PASSWORD 'postgres123';" >nul 2>&1
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE DATABASE bd_app_versus;" >nul 2>&1
echo ✅ PostgreSQL configurado

echo.
echo 9. Testando conexao...
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d bd_app_versus -c "SELECT version();" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Erro no teste de conexao
    pause
    exit /b 1
)
echo ✅ Conexao testada com sucesso

echo.
echo 10. Limpando arquivos temporarios...
del postgresql-installer.exe >nul 2>&1
echo ✅ Limpeza concluida

echo.
echo ========================================
echo    POSTGRESQL REINSTALADO COM SUCESSO!
echo ========================================
echo.
echo Configuracoes:
echo - Usuario: postgres
echo - Senha: postgres123
echo - Porta: 5432
echo - Banco: bd_app_versus
echo.
echo Agora execute: python migrate_final_correct.py
echo.
pause
