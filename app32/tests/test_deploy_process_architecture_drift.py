import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-app32.yml"
STALE_BLOB = "8b5c5f783a22a010d757a051b3e22709bce0b3ed"
TARGET_BLOB = "6290998521a2e28d64cd94223698184ebfcdd20c"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _remote_script() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["deploy"]["steps"]
    step = next(item for item in steps if item["name"] == "🚀 Executing remote ssh commands to deploy")
    return step["with"]["script"]


def _contingency_script() -> str:
    script = _remote_script()
    start = script.index(
        'if [ "${{ inputs.remediate_process_architecture_runtime_drift }}" = "true" ]; then'
    )
    end = script.index('if [ -f "app32/scripts/deploy_configr.sh" ]; then', start)
    return script[start:end]


def test_process_architecture_exception_is_human_only_and_bound_to_known_blobs():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    inputs = workflow[True]["workflow_dispatch"]["inputs"]
    exception = inputs["remediate_process_architecture_runtime_drift"]
    assert exception["type"] == "boolean"
    assert exception["default"] is False

    steps = workflow["jobs"]["deploy"]["steps"]
    provenance = next(item["run"] for item in steps if item["name"] == "🛡️ Validar proveniência e correlação")
    assert '"$ACTOR" != "VrsEco"' in provenance
    assert '"$TRIGGERING_ACTOR" != "VrsEco"' in provenance
    assert '"refs/heads/main"' in provenance
    assert 'inputs.remediate_chartjs_runtime_drift' in provenance
    assert 'inputs.mode' in provenance
    assert 'inputs.restart_mcp' in provenance

    target = next(item["run"] for item in steps if item["name"] == "🔒 Confirmar blob alvo da contingência de processos")
    assert TARGET_BLOB in target
    script = _remote_script()
    block = _contingency_script()
    assert STALE_BLOB in block
    assert 'status --porcelain=v1' in block
    assert ' M static/js/process_architecture.js' in block
    assert 'ls-remote origin refs/heads/main' in block
    assert 'diff --cached --quiet' in block
    assert 'diff --binary -- "$ASSET"' in block
    assert 'sha256sum -c SHA256SUMS' in block
    assert block.index('sha256sum -c SHA256SUMS') < block.index('checkout -- "$ASSET"')
    assert block.index('umask "$PREVIOUS_UMASK"') < block.index('checkout -- "$ASSET"')
    assert block.index('chmod 0644 "$ASSET_PATH"') > block.index('reset --hard "${{ github.sha }}"')
    assert script.index('checkout -- "$ASSET"') < script.index('DEPLOY_MODE=')
    assert 'SHA implantado diverge do run aprovado.' in script
    assert 'DEPLOY_EXPECTED_SHA="${{ github.sha }}"' in script
    assert script.index('sha256sum -c SHA256SUMS') < script.index('reset --hard "${{ github.sha }}"')
    assert script.index('FETCHED_MAIN_SHA="$(git -C "$REPO" rev-parse origin/main)"') < script.index(
        'reset --hard "${{ github.sha }}"'
    )

    public_asset = next(item["run"] for item in steps if item["name"] == "🔎 Conferir bytes públicos do asset de processos")
    assert 'git hash-object --stdin' in public_asset
    assert '/static/js/process_architecture.js?run=' in public_asset


@pytest.mark.parametrize(
    ("variant", "should_succeed"),
    [
        ("known_legacy_blob", True),
        ("unknown_blob", False),
        ("extra_untracked", False),
        ("main_advanced", False),
    ],
)
def test_controlled_snapshot_restores_only_exact_known_drift(tmp_path: Path, variant: str, should_succeed: bool):
    bash = Path(r"C:\Program Files\Git\bin\bash.exe") if os.name == "nt" else Path(shutil.which("bash") or "")
    if not bash.is_file() or shutil.which("git") is None:
        pytest.skip("bash/git indisponíveis")

    repo = tmp_path / "www"
    app = repo / "app32"
    asset = repo / "static" / "js" / "process_architecture.js"
    app.mkdir(parents=True)
    asset.parent.mkdir(parents=True)
    scripts = app / "scripts"
    scripts.mkdir()
    (scripts / "deploy_configr.sh").write_text("# DEPLOY_EXPECTED_SHA\n", encoding="utf-8")
    (app / ".keep").write_text("runtime\n", encoding="utf-8")
    asset.write_bytes(b"target\n")
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    _git(repo, "config", "user.email", "qa@app32.local")
    _git(repo, "config", "user.name", "QA APP32")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "target",)
    remote = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "--initial-branch=main", str(remote)], check=True, capture_output=True)
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "origin", "main")
    target_sha = _git(repo, "rev-parse", "HEAD")
    if variant == "main_advanced":
        other = tmp_path / "other"
        subprocess.run(["git", "clone", str(remote), str(other)], check=True, capture_output=True)
        _git(other, "config", "user.email", "qa@app32.local")
        _git(other, "config", "user.name", "QA APP32")
        (other / "app32" / ".keep").write_text("advanced main\n", encoding="utf-8")
        _git(other, "add", "app32/.keep")
        _git(other, "commit", "-m", "advanced")
        _git(other, "push", "origin", "main")
    backups = tmp_path / "backups"
    backups.mkdir()

    legacy = b"legacy\n"
    legacy_blob = subprocess.run(
        ["git", "hash-object", "--stdin"],
        input=legacy,
        check=True,
        capture_output=True,
    ).stdout.decode("ascii").strip()
    asset.write_bytes(legacy if variant != "unknown_blob" else b"unapproved\n")
    if os.name != "nt":
        asset.parent.chmod(0o700)
    if variant == "extra_untracked":
        (repo / "extra.txt").write_text("other drift\n", encoding="utf-8")

    script = "umask 077\n" + _contingency_script()
    script = script.replace(STALE_BLOB, legacy_blob)
    script = script.replace("${{ inputs.remediate_process_architecture_runtime_drift }}", "true")
    script = script.replace("${{ github.sha }}", target_sha)
    script = script.replace("${{ github.run_id }}", "123456")
    if os.name == "nt":
        script = script.replace(
            'REPO="$(git -C "$START_DIR" rev-parse --show-toplevel)"',
            'REPO="$(cygpath -u "$(git -C "$START_DIR" rev-parse --show-toplevel)")"',
        )

    result = subprocess.run(
        [str(bash), "-e", "-c", script],
        cwd=app,
        env=os.environ | {"ACTOR": "VrsEco"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    snapshots = list(backups.glob("worktree-drift-process-architecture-*"))
    if should_succeed:
        assert result.returncode == 0, result.stdout + result.stderr
        assert _git(repo, "status", "--porcelain=v1") == ""
        assert asset.read_text(encoding="utf-8").strip() == "target"
        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert (snapshot / "process_architecture.js").read_bytes() == legacy
        assert (snapshot / "process_architecture.patch").stat().st_size > 0
        assert (snapshot / "SHA256SUMS").stat().st_size > 0
        if os.name != "nt":
            assert snapshot.stat().st_mode & 0o777 == 0o700
            assert (snapshot / "process_architecture.js").stat().st_mode & 0o777 == 0o600
            assert asset.stat().st_mode & 0o777 == 0o644
            assert asset.parent.stat().st_mode & 0o777 == 0o755
    else:
        assert result.returncode != 0
        assert snapshots == []
        assert asset.read_text(encoding="utf-8").strip() in {"legacy", "unapproved"}
