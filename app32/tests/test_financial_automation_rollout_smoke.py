import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.financial_automation_service import FinancialAutomationService


ROOT = Path(__file__).resolve().parents[1]


def test_financial_automation_rollout_registers_all_api_endpoints():
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")

    required_endpoints = [
        "/api/financial/automation/options",
        "/api/financial/automation/batches",
        "/api/financial/automation/uploads",
        "/api/financial/automation/batches/<int:batch_id>/parse",
        "/api/financial/automation/records",
        "/api/financial/automation/records/<int:record_id>",
        "/api/financial/automation/records/bulk-status",
        "/api/financial/automation/generate",
    ]

    for endpoint in required_endpoints:
        assert endpoint in app_source


def test_financial_automation_rollout_frontend_has_upload_parse_generate_smoke_flow():
    html = (ROOT / "templates/modules/financial/automation_center.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/financial_automation_center.js").read_text(encoding="utf-8")

    assert "Central de Automação Financeira" in html
    assert 'id="fa-import-files"' in html
    assert 'id="fa-submit-import"' in html
    assert 'id="fa-generate"' in html
    assert "<th>Lote</th>" in html
    assert "<th>Documento</th>" not in html
    assert 'id="filter-batch"' in html
    assert "/api/financial/automation/uploads" in script
    assert "/parse?company_id=" in script
    assert "/api/financial/automation/generate" in script
    assert "batch_options" in script
    assert "batch_id" in script
    assert "batch.source_label ? ` ·" not in script
    assert "Upload concluído" in script


def test_financial_automation_rollout_service_contracts_exist():
    required_methods = [
        "upload_batch_files",
        "parse_batch_documents",
        "ingest_accountability_documents",
        "bulk_update_status",
        "delete_record",
        "generate_records",
    ]

    for method_name in required_methods:
        assert callable(getattr(FinancialAutomationService, method_name))

    result, error = FinancialAutomationService.ingest_accountability_documents(
        company_id=9,
        files=[],
        upload_root="C:/tmp/uploads",
        allowed_company_ids=[9],
    )
    assert result is None
    assert "arquivo" in error.lower()
