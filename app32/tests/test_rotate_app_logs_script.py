"""Rotação de logs do APP32: só a lista fixa, só acima do limite, sem perder o fluxo de quem grava em append."""

import gzip
import os
import subprocess
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rotate_app_logs.sh"


def _working_bash():
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

LIMIT = 1000  # bytes, só para o teste


@pytest.fixture()
def app(tmp_path):
    (tmp_path / "logs").mkdir()
    return tmp_path


def _run(app, *args, keep=3):
    return subprocess.run(
        [BASH, SCRIPT.as_posix(), *args],
        env={**os.environ, "APP32_APP_DIR": app.as_posix(), "APP32_LOG_ROTATE_MAX_BYTES": str(LIMIT), "APP32_LOG_ROTATE_KEEP": str(keep)},
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )


def _archives(app, name):
    return sorted((app / "logs").glob(f"{name}.*.gz"))


def test_big_file_is_compressed_then_truncated_and_content_is_preserved(app):
    big = app / "logs" / "scheduler_stderr.log"
    content = ("linha de log\n" * 200).encode("utf-8")
    big.write_bytes(content)
    result = _run(app)
    assert result.returncode == 0, result.stdout + result.stderr
    assert big.stat().st_size == 0
    (archive,) = _archives(app, "scheduler_stderr.log")
    assert gzip.decompress(archive.read_bytes()) == content


def test_small_files_and_unlisted_files_are_never_touched(app):
    small = app / "logs" / "scheduler_stderr.log"
    small.write_text("pequeno\n", encoding="utf-8")
    other = app / "logs" / "uwsgi.log"           # fora da lista fixa
    other.write_text("x" * 5000, encoding="utf-8")
    result = _run(app)
    assert result.returncode == 0
    assert small.read_text() == "pequeno\n" and other.stat().st_size == 5000
    assert _archives(app, "scheduler_stderr.log") == [] and _archives(app, "uwsgi.log") == []
    assert "Nada a rotacionar" in result.stdout


def test_dry_run_changes_nothing(app):
    big = app / "logs" / "mcp_http_stderr.log"
    big.write_text("x" * 5000, encoding="utf-8")
    result = _run(app, "--dry-run")
    assert result.returncode == 0 and "dry-run" in result.stdout
    assert big.stat().st_size == 5000 and _archives(app, "mcp_http_stderr.log") == []


def test_a_writer_in_append_mode_keeps_writing_after_the_truncation_without_holes(app):
    big = app / "logs" / "scheduler_stderr.log"
    big.write_bytes(b"antes\n" * 300)
    writer = open(big, "ab")   # como o nohup com ">>"
    try:
        assert _run(app).returncode == 0
        writer.write("depois da rotação\n".encode("utf-8"))
        writer.flush()
    finally:
        writer.close()
    data = big.read_bytes()
    assert data == "depois da rotação\n".encode("utf-8"), "sem bytes nulos nem buraco"
    assert b"\x00" not in data


def test_only_the_newest_archives_are_kept(app):
    big = app / "logs" / "scheduler_stderr.log"
    for i in range(4):
        big.write_text(f"rodada {i}\n" * 200, encoding="utf-8")
        assert _run(app, keep=2).returncode == 0
        time.sleep(1.1)  # o carimbo tem resolução de 1 segundo
    archives = _archives(app, "scheduler_stderr.log")
    assert len(archives) == 2
    assert "rodada 3" in gzip.decompress(archives[-1].read_bytes()).decode("utf-8")


def test_a_second_run_in_progress_is_not_disturbed(app):
    (app / "tmp" / "rotate_app_logs.lock").mkdir(parents=True)
    big = app / "logs" / "scheduler_stderr.log"
    big.write_text("x" * 5000, encoding="utf-8")
    result = _run(app)
    assert result.returncode == 0 and "já em execução" in result.stdout
    assert big.stat().st_size == 5000


def test_script_only_manipulates_the_fixed_list_of_app_logs():
    text = SCRIPT.read_text(encoding="utf-8")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    for forbidden in ("uwsgi", "nginx", ".env", "systemctl", "kill ", "pkill", "restart", "psql"):
        assert forbidden not in code.lower(), forbidden
    for name in ("scheduler_stderr.log", "mcp_http_stderr.log", "scheduler_monitor.log"):
        assert name in code
