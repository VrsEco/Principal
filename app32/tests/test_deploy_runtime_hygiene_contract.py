from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]


def test_deploy_does_not_change_tracked_script_modes_at_runtime():
    content = (APP_ROOT / "scripts" / "deploy_configr.sh").read_text(encoding="utf-8")

    assert 'chmod +x "$APP/scripts/manage_scheduler.sh"' not in content
    assert 'chmod +x "$APP/scripts/start_mcp_http.sh"' not in content
    assert 'chmod +x "$APP/scripts/manage_mcp_http.sh"' not in content
    assert 'bash "$APP/scripts/start_mcp_http.sh"' in content


def test_mcp_manager_runs_start_script_via_bash_without_chmod():
    content = (APP_ROOT / "scripts" / "manage_mcp_http.sh").read_text(encoding="utf-8")

    assert 'chmod +x "$START_SCRIPT"' not in content
    assert 'bash "$START_SCRIPT"' in content
