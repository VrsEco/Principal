@echo off
echo Iniciando PostgreSQL 14 manualmente...
"C:\Program Files\PostgreSQL\14\bin\pg_ctl" -D "C:\Program Files\PostgreSQL\14\data" start
pause