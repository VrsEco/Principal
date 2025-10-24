@echo off
cls
echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║  🚀 INICIAR MY WORK - Sistema de Gestão de Atividades    ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo 📋 Checklist de Início:
echo.
echo [1/3] Aplicando migração do banco de dados...
python apply_my_work_migration.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️  Migração falhou ou já foi aplicada anteriormente
    echo    Se tabelas já existem, isso é normal!
    echo.
)

echo.
echo [2/3] Reiniciando Docker com as novas alterações...
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d --build

echo.
echo [3/3] Aguardando servidor iniciar...
timeout /t 15 /nobreak >nul

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║  ✅ MY WORK PRONTO PARA USO!                             ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo 🌐 PASSO A PASSO:
echo.
echo    1. Fazer login:
echo       http://127.0.0.1:5003/login
echo.
echo    2. No menu superior, clicar em:
echo       [Minhas Atividades]
echo.
echo    OU acessar direto:
echo       http://127.0.0.1:5003/my-work/
echo.
echo 🎯 FUNCIONALIDADES PARA TESTAR:
echo.
echo    ✅ Trocar entre abas (Minhas, Equipe, Empresa)
echo    ✅ Clicar em "+ Horas" e registrar horas
echo    ✅ Clicar em "Comentar" e adicionar nota
echo    ✅ Clicar em "Finalizar" e concluir atividade
echo    ✅ Ver Team Overview na aba Equipe
echo    ✅ Ver Company Overview na aba Empresa
echo    ✅ Filtrar por Hoje/Semana/Atrasadas
echo    ✅ Buscar atividades
echo.
echo 📚 DOCUMENTAÇÃO:
echo    → _README_MY_WORK.md (README principal)
echo    → TESTAR_MY_WORK_AGORA.md (Guia de testes)
echo    → COMO_USAR_MY_WORK.md (Guia do usuário)
echo.
echo 🎉 Abrindo navegador...
start http://127.0.0.1:5003/login
echo.
echo ✨ Sistema My Work inicializado com sucesso!
echo.
pause


