"""Monitor do scheduler dedicado: age só após falhas consecutivas, só com start e nunca fora do scheduler."""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "monitor_scheduler.sh"


def _working_bash():
    """Primeiro bash que de fato executa (no Windows, 'bash' pode ser o stub do WSL sem distribuição)."""
    for candidate in (os.environ.get("APP32_TEST_BASH"), "bash", "C:/Program Files/Git/bin/bash.exe"):
        if not candidate:
            continue
        try:
            probe = subprocess.run([candidate, "-c", "echo ok"], capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


BASH = _working_bash()
pytestmark = pytest.mark.skipif(BASH is None, reason="bash funcional indisponível")

STUB_MANAGER = """#!/bin/bash
# Manager falso: health lê health_rc; start registra a chamada e, se start_rc=0, passa a ficar saudável.
D="$(dirname "$0")/stub"
case "$1" in
  health) exit "$(cat "$D/health_rc" 2>/dev/null || echo 1)" ;;
  start)  echo start >> "$D/calls"; rc="$(cat "$D/start_rc" 2>/dev/null || echo 0)"
          [ "$rc" = "0" ] && echo 0 > "$D/health_rc"; exit "$rc" ;;
  *)      echo "$1" >> "$D/calls"; exit 0 ;;
esac
"""


@pytest.fixture()
def env(tmp_path):
    scripts = tmp_path / "scripts"
    stub = scripts / "stub"
    stub.mkdir(parents=True)
    (scripts / "manage_scheduler.sh").write_text(STUB_MANAGER, encoding="utf-8", newline="\n")
    return tmp_path


def _set(env, health=None, start=None):
    stub = env / "scripts" / "stub"
    if health is not None:
        (stub / "health_rc").write_text(str(health))
    if start is not None:
        (stub / "start_rc").write_text(str(start))


def _run(env, threshold=2):
    return subprocess.run(
        [BASH, SCRIPT.as_posix()],
        env={**os.environ, "APP32_APP_DIR": env.as_posix(), "APP32_SCHEDULER_MONITOR_FAIL_THRESHOLD": str(threshold)},
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )


def _calls(env):
    f = env / "scripts" / "stub" / "calls"
    return f.read_text().split() if f.exists() else []


def _failures(env):
    return int((env / "tmp" / "scheduler_monitor.failures").read_text().strip())


def test_healthy_scheduler_is_left_alone_and_silent(env):
    _set(env, health=0)
    result = _run(env)
    assert result.returncode == 0 and result.stdout.strip() == "", "saudável não escreve no log"
    assert _calls(env) == [] and _failures(env) == 0


def test_a_single_failure_never_starts_anything(env):
    _set(env, health=1)
    result = _run(env)
    assert result.returncode == 0 and _calls(env) == [] and _failures(env) == 1


def test_second_consecutive_failure_runs_start_and_only_start(env):
    _set(env, health=1, start=0)
    _run(env)
    result = _run(env)
    assert result.returncode == 0
    assert _calls(env) == ["start"], "a única ação permitida é start"
    assert _failures(env) == 0 and "reparado" in result.stdout


def test_recovery_between_failures_resets_the_counter(env):
    _set(env, health=1)
    _run(env)
    _set(env, health=0)
    _run(env)
    _set(env, health=1)
    _run(env)
    assert _calls(env) == [] and _failures(env) == 1, "falhas não consecutivas não disparam ação"


def test_failed_start_reports_error_and_keeps_counting(env):
    _set(env, health=1, start=1)
    _run(env)
    result = _run(env)
    assert result.returncode == 1 and _calls(env) == ["start"] and _failures(env) == 2


def test_a_running_monitor_blocks_a_second_one(env):
    (env / "tmp" / "scheduler_monitor.lock").mkdir(parents=True)
    _set(env, health=1)
    result = _run(env)
    assert result.returncode == 0 and _calls(env) == [] and "já em execução" in result.stdout


def test_script_never_touches_other_services():
    text = SCRIPT.read_text(encoding="utf-8")
    for forbidden in ("uwsgi", "nginx", "keycloak", "manage_mcp_http", "systemctl", "kill ", "restart"):
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        assert forbidden not in code.lower().replace("reiniciar", ""), forbidden
    assert 'bash "$MANAGER" start' in text and 'bash "$MANAGER" health' in text
