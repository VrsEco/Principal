@echo off
chcp 65001 >nul
echo ========================================
echo CORRIGIR ERRO AO SALVAR APORTE
echo ========================================
echo.
echo Este script vai:
echo 1. Criar tabelas de investimentos
echo 2. Popular itens padrão
echo 3. Verificar resultado
echo.

echo [1/3] Aplicando migration...
python apply_investment_migration.py
if errorlevel 1 (
    echo ❌ Erro ao aplicar migration
    pause
    exit /b 1
)

echo.
echo [2/3] Populando itens de investimento...
python scripts\seed_investment_items.py
if errorlevel 1 (
    echo ❌ Erro ao popular itens
    pause
    exit /b 1
)

echo.
echo [3/3] Verificando resultado...
python check_investment_tables.py

echo.
echo ========================================
echo ✅ CORREÇÃO APLICADA COM SUCESSO!
echo ========================================
echo.
echo Agora teste em:
echo http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=8
echo.
echo Clique em "+ Adicionar Aporte" e preencha o formulário.
echo.
pause
