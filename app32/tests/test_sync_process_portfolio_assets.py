from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.sync_process_portfolio_assets import sync_process_portfolio_assets


def test_sync_process_portfolio_assets_copies_missing_files(monkeypatch, tmp_path):
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    (source_dir / "dashboard.jpg").write_bytes(b"dashboard")
    (source_dir / "planning.jpg").write_bytes(b"planning")

    monkeypatch.setattr("scripts.sync_process_portfolio_assets._source_dir", lambda: source_dir)
    monkeypatch.setattr("scripts.sync_process_portfolio_assets._target_dir", lambda: target_dir)
    monkeypatch.setattr(
        "scripts.sync_process_portfolio_assets.ASSET_FILENAMES",
        ("dashboard.jpg", "planning.jpg"),
    )

    result = sync_process_portfolio_assets()

    assert result["copied"] == ["dashboard.jpg", "planning.jpg"]
    assert result["missing_sources"] == []
    assert (target_dir / "dashboard.jpg").read_bytes() == b"dashboard"
    assert (target_dir / "planning.jpg").read_bytes() == b"planning"


def test_sync_process_portfolio_assets_skips_identical_files(monkeypatch, tmp_path):
    source_dir = tmp_path / "source"
    target_dir = tmp_path / "target"
    source_dir.mkdir()
    target_dir.mkdir()
    (source_dir / "team.jpg").write_bytes(b"same")
    (target_dir / "team.jpg").write_bytes(b"same")

    monkeypatch.setattr("scripts.sync_process_portfolio_assets._source_dir", lambda: source_dir)
    monkeypatch.setattr("scripts.sync_process_portfolio_assets._target_dir", lambda: target_dir)
    monkeypatch.setattr("scripts.sync_process_portfolio_assets.ASSET_FILENAMES", ("team.jpg",))

    result = sync_process_portfolio_assets()

    assert result["copied"] == []
    assert result["skipped"] == ["team.jpg"]
    assert result["missing_sources"] == []
