import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
for name in ("google_drive_backup", "run_external_backup"):
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)

runner = sys.modules["run_external_backup"]


def test_dry_run_never_requires_secrets_or_creates_artifacts(tmp_path):
    args = runner.parse_args(["--repo", str(tmp_path), "--staging-dir", str(tmp_path / "staging"), "--dry-run"])

    result = runner.run(args)

    assert result["mode"] == "dry-run"
    assert result["upload_enabled"] is False
    assert not (tmp_path / "staging").exists()


def test_upload_requires_explicit_opt_in(tmp_path):
    args = runner.parse_args(["--repo", str(tmp_path), "--staging-dir", str(tmp_path / "staging")])

    with pytest.raises(runner.BackupRunError, match="--upload"):
        runner.run(args)


def test_postgres_url_decodes_password_without_exposing_it():
    host, port, user, password, database = runner.parse_postgres_url("postgresql://app:p%40ss@db.example:5433/versus")

    assert (host, port, user, password, database) == ("db.example", "5433", "app", "p@ss", "versus")


def test_default_dotenv_is_the_runtime_app_directory():
    args = runner.parse_args(["--dry-run"])

    assert Path(args.dotenv).name == ".env"
    assert Path(args.dotenv).parent.name == "app32"
