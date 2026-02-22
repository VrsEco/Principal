@echo off
cls
echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║  🚀 REINICIAR DOCKER - MY WORK                           ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo 📦 Parando containers...
docker-compose -f docker-compose.dev.yml down

echo.
echo 🔨 Reconstruindo com novas alteracoes...
docker-compose -f docker-compose.dev.yml up -d --build

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║  ✅ Container reiniciado com sucesso!                    ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo 🌐 URL: http://127.0.0.1:5003/my-work-demo
echo.
echo ⚠️  IMPORTANTE: Você precisa estar LOGADO primeiro!
echo    1. Acesse: http://127.0.0.1:5003/login
echo    2. Faça login
echo    3. Depois acesse: http://127.0.0.1:5003/my-work-demo
echo.
echo ⏳ Aguardando servidor iniciar (15 segundos)...
timeout /t 15 /nobreak >nul

echo.
echo 🎉 Abrindo navegador...
echo.
echo ✨ Teste as funcionalidades:
echo    ✅ Trocar abas (Minhas, Equipe, Empresa)
echo    ✅ Clicar em "+ Horas" (modal abre)
echo    ✅ Clicar em "Comentar" (modal abre)
echo    ✅ Clicar em "Finalizar" (modal abre)
echo    ✅ Trocar entre "Hoje" e "Semana" na sidebar
echo.
start http://127.0.0.1:5003/my-work-demo

echo.
echo 📚 Consulte o checklist completo:
echo    MY_WORK_TESTING_CHECKLIST.md
echo.
pause

