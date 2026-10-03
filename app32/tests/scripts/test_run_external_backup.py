import importlib.util
import json
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


def test_upload_inventory_is_relative_hashed_and_ignores_symlinks(tmp_path):
    upload_root = tmp_path / "uploads"
    (upload_root / "financial").mkdir(parents=True)
    source = upload_root / "financial" / "receipt.pdf"
    source.write_bytes(b"customer document")
    inventory_path = tmp_path / "uploads.inventory.json"

    files, total_bytes = runner.create_upload_inventory(upload_root, inventory_path)

    assert total_bytes == len(b"customer document")
    assert files == [{
        "relative_path": "financial/receipt.pdf",
        "sha256": runner.sha256_file(source),
        "size": len(b"customer document"),
    }]
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert payload["files_count"] == 1
    assert payload["total_bytes"] == total_bytes


def test_upload_inventory_rejects_missing_root(tmp_path):
    with pytest.raises(runner.BackupRunError, match="Diretório de uploads"):
        runner.create_upload_inventory(tmp_path / "missing", tmp_path / "inventory.json")


def test_existing_artifacts_uses_content_addressed_object_key(tmp_path):
    artifact_file = tmp_path / "asset.bin"
    artifact_file.write_bytes(b"same content")
    artifact = runner.BackupArtifact(artifact_file, runner.sha256_file(artifact_file), "uploads")

    class FakeClient:
        def find_existing_artifact(self, object_key):
            assert object_key == artifact.object_key
            return {"id": "drive-123"}

    assert runner.existing_artifacts(FakeClient(), [artifact]) == {artifact.object_key: {"id": "drive-123"}}


def test_upload_records_keep_relative_paths_in_inventory_not_drive_properties(tmp_path):
    upload_root = tmp_path / "uploads"
    nested = upload_root / ("long-directory-" * 8)
    nested.mkdir(parents=True)
    source = nested / "receipt.pdf"
    source.write_bytes(b"customer document")

    records, metadata = runner.build_upload_records(upload_root, tmp_path / "uploads.inventory.json")

    asset_record = records[0]
    assert asset_record["type"] == "uploads"
    assert "extra_properties" not in asset_record
    assert metadata["files_count"] == 1


def _alert_args(tmp_path):
    return runner.parse_args(
        ["--repo", str(tmp_path), "--staging-dir", str(tmp_path / "staging"),
         "--drive-env-file", str(tmp_path / "missing.env"), "--upload"]
    )


def test_failure_sends_alert_once_within_throttle_window(tmp_path, monkeypatch):
    sent = []
    monkeypatch.setenv("GV_BACKUP_ALERT_WEBHOOK_URL", "https://alerts.example/hook")
    monkeypatch.setattr(runner, "send_failure_alert", lambda settings, subject, body: sent.append(body) or ["webhook"])
    args = _alert_args(tmp_path)

    runner.notify_failure(args, "Nao foi possivel renovar token OAuth (HTTP 400).")
    runner.notify_failure(args, "Nao foi possivel renovar token OAuth (HTTP 400).")

    assert len(sent) == 1
    assert "renovar token OAuth" in sent[0]
    status = json.loads((tmp_path / "staging" / "last_status.json").read_text(encoding="utf-8"))
    assert status["ok"] is False


def test_alert_repeats_after_throttle_window(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    old = datetime.now(runner.TZ) - timedelta(hours=13)
    (staging / ".last-alert.json").write_text(json.dumps({"sent_at": old.isoformat()}), encoding="utf-8")

    assert runner.should_send_alert(staging, datetime.now(runner.TZ), 12) is True


def test_alert_failure_never_masks_original_error(tmp_path, monkeypatch):
    def boom(*_args):
        raise OSError("smtp indisponivel")

    monkeypatch.setattr(runner, "send_failure_alert", boom)
    monkeypatch.setenv("GV_BACKUP_ALERT_WEBHOOK_URL", "https://alerts.example/hook")

    runner.notify_failure(_alert_args(tmp_path), "erro original")  # nao deve levantar


def test_main_alerts_on_drive_error_and_returns_nonzero(tmp_path, monkeypatch):
    calls = []
    args = _alert_args(tmp_path)
    monkeypatch.setattr(runner, "parse_args", lambda: args)

    def failing_run(_args):
        raise sys.modules["google_drive_backup"].BackupDriveError("token expirado")

    monkeypatch.setattr(runner, "run", failing_run)
    monkeypatch.setattr(runner, "notify_failure", lambda args, error: calls.append(error))

    assert runner.main() == 2
    assert calls == ["token expirado"]


def test_main_records_success_status(tmp_path, monkeypatch):
    args = _alert_args(tmp_path)
    monkeypatch.setattr(runner, "parse_args", lambda: args)
    monkeypatch.setattr(runner, "run", lambda _args: {"ok": True, "mode": "upload"})

    assert runner.main() == 0
    status = json.loads((tmp_path / "staging" / "last_status.json").read_text(encoding="utf-8"))
    assert status["ok"] is True and status["last_success_at"]


def test_no_alert_without_upload_flag(tmp_path, monkeypatch):
    calls = []
    args = runner.parse_args(["--repo", str(tmp_path), "--staging-dir", str(tmp_path / "staging")])
    monkeypatch.setattr(runner, "parse_args", lambda: args)
    monkeypatch.setattr(runner, "notify_failure", lambda *_: calls.append(1))

    assert runner.main() == 2
    assert calls == []
