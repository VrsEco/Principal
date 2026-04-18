from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import (
    FinancialAutomationBatch,
    FinancialAutomationDocument,
    FinancialAutomationHistory,
    FinancialAutomationRecord,
    db,
)
from models.financial import (
    FinancialAutomationExecution,
    FinancialAutomationRule,
    FinancialBankAccount,
    FinancialChartAccount,
    FinancialClassificationMemory,
    FinancialCostCenter,
    FinancialCounterparty,
    FinancialSchedule,
)
from models.process import Process, ProcessInstance, ProcessRoutine
from schemas.financial import FinancialAutomationRuleCreateInput, FinancialAutomationRuleUpdateInput
from schemas.financial_automation import (
    FinancialAutomationBatchCreateInput,
    FinancialAutomationBulkStatusInput,
    FinancialAutomationDocumentCreateInput,
    FinancialAutomationGenerateInput,
    FinancialAutomationHistoryCreateInput,
    FinancialAutomationRecordCreateInput,
    FinancialAutomationRecordUpdateInput,
)
from services.financial_accountability_service import FinancialAccountabilityService
from services.financial_catalog_service import FinancialCatalogService
from services.financial_domain_enablement_service import FinancialDomainEnablementService
from services.financial_import_service import FinancialImportService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_service import FinancialService


logger = logging.getLogger(__name__)


