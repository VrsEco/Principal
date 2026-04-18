from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def test_legacy_financial_ingestion_ui_files_are_removed():
    assert not (BASE_DIR / "templates" / "modules" / "financial" / "ingestions.html").exists()
    assert not (BASE_DIR / "templates" / "modules" / "financial" / "classification_queue.html").exists()
    assert not (BASE_DIR / "templates" / "modules" / "financial" / "classification_dashboard.html").exists()
    assert not (BASE_DIR / "templates" / "modules" / "financial" / "accountability.html").exists()
    assert not (BASE_DIR / "static" / "js" / "financial_ingestions.js").exists()
    assert not (BASE_DIR / "static" / "js" / "financial_accountability.js").exists()


def test_legacy_financial_accountability_api_is_not_registered():
    app_file = (BASE_DIR / "app.py").read_text(encoding="utf-8")
    resource_file = (BASE_DIR / "api" / "resources" / "financial.py").read_text(encoding="utf-8")

    assert "/api/financial/accountability/uploads" not in app_file
    assert "FinancialAccountabilityUploadResource" not in app_file
    assert "class FinancialAccountabilityUploadResource" not in resource_file
