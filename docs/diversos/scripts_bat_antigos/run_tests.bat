@echo off
echo ========================================================================
echo EXECUTANDO TODOS OS TESTES DO GESTAOVERSUS
echo ========================================================================
echo.

cd /d "%~dp0"
python -m pytest testsprite_tests\test_*.py -v --tb=short --maxfail=1000

echo.
echo ========================================================================
echo TESTES CONCLUIDOS
echo ========================================================================
pause

