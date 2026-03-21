from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import (
    FinancialClassificationMemory,
    FinancialClassificationSuggestion,
    FinancialImportBatch,
    FinancialImportRow,
)
from schemas.financial import FinancialClassificationMemoryUpdateInput
from services.financial_catalog_service import FinancialCatalogService
from services.financial_service import FinancialService


logger = logging.getLogger(__name__)


class FinancialClassificationHybridService:
    """Base persistente do modelo híbrido: memórias por cliente e sugestões ranqueadas."""

    HIGH_CONFIDENCE_THRESHOLD = Decimal("0.90")
    MEDIUM_CONFIDENCE_THRESHOLD = Decimal("0.75")

    @staticmethod
    def list_memories(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        items = FinancialClassificationMemory.query.filter(
            FinancialClassificationMemory.company_id == company_id,
            FinancialClassificationMemory.deleted_at.is_(None),
        ).order_by(
            FinancialClassificationMemory.times_confirmed.desc(),
            FinancialClassificationMemory.id.desc(),
        ).all()
        return [item.to_dict() for item in items], None

    @staticmethod
    def update_memory(
        *,
        memory_id: int,
        company_id: int,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        try:
            data = FinancialClassificationMemoryUpdateInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para atualização da memória: {str(exc)}"

        memory = FinancialClassificationMemory.query.filter(
            FinancialClassificationMemory.id == memory_id,
            FinancialClassificationMemory.company_id == company_id,
            FinancialClassificationMemory.deleted_at.is_(None),
        ).first()
        if not memory:
            return None, "Memória de classificação não encontrada no escopo da empresa."

        merged_payload = data.model_dump(exclude_unset=True)
        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            chart_account_id=merged_payload.get("chart_account_id", memory.chart_account_id),
            cost_center_id=merged_payload.get("cost_center_id", memory.cost_center_id),
        )
        if reference_error:
            return None, reference_error

        try:
            for key, value in merged_payload.items():
                setattr(memory, key, value)
            db.session.commit()
            return memory.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao atualizar memória de classificação %s", memory_id)
            return None, f"Erro ao atualizar memória de classificação: {str(exc)}"

    @staticmethod
    def toggle_memory(
        *,
        memory_id: int,
        company_id: int,
        is_active: bool,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        memory = FinancialClassificationMemory.query.filter(
            FinancialClassificationMemory.id == memory_id,
            FinancialClassificationMemory.company_id == company_id,
            FinancialClassificationMemory.deleted_at.is_(None),
        ).first()
        if not memory:
            return None, "Memória de classificação não encontrada no escopo da empresa."

        try:
            memory.is_active = bool(is_active)
            db.session.commit()
            return memory.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao alterar status da memória de classificação %s", memory_id)
            return None, f"Erro ao alterar status da memória de classificação: {str(exc)}"

    @staticmethod
    def list_suggestions(
        *,
        company_id: int,
        batch_id: Optional[int] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialClassificationSuggestion.query.filter(
            FinancialClassificationSuggestion.company_id == company_id,
            FinancialClassificationSuggestion.deleted_at.is_(None),
        )
        if batch_id is not None:
            query = query.filter(FinancialClassificationSuggestion.import_batch_id == batch_id)

        items = query.order_by(
            FinancialClassificationSuggestion.import_row_id.asc(),
            FinancialClassificationSuggestion.rank_position.asc(),
        ).all()
        return [item.to_dict() for item in items], None

    @staticmethod
    def _build_memory_payload_from_row(row: FinancialImportRow) -> Dict:
        normalized = row.normalized_payload or {}
        amount = Decimal(row.amount or 0)
        delta = Decimal("0.10") * amount if amount else Decimal("0")
        return {
            "supplier_name": row.counterparty_name,
            "description_pattern": row.description,
            "amount_range_min": (amount - delta) if amount else None,
            "amount_range_max": (amount + delta) if amount else None,
            "entry_type": normalized.get("entry_type"),
            "movement_nature": normalized.get("movement_nature") or row.movement_nature,
            "chart_account_id": normalized.get("chart_account_id"),
            "cost_center_id": normalized.get("cost_center_id"),
            "activity_id": normalized.get("activity_id"),
            "process_instance_id": normalized.get("process_instance_id"),
            "routine_id": normalized.get("routine_id"),
            "counterparty_hint": normalized.get("counterparty_hint") or row.counterparty_name,
        }

    @staticmethod
    def learn_from_confirmed_row(
        *,
        company_id: int,
        import_row_id: int,
        user_id: Optional[int] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        row = FinancialImportRow.query.filter(
            FinancialImportRow.id == import_row_id,
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.deleted_at.is_(None),
        ).first()
        if not row:
            return None, "Linha de importação não encontrada no escopo da empresa."

        payload = FinancialClassificationHybridService._build_memory_payload_from_row(row)
        if not payload.get("description_pattern") and not payload.get("supplier_name"):
            return None, "Linha sem dados suficientes para gerar memória de classificação."

        try:
            memory = FinancialClassificationMemory.query.filter(
                FinancialClassificationMemory.company_id == company_id,
                FinancialClassificationMemory.deleted_at.is_(None),
                FinancialClassificationMemory.supplier_name == payload.get("supplier_name"),
                FinancialClassificationMemory.description_pattern == payload.get("description_pattern"),
                FinancialClassificationMemory.chart_account_id == payload.get("chart_account_id"),
                FinancialClassificationMemory.cost_center_id == payload.get("cost_center_id"),
                FinancialClassificationMemory.activity_id == payload.get("activity_id"),
                FinancialClassificationMemory.process_instance_id == payload.get("process_instance_id"),
            ).first()

            if memory:
                memory.times_confirmed += 1
                memory.last_confirmed_by_user_id = user_id
                memory.last_confirmed_at = datetime.utcnow()
                memory.confidence_score = min(Decimal("1"), Decimal(memory.confidence_score or 0) + Decimal("0.05"))
            else:
                memory = FinancialClassificationMemory(
                    company_id=company_id,
                    source="user_confirmed",
                    confidence_score=Decimal("0.90"),
                    times_confirmed=1,
                    last_confirmed_by_user_id=user_id,
                    last_confirmed_at=datetime.utcnow(),
                    metadata_json={"origin_import_row_id": row.id},
                    **payload,
                )
                db.session.add(memory)

            db.session.commit()
            return memory.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao aprender memória de classificação da linha %s", import_row_id)
            return None, f"Erro ao registrar memória de classificação: {str(exc)}"

    @staticmethod
    def suggest_from_memory(
        *,
        batch_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        batch = FinancialImportBatch.query.filter(
            FinancialImportBatch.id == batch_id,
            FinancialImportBatch.company_id == company_id,
            FinancialImportBatch.deleted_at.is_(None),
        ).first()
        if not batch:
            return None, "Lote de importação não encontrado no escopo da empresa."

        rows = FinancialImportRow.query.filter(
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.import_batch_id == batch_id,
            FinancialImportRow.deleted_at.is_(None),
        ).order_by(FinancialImportRow.row_number.asc()).all()
        memories = FinancialClassificationMemory.query.filter(
            FinancialClassificationMemory.company_id == company_id,
            FinancialClassificationMemory.is_active.is_(True),
            FinancialClassificationMemory.deleted_at.is_(None),
        ).all()

        created = 0
        try:
            for row in rows:
                FinancialClassificationSuggestion.query.filter(
                    FinancialClassificationSuggestion.company_id == company_id,
                    FinancialClassificationSuggestion.import_row_id == row.id,
                    FinancialClassificationSuggestion.source_layer == "memory",
                ).delete(synchronize_session=False)

                candidates = []
                for memory in memories:
                    score = Decimal("0")
                    if memory.supplier_name and row.counterparty_name and memory.supplier_name.strip().lower() == row.counterparty_name.strip().lower():
                        score += Decimal("0.50")
                    if memory.description_pattern and row.description and memory.description_pattern.strip().lower() in row.description.strip().lower():
                        score += Decimal("0.30")
                    if memory.amount_range_min is not None and memory.amount_range_max is not None and row.amount is not None:
                        amount = Decimal(row.amount)
                        if Decimal(memory.amount_range_min) <= amount <= Decimal(memory.amount_range_max):
                            score += Decimal("0.20")
                    if score <= 0:
                        continue
                    candidates.append((score, memory))

                candidates.sort(key=lambda item: (item[0], item[1].times_confirmed), reverse=True)
                for position, (score, memory) in enumerate(candidates[:3], start=1):
                    suggestion = FinancialClassificationSuggestion(
                        company_id=company_id,
                        import_batch_id=batch_id,
                        import_row_id=row.id,
                        rank_position=position,
                        source_layer="memory",
                        score=min(score, Decimal("1")),
                        reason="memória histórica do cliente",
                        suggested_payload_json={
                            "entry_type": memory.entry_type,
                            "movement_nature": memory.movement_nature,
                            "chart_account_id": memory.chart_account_id,
                            "cost_center_id": memory.cost_center_id,
                            "activity_id": memory.activity_id,
                            "process_instance_id": memory.process_instance_id,
                            "routine_id": memory.routine_id,
                            "counterparty_hint": memory.counterparty_hint,
                            "counterparty_id": None,
                            "memory_id": memory.id,
                        },
                        metadata_json={"memory_times_confirmed": memory.times_confirmed},
                    )
                    db.session.add(suggestion)
                    created += 1

            db.session.commit()
            suggestions = FinancialClassificationSuggestion.query.filter(
                FinancialClassificationSuggestion.company_id == company_id,
                FinancialClassificationSuggestion.import_batch_id == batch_id,
                FinancialClassificationSuggestion.deleted_at.is_(None),
            ).order_by(
                FinancialClassificationSuggestion.import_row_id.asc(),
                FinancialClassificationSuggestion.rank_position.asc(),
            ).all()
            return {
                "batch_id": batch_id,
                "created_count": created,
                "items": [item.to_dict() for item in suggestions],
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao gerar sugestões por memória do lote %s", batch_id)
            return None, f"Erro ao gerar sugestões de classificação: {str(exc)}"

    @staticmethod
    def review_suggestion(
        *,
        suggestion_id: int,
        company_id: int,
        decision: str,
        user_id: Optional[int] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        if decision not in {"confirmed", "rejected", "applied"}:
            return None, "Decisão inválida para sugestão de classificação."

        suggestion = FinancialClassificationSuggestion.query.filter(
            FinancialClassificationSuggestion.id == suggestion_id,
            FinancialClassificationSuggestion.company_id == company_id,
            FinancialClassificationSuggestion.deleted_at.is_(None),
        ).first()
        if not suggestion:
            return None, "Sugestão de classificação não encontrada no escopo da empresa."

        row = FinancialImportRow.query.filter(
            FinancialImportRow.id == suggestion.import_row_id,
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.deleted_at.is_(None),
        ).first()
        if not row:
            return None, "Linha de importação vinculada à sugestão não encontrada."

        try:
            if decision in {"confirmed", "applied"}:
                normalized = dict(row.normalized_payload or {})
                normalized.update(suggestion.suggested_payload_json or {})
                normalized = FinancialCatalogService.enrich_reference_payload(
                    company_id=company_id,
                    payload=normalized,
                    counterparty_text=row.counterparty_name,
                    description_text=row.description,
                    bank_reference=row.bank_reference,
                )
                row.normalized_payload = normalized
                if row.processing_status == "staged":
                    row.processing_status = "validated"

            suggestion.status = decision
            suggestion.confirmed_by_user_id = user_id
            suggestion.confirmed_at = datetime.utcnow()

            if decision in {"confirmed", "applied"}:
                FinancialClassificationSuggestion.query.filter(
                    FinancialClassificationSuggestion.company_id == company_id,
                    FinancialClassificationSuggestion.import_row_id == suggestion.import_row_id,
                    FinancialClassificationSuggestion.id != suggestion.id,
                    FinancialClassificationSuggestion.deleted_at.is_(None),
                ).update({"status": "rejected"}, synchronize_session=False)

            db.session.commit()
            return suggestion.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao revisar sugestão de classificação %s", suggestion_id)
            return None, f"Erro ao revisar sugestão de classificação: {str(exc)}"

    @staticmethod
    def list_pending_queue(
        *,
        company_id: int,
        batch_id: Optional[int] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialImportRow.query.filter(
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.deleted_at.is_(None),
        )
        if batch_id is not None:
            query = query.filter(FinancialImportRow.import_batch_id == batch_id)

        rows = query.order_by(FinancialImportRow.import_batch_id.desc(), FinancialImportRow.row_number.asc()).all()
        items: List[Dict] = []

        for row in rows:
            suggestions = FinancialClassificationSuggestion.query.filter(
                FinancialClassificationSuggestion.company_id == company_id,
                FinancialClassificationSuggestion.import_row_id == row.id,
                FinancialClassificationSuggestion.deleted_at.is_(None),
            ).order_by(
                FinancialClassificationSuggestion.rank_position.asc(),
                FinancialClassificationSuggestion.score.desc(),
            ).all()

            top = suggestions[0] if suggestions else None
            top_score = Decimal(top.score or 0) if top and top.score is not None else Decimal("0")

            if top is None:
                queue_status = "ask_user"
                question = (
                    f"Não encontramos classificação suficiente para a linha {row.row_number}. "
                    "Qual classificação financeira deve ser aplicada?"
                )
            elif top_score >= FinancialClassificationHybridService.HIGH_CONFIDENCE_THRESHOLD:
                queue_status = "strong_suggestion"
                question = (
                    f"A linha {row.row_number} tem sugestão forte de classificação. "
                    "Deseja aplicar automaticamente ou revisar?"
                )
            elif top_score >= FinancialClassificationHybridService.MEDIUM_CONFIDENCE_THRESHOLD:
                queue_status = "confirm"
                question = (
                    f"A linha {row.row_number} possui classificação provável. "
                    "Confirma a melhor sugestão apresentada?"
                )
            else:
                queue_status = "ask_user"
                question = (
                    f"A confiança da classificação da linha {row.row_number} está baixa. "
                    "Qual opção correta devemos usar?"
                )

            items.append(
                {
                    "import_row_id": row.id,
                    "import_batch_id": row.import_batch_id,
                    "row_number": row.row_number,
                    "description": row.description,
                    "counterparty_name": row.counterparty_name,
                    "amount": float(row.amount) if row.amount is not None else None,
                    "processing_status": row.processing_status,
                    "queue_status": queue_status,
                    "question": question,
                    "top_score": float(top_score),
                    "suggestions": [item.to_dict() for item in suggestions],
                }
            )

        return items, None

    @staticmethod
    def resolve_user_answer(
        *,
        company_id: int,
        import_row_id: int,
        answer_payload: Dict,
        user_id: Optional[int] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        row = FinancialImportRow.query.filter(
            FinancialImportRow.id == import_row_id,
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.deleted_at.is_(None),
        ).first()
        if not row:
            return None, "Linha de importação não encontrada no escopo da empresa."

        suggestion_id = answer_payload.get("suggestion_id")
        remember_choice = bool(answer_payload.get("remember_choice"))

        try:
            applied_payload: Dict = {}
            reviewed_suggestion = None

            if suggestion_id:
                reviewed_suggestion, error = FinancialClassificationHybridService.review_suggestion(
                    suggestion_id=int(suggestion_id),
                    company_id=company_id,
                    decision="applied",
                    user_id=user_id,
                    allowed_company_ids=allowed_company_ids,
                )
                if error:
                    return None, error
                applied_payload = dict((reviewed_suggestion or {}).get("suggested_payload_json") or {})
            else:
                for field in [
                    "entry_type",
                    "movement_nature",
                    "chart_account_id",
                    "cost_center_id",
                    "activity_id",
                    "process_instance_id",
                    "routine_id",
                    "counterparty_hint",
                ]:
                    value = answer_payload.get(field)
                    if value in ("", None):
                        continue
                    applied_payload[field] = value

                normalized = dict(row.normalized_payload or {})
                normalized.update(applied_payload)
                normalized = FinancialCatalogService.enrich_reference_payload(
                    company_id=company_id,
                    payload=normalized,
                    counterparty_text=row.counterparty_name,
                    description_text=row.description,
                    bank_reference=row.bank_reference,
                )
                row.normalized_payload = normalized
                if row.processing_status == "staged":
                    row.processing_status = "validated"

            memory_result = None
            memory_error = None
            if remember_choice:
                from services.financial_classification_hybrid_service import FinancialClassificationHybridService as _Self
                memory_result, memory_error = _Self.learn_from_confirmed_row(
                    company_id=company_id,
                    import_row_id=import_row_id,
                    user_id=user_id,
                    allowed_company_ids=allowed_company_ids,
                )

            db.session.commit()
            return {
                "import_row_id": import_row_id,
                "applied_payload": applied_payload,
                "reviewed_suggestion": reviewed_suggestion,
                "classification_memory": memory_result,
                "classification_memory_error": memory_error,
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao resolver resposta do usuário para linha %s", import_row_id)
            return None, f"Erro ao aplicar resposta do usuário: {str(exc)}"
