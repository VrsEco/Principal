import os
import sys
from pathlib import Path

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import _resolve_public_upload_folder, _sync_legacy_upload_assets


def test_resolve_public_upload_folder_anchors_relative_path_to_public_root(tmp_path):
    app_root = tmp_path / "app32"
    app_root.mkdir()
    app = Flask(__name__, root_path=str(app_root))
    app.config["UPLOAD_FOLDER"] = "uploads"

    resolved = _resolve_public_upload_folder(app)

    assert Path(resolved) == tmp_path / "uploads"


def test_resolve_public_upload_folder_preserves_absolute_config(tmp_path):
    app_root = tmp_path / "app32"
    app_root.mkdir()
    absolute_upload = tmp_path / "custom_uploads"
    app = Flask(__name__, root_path=str(app_root))
    app.config["UPLOAD_FOLDER"] = str(absolute_upload)

    resolved = _resolve_public_upload_folder(app)

    assert Path(resolved) == absolute_upload


def test_sync_legacy_upload_assets_copies_legacy_files_to_public_root(tmp_path):
    app_root = tmp_path / "app32"
    legacy_uploads = app_root / "uploads" / "financial" / "automation" / "10" / "derived"
    public_uploads = tmp_path / "uploads"
    legacy_uploads.mkdir(parents=True)
    legacy_file = legacy_uploads / "preview.webp"
    legacy_file.write_bytes(b"preview-bytes")

    app = Flask(__name__, root_path=str(app_root))

    _sync_legacy_upload_assets(app, str(public_uploads))

    migrated = public_uploads / "financial" / "automation" / "10" / "derived" / "preview.webp"
    assert migrated.exists()
    assert migrated.read_bytes() == b"preview-bytes"
