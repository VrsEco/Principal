from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, Optional, Sequence, Tuple

from werkzeug.datastructures import FileStorage

from services.financial_automation_service import FinancialAutomationService


class FinancialAutomationChannelService:
    @staticmethod
    def stage_channel_document(
        *,
        company_id: int,
        user_id: Optional[int],
        upload_root: str,
        file_name: str,
        file_bytes: bytes,
        mime_type: Optional[str] = None,
        source_label: Optional[str] = None,
        source_metadata: Optional[Dict[str, Any]] = None,
        origin_type: str = "integration",
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        if not file_bytes:
            return None, "Arquivo recebido pelo canal está vazio."

        file_storage = FileStorage(
            stream=BytesIO(file_bytes),
            filename=file_name,
            name="file",
            content_type=mime_type or "application/octet-stream",
        )
        batch_result, upload_error = FinancialAutomationService.upload_batch_files(
            company_id=company_id,
            origin_type=origin_type,
            files=[file_storage],
            upload_root=upload_root,
            source_label=source_label,
            source_metadata=source_metadata,
            created_by_user_id=user_id,
            allowed_company_ids=allowed_company_ids,
        )
        if upload_error:
            return None, upload_error

        batch = dict((batch_result or {}).get("batch") or {})
        batch_id = batch.get("id")
        if not batch_id:
            return None, "Não foi possível criar o lote da Central para o arquivo recebido."

        parse_result, parse_error = FinancialAutomationService.parse_batch_documents(
            company_id=company_id,
            batch_id=int(batch_id),
            upload_root=upload_root,
            allowed_company_ids=allowed_company_ids,
            performed_by_user_id=user_id,
        )
        if parse_error:
            return None, parse_error

        records = list((parse_result or {}).get("records") or [])
        documents = list((batch_result or {}).get("documents") or [])
        return {
            "batch": batch,
            "documents": documents,
            "records": records,
            "record": records[0] if records else None,
            "document": documents[0] if documents else None,
        }, None
