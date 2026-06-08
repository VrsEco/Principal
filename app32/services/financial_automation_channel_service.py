from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Optional, Sequence, Tuple

from werkzeug.datastructures import FileStorage

from services.financial_automation_service import FinancialAutomationService


class FinancialAutomationChannelService:
    @staticmethod
    def stage_channel_documents(
        *,
        company_id: int,
        user_id: Optional[int],
        upload_root: str,
        documents: Sequence[Dict[str, Any]],
        source_label: Optional[str] = None,
        source_metadata: Optional[Dict[str, Any]] = None,
        origin_type: str = "integration",
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        normalized_documents: List[Dict[str, Any]] = []
        for raw_document in documents or []:
            payload = dict(raw_document or {})
            file_bytes = payload.get("file_bytes")
            file_name = str(payload.get("file_name") or payload.get("name") or "").strip()
            mime_type = payload.get("mime_type") or payload.get("content_type")
            if not isinstance(file_bytes, (bytes, bytearray)) or not file_bytes:
                return None, f"Arquivo recebido pelo canal está vazio: {file_name or 'sem nome'}."
            if not file_name:
                return None, "Arquivo recebido pelo canal sem nome identificável."
            normalized_documents.append(
                {
                    "file_name": file_name,
                    "file_bytes": bytes(file_bytes),
                    "mime_type": str(mime_type).strip() if mime_type else "application/octet-stream",
                }
            )

        if not normalized_documents:
            return None, "Nenhum arquivo válido foi recebido pelo canal."

        file_storages = [
            FileStorage(
                stream=BytesIO(item["file_bytes"]),
                filename=item["file_name"],
                name="file",
                content_type=item["mime_type"],
            )
            for item in normalized_documents
        ]
        batch_result, upload_error = FinancialAutomationService.upload_batch_files(
            company_id=company_id,
            origin_type=origin_type,
            files=file_storages,
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
        return FinancialAutomationChannelService.stage_channel_documents(
            company_id=company_id,
            user_id=user_id,
            upload_root=upload_root,
            documents=[
                {
                    "file_name": file_name,
                    "file_bytes": file_bytes,
                    "mime_type": mime_type,
                }
            ],
            source_label=source_label,
            source_metadata=source_metadata,
            origin_type=origin_type,
            allowed_company_ids=allowed_company_ids,
        )
