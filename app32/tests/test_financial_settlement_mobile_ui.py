from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_ROOT.parent


def test_settlement_modal_keeps_body_scrollable():
    css = (APP_ROOT / "static/css/financial_schedules.css").read_text(encoding="utf-8")

    assert ".settlement-composition-form {\n  display: flex;" in css
    assert "overflow-y: auto;" in css
    assert "overscroll-behavior: contain;" in css


def test_settlement_modal_uses_single_column_and_native_controls_on_mobile():
    css = (APP_ROOT / "static/css/financial_schedules.css").read_text(encoding="utf-8")
    mobile_css = css.split("@media (max-width: 768px)", maxsplit=1)[1]

    assert ".settlement-modal-body {\n    grid-template-columns: minmax(0, 1fr);" in mobile_css
    assert "max-height: calc(100dvh - 1rem);" in mobile_css
    assert "font-size: 16px;" in mobile_css
    assert "-webkit-appearance: menulist;" in mobile_css
    assert '.settlement-panel input[type="date"]' in mobile_css
    assert "-webkit-appearance: auto;" in mobile_css


def test_financial_schedule_asset_copies_and_cache_version_are_current():
    canonical_css = (APP_ROOT / "static/css/financial_schedules.css").read_text(encoding="utf-8")
    deployment_css = (PROJECT_ROOT / "static/css/financial_schedules.css").read_text(encoding="utf-8")
    template = (APP_ROOT / "templates/modules/financial/schedules.html").read_text(encoding="utf-8")

    assert deployment_css == canonical_css
    assert "20260812-settlement-mobile" in template
