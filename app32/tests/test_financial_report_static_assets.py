from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = ROOT / "static"


def test_financial_report_filter_static_assets_exist():
    required_assets = [
        "css/financial_report_workspace.css",
        "css/financial_report_filters_schedule.css",
        "css/financial_report_filters_bank_statement.css",
        "css/financial_income_statement.css",
        "js/financial_report_workspace.js",
        "js/financial_income_statement.js",
    ]

    missing = [asset for asset in required_assets if not (STATIC_ROOT / asset).is_file()]

    assert missing == []
