from __future__ import annotations

import csv
import hashlib
import io
import mimetypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, Sequence, Tuple

from pypdf import PdfReader
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from services.financial_service import FinancialService


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
}

_TEXT_EXTENSIONS = {".txt", ".csv"}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class AccountabilityUploadResult:
    file_name: str
    stored_relative_path: str
    public_url: str
    mime_type: Optional[str]
    file_size: int
    sha256: str
    extracted_text: str
    extracted_preview: str
    extraction_method: str
    extension: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_name": self.file_name,
            "stored_relative_path": self.stored_relative_path,
            "public_url": self.public_url,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "sha256": self.sha256,
            "extracted_text": self.extracted_text,
            "extracted_preview": self.extracted_preview,
            "extraction_method": self.extraction_method,
            "extension": self.extension,
        }


class FinancialAccountabilityService:
    @staticmethod
    def upload_document(
        *,
        company_id: int,
        file_storage: FileStorage | None,
        upload_root: str | Path,
        allowed_company_ids: Optional[Sequence[int]] = None,
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
        target_dir = Path(upload_root) / "financial" / "accountability" / str(company_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_name = f"{timestamp}_{file_hash[:12]}_{safe_name}"
        target_path = target_dir / target_name
        target_path.write_bytes(file_bytes)

        extracted_text, extraction_method = FinancialAccountabilityService._extract_text(
            file_name=safe_name,
            file_bytes=file_bytes,
        )
        preview = extracted_text[:1000]
        mime_type = file_storage.mimetype or mimetypes.guess_type(safe_name)[0]
        relative_path = target_path.relative_to(Path(upload_root)).as_posix()

        result = AccountabilityUploadResult(
            file_name=safe_name,
            stored_relative_path=relative_path,
            public_url=f"/uploads/{relative_path}",
            mime_type=mime_type,
            file_size=len(file_bytes),
            sha256=file_hash,
            extracted_text=extracted_text,
            extracted_preview=preview,
            extraction_method=extraction_method,
            extension=extension,
        )
        return result.to_dict(), None

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
