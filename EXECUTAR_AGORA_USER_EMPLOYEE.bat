@echo off
echo ================================================================================
echo APLICACAO DA SOLUCAO: Vinculo User - Employee
echo ================================================================================
echo.

echo [1/3] Aplicando migration no banco de dados...
C:\Users\mff20\anaconda3\python.exe apply_user_employee_link_migration.py
echo.

pause

echo [2/3] Vinculando users existentes aos employees...
C:\Users\mff20\anaconda3\python.exe link_users_to_employees.py
echo.

pause

echo [3/3] Teste manual:
echo    Acesse: http://127.0.0.1:5003/my-work/
echo.
echo ================================================================================
echo CONCLUIDO!
echo ================================================================================
pause