class FinancialAutomationService:
    MAX_ATTEMPTS = 3
    HIGH_CONFIDENCE_SUGGESTION_THRESHOLD = Decimal("0.75")

    @staticmethod
    def _refresh_batch_summary(batch: Optional[FinancialAutomationBatch]) -> None:
        if not batch:
            return
        records = batch.records.filter(FinancialAutomationRecord.deleted_at.is_(None)).all()
        batch.status_summary_json = {
            "records_total": len(records),
            "documents_total": batch.documents.filter(FinancialAutomationDocument.deleted_at.is_(None)).count(),
            "imported_count": sum(1 for item in records if item.status == "imported"),
            "validated_count": sum(1 for item in records if item.status == "validated"),
            "generated_count": sum(1 for item in records if item.status == "generated"),
            "excluded_count": sum(1 for item in records if item.status == "excluded"),
        }
        batch.updated_at = datetime.utcnow()

    @staticmethod
    def _ensure_company_scope(company_id: int, allowed_company_ids: Optional[Sequence[int]]) -> Optional[str]:
        return FinancialService._ensure_company_scope(company_id, allowed_company_ids)

    @staticmethod
    def _serialize_record(record: FinancialAutomationRecord) -> Dict[str, Any]:
        payload = record.to_dict()
        payload["document"] = record.source_document.to_dict() if record.source_document else None
        payload["batch"] = record.batch.to_dict() if getattr(record, "batch", None) else None
        payload["related_documents"] = FinancialAutomationService._list_related_documents(record)
        return payload

    @staticmethod
    def _list_related_documents(record: FinancialAutomationRecord) -> List[Dict[str, Any]]:
        if not getattr(record, "batch_id", None):
            return []
        if getattr(record, "document_group_key", None):
            try:
                query = FinancialAutomationDocument.query.filter(
                    FinancialAutomationDocument.company_id == record.company_id,
                    FinancialAutomationDocument.batch_id == record.batch_id,
                    FinancialAutomationDocument.document_group_key == record.document_group_key,
                    FinancialAutomationDocument.deleted_at.is_(None),
                )
                return [item.to_dict() for item in query.order_by(FinancialAutomationDocument.id.asc()).all()]
            except Exception:
                return [record.source_document.to_dict()] if getattr(record, "source_document", None) else []
        if getattr(record, "source_document", None):
            return [record.source_document.to_dict()]
        return []

    @staticmethod
    def _document_priority(document_type: Optional[str]) -> int:
        if document_type in {"nfe_xml", "nfce_xml", "cte_xml"}:
            return 300
        if document_type in {"danfe_pdf", "dacte_pdf"}:
            return 200
        if document_type in {"receipt_pdf", "receipt_image"}:
            return 120
        if document_type in {"spreadsheet", "ofx"}:
            return 100
        return 10

    @staticmethod
    def _digits_only(value: Optional[str]) -> str:
        return re.sub(r"\D", "", str(value or ""))

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        return str(value or "").strip()

    @staticmethod
    def _normalize_text_lower(value: Optional[str]) -> str:
        return FinancialAutomationService._normalize_text(value).lower()

    @staticmethod
    def _extract_counterparty_hint(
        *,
        entry_direction: Optional[str],
        structured_payload: Dict[str, Any],
    ) -> Tuple[Optional[str], Optional[str]]:
        if str(entry_direction or "").strip().lower() == "receivable":
            return (
                FinancialAutomationService._normalize_text(structured_payload.get("recipient_name")) or None,
                FinancialAutomationService._digits_only(structured_payload.get("recipient_document")) or None,
            )
        return (
            FinancialAutomationService._normalize_text(structured_payload.get("issuer_name")) or None,
            FinancialAutomationService._digits_only(structured_payload.get("issuer_document")) or None,
        )

    @staticmethod
    def _build_record_composite_fingerprint(record_kwargs: Dict[str, Any]) -> Optional[str]:
        amount = FinancialImportService._parse_decimal(record_kwargs.get("amount"))
        issue_date = FinancialImportService._parse_date(record_kwargs.get("issue_date"))
        document_number = FinancialAutomationService._normalize_text(record_kwargs.get("external_document_number"))
        issuer_document = FinancialAutomationService._digits_only(record_kwargs.get("issuer_document"))
        recipient_document = FinancialAutomationService._digits_only(record_kwargs.get("recipient_document"))
        if not amount or not issue_date:
            return None
        parts = [
            document_number or "-",
            issuer_document or "-",
            recipient_document or "-",
            issue_date.isoformat(),
            f"{Decimal(amount):.2f}",
        ]
        if all(part == "-" for part in parts[:3]):
            return None
        return "cmp:" + "|".join(parts)

    @staticmethod
    def _find_duplicate_context(
        *,
        company_id: int,
        batch_id: int,
        source_document: Optional[FinancialAutomationDocument],
        record_kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        document_key = FinancialAutomationService._normalize_text(record_kwargs.get("document_key"))
        document_group_key = FinancialAutomationService._normalize_text(record_kwargs.get("document_group_key"))
        sha256 = FinancialAutomationService._normalize_text(getattr(source_document, "sha256", None))
        composite_key = FinancialAutomationService._build_record_composite_fingerprint(record_kwargs)

        duplicate_context: Dict[str, Any] = {
            "status": "unique",
            "reason": None,
            "matched_record_id": None,
            "matched_batch_id": None,
            "matched_document_id": None,
            "matched_document_group_key": None,
            "matched_sha256": None,
            "composite_key": composite_key,
        }

        existing_record = None
        if document_key:
            existing_record = FinancialAutomationRecord.query.filter(
                FinancialAutomationRecord.company_id == company_id,
                FinancialAutomationRecord.deleted_at.is_(None),
                FinancialAutomationRecord.document_key == document_key,
                FinancialAutomationRecord.batch_id != batch_id,
            ).order_by(FinancialAutomationRecord.id.desc()).first()
            if existing_record:
                duplicate_context.update(
                    {
                        "status": "duplicate",
                        "reason": "document_key",
                        "matched_record_id": existing_record.id,
                        "matched_batch_id": existing_record.batch_id,
                        "matched_document_group_key": existing_record.document_group_key,
                    }
                )
                return duplicate_context

        if document_group_key:
            existing_record = FinancialAutomationRecord.query.filter(
                FinancialAutomationRecord.company_id == company_id,
                FinancialAutomationRecord.deleted_at.is_(None),
                FinancialAutomationRecord.document_group_key == document_group_key,
                FinancialAutomationRecord.batch_id != batch_id,
            ).order_by(FinancialAutomationRecord.id.desc()).first()
            if existing_record:
                duplicate_context.update(
                    {
                        "status": "duplicate" if document_group_key.startswith(("key:", "sha:")) else "possible_duplicate",
                        "reason": "document_group_key",
                        "matched_record_id": existing_record.id,
                        "matched_batch_id": existing_record.batch_id,
                        "matched_document_group_key": existing_record.document_group_key,
                    }
                )
                return duplicate_context

        if sha256:
            duplicate_document = FinancialAutomationDocument.query.filter(
                FinancialAutomationDocument.company_id == company_id,
                FinancialAutomationDocument.deleted_at.is_(None),
                FinancialAutomationDocument.sha256 == sha256,
                FinancialAutomationDocument.batch_id != batch_id,
            ).order_by(FinancialAutomationDocument.id.desc()).first()
            if duplicate_document:
                existing_record = FinancialAutomationRecord.query.filter(
                    FinancialAutomationRecord.company_id == company_id,
                    FinancialAutomationRecord.deleted_at.is_(None),
                    FinancialAutomationRecord.source_document_id == duplicate_document.id,
                ).order_by(FinancialAutomationRecord.id.desc()).first()
                duplicate_context.update(
                    {
                        "status": "duplicate",
                        "reason": "sha256",
                        "matched_record_id": getattr(existing_record, "id", None),
                        "matched_batch_id": getattr(existing_record, "batch_id", None) or duplicate_document.batch_id,
                        "matched_document_id": duplicate_document.id,
                        "matched_document_group_key": duplicate_document.document_group_key,
                        "matched_sha256": sha256,
                    }
                )
                return duplicate_context

        if composite_key:
            candidates = FinancialAutomationRecord.query.filter(
                FinancialAutomationRecord.company_id == company_id,
                FinancialAutomationRecord.deleted_at.is_(None),
                FinancialAutomationRecord.batch_id != batch_id,
                FinancialAutomationRecord.issue_date == FinancialImportService._parse_date(record_kwargs.get("issue_date")),
                FinancialAutomationRecord.amount == FinancialImportService._parse_decimal(record_kwargs.get("amount")),
            ).order_by(FinancialAutomationRecord.id.desc()).all()
            for candidate in candidates:
                candidate_key = FinancialAutomationService._build_record_composite_fingerprint(candidate.to_dict())
                if candidate_key and candidate_key == composite_key:
                    duplicate_context.update(
                        {
                            "status": "possible_duplicate",
                            "reason": "composite_fingerprint",
                            "matched_record_id": candidate.id,
                            "matched_batch_id": candidate.batch_id,
                            "matched_document_group_key": candidate.document_group_key,
                        }
                    )
                    return duplicate_context

        return duplicate_context

    @staticmethod
    def _find_classification_memory_suggestion(
        *,
        company_id: int,
        counterparty_name: Optional[str],
        counterparty_document: Optional[str],
        description: Optional[str],
        amount: Optional[Decimal],
    ) -> Optional[Dict[str, Any]]:
        memories = FinancialClassificationMemory.query.filter(
            FinancialClassificationMemory.company_id == company_id,
            FinancialClassificationMemory.is_active.is_(True),
            FinancialClassificationMemory.deleted_at.is_(None),
        ).order_by(
            FinancialClassificationMemory.times_confirmed.desc(),
            FinancialClassificationMemory.id.desc(),
        ).all()

        normalized_counterparty_name = FinancialAutomationService._normalize_text_lower(counterparty_name)
        normalized_counterparty_document = FinancialAutomationService._digits_only(counterparty_document)
        normalized_description = FinancialAutomationService._normalize_text_lower(description)
        normalized_amount = FinancialImportService._parse_decimal(amount)

        best: Optional[Dict[str, Any]] = None
        for memory in memories:
            score = Decimal("0")
            supplier_name = FinancialAutomationService._normalize_text_lower(getattr(memory, "supplier_name", None))
            supplier_document = FinancialAutomationService._digits_only(getattr(memory, "supplier_document", None))
            description_pattern = FinancialAutomationService._normalize_text_lower(getattr(memory, "description_pattern", None))

            if supplier_document and normalized_counterparty_document and supplier_document == normalized_counterparty_document:
                score += Decimal("0.55")
            elif supplier_name and normalized_counterparty_name and supplier_name == normalized_counterparty_name:
                score += Decimal("0.50")
            elif supplier_name and normalized_counterparty_name and supplier_name in normalized_counterparty_name:
                score += Decimal("0.25")

            if description_pattern and normalized_description and description_pattern in normalized_description:
                score += Decimal("0.30")

            if (
                normalized_amount is not None
                and getattr(memory, "amount_range_min", None) is not None
                and getattr(memory, "amount_range_max", None) is not None
                and Decimal(memory.amount_range_min) <= normalized_amount <= Decimal(memory.amount_range_max)
            ):
                score += Decimal("0.20")

            if score <= 0:
                continue

            candidate = {
                "memory_id": memory.id,
                "score": min(score, Decimal("1")),
                "chart_account_id": getattr(memory, "chart_account_id", None),
                "cost_center_id": getattr(memory, "cost_center_id", None),
                "counterparty_hint": getattr(memory, "counterparty_hint", None) or getattr(memory, "supplier_name", None),
                "times_confirmed": getattr(memory, "times_confirmed", 0) or 0,
                "reason": "memory",
            }
            if best is None or candidate["score"] > best["score"] or (
                candidate["score"] == best["score"] and candidate["times_confirmed"] > best["times_confirmed"]
            ):
                best = candidate
        return best

    @staticmethod
    def _apply_auto_suggestions_to_record_kwargs(
        *,
        company_id: int,
        source_document: Optional[FinancialAutomationDocument],
        record_kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated = dict(record_kwargs or {})
        metadata_json = dict(updated.get("metadata_json") or {})
        normalized_payload_json = dict(updated.get("normalized_payload_json") or {})
        structured_payload = dict(updated.get("extracted_fields_json") or {})
        entry_direction = updated.get("entry_direction")
        counterparty_name, counterparty_document = FinancialAutomationService._extract_counterparty_hint(
            entry_direction=entry_direction,
            structured_payload=structured_payload,
        )

        normalized_payload_json.setdefault("counterparty_hint", counterparty_document or counterparty_name)
        enriched = FinancialCatalogService.enrich_reference_payload(
            company_id=company_id,
            payload=normalized_payload_json,
            counterparty_text=counterparty_document or counterparty_name,
            description_text=updated.get("description"),
            bank_reference=FinancialAutomationService._normalize_text((getattr(source_document, "metadata_json", {}) or {}).get("bank_reference") if source_document else None),
        )

        memory_suggestion = FinancialAutomationService._find_classification_memory_suggestion(
            company_id=company_id,
            counterparty_name=counterparty_name,
            counterparty_document=counterparty_document,
            description=updated.get("description"),
            amount=FinancialImportService._parse_decimal(updated.get("amount")),
        )
        if memory_suggestion and memory_suggestion.get("score", Decimal("0")) >= FinancialAutomationService.HIGH_CONFIDENCE_SUGGESTION_THRESHOLD:
            memory_payload = dict(enriched or {})
            if not memory_payload.get("counterparty_id") and memory_suggestion.get("counterparty_hint"):
                memory_payload["counterparty_hint"] = memory_suggestion.get("counterparty_hint")
                memory_payload = FinancialCatalogService.enrich_reference_payload(
                    company_id=company_id,
                    payload=memory_payload,
                    counterparty_text=memory_suggestion.get("counterparty_hint"),
                    description_text=updated.get("description"),
                )
            if not memory_payload.get("chart_account_id") and memory_suggestion.get("chart_account_id"):
                memory_payload["chart_account_id"] = memory_suggestion.get("chart_account_id")
            if not memory_payload.get("cost_center_id") and memory_suggestion.get("cost_center_id"):
                memory_payload["cost_center_id"] = memory_suggestion.get("cost_center_id")
            enriched = memory_payload

        updated["counterparty_id"] = enriched.get("counterparty_id") or updated.get("counterparty_id")
        updated["bank_account_id"] = enriched.get("bank_account_id") or updated.get("bank_account_id")
        updated["chart_account_id"] = enriched.get("chart_account_id") or updated.get("chart_account_id")
        updated["cost_center_id"] = enriched.get("cost_center_id") or updated.get("cost_center_id")

        normalized_payload_json.update(
            {
                "counterparty_hint": enriched.get("counterparty_hint") or normalized_payload_json.get("counterparty_hint"),
                "counterparty_id": updated.get("counterparty_id"),
                "bank_account_id": updated.get("bank_account_id"),
                "chart_account_id": updated.get("chart_account_id"),
                "cost_center_id": updated.get("cost_center_id"),
            }
        )

        metadata_json["auto_suggestions"] = {
            "counterparty": {
                "counterparty_name": counterparty_name,
                "counterparty_document": counterparty_document,
                "suggested_id": updated.get("counterparty_id"),
                "source": "catalog",
            },
            "bank_account": {
                "suggested_id": updated.get("bank_account_id"),
                "source": "catalog" if updated.get("bank_account_id") else None,
            },
            "chart_account": {
                "suggested_id": updated.get("chart_account_id"),
                "source": "catalog_or_memory" if updated.get("chart_account_id") else None,
                "memory_score": float(memory_suggestion.get("score")) if memory_suggestion and memory_suggestion.get("chart_account_id") else None,
            },
            "cost_center": {
                "suggested_id": updated.get("cost_center_id"),
                "source": "catalog_or_memory" if updated.get("cost_center_id") else None,
                "memory_score": float(memory_suggestion.get("score")) if memory_suggestion and memory_suggestion.get("cost_center_id") else None,
            },
        }
        if memory_suggestion:
            metadata_json["auto_suggestions"]["memory"] = {
                "memory_id": memory_suggestion.get("memory_id"),
                "score": float(memory_suggestion.get("score") or 0),
                "reason": memory_suggestion.get("reason"),
            }

        updated["normalized_payload_json"] = normalized_payload_json
        updated["metadata_json"] = metadata_json
        return updated

    @staticmethod
    def _apply_duplicate_metadata_to_record_kwargs(
        *,
        company_id: int,
        batch_id: int,
        source_document: Optional[FinancialAutomationDocument],
        record_kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        updated = dict(record_kwargs or {})
        metadata_json = dict(updated.get("metadata_json") or {})
        review_flags = list(updated.get("review_flags_json") or [])
        duplicate_context = FinancialAutomationService._find_duplicate_context(
            company_id=company_id,
            batch_id=batch_id,
            source_document=source_document,
            record_kwargs=updated,
        )
        metadata_json["dedupe"] = duplicate_context
        if duplicate_context.get("status") == "duplicate" and "duplicate_detected" not in review_flags:
            review_flags.append("duplicate_detected")
            updated["validation_notes"] = "Duplicidade exata detectada por chave fiscal ou hash documental."
        elif duplicate_context.get("status") == "possible_duplicate" and "possible_duplicate_detected" not in review_flags:
            review_flags.append("possible_duplicate_detected")
            updated["validation_notes"] = updated.get("validation_notes") or "Possível duplicidade detectada; revisão humana recomendada."

        normalized_payload_json = dict(updated.get("normalized_payload_json") or {})
        normalized_payload_json["dedupe_status"] = duplicate_context.get("status")
        normalized_payload_json["dedupe_reason"] = duplicate_context.get("reason")

        updated["review_flags_json"] = review_flags
        updated["metadata_json"] = metadata_json
        updated["normalized_payload_json"] = normalized_payload_json
        return updated

    @staticmethod
    def _guess_entry_direction_from_document(
        document_type: Optional[str],
        structured_payload: Dict[str, Any],
    ) -> str:
        operation = str(structured_payload.get("operation_nature") or "").lower()
        if "receb" in operation or "servi" in operation:
            return "receivable"
        if document_type == "receipt_pdf" and "receb" in operation:
            return "receivable"
        return "payable"

    @staticmethod
    def _guess_settlement_state_from_document(
        document_type: Optional[str],
        structured_payload: Dict[str, Any],
    ) -> str:
        if document_type in {"nfce_xml", "receipt_pdf", "receipt_image"}:
            return "settled"
        summary = str(structured_payload.get("summary") or "").lower()
        if any(token in summary for token in ("pago", "recebido", "quitado")):
            return "settled"
        return "open"

    @staticmethod
    def _build_review_flags(
        document_type: Optional[str],
        structured_payload: Dict[str, Any],
    ) -> List[str]:
        flags: List[str] = []
        if not structured_payload.get("document_number"):
            flags.append("missing_document_number")
        if not structured_payload.get("issuer_name"):
            flags.append("missing_issuer")
        if structured_payload.get("total_amount") in (None, 0, 0.0):
            flags.append("missing_total_amount")
        if not structured_payload.get("issue_date"):
            flags.append("missing_issue_date")
        if document_type in {"receipt_pdf", "receipt_image", "unknown_document"}:
            flags.append("manual_review_required")
        return flags

    @staticmethod
    def _build_description_from_document(structured_payload: Dict[str, Any], document_type: Optional[str]) -> str:
        number = structured_payload.get("document_number")
        issuer = structured_payload.get("issuer_name")
        if document_type in {"nfe_xml", "danfe_pdf"}:
            base = "Nota fiscal"
        elif document_type in {"cte_xml", "dacte_pdf"}:
            base = "Conhecimento de transporte"
        elif document_type in {"receipt_pdf", "receipt_image"}:
            base = "Recibo"
        else:
            base = "Documento importado"
        suffix = " - ".join(part for part in [f"Nº {number}" if number else None, issuer] if part)
        return f"{base}{f' - {suffix}' if suffix else ''}"[:255]

    @staticmethod
    def _build_record_kwargs_from_document_group(
        *,
        company_id: int,
        batch_id: int,
        anchor_document: FinancialAutomationDocument,
        grouped_documents: Sequence[FinancialAutomationDocument],
    ) -> Dict[str, Any]:
        structured_payload = dict(anchor_document.structured_payload_json or {})
        document_type = anchor_document.document_type
        amount = FinancialImportService._parse_decimal(structured_payload.get("total_amount")) or Decimal("0")
        issue_date = FinancialImportService._parse_date(structured_payload.get("issue_date"))
        settlement_state = FinancialAutomationService._guess_settlement_state_from_document(document_type, structured_payload)
        review_flags = FinancialAutomationService._build_review_flags(document_type, structured_payload)
        record_kwargs = {
            "company_id": company_id,
            "batch_id": batch_id,
            "source_document_id": anchor_document.id,
            "status": "imported",
            "entry_direction": FinancialAutomationService._guess_entry_direction_from_document(document_type, structured_payload),
            "settlement_state": settlement_state,
            "description": FinancialAutomationService._build_description_from_document(structured_payload, document_type),
            "document_group_key": anchor_document.document_group_key,
            "document_type": document_type,
            "document_key": structured_payload.get("document_key"),
            "external_document_number": structured_payload.get("document_number"),
            "issuer_name": structured_payload.get("issuer_name"),
            "issuer_document": structured_payload.get("issuer_document"),
            "recipient_name": structured_payload.get("recipient_name"),
            "recipient_document": structured_payload.get("recipient_document"),
            "issue_date": issue_date,
            "amount": amount,
            "competence_date": issue_date,
            "due_date": issue_date if settlement_state == "settled" else None,
            "confidence_score": Decimal(str(anchor_document.confidence_score or 0)),
            "validation_notes": None if not review_flags else "Campos documentais pendentes de revisão humana.",
            "extracted_fields_json": structured_payload,
            "review_flags_json": review_flags,
            "normalized_payload_json": {
                "description": FinancialAutomationService._build_description_from_document(structured_payload, document_type),
                "amount": float(amount),
                "issue_date": issue_date.isoformat() if issue_date else None,
                "document_type": document_type,
                "document_key": structured_payload.get("document_key"),
                "document_number": structured_payload.get("document_number"),
                "document_group_key": anchor_document.document_group_key,
                "document_sha256": getattr(anchor_document, "sha256", None),
                "issuer_name": structured_payload.get("issuer_name"),
                "issuer_document": structured_payload.get("issuer_document"),
                "recipient_name": structured_payload.get("recipient_name"),
                "recipient_document": structured_payload.get("recipient_document"),
                "grouped_document_ids": [item.id for item in grouped_documents],
            },
            "metadata_json": {
                "generate_target": "entry" if settlement_state == "settled" else "schedule",
                "document_parser": anchor_document.document_type,
                "parser_mode": anchor_document.parser_status,
                "document_group_key": anchor_document.document_group_key,
                "grouped_document_ids": [item.id for item in grouped_documents],
                "related_document_count": len(grouped_documents),
            },
        }
        record_kwargs = FinancialAutomationService._apply_auto_suggestions_to_record_kwargs(
            company_id=company_id,
            source_document=anchor_document,
            record_kwargs=record_kwargs,
        )
        record_kwargs = FinancialAutomationService._apply_duplicate_metadata_to_record_kwargs(
            company_id=company_id,
            batch_id=batch_id,
            source_document=anchor_document,
            record_kwargs=record_kwargs,
        )
        return record_kwargs

    @staticmethod
    def _append_history(
        *,
        company_id: int,
        record_id: int,
        action_type: str,
        performed_by_user_id: Optional[int],
        payload_before_json: Optional[Dict[str, Any]] = None,
        payload_after_json: Optional[Dict[str, Any]] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> None:
        history_data = FinancialAutomationHistoryCreateInput(
            company_id=company_id,
            record_id=record_id,
            action_type=action_type,
            performed_by_user_id=performed_by_user_id,
            payload_before_json=payload_before_json or {},
            payload_after_json=payload_after_json or {},
            metadata_json=metadata_json or {},
        )
        db.session.add(FinancialAutomationHistory(**history_data.model_dump()))

    @staticmethod
    def _validate_catalog_links(
        *,
        company_id: int,
        bank_account_id: Optional[int],
        counterparty_id: Optional[int],
        chart_account_id: Optional[int],
        cost_center_id: Optional[int],
    ) -> Optional[str]:
        return FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            bank_account_id=bank_account_id,
            counterparty_id=counterparty_id,
            chart_account_id=chart_account_id,
            cost_center_id=cost_center_id,
        )

    @staticmethod
    def _validate_domain_link(company_id: int, domain_type: Optional[str], domain_source_id: Optional[int]) -> Optional[str]:
        if not domain_type or not domain_source_id:
            return None
        _, error = FinancialDomainEnablementService._load_source(company_id, domain_type, domain_source_id)
        return error

    @staticmethod
    def _serialize_rule(rule: FinancialAutomationRule) -> Dict[str, Any]:
        payload = rule.to_dict()
        payload["signed_template_amount"] = FinancialService.get_signed_amount(
            payload.get("template_amount"),
            payload.get("movement_nature"),
        )
        payload["display_variant"] = "negative" if payload["signed_template_amount"] < 0 else "positive"
        return payload

    @staticmethod
    def list_rules(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        rules = FinancialAutomationRule.query.filter(
            FinancialAutomationRule.company_id == company_id,
            FinancialAutomationRule.deleted_at.is_(None),
        ).order_by(FinancialAutomationRule.id.desc()).all()
        return [FinancialAutomationService._serialize_rule(rule) for rule in rules], None

    @staticmethod
    def list_executions(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        rule_id: Optional[int] = None,
        process_instance_id: Optional[int] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialAutomationExecution.query.filter(
            FinancialAutomationExecution.company_id == company_id,
        )
        if rule_id:
            query = query.filter(FinancialAutomationExecution.rule_id == rule_id)
        if process_instance_id:
            query = query.filter(FinancialAutomationExecution.process_instance_id == process_instance_id)

        rows = query.order_by(
            FinancialAutomationExecution.executed_at.desc(),
            FinancialAutomationExecution.id.desc(),
        ).limit(200).all()
        return [row.to_dict() for row in rows], None

    @staticmethod
    def create_rule(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialAutomationRuleCreateInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para regra de automação financeira: {exc}"

        scope_error = FinancialAutomationService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        validation_error = FinancialAutomationService._validate_rule_scope(
            company_id=data.company_id,
            process_id=data.process_id,
            activity_id=data.activity_id,
            bank_account_id=data.bank_account_id,
            counterparty_id=data.counterparty_id,
            chart_account_id=data.chart_account_id,
            cost_center_id=data.cost_center_id,
            routine_id=data.routine_id,
        )
        if validation_error:
            return None, validation_error

        existing = FinancialAutomationRule.query.filter(
            FinancialAutomationRule.company_id == data.company_id,
            FinancialAutomationRule.rule_code == data.rule_code,
            FinancialAutomationRule.deleted_at.is_(None),
        ).first()
        if existing:
            return None, f"Já existe regra com código {data.rule_code} para esta empresa."

        try:
            rule = FinancialAutomationRule(**data.model_dump())
            db.session.add(rule)
            db.session.commit()
            return FinancialAutomationService._serialize_rule(rule), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar regra de automação financeira")
            return None, f"Erro ao criar regra de automação financeira: {exc}"

    @staticmethod
    def update_rule(
        *,
        rule_id: int,
        company_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialAutomationRuleUpdateInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para atualização da regra: {exc}"

        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        rule = FinancialAutomationRule.query.filter(
            FinancialAutomationRule.id == rule_id,
            FinancialAutomationRule.company_id == company_id,
            FinancialAutomationRule.deleted_at.is_(None),
        ).first()
        if not rule:
            return None, "Regra de automação financeira não encontrada no escopo da empresa."

        merged = data.model_dump(exclude_unset=True)
        if "rule_code" in merged:
            if merged["rule_code"] != rule.rule_code:
                return None, "O código da regra de automação não pode ser alterado após a criação."
            merged.pop("rule_code", None)
        validation_error = FinancialAutomationService._validate_rule_scope(
            company_id=company_id,
            process_id=merged.get("process_id", rule.process_id),
            activity_id=merged.get("activity_id", rule.activity_id),
            bank_account_id=merged.get("bank_account_id", rule.bank_account_id),
            counterparty_id=merged.get("counterparty_id", rule.counterparty_id),
            chart_account_id=merged.get("chart_account_id", rule.chart_account_id),
            cost_center_id=merged.get("cost_center_id", rule.cost_center_id),
            routine_id=merged.get("routine_id", rule.routine_id),
        )
        if validation_error:
            return None, validation_error

        try:
            for key, value in merged.items():
                setattr(rule, key, value)
            db.session.commit()
            return FinancialAutomationService._serialize_rule(rule), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao atualizar regra de automação financeira %s", rule_id)
            return None, f"Erro ao atualizar regra de automação financeira: {exc}"

    @staticmethod
    def apply_rules_to_instance(
        *,
        company_id: int,
        process_instance_id: int,
        rule_id: Optional[int] = None,
        trigger_status: Optional[str] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        instance = ProcessInstance.query.filter(
            ProcessInstance.id == process_instance_id,
            ProcessInstance.company_id == company_id,
        ).first()
        if not instance:
            return None, "Instância de processo não encontrada no escopo da empresa."

        current_status = trigger_status or instance.status or "pending"
        rules = FinancialAutomationRule.query.filter(
            FinancialAutomationRule.company_id == company_id,
            FinancialAutomationRule.is_active.is_(True),
            FinancialAutomationRule.deleted_at.is_(None),
        ).all()
        if rule_id:
            rules = [rule for rule in rules if rule.id == rule_id]

        matched_rules = [
            rule
            for rule in rules
            if FinancialAutomationService._matches_rule(rule=rule, instance=instance, trigger_status=current_status)
        ]

        created_schedules: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        executions: List[Dict[str, Any]] = []

        try:
            for rule in matched_rules:
                idempotency_key = FinancialAutomationService._build_idempotency_key(
                    rule_id=rule.id,
                    process_instance_id=process_instance_id,
                    trigger_status=current_status,
                )
                previous_success = FinancialAutomationExecution.query.filter(
                    FinancialAutomationExecution.company_id == company_id,
                    FinancialAutomationExecution.rule_id == rule.id,
                    FinancialAutomationExecution.process_instance_id == process_instance_id,
                    FinancialAutomationExecution.idempotency_key == idempotency_key,
                    FinancialAutomationExecution.execution_status == "success",
                ).first()
                if previous_success:
                    skipped_payload = {
                        "rule_id": rule.id,
                        "reason": "idempotent_already_applied",
                        "execution_id": previous_success.id,
                    }
                    skipped.append(skipped_payload)
                    executions.append(
                        FinancialAutomationService._register_execution(
                            company_id=company_id,
                            rule_id=rule.id,
                            process_instance_id=process_instance_id,
                            schedule_id=previous_success.schedule_id,
                            trigger_status=current_status,
                            idempotency_key=idempotency_key,
                            execution_status="skipped",
                            payload_json=skipped_payload,
                        ).to_dict()
                    )
                    continue

                attempt_number = FinancialAutomationExecution.query.filter(
                    FinancialAutomationExecution.company_id == company_id,
                    FinancialAutomationExecution.rule_id == rule.id,
                    FinancialAutomationExecution.process_instance_id == process_instance_id,
                    FinancialAutomationExecution.idempotency_key == idempotency_key,
                ).count() + 1
                if attempt_number > FinancialAutomationService.MAX_ATTEMPTS:
                    skipped_payload = {
                        "rule_id": rule.id,
                        "reason": "max_attempts_reached",
                        "max_attempts": FinancialAutomationService.MAX_ATTEMPTS,
                    }
                    skipped.append(skipped_payload)
                    executions.append(
                        FinancialAutomationService._register_execution(
                            company_id=company_id,
                            rule_id=rule.id,
                            process_instance_id=process_instance_id,
                            schedule_id=None,
                            trigger_status=current_status,
                            idempotency_key=idempotency_key,
                            execution_status="skipped",
                            attempt_number=attempt_number,
                            payload_json=skipped_payload,
                            error_message="Número máximo de tentativas atingido.",
                        ).to_dict()
                    )
                    continue

                schedule_code = f"{rule.rule_code}-{process_instance_id}"
                existing = FinancialSchedule.query.filter(
                    FinancialSchedule.company_id == company_id,
                    FinancialSchedule.schedule_code == schedule_code,
                    FinancialSchedule.deleted_at.is_(None),
                ).first()
                if existing:
                    payload_json = {"rule_id": rule.id, "reason": "schedule_already_exists", "schedule_id": existing.id}
                    skipped.append(payload_json)
                    executions.append(
                        FinancialAutomationService._register_execution(
                            company_id=company_id,
                            rule_id=rule.id,
                            process_instance_id=process_instance_id,
                            schedule_id=existing.id,
                            trigger_status=current_status,
                            idempotency_key=idempotency_key,
                            execution_status="skipped",
                            attempt_number=attempt_number,
                            payload_json=payload_json,
                        ).to_dict()
                    )
                    continue

                payload = FinancialAutomationService._build_schedule_payload(rule=rule, instance=instance)
                schedule, error = FinancialScheduleService.create_schedule(
                    payload=payload,
                    allowed_company_ids=allowed_company_ids,
                )
                if error:
                    payload_json = {"rule_id": rule.id, "reason": error, "schedule_code": payload["schedule_code"]}
                    skipped.append(payload_json)
                    executions.append(
                        FinancialAutomationService._register_execution(
                            company_id=company_id,
                            rule_id=rule.id,
                            process_instance_id=process_instance_id,
                            schedule_id=None,
                            trigger_status=current_status,
                            idempotency_key=idempotency_key,
                            execution_status="error",
                            attempt_number=attempt_number,
                            payload_json=payload_json,
                            error_message=error,
                        ).to_dict()
                    )
                    continue

                persisted = FinancialSchedule.query.filter(
                    FinancialSchedule.company_id == company_id,
                    FinancialSchedule.schedule_code == payload["schedule_code"],
                    FinancialSchedule.deleted_at.is_(None),
                ).first()
                rule.last_execution_at = datetime.utcnow()
                if persisted:
                    rule.last_generated_schedule_id = persisted.id
                executions.append(
                    FinancialAutomationService._register_execution(
                        company_id=company_id,
                        rule_id=rule.id,
                        process_instance_id=process_instance_id,
                        schedule_id=persisted.id if persisted else None,
                        trigger_status=current_status,
                        idempotency_key=idempotency_key,
                        execution_status="success",
                        attempt_number=attempt_number,
                        payload_json={
                            "rule_id": rule.id,
                            "schedule_code": payload["schedule_code"],
                            "created_schedule_id": persisted.id if persisted else None,
                        },
                    ).to_dict()
                )
                created_schedules.append(schedule)

            db.session.commit()
            return {
                "company_id": company_id,
                "process_instance_id": process_instance_id,
                "trigger_status": current_status,
                "matched_rules": len(matched_rules),
                "created_count": len(created_schedules),
                "created_schedules": created_schedules,
                "skipped": skipped,
                "executions": executions,
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao aplicar automação financeira à instância %s", process_instance_id)
            return None, f"Erro ao aplicar automação financeira à instância: {exc}"

    @staticmethod
    def _matches_rule(*, rule: FinancialAutomationRule, instance: ProcessInstance, trigger_status: str) -> bool:
        if rule.process_id and rule.process_id != instance.process_id:
            return False
        if rule.trigger_status not in {"any", trigger_status}:
            return False
        if rule.activity_id and rule.activity_id != instance.routine_id:
            return False
        return True

    @staticmethod
    def _build_schedule_payload(*, rule: FinancialAutomationRule, instance: ProcessInstance) -> Dict[str, Any]:
        base_date = instance.due_date or date.today()
        start_date = base_date + timedelta(days=int(rule.start_offset_days or 0))
        due_date = base_date + timedelta(days=int(rule.due_offset_days or 0))
        schedule_name = FinancialAutomationService._render_template(rule.schedule_name_template, instance)
        description = FinancialAutomationService._render_template(rule.description_template, instance)
        schedule_code = f"{rule.rule_code}-{instance.id}"

        return {
            "company_id": rule.company_id,
            "schedule_code": schedule_code,
            "name": schedule_name[:120],
            "entry_type": rule.entry_type,
            "movement_nature": rule.movement_nature,
            "origin_type": rule.origin_type,
            "status": "active" if rule.auto_activate_schedule else "draft",
            "frequency": rule.frequency,
            "interval_value": rule.interval_value,
            "start_date": start_date,
            "first_due_date": due_date,
            "next_due_date": due_date,
            "description": description[:255],
            "memo": instance.description,
            "document_number_prefix": instance.instance_code or rule.rule_code,
            "template_amount": rule.template_amount,
            "currency_code": rule.currency_code,
            "auto_post": rule.auto_post,
            "generate_advance_days": rule.generate_advance_days,
            "bank_account_id": rule.bank_account_id,
            "counterparty_id": rule.counterparty_id,
            "chart_account_id": rule.chart_account_id,
            "cost_center_id": rule.cost_center_id,
            "activity_id": rule.activity_id or instance.routine_id,
            "process_instance_id": instance.id,
            "routine_id": rule.routine_id or instance.routine_id,
            "notes": rule.notes,
            "metadata_json": {
                **(rule.metadata_json or {}),
                "financial_automation_rule_id": rule.id,
                "generated_from_process_instance": instance.id,
                "process_id": instance.process_id,
                "instance_status": instance.status,
            },
        }

    @staticmethod
    def _render_template(template: str, instance: ProcessInstance) -> str:
        values = {
            "instance_id": str(instance.id),
            "instance_code": instance.instance_code or f"PI-{instance.id}",
            "instance_title": instance.title or "",
            "process_id": str(instance.process_id),
            "status": instance.status or "",
            "due_date": instance.due_date.isoformat() if instance.due_date else "",
        }

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return values.get(key, "")

        return re.sub(r"\{([a-z_]+)\}", replace, template or "")

    @staticmethod
    def _build_idempotency_key(*, rule_id: int, process_instance_id: int, trigger_status: str) -> str:
        return f"rule:{rule_id}|instance:{process_instance_id}|status:{trigger_status}"

    @staticmethod
    def _register_execution(
        *,
        company_id: int,
        rule_id: int,
        process_instance_id: int,
        schedule_id: Optional[int],
        trigger_status: str,
        idempotency_key: str,
        execution_status: str,
        payload_json: Dict[str, Any],
        attempt_number: int = 1,
        error_message: Optional[str] = None,
    ) -> FinancialAutomationExecution:
        execution = FinancialAutomationExecution(
            company_id=company_id,
            rule_id=rule_id,
            process_instance_id=process_instance_id,
            schedule_id=schedule_id,
            trigger_status=trigger_status,
            idempotency_key=idempotency_key,
            execution_status=execution_status,
            attempt_number=attempt_number,
            error_message=error_message,
            payload_json=payload_json,
        )
        db.session.add(execution)
        return execution

    @staticmethod
    def _validate_rule_scope(
        *,
        company_id: int,
        process_id: Optional[int],
        activity_id: Optional[int],
        bank_account_id: Optional[int],
        counterparty_id: Optional[int],
        chart_account_id: Optional[int],
        cost_center_id: Optional[int],
        routine_id: Optional[int],
    ) -> Optional[str]:
        if not process_id and not activity_id:
            return "A regra precisa de process_id ou activity_id."

        if process_id:
            process = Process.query.filter(Process.id == process_id, Process.company_id == company_id).first()
            if not process:
                return "Processo não encontrado no escopo da empresa."

        if activity_id:
            activity = ProcessRoutine.query.filter(
                ProcessRoutine.id == activity_id,
                ProcessRoutine.company_id == company_id,
            ).first()
            if not activity:
                return "Atividade de processo não encontrada no escopo da empresa."

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            bank_account_id=bank_account_id,
            counterparty_id=counterparty_id,
            chart_account_id=chart_account_id,
            cost_center_id=cost_center_id,
        )
        if reference_error:
            return reference_error

        return FinancialService._validate_operational_links(
            company_id=company_id,
            activity_id=activity_id,
            process_instance_id=None,
            routine_id=routine_id,
        )

    @staticmethod
    def list_options(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        def _ordered_items(model):
            return model.query.filter(
                model.company_id == company_id,
                model.deleted_at.is_(None),
            ).order_by(model.name.asc(), model.id.asc()).all()

        domains, domain_error = FinancialDomainEnablementService.list_items(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if domain_error:
            return None, domain_error

        items_by_type = (domains or {}).get("items_by_type") or {}
        domain_options: List[Dict[str, Any]] = []
        for domain_type, items in items_by_type.items():
            for item in items or []:
                domain_options.append(
                    {
                        "domain_type": domain_type,
                        "source_id": item.get("source_id"),
                        "label": item.get("display_label"),
                        "is_enabled": item.get("is_enabled"),
                    }
                )

        return {
            "bank_accounts": [item.to_dict() for item in _ordered_items(FinancialBankAccount)],
            "chart_accounts": [item.to_dict() for item in _ordered_items(FinancialChartAccount)],
            "cost_centers": [item.to_dict() for item in _ordered_items(FinancialCostCenter)],
            "counterparties": [item.to_dict() for item in _ordered_items(FinancialCounterparty)],
            "domain_options": domain_options,
            "status_options": ["imported", "validated", "generated", "excluded"],
            "entry_direction_options": ["payable", "receivable"],
            "settlement_state_options": ["settled", "open"],
            "generate_target_options": ["entry", "schedule"],
            "document_type_options": [
                "nfe_xml",
                "nfce_xml",
                "cte_xml",
                "danfe_pdf",
                "dacte_pdf",
                "receipt_pdf",
                "receipt_image",
                "spreadsheet",
                "ofx",
                "unknown_document",
            ],
        }, None

    @staticmethod
    def create_batch(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        raw_payload = dict(payload or {})
        raw_documents = list(raw_payload.pop("documents", []) or [])
        raw_records = list(raw_payload.pop("records", []) or [])

        try:
            batch_data = FinancialAutomationBatchCreateInput.model_validate(raw_payload)
        except Exception as exc:
            return None, f"Payload inválido para lote da Central de Automação Financeira: {exc}"

        scope_error = FinancialAutomationService._ensure_company_scope(batch_data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        try:
            batch = FinancialAutomationBatch(**batch_data.model_dump())
            db.session.add(batch)
            db.session.flush()

            created_documents: List[FinancialAutomationDocument] = []
            for raw_document in raw_documents:
                document_data = FinancialAutomationDocumentCreateInput.model_validate(
                    {
                        **dict(raw_document or {}),
                        "company_id": batch.company_id,
                        "batch_id": batch.id,
                    }
                )
                document = FinancialAutomationDocument(**document_data.model_dump())
                db.session.add(document)
                db.session.flush()
                created_documents.append(document)

            created_records: List[FinancialAutomationRecord] = []
            for raw_record in raw_records:
                record_data = FinancialAutomationRecordCreateInput.model_validate(
                    {
                        **dict(raw_record or {}),
                        "company_id": batch.company_id,
                        "batch_id": batch.id,
                    }
                )
                reference_error = FinancialAutomationService._validate_catalog_links(
                    company_id=batch.company_id,
                    bank_account_id=record_data.bank_account_id,
                    counterparty_id=record_data.counterparty_id,
                    chart_account_id=record_data.chart_account_id,
                    cost_center_id=record_data.cost_center_id,
                )
                if reference_error:
                    raise ValueError(reference_error)
                domain_error = FinancialAutomationService._validate_domain_link(
                    batch.company_id,
                    record_data.domain_type,
                    record_data.domain_source_id,
                )
                if domain_error:
                    raise ValueError(domain_error)
                record = FinancialAutomationRecord(**record_data.model_dump())
                db.session.add(record)
                db.session.flush()
                created_records.append(record)
                FinancialAutomationService._append_history(
                    company_id=batch.company_id,
                    record_id=record.id,
                    action_type="import",
                    performed_by_user_id=batch.created_by_user_id,
                    payload_after_json=record.to_dict(),
                    metadata_json={"batch_id": batch.id},
                )

            batch.status_summary_json = {
                "records_total": len(created_records),
                "documents_total": len(created_documents),
                "imported_count": len(created_records),
                "validated_count": 0,
                "generated_count": 0,
                "excluded_count": 0,
            }
            db.session.commit()
            return {
                "batch": batch.to_dict(),
                "documents": [item.to_dict() for item in created_documents],
                "records": [FinancialAutomationService._serialize_record(item) for item in created_records],
            }, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao criar lote da Central de Automação Financeira: {exc}"

    @staticmethod
    def upload_batch_files(
        *,
        company_id: int,
        origin_type: str,
        files: Sequence[Any] | None,
        upload_root: str,
        source_label: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        file_items = [item for item in (files or []) if item is not None]
        if not file_items:
            return None, "Selecione ao menos um arquivo para upload na Central."

        try:
            batch_data = FinancialAutomationBatchCreateInput.model_validate(
                {
                    "company_id": company_id,
                    "origin_type": origin_type,
                    "source_label": source_label,
                    "created_by_user_id": created_by_user_id,
                }
            )
        except Exception as exc:
            return None, f"Payload inválido para upload da Central: {exc}"

        try:
            batch = FinancialAutomationBatch(**batch_data.model_dump())
            db.session.add(batch)
            db.session.flush()

            created_documents: List[FinancialAutomationDocument] = []
            for file_storage in file_items:
                uploaded, upload_error = FinancialAccountabilityService.store_document(
                    company_id=company_id,
                    file_storage=file_storage,
                    upload_root=upload_root,
                    allowed_company_ids=allowed_company_ids,
                    storage_scope="automation",
                )
                if upload_error:
                    raise ValueError(upload_error)
                document = FinancialAutomationDocument(
                    company_id=company_id,
                    batch_id=batch.id,
                    file_name=uploaded["file_name"],
                    stored_relative_path=uploaded["stored_relative_path"],
                    original_relative_path=uploaded.get("original_relative_path"),
                    optimized_relative_path=uploaded.get("optimized_relative_path"),
                    preview_relative_path=uploaded.get("preview_relative_path"),
                    mime_type=uploaded["mime_type"],
                    file_size=uploaded["file_size"],
                    file_size_original=uploaded.get("file_size_original"),
                    file_size_optimized=uploaded.get("file_size_optimized"),
                    sha256=uploaded["sha256"],
                    document_family=uploaded.get("document_family"),
                    document_type=uploaded.get("document_type"),
                    source_kind=uploaded.get("source_kind"),
                    parser_status=uploaded.get("parser_status") or "uploaded",
                    parser_version=uploaded.get("parser_version"),
                    document_group_key=uploaded.get("document_group_key"),
                    confidence_score=uploaded.get("confidence_score"),
                    extracted_text=uploaded.get("extracted_text"),
                    preview_payload_json={
                        "public_url": uploaded.get("public_url"),
                        "original_public_url": uploaded.get("original_public_url"),
                        "optimized_public_url": uploaded.get("optimized_public_url"),
                        "preview_public_url": uploaded.get("preview_public_url"),
                        "extracted_preview": uploaded.get("extracted_preview"),
                        "extraction_method": uploaded.get("extraction_method"),
                        "extension": uploaded.get("extension"),
                        "document_type": uploaded.get("document_type"),
                    },
                    structured_payload_json=uploaded.get("structured_payload_json") or {},
                    metadata_json={
                        **(uploaded.get("metadata_json") or {}),
                        "upload_origin_type": origin_type,
                    },
                )
                db.session.add(document)
                db.session.flush()
                created_documents.append(document)

            batch.status_summary_json = {
                "records_total": 0,
                "documents_total": len(created_documents),
                "imported_count": 0,
                "validated_count": 0,
                "generated_count": 0,
                "excluded_count": 0,
            }
            db.session.commit()
            return {
                "batch": batch.to_dict(),
                "documents": [item.to_dict() for item in created_documents],
                "records": [],
            }, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao fazer upload de arquivos da Central: {exc}"

    @staticmethod
    def _load_batch_for_company(company_id: int, batch_id: int) -> Optional[FinancialAutomationBatch]:
        return FinancialAutomationBatch.query.filter(
            FinancialAutomationBatch.id == batch_id,
            FinancialAutomationBatch.company_id == company_id,
            FinancialAutomationBatch.deleted_at.is_(None),
        ).first()

    @staticmethod
    def _infer_document_source_type(batch: FinancialAutomationBatch, document: FinancialAutomationDocument) -> str:
        if document.document_type in {"nfe_xml", "nfce_xml", "cte_xml"}:
            return "xml"
        if document.document_type in {"danfe_pdf", "dacte_pdf", "receipt_pdf", "receipt_image", "unknown_document"}:
            return document.document_type
        if document.source_kind == "spreadsheet":
            extension = Path(document.file_name or "").suffix.lower()
            if extension == ".csv":
                return "csv"
            if extension in {".xlsx", ".xls"}:
                return "xlsx"
        if document.source_kind == "ofx":
            return "ofx"
        extension = Path(document.file_name or "").suffix.lower()
        if extension == ".csv":
            return "csv"
        if extension in {".xlsx", ".xls"}:
            return "xlsx"
        if extension == ".ofx":
            return "ofx"
        return str(batch.origin_type or "document").lower()

    @staticmethod
    def _read_document_bytes(upload_root: str, document: FinancialAutomationDocument) -> bytes:
        relative_path = document.original_relative_path or document.stored_relative_path
        if not relative_path:
            return b""
        target_path = Path(upload_root) / Path(relative_path)
        return target_path.read_bytes() if target_path.exists() else b""

    @staticmethod
    def _hydrate_document_from_file(document: FinancialAutomationDocument, file_bytes: bytes) -> None:
        if document.document_type and document.structured_payload_json:
            return
        extracted_text = document.extracted_text
        preview_payload = dict(document.preview_payload_json or {})
        extraction_method = preview_payload.get("extraction_method")
        if extracted_text is None or not extraction_method:
            extracted_text, extraction_method = FinancialAccountabilityService._extract_text(
                file_name=document.file_name or "",
                file_bytes=file_bytes,
            )
            document.extracted_text = extracted_text
        profile = FinancialAccountabilityService._detect_document_profile(
            file_name=document.file_name or "",
            file_bytes=file_bytes,
            extracted_text=extracted_text or "",
            extension=Path(document.file_name or "").suffix.lower(),
        )
        document.document_family = profile.get("document_family")
        document.document_type = profile.get("document_type")
        document.source_kind = profile.get("source_kind")
        document.parser_status = profile.get("parser_status") or document.parser_status
        document.parser_version = profile.get("parser_version") or document.parser_version or "v2"
        document.document_group_key = profile.get("document_group_key")
        document.confidence_score = profile.get("confidence_score")
        document.structured_payload_json = profile.get("structured_payload_json") or {}
        preview_payload.update(
            {
                "document_type": document.document_type,
                "document_family": document.document_family,
                "extraction_method": extraction_method,
            }
        )
        document.preview_payload_json = preview_payload

    @staticmethod
    def _guess_entry_direction(movement_nature: Optional[str]) -> str:
        return "receivable" if str(movement_nature or "").lower() == "credit" else "payable"

    @staticmethod
    def _guess_settlement_state(source_type: str, normalized_payload: Dict[str, Any]) -> str:
        source = str(source_type or "").lower()
        if source == "ofx":
            return "settled"
        if normalized_payload.get("occurred_on") and not normalized_payload.get("due_date"):
            return "settled"
        return "open"

    @staticmethod
    def _build_record_kwargs_from_import_row(
        *,
        company_id: int,
        batch_id: int,
        source_document_id: int,
        row_number: int,
        row_input: Any,
        source_type: str,
    ) -> Dict[str, Any]:
        normalized_payload = dict(getattr(row_input, "normalized_payload", {}) or {})
        movement_nature = normalized_payload.get("movement_nature")
        amount = getattr(row_input, "amount", None) or Decimal("0")
        competence_date = getattr(row_input, "occurred_on", None) or getattr(row_input, "due_date", None)
        due_date = getattr(row_input, "due_date", None) or competence_date
        settlement_state = FinancialAutomationService._guess_settlement_state(source_type, normalized_payload)
        record_kwargs = {
            "company_id": company_id,
            "batch_id": batch_id,
            "source_document_id": source_document_id,
            "status": "imported",
            "entry_direction": FinancialAutomationService._guess_entry_direction(movement_nature),
            "settlement_state": settlement_state,
            "description": str(getattr(row_input, "description", None) or f"Documento importado {source_document_id}")[:255],
            "amount": amount,
            "competence_date": competence_date,
            "due_date": due_date,
            "confidence_score": Decimal("0.78"),
            "validation_notes": None if getattr(row_input, "processing_status", None) != "rejected" else getattr(row_input, "error_message", None),
            "normalized_payload_json": {
                **normalized_payload,
                "row_number": row_number,
                "source_type": source_type,
            },
            "metadata_json": {
                "generate_target": "entry" if settlement_state == "settled" else "schedule",
                "document_parser": source_type,
                "parser_mode": "structured_import",
                "bank_reference": getattr(row_input, "bank_reference", None),
                "document_number": getattr(row_input, "document_number", None),
                "counterparty_name": getattr(row_input, "counterparty_name", None),
            },
        }
        source_document = FinancialAutomationDocument.query.filter(
            FinancialAutomationDocument.id == source_document_id,
            FinancialAutomationDocument.company_id == company_id,
        ).first()
        record_kwargs = FinancialAutomationService._apply_auto_suggestions_to_record_kwargs(
            company_id=company_id,
            source_document=source_document,
            record_kwargs=record_kwargs,
        )
        record_kwargs = FinancialAutomationService._apply_duplicate_metadata_to_record_kwargs(
            company_id=company_id,
            batch_id=batch_id,
            source_document=source_document,
            record_kwargs=record_kwargs,
        )
        return record_kwargs

    @staticmethod
    def _extract_decimal_from_text(text: str) -> Optional[Decimal]:
        if not text:
            return None
        match = re.search(r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+\.\d{2})", text)
        if not match:
            return None
        return FinancialImportService._parse_decimal(match.group(1))

    @staticmethod
    def _build_fallback_record_kwargs_from_document(
        *,
        company_id: int,
        batch_id: int,
        document: FinancialAutomationDocument,
    ) -> Dict[str, Any]:
        preview_payload = dict(document.preview_payload_json or {})
        extracted_text = str(document.extracted_text or "").strip()
        first_line = next((line.strip() for line in extracted_text.splitlines() if line.strip()), "") if extracted_text else ""
        description = first_line or document.file_name or f"Documento {document.id}"
        amount = FinancialAutomationService._extract_decimal_from_text(extracted_text) or Decimal("0")
        record_kwargs = {
            "company_id": company_id,
            "batch_id": batch_id,
            "source_document_id": document.id,
            "status": "imported",
            "entry_direction": "payable",
            "settlement_state": "open",
            "description": description[:255],
            "amount": amount,
            "competence_date": None,
            "due_date": None,
            "confidence_score": Decimal("0.35"),
            "validation_notes": "Documento sem estrutura tabular detectada; revisão humana necessária.",
            "normalized_payload_json": {
                "source_type": "document",
                "extracted_preview": preview_payload.get("extracted_preview"),
                "extraction_method": preview_payload.get("extraction_method"),
            },
            "metadata_json": {
                "generate_target": "schedule",
                "document_parser": "document_fallback",
                "parser_mode": "document_preview",
            },
        }
        record_kwargs = FinancialAutomationService._apply_auto_suggestions_to_record_kwargs(
            company_id=company_id,
            source_document=document,
            record_kwargs=record_kwargs,
        )
        record_kwargs = FinancialAutomationService._apply_duplicate_metadata_to_record_kwargs(
            company_id=company_id,
            batch_id=batch_id,
            source_document=document,
            record_kwargs=record_kwargs,
        )
        return record_kwargs

    @staticmethod
    def parse_batch_documents(
        *,
        company_id: int,
        batch_id: int,
        upload_root: str,
        allowed_company_ids: Optional[Sequence[int]] = None,
        performed_by_user_id: Optional[int] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        batch = FinancialAutomationService._load_batch_for_company(company_id, batch_id)
        if not batch:
            return None, "Lote da Central não encontrado no escopo da empresa."

        documents = batch.documents.filter(FinancialAutomationDocument.deleted_at.is_(None)).all()
        if not documents:
            return None, "O lote não possui documentos para processar."

        created_records: List[FinancialAutomationRecord] = []
        parsed_documents = 0
        skipped_documents = 0

        try:
            document_groups: Dict[str, List[FinancialAutomationDocument]] = {}
            for document in documents:
                if document.records.filter(FinancialAutomationRecord.deleted_at.is_(None)).count() > 0:
                    skipped_documents += 1
                    continue

                source_type = FinancialAutomationService._infer_document_source_type(batch, document)
                file_bytes = FinancialAutomationService._read_document_bytes(upload_root, document)
                if file_bytes and (not document.document_type or not document.structured_payload_json):
                    FinancialAutomationService._hydrate_document_from_file(document, file_bytes)
                    source_type = FinancialAutomationService._infer_document_source_type(batch, document)
                record_kwargs_list: List[Dict[str, Any]] = []

                if source_type in {"csv", "xlsx", "ofx"} and file_bytes:
                    parsed_rows = FinancialImportService._parse_source_rows(source_type, file_bytes)
                    for row_number, raw_row in enumerate(parsed_rows, start=1):
                        row_input = FinancialImportService._normalize_row(row_number, raw_row)
                        record_kwargs_list.append(
                            FinancialAutomationService._build_record_kwargs_from_import_row(
                                company_id=company_id,
                                batch_id=batch.id,
                                source_document_id=document.id,
                                row_number=row_number,
                                row_input=row_input,
                                source_type=source_type,
                            )
                        )

                for record_kwargs in record_kwargs_list:
                    record = FinancialAutomationRecord(**record_kwargs)
                    db.session.add(record)
                    db.session.flush()
                    created_records.append(record)
                    FinancialAutomationService._append_history(
                        company_id=company_id,
                        record_id=record.id,
                        action_type="parse_document",
                        performed_by_user_id=performed_by_user_id,
                        payload_after_json=record.to_dict(),
                        metadata_json={
                            "batch_id": batch.id,
                            "source_document_id": document.id,
                            "parser": record_kwargs.get("metadata_json", {}).get("document_parser"),
                        },
                    )
                if record_kwargs_list:
                    parsed_documents += 1
                    continue

                group_key = document.document_group_key or f"document:{document.id}"
                document_groups.setdefault(group_key, []).append(document)

            existing_group_keys = {
                item.document_group_key
                for item in batch.records.filter(FinancialAutomationRecord.deleted_at.is_(None)).all()
                if getattr(item, "document_group_key", None)
            }
            for group_key, grouped_docs in document_groups.items():
                if group_key in existing_group_keys:
                    skipped_documents += len(grouped_docs)
                    continue
                anchor_document = sorted(
                    grouped_docs,
                    key=lambda item: (
                        FinancialAutomationService._document_priority(item.document_type),
                        float(item.confidence_score or 0),
                        -int(item.id or 0),
                    ),
                    reverse=True,
                )[0]
                record_kwargs = FinancialAutomationService._build_record_kwargs_from_document_group(
                    company_id=company_id,
                    batch_id=batch.id,
                    anchor_document=anchor_document,
                    grouped_documents=grouped_docs,
                )
                record = FinancialAutomationRecord(**record_kwargs)
                db.session.add(record)
                db.session.flush()
                created_records.append(record)
                FinancialAutomationService._append_history(
                    company_id=company_id,
                    record_id=record.id,
                    action_type="parse_document_group",
                    performed_by_user_id=performed_by_user_id,
                    payload_after_json=record.to_dict(),
                    metadata_json={
                        "batch_id": batch.id,
                        "source_document_id": anchor_document.id,
                        "group_key": group_key,
                        "grouped_document_ids": [item.id for item in grouped_docs],
                        "parser": anchor_document.document_type,
                    },
                )
                parsed_documents += len(grouped_docs)

            FinancialAutomationService._refresh_batch_summary(batch)
            db.session.commit()
            return {
                "batch": batch.to_dict(),
                "records": [FinancialAutomationService._serialize_record(item) for item in created_records],
                "parsed_documents": parsed_documents,
                "skipped_documents": skipped_documents,
                "count": len(created_records),
            }, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao processar documentos do lote da Central: {exc}"

    @staticmethod
    def list_records(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        status: Optional[str] = None,
        origin_type: Optional[str] = None,
        document_type: Optional[str] = None,
        batch_id: Optional[int] = None,
        competence_date_from: Optional[str] = None,
        competence_date_to: Optional[str] = None,
        due_date_from: Optional[str] = None,
        due_date_to: Optional[str] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialAutomationRecord.query.join(
            FinancialAutomationBatch,
            FinancialAutomationBatch.id == FinancialAutomationRecord.batch_id,
        ).filter(
            FinancialAutomationRecord.company_id == company_id,
            FinancialAutomationRecord.deleted_at.is_(None),
            FinancialAutomationBatch.deleted_at.is_(None),
        )

        if status:
            query = query.filter(FinancialAutomationRecord.status == status)
        if origin_type:
            query = query.filter(FinancialAutomationBatch.origin_type == origin_type)
        if document_type:
            query = query.filter(FinancialAutomationRecord.document_type == document_type)
        if batch_id:
            query = query.filter(FinancialAutomationRecord.batch_id == batch_id)
        if competence_date_from:
            query = query.filter(FinancialAutomationRecord.competence_date >= competence_date_from)
        if competence_date_to:
            query = query.filter(FinancialAutomationRecord.competence_date <= competence_date_to)
        if due_date_from:
            query = query.filter(FinancialAutomationRecord.due_date >= due_date_from)
        if due_date_to:
            query = query.filter(FinancialAutomationRecord.due_date <= due_date_to)

        items = query.order_by(FinancialAutomationRecord.created_at.desc(), FinancialAutomationRecord.id.desc()).all()
        return [FinancialAutomationService._serialize_record(item) for item in items], None

    @staticmethod
    def get_record(
        *,
        company_id: int,
        record_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        item = FinancialAutomationRecord.query.filter(
            FinancialAutomationRecord.id == record_id,
            FinancialAutomationRecord.company_id == company_id,
            FinancialAutomationRecord.deleted_at.is_(None),
        ).first()
        if not item:
            return None, "Registro da Central de Automação Financeira não encontrado no escopo da empresa."
        payload = FinancialAutomationService._serialize_record(item)
        payload["history"] = [
            history.to_dict()
            for history in item.history_items.order_by(FinancialAutomationHistory.created_at.desc()).all()
        ]
        return payload, None

    @staticmethod
    def update_record(
        *,
        company_id: int,
        record_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
        performed_by_user_id: Optional[int] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        item = FinancialAutomationRecord.query.filter(
            FinancialAutomationRecord.id == record_id,
            FinancialAutomationRecord.company_id == company_id,
            FinancialAutomationRecord.deleted_at.is_(None),
        ).first()
        if not item:
            return None, "Registro da Central de Automação Financeira não encontrado no escopo da empresa."
        if item.status == "generated":
            return None, "Registro já gerado não pode ser editado por este fluxo."

        try:
            data = FinancialAutomationRecordUpdateInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para atualização do registro: {exc}"

        merged = data.model_dump(exclude_unset=True)
        if merged.get("status") == "generated":
            return None, "Status Gerada só pode ser definido pelo processamento oficial da Central."
        reference_error = FinancialAutomationService._validate_catalog_links(
            company_id=company_id,
            bank_account_id=merged.get("bank_account_id", item.bank_account_id),
            counterparty_id=merged.get("counterparty_id", item.counterparty_id),
            chart_account_id=merged.get("chart_account_id", item.chart_account_id),
            cost_center_id=merged.get("cost_center_id", item.cost_center_id),
        )
        if reference_error:
            return None, reference_error
        domain_error = FinancialAutomationService._validate_domain_link(
            company_id,
            merged.get("domain_type", item.domain_type),
            merged.get("domain_source_id", item.domain_source_id),
        )
        if domain_error:
            return None, domain_error

        before = item.to_dict()
        try:
            for key, value in merged.items():
                setattr(item, key, value)
            if item.status == "validated":
                item.validated_by_user_id = performed_by_user_id
                item.validated_at = datetime.utcnow()
            FinancialAutomationService._refresh_batch_summary(item.batch)
            item.updated_at = datetime.utcnow()
            FinancialAutomationService._append_history(
                company_id=company_id,
                record_id=item.id,
                action_type="update",
                performed_by_user_id=performed_by_user_id,
                payload_before_json=before,
                payload_after_json=item.to_dict(),
            )
            db.session.commit()
            return FinancialAutomationService._serialize_record(item), None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao atualizar registro da Central: {exc}"

    @staticmethod
    def bulk_update_status(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
        performed_by_user_id: Optional[int] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialAutomationBulkStatusInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para atualização em lote: {exc}"

        scope_error = FinancialAutomationService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        items = FinancialAutomationRecord.query.filter(
            FinancialAutomationRecord.company_id == data.company_id,
            FinancialAutomationRecord.id.in_(data.record_ids),
            FinancialAutomationRecord.deleted_at.is_(None),
        ).all()
        if len(items) != len(set(data.record_ids)):
            return None, "Um ou mais registros não foram encontrados no escopo da empresa."
        if data.status == "generated":
            return None, "Use a ação de geração oficial para marcar registros como Gerada."

        updated_items: List[Dict[str, Any]] = []
        try:
            for item in items:
                if item.status == "generated" and data.status != "generated":
                    return None, "Registros já gerados não podem voltar de status por este fluxo."
                before = item.to_dict()
                item.status = data.status
                if data.validation_notes is not None:
                    item.validation_notes = data.validation_notes
                if data.status == "validated":
                    item.validated_by_user_id = performed_by_user_id
                    item.validated_at = datetime.utcnow()
                FinancialAutomationService._append_history(
                    company_id=data.company_id,
                    record_id=item.id,
                    action_type="bulk_status",
                    performed_by_user_id=performed_by_user_id,
                    payload_before_json=before,
                    payload_after_json=item.to_dict(),
                    metadata_json={"new_status": data.status},
                )
                updated_items.append(FinancialAutomationService._serialize_record(item))
            for batch in {item.batch for item in items if getattr(item, "batch", None)}:
                FinancialAutomationService._refresh_batch_summary(batch)
            db.session.commit()
            return {"items": updated_items, "count": len(updated_items)}, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao atualizar registros em lote: {exc}"

    @staticmethod
    def get_document(
        *,
        company_id: int,
        document_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialAutomationService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        item = FinancialAutomationDocument.query.filter(
            FinancialAutomationDocument.id == document_id,
            FinancialAutomationDocument.company_id == company_id,
            FinancialAutomationDocument.deleted_at.is_(None),
        ).first()
        if not item:
            return None, "Documento de origem não encontrado no escopo da empresa."
        payload = item.to_dict()
        payload["public_url"] = f"/uploads/{item.stored_relative_path}" if item.stored_relative_path else None
        if item.original_relative_path:
            payload["original_public_url"] = f"/uploads/{item.original_relative_path}"
        if item.optimized_relative_path:
            payload["optimized_public_url"] = f"/uploads/{item.optimized_relative_path}"
        if item.preview_relative_path:
            payload["preview_public_url"] = f"/uploads/{item.preview_relative_path}"
        if item.document_group_key:
            related = FinancialAutomationDocument.query.filter(
                FinancialAutomationDocument.company_id == company_id,
                FinancialAutomationDocument.batch_id == item.batch_id,
                FinancialAutomationDocument.document_group_key == item.document_group_key,
                FinancialAutomationDocument.deleted_at.is_(None),
            ).order_by(FinancialAutomationDocument.id.asc()).all()
            payload["related_documents"] = [doc.to_dict() for doc in related]
        else:
            payload["related_documents"] = [item.to_dict()]
        return payload, None

    @staticmethod
    def _generate_entry_code(company_id: int) -> str:
        return f"FAC-{company_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    def _build_generation_metadata(record: FinancialAutomationRecord) -> Dict[str, Any]:
        metadata = dict(record.metadata_json or {})
        metadata["financial_automation_record_id"] = record.id
        metadata["financial_automation_batch_id"] = record.batch_id
        return metadata

    @staticmethod
    def _generate_entry_from_record(
        record: FinancialAutomationRecord,
        generated_by_user_id: Optional[int],
        allowed_company_ids: Optional[Sequence[int]],
    ) -> Tuple[Optional[int], Optional[str]]:
        payload = {
            "company_id": record.company_id,
            "entry_code": FinancialAutomationService._generate_entry_code(record.company_id),
            "entry_type": record.entry_direction,
            "movement_nature": "credit" if record.entry_direction == "receivable" else "debit",
            "origin_type": "api",
            "status": "posted",
            "review_status": "approved",
            "description": record.description or "Registro gerado pela Central de Automação Financeira",
            "memo": record.validation_notes,
            "external_reference": f"financial_automation:{record.id}",
            "origin_reference": f"financial_automation_batch:{record.batch_id}",
            "competence_date": record.competence_date or datetime.utcnow().date(),
            "due_date": record.due_date,
            "occurred_on": record.competence_date or datetime.utcnow().date(),
            "original_amount": Decimal(str(record.amount or 0)),
            "bank_account_id": record.bank_account_id,
            "counterparty_id": record.counterparty_id,
            "chart_account_id": record.chart_account_id,
            "cost_center_id": record.cost_center_id,
            "created_by_user_id": generated_by_user_id,
            "approved_by_user_id": generated_by_user_id,
            "metadata_json": FinancialAutomationService._build_generation_metadata(record),
        }
        entry, error = FinancialService.create_entry(payload=payload, allowed_company_ids=allowed_company_ids)
        if error:
            return None, error
        if record.settlement_state == "settled":
            settlement_payload = {
                "company_id": record.company_id,
                "financial_entry_id": entry.id,
                "settlement_type": "manual",
                "settlement_status": "posted",
                "settlement_date": record.due_date or record.competence_date or datetime.utcnow().date(),
                "bank_account_id": record.bank_account_id,
                "principal_amount": Decimal(str(record.amount or 0)),
                "interest_amount": Decimal("0"),
                "penalty_amount": Decimal("0"),
                "discount_amount": Decimal("0"),
                "fee_amount": Decimal("0"),
                "other_adjustments_amount": Decimal("0"),
                "net_amount": Decimal(str(record.amount or 0)),
                "reconciliation_status": "pending",
                "notes": f"Liquidação criada pela Central de Automação Financeira (record {record.id}).",
                "metadata_json": FinancialAutomationService._build_generation_metadata(record),
            }
            _, settlement_error = FinancialService.create_settlement(
                payload=settlement_payload,
                allowed_company_ids=allowed_company_ids,
            )
            if settlement_error:
                return None, settlement_error
        return entry.id, None

    @staticmethod
    def _generate_schedule_from_record(
        record: FinancialAutomationRecord,
        generated_by_user_id: Optional[int],
        allowed_company_ids: Optional[Sequence[int]],
    ) -> Tuple[Optional[int], Optional[str]]:
        base_date = record.competence_date or record.due_date or datetime.utcnow().date()
        payload = {
            "company_id": record.company_id,
            "name": (record.description or "Registro da Central")[:120],
            "entry_type": record.entry_direction,
            "movement_nature": "credit" if record.entry_direction == "receivable" else "debit",
            "origin_type": "api",
            "status": "active",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": base_date,
            "first_due_date": record.due_date or base_date,
            "next_due_date": record.due_date or base_date,
            "description": (record.description or "Agendamento gerado pela Central de Automação Financeira")[:255],
            "template_amount": Decimal(str(record.amount or 0)),
            "bank_account_id": record.bank_account_id,
            "counterparty_id": record.counterparty_id,
            "chart_account_id": record.chart_account_id,
            "cost_center_id": record.cost_center_id,
            "created_by_user_id": generated_by_user_id,
            "notes": record.validation_notes,
            "metadata_json": FinancialAutomationService._build_generation_metadata(record),
        }
        result, error = FinancialScheduleService.create_schedule(
            payload=payload,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error
        return int(result["id"]), None

    @staticmethod
    def generate_records(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialAutomationGenerateInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para geração: {exc}"

        scope_error = FinancialAutomationService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialAutomationRecord.query.filter(
            FinancialAutomationRecord.company_id == data.company_id,
            FinancialAutomationRecord.deleted_at.is_(None),
            FinancialAutomationRecord.status == data.only_status,
        )
        if data.record_ids:
            query = query.filter(FinancialAutomationRecord.id.in_(data.record_ids))
        items = query.order_by(FinancialAutomationRecord.id.asc()).all()
        if not items:
            return {"items": [], "count": 0}, None

        duplicate_blockers = [
            str(item.id)
            for item in items
            if str(((item.metadata_json or {}).get("dedupe") or {}).get("status") or "").strip().lower() == "duplicate"
        ]
        if duplicate_blockers:
            return None, (
                "Há registros com duplicidade exata detectada por chave fiscal/hash documental. "
                f"Revise antes de gerar: {', '.join(duplicate_blockers)}."
            )

        generated_items: List[Dict[str, Any]] = []
        try:
            for item in items:
                before = item.to_dict()
                generate_target = (
                    (item.metadata_json or {}).get("generate_target")
                    or (item.normalized_payload_json or {}).get("generate_target")
                    or ("entry" if item.settlement_state == "settled" else "schedule")
                )
                if generate_target == "entry":
                    entry_id, error = FinancialAutomationService._generate_entry_from_record(
                        item,
                        data.generated_by_user_id,
                        allowed_company_ids,
                    )
                    if error:
                        return None, error
                    item.generated_financial_entry_id = entry_id
                else:
                    schedule_id, error = FinancialAutomationService._generate_schedule_from_record(
                        item,
                        data.generated_by_user_id,
                        allowed_company_ids,
                    )
                    if error:
                        return None, error
                    item.generated_financial_schedule_id = schedule_id
                item.status = "generated"
                item.generated_by_user_id = data.generated_by_user_id
                item.generated_at = datetime.utcnow()
                FinancialAutomationService._append_history(
                    company_id=data.company_id,
                    record_id=item.id,
                    action_type="generate",
                    performed_by_user_id=data.generated_by_user_id,
                    payload_before_json=before,
                    payload_after_json=item.to_dict(),
                    metadata_json={"generate_target": generate_target},
                )
                generated_items.append(FinancialAutomationService._serialize_record(item))
            for batch in {item.batch for item in items if getattr(item, "batch", None)}:
                FinancialAutomationService._refresh_batch_summary(batch)
            db.session.commit()
            return {"items": generated_items, "count": len(generated_items)}, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao gerar registros da Central: {exc}"
