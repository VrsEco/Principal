from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_hours_decimal_formatter_is_idempotent_for_normalized_submission():
    source = (REPO_ROOT / "static/js/input_formatters.js").read_text(encoding="utf-8")

    assert "if (digits && digits.length <= 2)" in source
    assert "return Number(digits);" in source
    assert "const totalMinutesFromDigits = parseClockToMinutes(clockValue);" in source
