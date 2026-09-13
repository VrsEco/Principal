import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "google_drive_backup.py"
SPEC = importlib.util.spec_from_file_location("google_drive_backup", SCRIPT_PATH)
google_drive_backup = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = google_drive_backup
SPEC.loader.exec_module(google_drive_backup)


def test_sha256_and_dry_run_do_not_require_oauth(tmp_path):
    artifact = tmp_path / "backup.sql.gz"
    artifact.write_bytes(b"gestao-versus-backup")

    args = google_drive_backup.parse_args(
        [
            "--remote-folder",
            "database/2026/09/13",
            "--artifact-type",
            "database",
            "--source",
            str(artifact),
            "--dry-run",
        ]
    )

    result = google_drive_backup.run(args)

    assert result[0]["status"] == "validated"
    assert result[0]["name"] == "backup.sql.gz"
    assert len(result[0]["sha256"]) == 64


def test_object_key_is_stable_for_replay(tmp_path):
    artifact = tmp_path / "same-file.gz"
    artifact.write_bytes(b"same-data")
    digest = google_drive_backup.sha256_file(artifact)

    first = google_drive_backup.BackupArtifact(artifact, digest, "database")
    replay = google_drive_backup.BackupArtifact(artifact, digest, "database")

    assert first.object_key == replay.object_key
    assert first.object_key.startswith("database:")


def test_remote_query_escapes_user_controlled_value():
    assert google_drive_backup.escape_drive_query("a'b\\c") == "a\\'b\\\\c"
