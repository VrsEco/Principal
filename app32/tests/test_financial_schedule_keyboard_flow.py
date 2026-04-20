from pathlib import Path


def test_settlement_keyboard_navigation_is_declared():
    content = Path(r"C:\GestaoVersus\app32\app32\static\js\financial_schedules.js").read_text(encoding="utf-8")
    assert "const settlementFocusSelector" in content
    assert "event.key === 'Tab'" in content
    assert "settlementLastFocus" in content
    assert "settlementLastFocus.focus()" in content


def test_settlement_modal_semantics_and_live_regions_are_present():
    content = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\schedules.html").read_text(encoding="utf-8")
    assert 'role="dialog"' in content
    assert 'aria-modal="true"' in content
    assert 'aria-labelledby="settlement-modal-title"' in content
    assert 'aria-live="polite"' in content
