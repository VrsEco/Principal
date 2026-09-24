import os
import shutil
import subprocess
from pathlib import Path

import pytest


DEPLOY_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "deploy_configr.sh"


def test_configr_deploy_targets_versioned_app_directory_and_fails_on_drift():
    content = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'REPO="$WWW"' in content
    assert 'APP="$WWW/app32"' in content
    assert 'git -C "$REPO" status --porcelain' in content
    assert 'git -C "$REPO" update-index --refresh -q' in content
    assert 'git -C "$REPO" update-index --refresh --quiet' not in content
    assert 'DEPLOY_EXPECTED_SHA' in content
    assert 'FETCHED_SHA="$(git -C "$REPO" rev-parse origin/main)"' in content
    assert 'RESET_TARGET="$DEPLOY_EXPECTED_SHA"' in content
    assert 'git -C "$REPO" reset --hard "$RESET_TARGET"' in content
    assert content.index('FETCHED_SHA="$(git -C "$REPO" rev-parse origin/main)"') < content.index(
        'git -C "$REPO" reset --hard "$RESET_TARGET"'
    )
    assert 'DEPLOY_ALLOW_DIRTY' in content
    assert 'DEPLOY_DIRTY_SNAPSHOT' in content
    assert '"$BASE"/backups/*' in content
    assert content.index('git -C "$REPO" status --porcelain') < content.index(
        'git -C "$REPO" reset --hard "$RESET_TARGET"'
    )
    assert 'if [ ! -f "$APP/app.py" ] || [ ! -f "$APP/requirements.txt" ]; then' in content
    assert '"chdir": app_dir,' in content
    assert '"module": "passenger_wsgi:application",' in content


def test_configr_deploy_validates_isolated_versioned_runtime(tmp_path):
    bash = Path(r"C:\Program Files\Git\bin\bash.exe") if os.name == "nt" else Path(shutil.which("bash") or "")
    if not bash.is_file() or shutil.which("git") is None:
        pytest.skip("bash/git indisponíveis")

    repo = tmp_path / "www"
    app = repo / "app32"
    app.mkdir(parents=True)
    (app / "app.py").write_text("application = object()\n", encoding="utf-8")
    (app / "requirements.txt").write_text("\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "qa@app32.local"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "QA APP32"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "app32"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "test runtime layout"], check=True, capture_output=True)

    deploy_base = tmp_path.as_posix()
    if os.name == "nt":
        deploy_base = subprocess.run(
            [str(bash), "-lc", 'cygpath -u "$1"', "_", str(tmp_path)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
    env = os.environ | {
        "APP32_DEPLOY_BASE": deploy_base,
        "DEPLOY_VALIDATE_ONLY": "1",
    }
    result = subprocess.run(
        [str(bash), str(DEPLOY_SCRIPT)],
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, (result.stderr or "") + (result.stdout or "")
    assert "Validação local do contrato concluída" in result.stdout


def test_configr_deploy_refuses_advanced_main_before_reset(tmp_path):
    bash = Path(r"C:\Program Files\Git\bin\bash.exe") if os.name == "nt" else Path(shutil.which("bash") or "")
    if not bash.is_file() or shutil.which("git") is None:
        pytest.skip("bash/git indisponíveis")

    repo = tmp_path / "www"
    app = repo / "app32"
    app.mkdir(parents=True)
    (app / "app.py").write_text("application = object()\n", encoding="utf-8")
    (app / "requirements.txt").write_text("\n", encoding="utf-8")
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "qa@app32.local"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "QA APP32"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "app32"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "approved"], check=True, capture_output=True)
    approved_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout.strip()

    remote = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", str(remote)],
        check=True, capture_output=True,
    )
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", str(remote)], check=True)
    subprocess.run(["git", "-C", str(repo), "push", "origin", "main"], check=True, capture_output=True)

    other = tmp_path / "other"
    subprocess.run(["git", "clone", str(remote), str(other)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(other), "config", "user.email", "qa@app32.local"], check=True)
    subprocess.run(["git", "-C", str(other), "config", "user.name", "QA APP32"], check=True)
    (other / "app32" / "app.py").write_text("application = 'new main'\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(other), "add", "app32/app.py"], check=True)
    subprocess.run(["git", "-C", str(other), "commit", "-m", "advanced"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(other), "push", "origin", "main"], check=True, capture_output=True)

    deploy_base = tmp_path.as_posix()
    if os.name == "nt":
        deploy_base = subprocess.run(
            [str(bash), "-lc", 'cygpath -u "$1"', "_", str(tmp_path)],
            check=True, capture_output=True, text=True, encoding="utf-8",
        ).stdout.strip()
    env = os.environ | {
        "APP32_DEPLOY_BASE": deploy_base,
        "DEPLOY_EXPECTED_SHA": approved_sha,
        "DEPLOY_MODE": "quick",
        "RESTART_MCP": "false",
    }
    result = subprocess.run(
        [str(bash), str(DEPLOY_SCRIPT)],
        env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=False,
    )
    assert result.returncode != 0
    assert "Reset recusado" in result.stdout
    current_sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, encoding="utf-8",
    ).stdout.strip()
    assert current_sha == approved_sha
