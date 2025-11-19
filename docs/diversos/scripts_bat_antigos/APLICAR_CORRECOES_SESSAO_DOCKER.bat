@echo off
echo ============================================
echo   APLICAR CORRECOES DE SESSAO - DOCKER
echo   GestaoVersus - Ambiente Desenvolvimento
echo ============================================
echo.

echo [INFO] As seguintes correcoes serao aplicadas:
echo   ✅ Reducao de sessao persistente (30 → 7 dias)
echo   ✅ Protecoes XSS e CSRF
echo   ✅ Logout via GET habilitado
echo.

echo ============================================
echo   PASSO 1: Verificar containers em execucao
echo ============================================
docker ps --format "table {{.Names}}\t{{.Status}}" | findstr gestaoversus
echo.

echo ============================================
echo   PASSO 2: Reiniciar container da aplicacao
echo ============================================
echo [INFO] Reiniciando gestaoversus_app_dev...
docker-compose -f docker-compose.dev.yml restart app_dev
echo.

echo ⏳ Aguardando 5 segundos para app inicializar...
timeout /t 5 /nobreak > nul
echo.

echo ============================================
echo   PASSO 3: Verificar logs da aplicacao
echo ============================================
echo [INFO] Ultimas 20 linhas do log:
docker logs gestaoversus_app_dev --tail 20
echo.

echo ============================================
echo   PASSO 4: Testar se app responde
echo ============================================
curl -s -o nul -w "HTTP Status: %%{http_code}\n" http://localhost:5003/
echo.

echo ============================================
echo   PROXIMOS PASSOS - TESTE MANUAL
echo ============================================
echo.
echo 1. FAZER LOGOUT:
echo    - Acesse: http://127.0.0.1:5003/auth/logout
echo    - Deve redirecionar para login
echo.
echo 2. TESTAR PROTECAO:
echo    - Acesse: http://127.0.0.1:5003/main
echo    - Deve solicitar login (se nao estiver autenticado)
echo.
echo 3. FAZER LOGIN:
echo    - Email: admin@versus.com.br
echo    - Senha: 123456
echo.
echo 4. VERIFICAR COOKIES (F12 - Application):
echo    - Veja cookie "session"
echo    - Deve ter HttpOnly = true
echo    - Deve ter SameSite = Lax
echo.
echo ============================================
echo   ARQUIVOS MODIFICADOS
echo ============================================
echo   - config.py (configuracoes de sessao)
echo   - api/auth.py (logout via GET)
echo.
echo ============================================
echo   DOCUMENTACAO
echo ============================================
echo   - CORRECAO_SESSAO_PERSISTENTE.md
echo   - GUIA_RAPIDO_LOGOUT.md
echo.

pause


