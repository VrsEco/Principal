from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence, Tuple

from models import db
from models.financial import FinancialEntry, FinancialImportBatch, FinancialIngestionRecord, FinancialSchedule
from schemas.financial import FinancialIngestionRecordInput, FinancialIngestionRecordUpdateInput
from services.financial_service import FinancialService
from services.financial_schedule_service import FinancialScheduleService


class FinancialIngestionService:
    @staticmethod
    def _serialize(record: FinancialIngestionRecord) -> Dict[str, Any]:
        payload = record.to_dict()
        payload["related_schedule"] = (
            FinancialScheduleService._serialize_schedule(record.related_schedule)
            if record.related_schedule is not None
            else None
        )
        payload["related_entry"] = (
            FinancialService.serialize_entry(record.related_entry, include_children=False)
            if record.related_entry is not None
            else None
        )
        return payload

    @staticmethod
    def _sanitize_json(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: FinancialIngestionService._sanitize_json(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [FinancialIngestionService._sanitize_json(item) for item in value]
        if hasattr(value, "model_dump") and callable(value.model_dump):
            return FinancialIngestionService._sanitize_json(value.model_dump())
        return value

    @staticmethod
    def _validate_related_links(*, company_id: int, import_batch_id: Optional[int], related_schedule_id: Optional[int], related_entry_id: Optional[int]) -> Optional[str]:
        if import_batch_id:
            batch = FinancialImportBatch.query.filter(
                FinancialImportBatch.company_id == company_id,
                FinancialImportBatch.id == import_batch_id,
                FinancialImportBatch.deleted_at.is_(None),
            ).first()
            if not batch:
                return "Lote de importação não encontrado para a empresa informada."

        if related_schedule_id:
            schedule = FinancialSchedule.query.filter(
                FinancialSchedule.company_id == company_id,
                FinancialSchedule.id == related_schedule_id,
                FinancialSchedule.deleted_at.is_(None),
            ).first()
            if not schedule:
                return "Agendamento relacionado não encontrado para a empresa informada."

        if related_entry_id:
            entry = FinancialEntry.query.filter(
                FinancialEntry.company_id == company_id,
                FinancialEntry.id == related_entry_id,
                FinancialEntry.deleted_at.is_(None),
            ).first()
            if not entry:
                return "Lançamento relacionado não encontrado para a empresa informada."

        return None

    @staticmethod
    def list_records(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        origin_type: Optional[str] = None,
        completion_status: Optional[str] = None,
        review_status: Optional[str] = None,
    ) -> Tuple[Optional[list[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialIngestionRecord.query.filter(
            FinancialIngestionRecord.company_id == company_id,
            FinancialIngestionRecord.deleted_at.is_(None),
        )
        if origin_type:
            query = query.filter(FinancialIngestionRecord.origin_type == origin_type)
        if completion_status:
            query = query.filter(FinancialIngestionRecord.completion_status == completion_status)
        if review_status:
            query = query.filter(FinancialIngestionRecord.review_status == review_status)

        records = query.order_by(FinancialIngestionRecord.id.desc()).all()
        return [FinancialIngestionService._serialize(item) for item in records], None

    @staticmethod
    def get_record(
        *,
        record_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        record = FinancialIngestionRecord.query.filter(
            FinancialIngestionRecord.company_id == company_id,
            FinancialIngestionRecord.id == record_id,
            FinancialIngestionRecord.deleted_at.is_(None),
        ).first()
        if not record:
            return None, "Registro de ingestão financeira não encontrado no escopo da empresa."
        return FinancialIngestionService._serialize(record), None

    @staticmethod
    def create_record(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialIngestionRecordInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para ingestão financeira: {exc}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        link_error = FinancialIngestionService._validate_related_links(
            company_id=data.company_id,
            import_batch_id=data.import_batch_id,
            related_schedule_id=data.related_schedule_id,
            related_entry_id=data.related_entry_id,
        )
        if link_error:
            return None, link_error

        try:
            normalized = data.model_dump()
            for key in ("raw_payload_json", "normalized_payload_json", "llm_response_json", "metadata_json"):
                normalized[key] = FinancialIngestionService._sanitize_json(normalized.get(key) or {})
            record = FinancialIngestionRecord(**normalized)
            db.session.add(record)
            db.session.commit()
            db.session.refresh(record)
            return FinancialIngestionService._serialize(record), None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao criar registro de ingestão financeira: {exc}"

    @staticmethod
    def update_record(
        *,
        record_id: int,
        company_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialIngestionRecordUpdateInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para atualização da ingestão financeira: {exc}"

        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        record = FinancialIngestionRecord.query.filter(
            FinancialIngestionRecord.company_id == company_id,
            FinancialIngestionRecord.id == record_id,
            FinancialIngestionRecord.deleted_at.is_(None),
        ).first()
        if not record:
            return None, "Registro de ingestão financeira não encontrado no escopo da empresa."

        merged = data.model_dump(exclude_unset=True)
        link_error = FinancialIngestionService._validate_related_links(
            company_id=company_id,
            import_batch_id=merged.get("import_batch_id", record.import_batch_id),
            related_schedule_id=merged.get("related_schedule_id", record.related_schedule_id),
            related_entry_id=merged.get("related_entry_id", record.related_entry_id),
        )
        if link_error:
            return None, link_error

        try:
            for key, value in merged.items():
                if key in {"raw_payload_json", "normalized_payload_json", "llm_response_json", "metadata_json"} and value is not None:
                    value = FinancialIngestionService._sanitize_json(value)
                setattr(record, key, value)
            if "review_status" in merged and merged.get("review_status") in {"reviewed", "rejected"}:
                record.reviewed_at = datetime.utcnow()
            db.session.commit()
            db.session.refresh(record)
            return FinancialIngestionService._serialize(record), None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao atualizar registro de ingestão financeira: {exc}"

    @staticmethod
    def review_record(
        *,
        record_id: int,
        company_id: int,
        review_status: str,
        review_notes: Optional[str] = None,
        completion_status: Optional[str] = None,
        reviewed_by_user_id: Optional[int] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        payload: Dict[str, Any] = {
            "review_status": review_status,
            "review_notes": review_notes,
            "reviewed_by_user_id": reviewed_by_user_id,
        }
        if completion_status:
            payload["completion_status"] = completion_status
        return FinancialIngestionService.update_record(
            record_id=record_id,
            company_id=company_id,
            payload=payload,
            allowed_company_ids=allowed_company_ids,
        )

    @staticmethod
    def convert_record(
        *,
        record_id: int,
        company_id: int,
        target_type: str,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        record = FinancialIngestionRecord.query.filter(
            FinancialIngestionRecord.company_id == company_id,
            FinancialIngestionRecord.id == record_id,
            FinancialIngestionRecord.deleted_at.is_(None),
        ).first()
        if not record:
            return None, "Registro de ingestão financeira não encontrado no escopo da empresa."

        normalized = dict(record.normalized_payload_json or {})
        raw = dict(record.raw_payload_json or {})
        target = str(target_type or "").strip().lower()

        if target == "schedule":
            payload = FinancialIngestionService._build_schedule_payload(company_id=company_id, record=record, normalized=normalized, raw=raw)
            result, error = FinancialScheduleService.create_schedule(payload=payload, allowed_company_ids=allowed_company_ids)
            if error:
                return None, error
            record.related_schedule_id = result["id"]
            record.completion_status = "approved" if record.completion_status not in {"settled", "closed"} else record.completion_status
            record.review_status = "reviewed" if record.review_status == "pending_review" else record.review_status
            record.reviewed_at = record.reviewed_at or datetime.utcnow()
            db.session.commit()
            return {"target_type": "schedule", "schedule": result, "record": FinancialIngestionService._serialize(record)}, None

        if target == "entry":
            payload = FinancialIngestionService._build_entry_payload(company_id=company_id, record=record, normalized=normalized, raw=raw)
            entry, error = FinancialService.create_entry(payload=payload, allowed_company_ids=allowed_company_ids)
            if error:
                return None, error
            record.related_entry_id = entry.id
            record.completion_status = "approved" if record.completion_status not in {"settled", "closed"} else record.completion_status
            record.review_status = "reviewed" if record.review_status == "pending_review" else record.review_status
            record.reviewed_at = record.reviewed_at or datetime.utcnow()
            db.session.commit()
            return {"target_type": "entry", "entry": FinancialService.serialize_entry(entry), "record": FinancialIngestionService._serialize(record)}, None

        return None, "target_type inválido. Use 'schedule' ou 'entry'."

    @staticmethod
    def _build_schedule_payload(*, company_id: int, record: FinancialIngestionRecord, normalized: Dict[str, Any], raw: Dict[str, Any]) -> Dict[str, Any]:
        description = normalized.get("description") or raw.get("description") or raw.get("history") or f"Ingestão financeira {record.id}"
        due_date = normalized.get("due_date") or normalized.get("first_due_date") or normalized.get("competence_date") or datetime.utcnow().date().isoformat()
        competence_date = normalized.get("competence_date") or normalized.get("start_date") or due_date
        amount = normalized.get("amount") or normalized.get("template_amount") or raw.get("amount") or 0
        movement_nature = normalized.get("movement_nature") or ("credit" if normalized.get("entry_type") == "receivable" else "debit")
        metadata_json = dict(normalized.get("metadata_json") or {})
        metadata_json.setdefault("ingestion_record_id", record.id)
        metadata_json.setdefault("origin_payload", raw)
        metadata_json.setdefault("document_number", normalized.get("document_number") or raw.get("document_number"))
        payload = {
            "company_id": company_id,
            "schedule_code": normalized.get("schedule_code") or f"ING-SCH-{record.id:06d}",
            "name": str(description)[:120],
            "description": str(description)[:255],
            "entry_type": normalized.get("entry_type") or "payable",
            "movement_nature": movement_nature,
            "origin_type": "sapiens" if str(record.origin_type).startswith("sapiens") else "api" if record.origin_type in {"api", "mcp", "integration_erp"} else "manual",
            "status": "draft",
            "frequency": normalized.get("frequency") or "one_time",
            "interval_value": int(normalized.get("interval_value") or 1),
            "start_date": competence_date,
            "first_due_date": due_date,
            "next_due_date": normalized.get("next_due_date") or due_date,
            "template_amount": amount,
            "counterparty_id": normalized.get("counterparty_id"),
            "chart_account_id": normalized.get("chart_account_id"),
            "cost_center_id": normalized.get("cost_center_id"),
            "notes": normalized.get("notes") or record.review_notes,
            "metadata_json": metadata_json,
        }
        if normalized.get("bank_account_id"):
            payload["bank_account_id"] = normalized.get("bank_account_id")
        return payload

    @staticmethod
    def _build_entry_payload(*, company_id: int, record: FinancialIngestionRecord, normalized: Dict[str, Any], raw: Dict[str, Any]) -> Dict[str, Any]:
        description = normalized.get("description") or raw.get("description") or raw.get("history") or f"Ingestão financeira {record.id}"
        competence_date = normalized.get("competence_date") or normalized.get("occurred_on") or normalized.get("due_date") or datetime.utcnow().date().isoformat()
        amount = normalized.get("amount") or normalized.get("original_amount") or raw.get("amount") or 0
        entry_type = normalized.get("entry_type") or "bank_movement"
        metadata_json = dict(normalized.get("metadata_json") or {})
        metadata_json.setdefault("ingestion_record_id", record.id)
        metadata_json.setdefault("origin_payload", raw)
        return {
            "company_id": company_id,
            "entry_code": normalized.get("entry_code") or f"ING-ENT-{record.id:06d}",
            "entry_type": entry_type,
            "movement_nature": normalized.get("movement_nature") or ("credit" if entry_type == "receivable" else "debit"),
            "origin_type": "sapiens" if str(record.origin_type).startswith("sapiens") else "api" if record.origin_type in {"api", "mcp", "integration_erp"} else "manual",
            "status": normalized.get("status") or "draft",
            "review_status": "pending_review",
            "description": str(description)[:255],
            "document_number": normalized.get("document_number") or raw.get("document_number"),
            "origin_reference": record.origin_reference,
            "external_reference": normalized.get("external_reference") or f"ingestion-record:{record.id}",
            "competence_date": competence_date,
            "due_date": normalized.get("due_date"),
            "occurred_on": normalized.get("occurred_on") or competence_date,
            "original_amount": amount,
            "bank_account_id": normalized.get("bank_account_id"),
            "counterparty_id": normalized.get("counterparty_id"),
            "chart_account_id": normalized.get("chart_account_id"),
            "cost_center_id": normalized.get("cost_center_id"),
            "notes": normalized.get("notes") or record.review_notes,
            "metadata_json": metadata_json,
        }
