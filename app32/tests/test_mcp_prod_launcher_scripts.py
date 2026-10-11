from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_prod_launcher_script_does_not_require_fixed_company_env():
    script = (_REPO_ROOT / "scripts" / "start_mcp_prod_ssh.ps1").read_text(encoding="utf-8")

    assert 'Require-Env "APP32_MCP_COMPANY_ID"' not in script
    # O id do usuário é citado com Quote-Posix (quoting seguro para o shell remoto), não por aspas fixas.
    assert '"APP32_MCP_USER_ID=$(Quote-Posix $userId)"' in script
    assert 'APP32_MCP_COMPANY_ID' in script


def test_prod_installer_documents_company_pin_as_optional():
    script = (_REPO_ROOT / "scripts" / "install_claude_mcp_app32_prod.ps1").read_text(encoding="utf-8")

    assert 'throw "Para usar -PersistUserEnv, informe pelo menos -McpUserId."' in script
    assert '`APP32_MCP_COMPANY_ID` é opcional' in script
    assert 'Write-Host "  # Opcional: `$env:APP32_MCP_COMPANY_ID=' in script


def test_deploy_script_forces_mcp_http_restart_after_publish():
    script = (_REPO_ROOT / "scripts" / "deploy_configr.sh").read_text(encoding="utf-8")

    assert 'Reiniciando runtime MCP HTTP remoto para refletir o código recém-publicado' in script
    # O reinício é delegado ao gerenciador idempotente; o start direto legado só roda se ele não existir.
    assert 'bash "$APP/scripts/manage_mcp_http.sh" restart' in script
    assert 'manage_mcp_http.sh não encontrado; usando start direto legado' in script
    assert 'lsof -tiTCP:8101 -sTCP:LISTEN' in script
    assert 'MCP HTTP remoto ativo em 127.0.0.1:8101 com código atualizado.' in script
    assert 'MCP_PUBLIC_HEALTH_URL="https://app.gestaoversus.com.br/mcp/healthz"' in script
    assert 'Listener MCP HTTP ativo na porta 8101 com PID(s)' in script
    assert 'MCP HTTP remoto respondeu também no health público /mcp/healthz.' in script
    assert 'for i in {1..30}; do' in script


def test_mcp_manager_stops_the_old_listener_and_checks_health():
    manager = (_REPO_ROOT / "scripts" / "manage_mcp_http.sh").read_text(encoding="utf-8")

    assert 'kill -TERM $pids' in manager and 'kill -KILL $pids' in manager
    assert 'forçando parada' in manager
    assert 'health_ok' in manager and 'public_health_ok' in manager
