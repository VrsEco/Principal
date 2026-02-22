@echo off
echo ========================================
echo TESTE DE ACESSO - Cadastro de Produtos
echo ========================================
echo.
echo Este script ajuda a identificar problemas de acesso
echo.

echo [1/4] Verificando containers...
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr gestaoversus

echo.
echo [2/4] Testando porta 5003...
curl -s -o nul -w "Status HTTP: %%{http_code}" http://localhost:5003/ 
echo.

echo.
echo [3/4] Verificando rota de produtos...
curl -s http://localhost:5003/pev/dashboard | findstr /C:"pev_dashboard" >nul
IF %ERRORLEVEL% EQU 0 (
    echo ✅ Dashboard PEV está acessível
) ELSE (
    echo ❌ Problema ao acessar dashboard
)

echo.
echo [4/4] Instruções de Acesso:
echo.
echo ========================================
echo COMO ACESSAR:
echo ========================================
echo.
echo 1. Abra no navegador:
echo    http://localhost:5003/pev/dashboard
echo.
echo 2. Escolha uma empresa/planejamento
echo.
echo 3. Clique em "Visualizar Implantação"
echo.
echo 4. No MENU LATERAL ESQUERDO, procure:
echo    "📦 Cadastro de Produtos"
echo.
echo 5. Está entre:
echo    - Estruturas de Execução (acima)
echo    - Modelagem Financeira (abaixo)
echo.
echo ========================================
echo.
echo Ou use o ACESSO DIRETO (substitua X pelo plan_id):
echo.
echo http://localhost:5003/pev/implantacao/modelo/produtos?plan_id=X
echo.
echo ========================================

pause



