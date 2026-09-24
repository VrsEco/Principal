from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.sync_process_portfolio_assets import (
    ASSET_FILENAMES,
    PORTFOLIO_NAME,
    _source_dir,
    _target_dir,
    sync_process_portfolio_assets,
)


def test_canonical_portfolio_assets_use_versioned_root_static():
    repo_root = Path(__file__).resolve().parents[2]
    source_dir = repo_root / "static" / "assets" / "process_portfolios" / PORTFOLIO_NAME

    assert _source_dir() == source_dir
    assert len(ASSET_FILENAMES) == 8
    assert set(ASSET_FILENAMES) == {
        "dashboard.jpg", "documents.jpg", "onboarding.jpg", "planning.jpg",
        "screening.jpg", "signature.jpg", "team.jpg", "workstation.jpg",
    }
    assert [name for name in ASSET_FILENAMES if not (source_dir / name).is_file()] == []
    assert _target_dir() == repo_root / "app32" / "uploads" / "pop" / PORTFOLIO_NAME


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
