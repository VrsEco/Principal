from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app32"

for path in (ROOT_DIR, APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app32.services.process_book_service import (
    _format_schedule_detail,
    _format_schedule_summary,
)


def test_format_schedule_detail_specific_date_inverts_iso():
    assert _format_schedule_detail("specific", "2026-05-27", "08:30") == "27/05/2026 às 08:30"


def test_format_schedule_summary_weekly_with_days_and_time():
    assert _format_schedule_summary("weekly", "monday,wednesday", "07:15") == "Semanal · Segunda, Quarta às 07:15"


def test_format_schedule_summary_daily_keeps_time():
    assert _format_schedule_summary("daily", None, "06:00") == "Diária · 06:00"
