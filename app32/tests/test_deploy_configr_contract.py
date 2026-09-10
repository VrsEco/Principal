import os
import shutil
import subprocess
from pathlib import Path


DEPLOY_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "deploy_configr.sh"


def test_configr_deploy_targets_versioned_app_directory_and_fails_on_drift():
    content = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    assert 'REPO="$WWW"' in content
    assert 'APP="$WWW/app32"' in content
    assert 'git -C "$REPO" status --porcelain' in content
    assert 'git -C "$REPO" reset --hard origin/main' in content
    assert 'DEPLOY_ALLOW_DIRTY' in content
    assert 'DEPLOY_DIRTY_SNAPSHOT' in content
    assert '"$BASE"/backups/*' in content
    assert content.index('git -C "$REPO" status --porcelain') < content.index(
        'git -C "$REPO" reset --hard origin/main'
    )
    assert 'if [ ! -f "$APP/app.py" ] || [ ! -f "$APP/requirements.txt" ]; then' in content
    assert 'chdir = $APP' in content
    assert 'module = passenger_wsgi:application' in content


def test_configr_deploy_validates_isolated_versioned_runtime(tmp_path):
    bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if not bash.exists() or shutil.which("git") is None:
        return

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

    env = os.environ | {
        "APP32_DEPLOY_BASE": tmp_path.as_posix(),
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
