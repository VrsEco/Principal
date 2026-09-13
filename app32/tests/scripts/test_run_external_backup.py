import importlib.util
import sys
from datetime import datetime, timedelta
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


def test_gfs_metadata_uses_intraday_daily_and_monthly_windows():
    intraday, intraday_until = runner.retention_metadata(datetime(2026, 9, 13, 22, tzinfo=runner.TZ))
    daily, daily_until = runner.retention_metadata(datetime(2026, 9, 13, 3, tzinfo=runner.TZ))
    monthly, monthly_until = runner.retention_metadata(datetime(2026, 10, 1, 3, tzinfo=runner.TZ))

    assert (intraday, daily, monthly) == ("intraday", "daily", "monthly")
    assert intraday_until - datetime(2026, 9, 13, 22, tzinfo=runner.TZ) == timedelta(days=30)
    assert daily_until - datetime(2026, 9, 13, 3, tzinfo=runner.TZ) == timedelta(days=90)
    assert monthly_until - datetime(2026, 10, 1, 3, tzinfo=runner.TZ) == timedelta(days=180)


def test_drive_capacity_fails_closed_when_quota_is_unknown_or_insufficient():
    with pytest.raises(runner.BackupRunError, match="quota"):
        runner.assert_drive_capacity({"limit": None, "usage": 1}, 10, 5)

    with pytest.raises(runner.BackupRunError, match="Espaço insuficiente"):
        runner.assert_drive_capacity({"limit": 100, "usage": 80}, 10, 20)

    runner.assert_drive_capacity({"limit": 100, "usage": 60}, 10, 20)


def test_prune_local_staging_removes_only_expired_manifest_runs(tmp_path):
    expired = tmp_path / "expired"
    expired.mkdir()
    (expired / "manifest.json").write_text('{"retain_until":"2026-09-01T03:00:00-03:00"}', encoding="utf-8")
    retained = tmp_path / "retained"
    retained.mkdir()
    (retained / "manifest.json").write_text('{"retain_until":"2026-12-01T03:00:00-03:00"}', encoding="utf-8")
    legacy = tmp_path / "legacy"
    legacy.mkdir()

    removed = runner.prune_local_staging(tmp_path, datetime(2026, 9, 13, 3, tzinfo=runner.TZ), exclude=retained)

    assert removed == ["expired"]
    assert not expired.exists()
    assert retained.exists()
    assert legacy.exists()
