import os
import sys
from io import BytesIO

from werkzeug.datastructures import FileStorage

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.financial_accountability_service import FinancialAccountabilityService
import services.financial_accountability_service as accountability_module


def test_upload_document_extracts_csv_and_generates_public_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        accountability_module.FinancialService,
        "_ensure_company_scope",
        lambda company_id, allowed_company_ids=None: None,
    )

    storage = FileStorage(
        stream=BytesIO(b"documento,valor\nTaxi aeroporto,120.50\nHotel,450.00\n"),
        filename="prestacao.csv",
        content_type="text/csv",
    )

    result, error = FinancialAccountabilityService.upload_document(
        company_id=9,
        file_storage=storage,
        upload_root=tmp_path,
        allowed_company_ids=[9],
    )

    assert error is None
    assert result is not None
    assert result["file_name"] == "prestacao.csv"
    assert result["stored_relative_path"].startswith("financial/accountability/9/")
    assert result["public_url"].startswith("/uploads/financial/accountability/9/")
    assert result["file_size"] > 0
    assert result["extraction_method"] == "csv_text"
    assert "Taxi aeroporto | 120.50" in result["extracted_text"]
    assert (tmp_path / result["stored_relative_path"]).exists()


def test_upload_document_rejects_extension_outside_allowlist(tmp_path, monkeypatch):
    monkeypatch.setattr(
        accountability_module.FinancialService,
        "_ensure_company_scope",
        lambda company_id, allowed_company_ids=None: None,
    )

    storage = FileStorage(
        stream=BytesIO(b"malicioso"),
        filename="script.exe",
        content_type="application/octet-stream",
    )

    result, error = FinancialAccountabilityService.upload_document(
        company_id=9,
        file_storage=storage,
        upload_root=tmp_path,
        allowed_company_ids=[9],
    )

    assert result is None
    assert error == "Extensão de arquivo não permitida para prestação de contas."
