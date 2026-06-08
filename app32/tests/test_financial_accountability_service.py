import os
import sys
from io import BytesIO

from PIL import Image
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


def test_store_document_accepts_custom_storage_scope(tmp_path, monkeypatch):
    monkeypatch.setattr(
        accountability_module.FinancialService,
        "_ensure_company_scope",
        lambda company_id, allowed_company_ids=None: None,
    )

    storage = FileStorage(
        stream=BytesIO(b"descricao,valor\nServico,99.90\n"),
        filename="automacao.csv",
        content_type="text/csv",
    )

    result, error = FinancialAccountabilityService.store_document(
        company_id=9,
        file_storage=storage,
        upload_root=tmp_path,
        allowed_company_ids=[9],
        storage_scope="automation",
    )

    assert error is None
    assert result is not None
    assert result["stored_relative_path"].startswith("financial/automation/9/")
    assert result["public_url"].startswith("/uploads/financial/automation/9/")


def test_store_document_classifies_nfe_xml_and_generates_group_key(tmp_path, monkeypatch):
    monkeypatch.setattr(
        accountability_module.FinancialService,
        "_ensure_company_scope",
        lambda company_id, allowed_company_ids=None: None,
    )

    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe Id="NFe35260412345678000199550010000012341000012345">
      <ide>
        <mod>55</mod>
        <serie>1</serie>
        <nNF>1234</nNF>
        <dhEmi>2026-04-17T10:00:00-03:00</dhEmi>
        <natOp>Venda de serviços</natOp>
      </ide>
      <emit>
        <CNPJ>12345678000199</CNPJ>
        <xNome>Empresa Emitente LTDA</xNome>
      </emit>
      <dest>
        <CNPJ>99887766000155</CNPJ>
        <xNome>Cliente Teste SA</xNome>
      </dest>
      <total>
        <ICMSTot>
          <vNF>1500.00</vNF>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
</nfeProc>
""".encode("utf-8")
    storage = FileStorage(
        stream=BytesIO(xml_payload),
        filename="nfe_1234.xml",
        content_type="application/xml",
    )

    result, error = FinancialAccountabilityService.store_document(
        company_id=9,
        file_storage=storage,
        upload_root=tmp_path,
        allowed_company_ids=[9],
        storage_scope="automation",
    )

    assert error is None
    assert result is not None
    assert result["document_type"] == "nfe_xml"
    assert result["document_family"] == "fiscal"
    assert result["document_group_key"].startswith("key:")
    assert result["structured_payload_json"]["document_number"] == "1234"
    assert result["structured_payload_json"]["issuer_name"] == "Empresa Emitente LTDA"


def test_store_document_mirrors_generated_assets_to_gcs_when_configured(tmp_path, monkeypatch):
    monkeypatch.setattr(
        accountability_module.FinancialService,
        "_ensure_company_scope",
        lambda company_id, allowed_company_ids=None: None,
    )
    monkeypatch.setattr(accountability_module, "get_gcs_config", lambda: "bucket-test")

    uploaded_assets = []

    def _fake_upload_to_gcs(handle, final_name, subfolder=""):
        uploaded_assets.append((subfolder, final_name, handle.read()))
        handle.seek(0)
        return f"{subfolder}/{final_name}" if subfolder else final_name

    monkeypatch.setattr(accountability_module, "upload_to_gcs", _fake_upload_to_gcs)

    image = Image.new("RGB", (64, 64), color="red")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    storage = FileStorage(
        stream=buffer,
        filename="comprovante.png",
        content_type="image/png",
    )

    result, error = FinancialAccountabilityService.store_document(
        company_id=10,
        file_storage=storage,
        upload_root=tmp_path,
        allowed_company_ids=[10],
        storage_scope="automation",
    )

    assert error is None
    assert result is not None
    uploaded_paths = {f"{subfolder}/{final_name}" if subfolder else final_name for subfolder, final_name, _ in uploaded_assets}
    assert result["original_relative_path"] in uploaded_paths
    assert result["optimized_relative_path"] in uploaded_paths
    assert result["preview_relative_path"] in uploaded_paths
