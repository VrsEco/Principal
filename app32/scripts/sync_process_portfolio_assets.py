from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from flask import current_app, has_app_context


PORTFOLIO_NAME = "m1_rh_portfolio"
ASSET_FILENAMES = (
    "dashboard.jpg",
    "documents.jpg",
    "onboarding.jpg",
    "planning.jpg",
    "screening.jpg",
    "signature.jpg",
    "team.jpg",
    "workstation.jpg",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _source_dir() -> Path:
    return _repo_root() / "static" / "assets" / "process_portfolios" / PORTFOLIO_NAME


def _upload_root() -> Path:
    if has_app_context():
        return Path(current_app.config.get("UPLOAD_FOLDER", "uploads"))
    return _repo_root() / "uploads"


def _target_dir() -> Path:
    return _upload_root() / "pop" / PORTFOLIO_NAME


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sync_process_portfolio_assets() -> dict[str, object]:
    source_dir = _source_dir()
    target_dir = _target_dir()

    if not source_dir.exists():
        raise FileNotFoundError(f"Diretório de assets canônicos não encontrado: {source_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    skipped: list[str] = []
    missing_sources: list[str] = []

    for filename in ASSET_FILENAMES:
        source = source_dir / filename
        target = target_dir / filename
        if not source.exists():
            missing_sources.append(filename)
            continue
        if target.exists() and _sha256(source) == _sha256(target):
            skipped.append(filename)
            continue
        shutil.copy2(source, target)
        copied.append(filename)

    return {
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "copied": copied,
        "skipped": skipped,
        "missing_sources": missing_sources,
    }


def main() -> int:
    result = sync_process_portfolio_assets()
    print(f"SOURCE_DIR={result['source_dir']}")
    print(f"TARGET_DIR={result['target_dir']}")
    print(f"COPIED={','.join(result['copied'])}")
    print(f"SKIPPED={','.join(result['skipped'])}")
    print(f"MISSING_SOURCES={','.join(result['missing_sources'])}")
    return 0 if not result["missing_sources"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
