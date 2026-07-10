from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_deploy_uses_idempotent_mcp_manager():
    deploy = (ROOT / "scripts" / "deploy_configr.sh").read_text(encoding="utf-8")

    assert "scripts/manage_mcp_http.sh" in deploy
    assert 'bash "$APP/scripts/manage_mcp_http.sh" restart' in deploy
    assert "MCP_LEGACY_PIDS=$(lsof -tiTCP:8101 -sTCP:LISTEN" in deploy
    assert "pkill -TERM -f \"start_mcp_http.sh|src.core.mcp_http_server\"" not in deploy


def test_mcp_manager_has_lock_pid_and_health_contract():
    manager = (ROOT / "scripts" / "manage_mcp_http.sh").read_text(encoding="utf-8")

    assert "LOCK_DIR=\"$TMP_DIR/mcp_http.lock\"" in manager
    assert "PID_FILE=\"$TMP_DIR/mcp_http.pid\"" in manager
    assert "HEALTH_URL=\"http://$HOST:$PORT/healthz\"" in manager
    assert "PUBLIC_HEALTH_URL=\"$PUBLIC_BASE/mcp/healthz\"" in manager
    assert "acquire_lock" in manager
    assert "start|stop|restart|status|health" in manager
