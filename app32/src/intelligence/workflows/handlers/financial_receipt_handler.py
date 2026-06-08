from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FinancialReceiptIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class FinancialReceiptIngestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class FinancialReceiptIngestExecutionHandler:
    def __init__(
        self,
        *,
        upload_root_provider: Callable[[], str],
        stage_channel_documents: Callable[..., tuple[Optional[Dict[str, Any]], Optional[str]]],
    ):
        self._upload_root_provider = upload_root_provider
        self._stage_channel_documents = stage_channel_documents

    def execute(self, request: FinancialReceiptIngestRequest) -> FinancialReceiptIngestResult:
        company_id = request.active_company_id
        if not company_id:
            return FinancialReceiptIngestResult(
                response_text="Não consegui identificar a empresa para enviar o recibo à automação financeira."
            )

        payload = dict(request.payload or {})
        attachments_payload = list(payload.get("_attachments") or payload.get("attachments") or [])
        if not attachments_payload:
            single_attachment = dict(payload.get("_attachment") or payload.get("attachment") or {})
            if single_attachment:
                attachments_payload = [single_attachment]

        normalized_attachments: List[Dict[str, Any]] = []
        for raw_attachment in attachments_payload:
            attachment = dict(raw_attachment or {})
            file_name = str(attachment.get("file_name") or attachment.get("name") or "recibo.pdf").strip()
            file_bytes = attachment.get("file_bytes")
            mime_type = str(attachment.get("mime_type") or attachment.get("content_type") or "").strip() or None
            if not isinstance(file_bytes, (bytes, bytearray)) or not file_bytes:
                continue
            normalized_attachments.append(
                {
                    "file_name": file_name,
                    "file_bytes": bytes(file_bytes),
                    "mime_type": mime_type,
                }
            )

        channel_label = str(payload.get("_channel_label") or "Sapiens").strip()
        source_label = str(payload.get("_source_label") or f"{channel_label} - recebimento assistido").strip()
        source_channel = str(payload.get("_source_channel") or channel_label or "sapiens").strip().lower()
        source_contact = str(payload.get("_source_contact") or "").strip()
        source_external_reference = str(payload.get("_source_external_reference") or "").strip()
        source_thread_id = str(payload.get("_thread_id") or payload.get("thread_id") or "").strip()

        if not normalized_attachments:
            return FinancialReceiptIngestResult(
                response_text="Recebi a solicitação, mas nenhum arquivo válido do recibo estava disponível para envio à Central."
            )

        result, error = self._stage_channel_documents(
            company_id=int(company_id),
            user_id=request.user_id,
            upload_root=self._upload_root_provider(),
            documents=normalized_attachments,
            source_label=source_label,
            source_metadata={
                "source_channel": source_channel,
                "source_contact": source_contact,
                "source_external_reference": source_external_reference,
                "source_thread_id": source_thread_id,
            },
            origin_type="integration",
            allowed_company_ids=[int(company_id)],
        )
        if error:
            return FinancialReceiptIngestResult(
                response_text=f"Não consegui enviar o recibo para a automação financeira: {error}"
            )

        batch = dict((result or {}).get("batch") or {})
        records = list((result or {}).get("records") or [])
        documents = list((result or {}).get("documents") or [])
        record = dict((result or {}).get("record") or {})
        dedupe = dict((record.get("metadata_json") or {}).get("dedupe") or {})
        duplicate_hint = ""
        if str(dedupe.get("status") or "").strip().lower() == "duplicate":
            duplicate_hint = "\n- Atenção: encontrei duplicidade exata por chave fiscal/hash e deixei sinalizado para revisão."

        record_count = len(records)
        document_count = len(documents)
        first_file_name = normalized_attachments[0]["file_name"]
        if record_count > 1 or document_count > 1:
            return FinancialReceiptIngestResult(
                response_text=(
                    "Arquivos enviados para a Central de Automação Financeira com sucesso.\n\n"
                    f"- Lote: {batch.get('id') or '-'}\n"
                    f"- Documentos no lote: {document_count or len(normalized_attachments)}\n"
                    f"- Registros gerados: {record_count}\n"
                    f"- Primeiro documento: {(documents[0] or {}).get('file_name') if documents else first_file_name}\n\n"
                    "Os documentos aparecerão no mesmo lote e poderão ser tratados separadamente em /financial/automation."
                )
            )

        return FinancialReceiptIngestResult(
            response_text=(
                "Arquivo enviado para a Central de Automação Financeira com sucesso.\n\n"
                f"- Lote: {batch.get('id') or '-'}\n"
                f"- Registro: {record.get('id') or '-'}\n"
                f"- Documento: {record.get('document_type') or 'documento'}\n"
                f"- Descrição: {record.get('description') or first_file_name}\n"
                f"- Status inicial: {record.get('status') or 'imported'}"
                f"{duplicate_hint}\n\n"
                "Você já pode revisar em /financial/automation."
            )
        )
