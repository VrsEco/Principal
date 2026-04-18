from __future__ import annotations

from typing import Any, Callable, Dict, Optional

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
        stage_channel_document: Callable[..., tuple[Optional[Dict[str, Any]], Optional[str]]],
    ):
        self._upload_root_provider = upload_root_provider
        self._stage_channel_document = stage_channel_document

    def execute(self, request: FinancialReceiptIngestRequest) -> FinancialReceiptIngestResult:
        company_id = request.active_company_id
        if not company_id:
            return FinancialReceiptIngestResult(
                response_text="Não consegui identificar a empresa para enviar o recibo à automação financeira."
            )

        payload = dict(request.payload or {})
        attachment = dict(payload.get("_attachment") or payload.get("attachment") or {})
        file_name = str(attachment.get("file_name") or attachment.get("name") or "recibo.pdf").strip()
        file_bytes = attachment.get("file_bytes")
        mime_type = str(attachment.get("mime_type") or attachment.get("content_type") or "").strip() or None
        channel_label = str(payload.get("_channel_label") or "Sapiens").strip()
        source_label = str(payload.get("_source_label") or f"{channel_label} - recebimento assistido").strip()

        if not isinstance(file_bytes, (bytes, bytearray)) or not file_bytes:
            return FinancialReceiptIngestResult(
                response_text="Recebi a solicitação, mas o arquivo do recibo não estava disponível para envio à Central."
            )

        result, error = self._stage_channel_document(
            company_id=int(company_id),
            user_id=request.user_id,
            upload_root=self._upload_root_provider(),
            file_name=file_name,
            file_bytes=bytes(file_bytes),
            mime_type=mime_type,
            source_label=source_label,
            origin_type="integration",
            allowed_company_ids=[int(company_id)],
        )
        if error:
            return FinancialReceiptIngestResult(
                response_text=f"Não consegui enviar o recibo para a automação financeira: {error}"
            )

        record = dict((result or {}).get("record") or {})
        batch = dict((result or {}).get("batch") or {})
        dedupe = dict((record.get("metadata_json") or {}).get("dedupe") or {})
        duplicate_hint = ""
        if str(dedupe.get("status") or "").strip().lower() == "duplicate":
            duplicate_hint = "\n- Atenção: encontrei duplicidade exata por chave fiscal/hash e deixei sinalizado para revisão."

        return FinancialReceiptIngestResult(
            response_text=(
                "Arquivo enviado para a Central de Automação Financeira com sucesso.\n\n"
                f"- Lote: {batch.get('id') or '-'}\n"
                f"- Registro: {record.get('id') or '-'}\n"
                f"- Documento: {record.get('document_type') or 'documento'}\n"
                f"- Descrição: {record.get('description') or file_name}\n"
                f"- Status inicial: {record.get('status') or 'imported'}"
                f"{duplicate_hint}\n\n"
                "Você já pode revisar em /financial/automation."
            )
        )
