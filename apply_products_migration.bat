@echo off
echo ========================================
echo Aplicando Migration: plan_products
echo ========================================

echo.
echo Conectando ao PostgreSQL...

docker exec gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -f /app/migrations/create_plan_products_table.sql

IF %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✅ Migration aplicada com sucesso!
    echo ========================================
) ELSE (
    echo.
    echo ========================================
    echo ❌ Erro ao aplicar migration
    echo ========================================
)

pause

