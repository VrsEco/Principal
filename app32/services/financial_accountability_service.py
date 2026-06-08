from __future__ import annotations

import csv
import hashlib
import io
import logging
import mimetypes
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

from PIL import Image, ImageOps
from pypdf import PdfReader
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from services.financial_import_service import FinancialImportService
from services.financial_service import FinancialService
from utils.gcs_utils import get_gcs_config, upload_to_gcs


logger = logging.getLogger(__name__)


_ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".doc",
    ".docx",
    ".xlsx",
    ".xls",
    ".csv",
    ".txt",
    ".xml",
}

_TEXT_EXTENSIONS = {".txt", ".csv", ".xml"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
_SPREADSHEET_EXTENSIONS = {".xlsx", ".xls", ".csv"}
_XML_EXTENSIONS = {".xml"}
_FISCAL_DOCUMENT_TYPES = {"nfe_xml", "nfce_xml", "cte_xml", "danfe_pdf", "dacte_pdf"}
_PARSER_VERSION = "v2"


@dataclass(frozen=True)
class AccountabilityUploadResult:
    file_name: str
    stored_relative_path: str
    original_relative_path: str
    optimized_relative_path: Optional[str]
    preview_relative_path: Optional[str]
    public_url: str
    original_public_url: str
    optimized_public_url: Optional[str]
    preview_public_url: Optional[str]
    mime_type: Optional[str]
    file_size: int
    file_size_original: int
    file_size_optimized: Optional[int]
    sha256: str
    extracted_text: str
    extracted_preview: str
    extraction_method: str
    extension: str
    document_family: str
    document_type: str
    source_kind: str
    parser_status: str
    parser_version: str
    document_group_key: Optional[str]
    confidence_score: float
    structured_payload_json: Dict[str, Any]
    preview_payload_json: Dict[str, Any]
    metadata_json: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "stored_relative_path": self.stored_relative_path,
            "original_relative_path": self.original_relative_path,
            "optimized_relative_path": self.optimized_relative_path,
            "preview_relative_path": self.preview_relative_path,
            "public_url": self.public_url,
            "original_public_url": self.original_public_url,
            "optimized_public_url": self.optimized_public_url,
            "preview_public_url": self.preview_public_url,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "file_size_original": self.file_size_original,
            "file_size_optimized": self.file_size_optimized,
            "sha256": self.sha256,
            "extracted_text": self.extracted_text,
            "extracted_preview": self.extracted_preview,
            "extraction_method": self.extraction_method,
            "extension": self.extension,
            "document_family": self.document_family,
            "document_type": self.document_type,
            "source_kind": self.source_kind,
            "parser_status": self.parser_status,
            "parser_version": self.parser_version,
            "document_group_key": self.document_group_key,
            "confidence_score": self.confidence_score,
            "structured_payload_json": self.structured_payload_json,
            "preview_payload_json": self.preview_payload_json,
            "metadata_json": self.metadata_json,
        }


class FinancialAccountabilityService:
    @staticmethod
    def store_document(
        *,
        company_id: int,
        file_storage: FileStorage | None,
        upload_root: str | Path,
        allowed_company_ids: Optional[Sequence[int]] = None,
        storage_scope: str = "accountability",
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        if file_storage is None:
            return None, "Arquivo não enviado."

        original_name = str(file_storage.filename or "").strip()
        if not original_name:
            return None, "Nome do arquivo inválido."

        safe_name = secure_filename(original_name)
        extension = Path(safe_name).suffix.lower()
        if not extension or extension not in _ALLOWED_EXTENSIONS:
            return None, "Extensão de arquivo não permitida para prestação de contas."

        file_bytes = file_storage.read() or b""
        if not file_bytes:
            return None, "Arquivo enviado está vazio."

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        safe_scope = str(storage_scope or "accountability").strip().lower().replace("\\", "/").replace("..", "")
        safe_scope = safe_scope.replace("/", "_") or "accountability"
        base_dir = Path(upload_root) / "financial" / safe_scope / str(company_id)
        original_dir = base_dir / "original"
        derived_dir = base_dir / "derived"
        original_dir.mkdir(parents=True, exist_ok=True)
        derived_dir.mkdir(parents=True, exist_ok=True)

        target_stem = f"{timestamp}_{file_hash[:12]}_{Path(safe_name).stem}"
        original_name_with_hash = f"{target_stem}{extension}"
        original_path = original_dir / original_name_with_hash
        original_path.write_bytes(file_bytes)

        extracted_text, extraction_method = FinancialAccountabilityService._extract_text(
            file_name=safe_name,
            file_bytes=file_bytes,
        )
        document_info = FinancialAccountabilityService._detect_document_profile(
            file_name=safe_name,
            file_bytes=file_bytes,
            extracted_text=extracted_text,
            extension=extension,
        )
        optimized = FinancialAccountabilityService._build_optimized_assets(
            file_name=safe_name,
            extension=extension,
            file_bytes=file_bytes,
            derived_dir=derived_dir,
            target_stem=target_stem,
        )

        mime_type = file_storage.mimetype or mimetypes.guess_type(safe_name)[0]
        original_relative_path = original_path.relative_to(Path(upload_root)).as_posix()
        optimized_relative_path = optimized["optimized_relative_path"]
        preview_relative_path = optimized["preview_relative_path"]
        FinancialAccountabilityService._mirror_generated_assets_to_gcs(
            upload_root=upload_root,
            relative_paths=[
                original_relative_path,
                optimized_relative_path,
                preview_relative_path,
            ],
        )
        preview_payload = {
            "public_url": f"/uploads/{original_relative_path}",
            "original_public_url": f"/uploads/{original_relative_path}",
            "optimized_public_url": f"/uploads/{optimized_relative_path}" if optimized_relative_path else None,
            "preview_public_url": f"/uploads/{preview_relative_path}" if preview_relative_path else None,
            "extracted_preview": extracted_text[:1000],
            "extraction_method": extraction_method,
            "extension": extension,
            "document_type": document_info["document_type"],
            "document_family": document_info["document_family"],
            "parser_status": document_info["parser_status"],
            "parser_version": _PARSER_VERSION,
        }

        result = AccountabilityUploadResult(
            file_name=safe_name,
            stored_relative_path=original_relative_path,
            original_relative_path=original_relative_path,
            optimized_relative_path=optimized_relative_path,
            preview_relative_path=preview_relative_path,
            public_url=f"/uploads/{original_relative_path}",
            original_public_url=f"/uploads/{original_relative_path}",
            optimized_public_url=f"/uploads/{optimized_relative_path}" if optimized_relative_path else None,
            preview_public_url=f"/uploads/{preview_relative_path}" if preview_relative_path else None,
            mime_type=mime_type,
            file_size=len(file_bytes),
            file_size_original=len(file_bytes),
            file_size_optimized=optimized["file_size_optimized"],
            sha256=file_hash,
            extracted_text=extracted_text,
            extracted_preview=extracted_text[:1000],
            extraction_method=extraction_method,
            extension=extension,
            document_family=document_info["document_family"],
            document_type=document_info["document_type"],
            source_kind=document_info["source_kind"],
            parser_status=document_info["parser_status"],
            parser_version=_PARSER_VERSION,
            document_group_key=document_info["document_group_key"],
            confidence_score=document_info["confidence_score"],
            structured_payload_json=document_info["structured_payload_json"],
            preview_payload_json=preview_payload,
            metadata_json={
                "storage_scope": safe_scope,
                "classification_reason": document_info["classification_reason"],
                "extraction_method": extraction_method,
            },
        )
        return result.to_dict(), None

    @staticmethod
    def upload_document(
        *,
        company_id: int,
        file_storage: FileStorage | None,
        upload_root: str | Path,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        return FinancialAccountabilityService.store_document(
            company_id=company_id,
            file_storage=file_storage,
            upload_root=upload_root,
            allowed_company_ids=allowed_company_ids,
            storage_scope="accountability",
        )

    @staticmethod
    def _extract_text(*, file_name: str, file_bytes: bytes) -> Tuple[str, str]:
        extension = Path(file_name).suffix.lower()

        if extension == ".pdf":
            try:
                reader = PdfReader(io.BytesIO(file_bytes))
                text_parts = []
                for page in reader.pages:
                    page_text = (page.extract_text() or "").strip()
                    if page_text:
                        text_parts.append(page_text)
                return ("\n\n".join(text_parts)).strip(), "pdf_text"
            except Exception:
                return "", "pdf_unreadable"

        if extension in _TEXT_EXTENSIONS:
            text = FinancialAccountabilityService._decode_bytes(file_bytes)
            if extension == ".csv" and text:
                return FinancialAccountabilityService._normalize_csv_text(text), "csv_text"
            if extension == ".xml" and text:
                return text, "xml_text"
            return text, "plain_text"

        if extension in _IMAGE_EXTENSIONS:
            return "", "image_pending_ocr"

        return "", "binary_pending_parser"

    @staticmethod
    def _decode_bytes(file_bytes: bytes) -> str:
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return file_bytes.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        return ""

    @staticmethod
    def _normalize_csv_text(text: str) -> str:
        rows = []
        try:
            reader = csv.reader(io.StringIO(text))
            for index, row in enumerate(reader):
                if index >= 20:
                    break
                cleaned = " | ".join((cell or "").strip() for cell in row if str(cell or "").strip())
                if cleaned:
                    rows.append(cleaned)
        except Exception:
            return text.strip()
        return "\n".join(rows).strip()

    @staticmethod
    def _build_optimized_assets(
        *,
        file_name: str,
        extension: str,
        file_bytes: bytes,
        derived_dir: Path,
        target_stem: str,
    ) -> Dict[str, Any]:
        optimized_relative_path = None
        preview_relative_path = None
        file_size_optimized = None

        if extension in _IMAGE_EXTENSIONS:
            try:
                image = Image.open(io.BytesIO(file_bytes))
                image = ImageOps.exif_transpose(image)
                image.thumbnail((1800, 1800))
                optimized_path = derived_dir / f"{target_stem}_optimized.webp"
                image.save(optimized_path, format="WEBP", quality=82, method=6)
                preview_path = derived_dir / f"{target_stem}_preview.webp"
                preview = image.copy()
                preview.thumbnail((480, 480))
                preview.save(preview_path, format="WEBP", quality=70, method=6)
                optimized_relative_path = optimized_path.relative_to(derived_dir.parents[3]).as_posix()
                preview_relative_path = preview_path.relative_to(derived_dir.parents[3]).as_posix()
                file_size_optimized = optimized_path.stat().st_size
            except Exception:
                optimized_relative_path = None
                preview_relative_path = None
                file_size_optimized = None

        elif extension == ".pdf":
            try:
                import fitz

                pdf = fitz.open(stream=file_bytes, filetype="pdf")
                if pdf.page_count:
                    page = pdf.load_page(0)
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.3, 1.3), alpha=False)
                    preview_path = derived_dir / f"{target_stem}_preview.webp"
                    preview_path.write_bytes(pix.tobytes("webp"))
                    preview_relative_path = preview_path.relative_to(derived_dir.parents[3]).as_posix()
                pdf.close()
            except Exception:
                preview_relative_path = None

        return {
            "optimized_relative_path": optimized_relative_path,
            "preview_relative_path": preview_relative_path,
            "file_size_optimized": file_size_optimized,
        }

    @staticmethod
    def _mirror_generated_assets_to_gcs(
        *,
        upload_root: str | Path,
        relative_paths: Sequence[Optional[str]],
    ) -> None:
        if not get_gcs_config():
            return

        root_path = Path(upload_root)
        for relative_path in relative_paths:
            if not relative_path:
                continue

            absolute_path = root_path / relative_path
            if not absolute_path.exists():
                logger.warning(
                    "Asset gerado para upload GCS não encontrado localmente: %s",
                    absolute_path,
                )
                continue

            path_obj = Path(relative_path)
            subfolder = path_obj.parent.as_posix() if path_obj.parent.as_posix() != "." else ""
            try:
                with absolute_path.open("rb") as handle:
                    uploaded_path = upload_to_gcs(handle, path_obj.name, subfolder=subfolder)
                if not uploaded_path:
                    logger.warning("Falha ao espelhar asset no GCS: %s", relative_path)
            except Exception as exc:
                logger.warning("Erro ao espelhar asset no GCS (%s): %s", relative_path, exc)

    @staticmethod
    def _detect_document_profile(
        *,
        file_name: str,
        file_bytes: bytes,
        extracted_text: str,
        extension: str,
    ) -> Dict[str, Any]:
        source_kind = FinancialAccountabilityService._infer_source_kind(extension)
        structured_payload: Dict[str, Any] = {}
        document_family = "generic"
        document_type = "unknown_document"
        parser_status = "needs_review"
        classification_reason = "fallback"
        confidence_score = 0.35

        if extension in _XML_EXTENSIONS:
            structured_payload = FinancialAccountabilityService._parse_fiscal_xml(file_bytes)
            document_type = structured_payload.get("document_type") or "unknown_document"
            document_family = "fiscal" if document_type in {"nfe_xml", "nfce_xml", "cte_xml"} else "generic"
            parser_status = "parsed" if structured_payload else "failed"
            classification_reason = "xml_signature"
            confidence_score = 0.98 if document_family == "fiscal" else 0.40
        elif extension in _SPREADSHEET_EXTENSIONS:
            document_type = "spreadsheet"
            parser_status = "parsed"
            classification_reason = "tabular_source"
            confidence_score = 0.85
        elif extension == ".pdf":
            structured_payload = FinancialAccountabilityService._parse_document_text_payload(
                file_name=file_name,
                extracted_text=extracted_text,
            )
            document_type = structured_payload.get("document_type") or "unknown_document"
            document_family = FinancialAccountabilityService._infer_document_family(document_type)
            parser_status = "parsed" if extracted_text else "needs_review"
            classification_reason = "pdf_text_detection"
            confidence_score = 0.84 if document_type in {"danfe_pdf", "dacte_pdf"} else 0.58 if document_type == "receipt_pdf" else 0.35
        elif extension in _IMAGE_EXTENSIONS:
            structured_payload = FinancialAccountabilityService._parse_document_text_payload(
                file_name=file_name,
                extracted_text=extracted_text,
            )
            if "recibo" in file_name.lower() or "receipt" in file_name.lower():
                document_type = "receipt_image"
            document_family = FinancialAccountabilityService._infer_document_family(document_type)
            parser_status = "needs_review"
            classification_reason = "image_filename_detection"
            confidence_score = 0.32
        elif extension == ".txt":
            structured_payload = FinancialAccountabilityService._parse_document_text_payload(
                file_name=file_name,
                extracted_text=extracted_text,
            )
            document_type = structured_payload.get("document_type") or "unknown_document"
            document_family = FinancialAccountabilityService._infer_document_family(document_type)
            parser_status = "parsed" if extracted_text else "needs_review"
            classification_reason = "text_detection"
            confidence_score = 0.40
        elif extension == ".ofx":
            document_type = "ofx"
            document_family = "bank"
            parser_status = "parsed"
            classification_reason = "ofx_extension"
            confidence_score = 0.95

        document_group_key = FinancialAccountabilityService._build_document_group_key(
            document_type=document_type,
            structured_payload=structured_payload,
            file_bytes=file_bytes,
        )

        return {
            "document_family": document_family,
            "document_type": document_type,
            "source_kind": source_kind,
            "parser_status": parser_status,
            "classification_reason": classification_reason,
            "confidence_score": confidence_score,
            "document_group_key": document_group_key,
            "structured_payload_json": structured_payload,
        }

    @staticmethod
    def _infer_source_kind(extension: str) -> str:
        if extension in _XML_EXTENSIONS:
            return "xml"
        if extension == ".pdf":
            return "pdf"
        if extension in _IMAGE_EXTENSIONS:
            return "image"
        if extension in _SPREADSHEET_EXTENSIONS:
            return "spreadsheet"
        if extension == ".ofx":
            return "ofx"
        if extension in _TEXT_EXTENSIONS:
            return "text"
        return "binary"

    @staticmethod
    def _infer_document_family(document_type: str) -> str:
        if document_type in _FISCAL_DOCUMENT_TYPES:
            return "fiscal"
        if document_type in {"receipt_pdf", "receipt_image"}:
            return "receipt"
        if document_type == "ofx":
            return "bank"
        return "generic"

    @staticmethod
    def _strip_namespaces(root: ET.Element) -> ET.Element:
        for element in root.iter():
            if "}" in element.tag:
                element.tag = element.tag.split("}", 1)[1]
        return root

    @staticmethod
    def _find_text(root: ET.Element, path: str) -> Optional[str]:
        node = root.find(path)
        if node is None or node.text is None:
            return None
        value = node.text.strip()
        return value or None

    @staticmethod
    def _only_digits(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        digits = re.sub(r"\D+", "", str(value))
        return digits or None

    @staticmethod
    def _parse_fiscal_xml(file_bytes: bytes) -> Dict[str, Any]:
        try:
            root = ET.fromstring(file_bytes)
            root = FinancialAccountabilityService._strip_namespaces(root)
        except Exception:
            return {}

        if root.tag == "procNFe":
            root = root.find("NFe") or root
        elif root.tag == "nfeProc":
            root = root.find("NFe") or root
        elif root.tag == "cteProc":
            root = root.find("CTe") or root

        document_type = "unknown_document"
        access_key = None
        number = None
        series = None
        issuer_name = None
        issuer_document = None
        recipient_name = None
        recipient_document = None
        issue_date = None
        total_amount = None
        operation_nature = None

        if root.find("infNFe") is not None:
            inf = root.find("infNFe")
            ide = inf.find("ide") if inf is not None else None
            emit = inf.find("emit") if inf is not None else None
            dest = inf.find("dest") if inf is not None else None
            total = inf.find("total/ICMSTot") if inf is not None else None
            document_type = "nfce_xml" if FinancialAccountabilityService._find_text(ide, "mod") == "65" else "nfe_xml"
            access_key = FinancialAccountabilityService._only_digits((inf.attrib or {}).get("Id"))
            number = FinancialAccountabilityService._find_text(ide, "nNF")
            series = FinancialAccountabilityService._find_text(ide, "serie")
            operation_nature = FinancialAccountabilityService._find_text(ide, "natOp")
            issuer_name = FinancialAccountabilityService._find_text(emit, "xNome")
            issuer_document = FinancialAccountabilityService._only_digits(
                FinancialAccountabilityService._find_text(emit, "CNPJ") or FinancialAccountabilityService._find_text(emit, "CPF")
            )
            recipient_name = FinancialAccountabilityService._find_text(dest, "xNome")
            recipient_document = FinancialAccountabilityService._only_digits(
                FinancialAccountabilityService._find_text(dest, "CNPJ") or FinancialAccountabilityService._find_text(dest, "CPF")
            )
            issue_date = FinancialAccountabilityService._normalize_xml_date(
                FinancialAccountabilityService._find_text(ide, "dhEmi") or FinancialAccountabilityService._find_text(ide, "dEmi")
            )
            total_amount = FinancialAccountabilityService._parse_decimal_safe(
                FinancialAccountabilityService._find_text(total, "vNF")
            )
        elif root.find("infCte") is not None:
            inf = root.find("infCte")
            ide = inf.find("ide") if inf is not None else None
            emit = inf.find("emit") if inf is not None else None
            rem = inf.find("rem") if inf is not None else None
            vprest = inf.find("vPrest") if inf is not None else None
            document_type = "cte_xml"
            access_key = FinancialAccountabilityService._only_digits((inf.attrib or {}).get("Id"))
            number = FinancialAccountabilityService._find_text(ide, "nCT")
            series = FinancialAccountabilityService._find_text(ide, "serie")
            operation_nature = FinancialAccountabilityService._find_text(ide, "natOp")
            issuer_name = FinancialAccountabilityService._find_text(emit, "xNome")
            issuer_document = FinancialAccountabilityService._only_digits(
                FinancialAccountabilityService._find_text(emit, "CNPJ") or FinancialAccountabilityService._find_text(emit, "CPF")
            )
            recipient_name = FinancialAccountabilityService._find_text(rem, "xNome")
            recipient_document = FinancialAccountabilityService._only_digits(
                FinancialAccountabilityService._find_text(rem, "CNPJ") or FinancialAccountabilityService._find_text(rem, "CPF")
            )
            issue_date = FinancialAccountabilityService._normalize_xml_date(
                FinancialAccountabilityService._find_text(ide, "dhEmi")
            )
            total_amount = FinancialAccountabilityService._parse_decimal_safe(
                FinancialAccountabilityService._find_text(vprest, "vTPrest")
            )

        payload = {
            "document_type": document_type,
            "document_key": access_key,
            "document_number": number,
            "document_series": series,
            "issuer_name": issuer_name,
            "issuer_document": issuer_document,
            "recipient_name": recipient_name,
            "recipient_document": recipient_document,
            "issue_date": issue_date,
            "total_amount": float(total_amount) if total_amount is not None else None,
            "operation_nature": operation_nature,
        }
        payload["summary"] = " | ".join(
            part
            for part in [
                document_type,
                f"Nº {number}" if number else None,
                issuer_name,
                f"R$ {payload['total_amount']:.2f}" if payload["total_amount"] is not None else None,
            ]
            if part
        )
        return payload

    @staticmethod
    def _normalize_xml_date(raw_value: Optional[str]) -> Optional[str]:
        text = str(raw_value or "").strip()
        if not text:
            return None
        text = text[:10]
        if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
            return text
        return None

    @staticmethod
    def _parse_decimal_safe(value: Optional[str]) -> Optional[Decimal]:
        parsed = FinancialImportService._parse_decimal(value)
        if parsed is None:
            return None
        return parsed.copy_abs()

    @staticmethod
    def _parse_document_text_payload(*, file_name: str, extracted_text: str) -> Dict[str, Any]:
        text = str(extracted_text or "")
        lowered = text.lower()
        file_lower = str(file_name or "").lower()
        document_type = "unknown_document"
        if "danfe" in lowered or "danfe" in file_lower or "nf-e" in lowered:
            document_type = "danfe_pdf"
        elif "dacte" in lowered or "cte" in lowered:
            document_type = "dacte_pdf"
        elif "recibo" in lowered or "receipt" in file_lower:
            document_type = "receipt_pdf"

        key_match = re.search(r"(\d[\s.]*){44}", text)
        document_key = re.sub(r"\D+", "", key_match.group(0)) if key_match else None
        amount = FinancialImportService._parse_decimal(
            next(
                (
                    match.group(1)
                    for match in re.finditer(r"(?:valor\s*(?:total)?[:\s]*|r\$\s*)(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2})", text, re.IGNORECASE)
                ),
                None,
            )
        )
        if amount is None:
            amount = FinancialImportService._parse_decimal(
                next(
                    (
                        match.group(1)
                        for match in re.finditer(r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2})", text)
                    ),
                    None,
                )
            )
        date_match = re.search(r"\b(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\b", text)
        number_match = re.search(r"(?:n[oº°]*\s*documento|n[oº°]*|nf-e|cte)\s*[:#]?\s*([0-9]{1,20})", text, re.IGNORECASE)
        series_match = re.search(r"s[ée]rie\s*[:#]?\s*([0-9A-Za-z\-]+)", text, re.IGNORECASE)

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        issuer_name = lines[0][:255] if lines else None
        return {
            "document_type": document_type,
            "document_key": document_key,
            "document_number": number_match.group(1) if number_match else None,
            "document_series": series_match.group(1) if series_match else None,
            "issuer_name": issuer_name,
            "issuer_document": FinancialAccountabilityService._extract_cpf_cnpj(text),
            "recipient_name": None,
            "recipient_document": None,
            "issue_date": FinancialAccountabilityService._normalize_date_string(date_match.group(1)) if date_match else None,
            "total_amount": float(amount) if amount is not None else None,
            "operation_nature": None,
            "summary": lines[0][:255] if lines else None,
        }

    @staticmethod
    def _extract_cpf_cnpj(text: str) -> Optional[str]:
        match = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b|\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", text)
        if not match:
            return None
        return FinancialAccountabilityService._only_digits(match.group(0))

    @staticmethod
    def _normalize_date_string(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        raw = str(value).strip()
        parsed = FinancialImportService._parse_date(raw)
        return parsed.isoformat() if parsed else None

    @staticmethod
    def _build_document_group_key(
        *,
        document_type: str,
        structured_payload: Dict[str, Any],
        file_bytes: bytes,
    ) -> Optional[str]:
        document_key = structured_payload.get("document_key")
        if document_key:
            return f"key:{document_key}"
        parts = [
            document_type or "unknown",
            structured_payload.get("issuer_document") or "",
            structured_payload.get("recipient_document") or "",
            structured_payload.get("document_number") or "",
            structured_payload.get("document_series") or "",
            structured_payload.get("issue_date") or "",
            str(structured_payload.get("total_amount") or ""),
        ]
        raw = "|".join(parts).strip("|")
        if raw:
            return f"fp:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]}"
        return f"sha:{hashlib.sha256(file_bytes).hexdigest()[:32]}"
