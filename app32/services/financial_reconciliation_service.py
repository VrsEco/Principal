from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import (
    FinancialBankAccount,
    FinancialCounterparty,
    FinancialEntry,
    FinancialImportBatch,
    FinancialImportRow,
    FinancialReconciliationMatch,
    FinancialSchedule,
    FinancialSettlement,
)
from services.financial_catalog_service import FinancialCatalogService
from services.financial_service import FinancialService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_classification_hybrid_service import FinancialClassificationHybridService


logger = logging.getLogger(__name__)


class FinancialReconciliationService:
    """Motor determinístico inicial de matching entre staging e ledger."""

    @staticmethod
    def _decimal(value) -> Decimal:
        return Decimal(str(value or 0))

    @staticmethod
    def _normalize_ids(values: Optional[Sequence[int]]) -> List[int]:
        normalized: List[int] = []
        seen = set()
        for raw_value in values or []:
            try:
                current_id = int(raw_value or 0)
            except (TypeError, ValueError):
                current_id = 0
            if current_id > 0 and current_id not in seen:
                seen.add(current_id)
                normalized.append(current_id)
        return normalized

    @staticmethod
    def _get_remaining_principal(entry: FinancialEntry) -> Decimal:
        total_liquidated = (
            db.session.query(db.func.coalesce(db.func.sum(FinancialSettlement.principal_amount), 0))
            .filter(
                FinancialSettlement.company_id == entry.company_id,
                FinancialSettlement.financial_entry_id == entry.id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            )
            .scalar()
        ) or Decimal("0")
        return Decimal(entry.original_amount or 0) - Decimal(total_liquidated)

    @staticmethod
    def _get_settled_principal(entry: FinancialEntry) -> Decimal:
        total_liquidated = (
            db.session.query(db.func.coalesce(db.func.sum(FinancialSettlement.principal_amount), 0))
            .filter(
                FinancialSettlement.company_id == entry.company_id,
                FinancialSettlement.financial_entry_id == entry.id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            )
            .scalar()
        ) or Decimal("0")
        return Decimal(total_liquidated)

    @staticmethod
    def _create_auto_settlement_from_match(
        *,
        company_id: int,
        row: FinancialImportRow,
        entry: FinancialEntry,
        match: FinancialReconciliationMatch,
        adjustments: Optional[Dict] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        existing = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.financial_entry_id == entry.id,
            FinancialSettlement.external_reference == f"reconciliation-match:{match.id}",
            FinancialSettlement.deleted_at.is_(None),
        ).first()
        if existing:
            return existing.to_dict(), None

        adjustments = adjustments or {}
        remaining_principal = FinancialReconciliationService._get_remaining_principal(entry)
        row_amount = Decimal(row.amount or 0)
        interest_amount = Decimal(str(adjustments.get("interest_amount") or 0))
        penalty_amount = Decimal(str(adjustments.get("penalty_amount") or 0))
        discount_amount = Decimal(str(adjustments.get("discount_amount") or 0))
        fee_amount = Decimal(str(adjustments.get("fee_amount") or 0))
        other_adjustments_amount = Decimal(str(adjustments.get("other_adjustments_amount") or 0))
        principal_amount = adjustments.get("principal_amount")
        if principal_amount is None:
            principal_amount = (
                row_amount
                - interest_amount
                - penalty_amount
                - fee_amount
                - other_adjustments_amount
                + discount_amount
            )
        principal_amount = Decimal(str(principal_amount or 0))
        if principal_amount <= 0:
            return None, "Linha conciliada sem valor elegível para baixa automática."
        if remaining_principal <= 0:
            return None, "Lançamento já está totalmente baixado."
        if principal_amount > remaining_principal:
            return None, "Valor conciliado excede o saldo em aberto do lançamento."

        settlement_payload = {
            "company_id": company_id,
            "financial_entry_id": entry.id,
            "settlement_code": f"REC-{match.id}",
            "settlement_type": "automatic_rule",
            "settlement_status": "posted",
            "settlement_date": row.occurred_on or row.due_date or entry.due_date or entry.competence_date,
            "principal_amount": principal_amount,
            "interest_amount": interest_amount,
            "penalty_amount": penalty_amount,
            "discount_amount": discount_amount,
            "fee_amount": fee_amount,
            "other_adjustments_amount": other_adjustments_amount,
            "external_reference": f"reconciliation-match:{match.id}",
            "reconciliation_status": "reconciled",
            "notes": f"Baixa automática gerada pela confirmação do match {match.id}.",
            "metadata_json": {
                "import_batch_id": match.import_batch_id,
                "import_row_id": row.id,
                "reconciliation_match_id": match.id,
                "mode": "auto_settlement_from_reconciliation",
                "row_amount": float(row_amount),
            },
        }
        settlement, error = FinancialService.create_settlement(payload=settlement_payload)
        if error:
            return None, error
        FinancialService.set_entry_reconciliation_state(
            entry=entry,
            reconciled=True,
            actor_reason=f"Match {match.id} confirmado via conciliação bancária.",
        )
        return settlement.to_dict(), None

    @staticmethod
    def _update_entry_reconciliation_metadata(
        *,
        entry: FinancialEntry,
        reconciled: bool,
        actor_reason: Optional[str] = None,
    ) -> None:
        metadata = dict(entry.metadata_json or {})
        metadata.pop("reconciled", None)
        metadata["reconciliation_updated_reason"] = actor_reason
        entry.metadata_json = metadata

    @staticmethod
    def _append_reconciliation_audit_event(entry: FinancialEntry, payload: Dict) -> None:
        metadata = dict(entry.metadata_json or {})
        history = list(metadata.get("reconciliation_audit_history") or [])
        history.append(payload)
        metadata["reconciliation_audit_history"] = history[-20:]
        entry.metadata_json = metadata

    @staticmethod
    def _adjust_open_title_original_amount(
        *,
        entry: FinancialEntry,
        target_amount: Decimal,
        row: FinancialImportRow,
    ) -> Dict:
        target_amount = FinancialReconciliationService._decimal(target_amount).quantize(Decimal("0.01"))
        settled_before = FinancialReconciliationService._get_settled_principal(entry).quantize(Decimal("0.01"))
        if target_amount <= 0:
            raise ValueError("O novo valor do título precisa ser maior que zero.")
        if target_amount < settled_before:
            raise ValueError("O novo valor do título não pode ser menor que o valor já baixado.")

        previous_amount = FinancialReconciliationService._decimal(entry.original_amount or 0).quantize(Decimal("0.01"))
        entry.original_amount = target_amount
        if entry.financial_schedule_id:
            schedule = FinancialSchedule.query.filter(
                FinancialSchedule.id == entry.financial_schedule_id,
                FinancialSchedule.company_id == entry.company_id,
                FinancialSchedule.deleted_at.is_(None),
            ).first()
            if schedule:
                schedule.template_amount = target_amount
                schedule_metadata = dict(schedule.metadata_json or {})
                schedule_metadata["reconciliation_title_amount_adjustment"] = {
                    "source": "bank_reconciliation_open_title",
                    "row_id": row.id,
                    "previous_amount": float(previous_amount),
                    "new_amount": float(target_amount),
                }
                schedule.metadata_json = schedule_metadata

        FinancialReconciliationService._append_reconciliation_audit_event(
            entry,
            {
                "event": "title_original_amount_adjusted_via_reconciliation",
                "row_id": row.id,
                "import_batch_id": row.import_batch_id,
                "previous_amount": float(previous_amount),
                "new_amount": float(target_amount),
            },
        )
        return {
            "previous_amount": float(previous_amount),
            "new_amount": float(target_amount),
            "settled_before": float(settled_before),
        }

    @staticmethod
    def _resolve_row_context(company_id: int, row: FinancialImportRow) -> Dict:
        normalized = FinancialCatalogService.enrich_reference_payload(
            company_id=company_id,
            payload=row.normalized_payload or {},
            counterparty_text=row.counterparty_name,
            description_text=row.description,
            bank_reference=row.bank_reference,
        )
        return normalized

    @staticmethod
    def _counterparty_name(entry: FinancialEntry) -> str:
        if entry.counterparty_id:
            item = FinancialCounterparty.query.filter(
                FinancialCounterparty.id == entry.counterparty_id,
                FinancialCounterparty.company_id == entry.company_id,
                FinancialCounterparty.deleted_at.is_(None),
            ).first()
            if item:
                return str(item.name or item.legal_name or "").strip().lower()
        return ""

    @staticmethod
    def _bank_account_signature(entry: FinancialEntry) -> str:
        if entry.bank_account_id:
            item = FinancialBankAccount.query.filter(
                FinancialBankAccount.id == entry.bank_account_id,
                FinancialBankAccount.company_id == entry.company_id,
                FinancialBankAccount.deleted_at.is_(None),
            ).first()
            if item:
                return " ".join(
                    filter(
                        None,
                        [
                            str(item.code or "").strip().lower(),
                            str(item.name or "").strip().lower(),
                            str(item.bank_name or "").strip().lower(),
                            str(item.account_number or "").strip().lower(),
                        ],
                    )
                )
        return ""

    @staticmethod
    def _score_match(row: FinancialImportRow, entry: FinancialEntry, row_context: Optional[Dict] = None) -> Tuple[Decimal, str]:
        score = Decimal("0")
        reasons: List[str] = []
        row_context = row_context or {}

        row_amount = Decimal(row.amount or 0)
        entry_amount = Decimal(entry.original_amount or 0)
        if row_amount and entry_amount and row_amount == entry_amount:
            score += Decimal("0.55")
            reasons.append("valor exato")

        row_date = row.occurred_on or row.due_date
        entry_date = entry.occurred_on or entry.due_date or entry.competence_date
        if row_date and entry_date:
            delta_days = abs((entry_date - row_date).days)
            if delta_days == 0:
                score += Decimal("0.20")
                reasons.append("mesma data")
            elif delta_days <= 2:
                score += Decimal("0.10")
                reasons.append("data próxima")

        if row.document_number and entry.document_number and str(row.document_number).strip() == str(entry.document_number).strip():
            score += Decimal("0.15")
            reasons.append("mesmo documento")

        row_reference = (row.bank_reference or "").strip().lower()
        entry_reference = " ".join(
            filter(
                None,
                [
                    str(entry.external_reference or "").strip().lower(),
                    str(entry.description or "").strip().lower(),
                    str(entry.document_number or "").strip().lower(),
                ],
            )
        )
        if row_reference and row_reference in entry_reference:
            score += Decimal("0.10")
            reasons.append("referência bancária")

        row_counterparty_id = row_context.get("counterparty_id")
        if row_counterparty_id and entry.counterparty_id and int(row_counterparty_id) == int(entry.counterparty_id):
            score += Decimal("0.18")
            reasons.append("mesmo favorecido")
        else:
            row_counterparty_name = str(row.counterparty_name or row_context.get("counterparty_hint") or "").strip().lower()
            entry_counterparty_name = FinancialReconciliationService._counterparty_name(entry)
            if row_counterparty_name and entry_counterparty_name:
                if row_counterparty_name == entry_counterparty_name:
                    score += Decimal("0.12")
                    reasons.append("nome do favorecido")
                elif row_counterparty_name in entry_counterparty_name or entry_counterparty_name in row_counterparty_name:
                    score += Decimal("0.06")
                    reasons.append("favorecido semelhante")

        if row_context.get("chart_account_id") and entry.chart_account_id and int(row_context["chart_account_id"]) == int(entry.chart_account_id):
            score += Decimal("0.08")
            reasons.append("mesma conta gerencial")

        if row_context.get("cost_center_id") and entry.cost_center_id and int(row_context["cost_center_id"]) == int(entry.cost_center_id):
            score += Decimal("0.06")
            reasons.append("mesmo centro de custo")

        if row_context.get("activity_id") and entry.activity_id and int(row_context["activity_id"]) == int(entry.activity_id):
            score += Decimal("0.06")
            reasons.append("mesma atividade")

        if row_context.get("process_instance_id") and entry.process_instance_id and int(row_context["process_instance_id"]) == int(entry.process_instance_id):
            score += Decimal("0.06")
            reasons.append("mesma instância")

        row_bank_account_id = row_context.get("bank_account_id")
        if row_bank_account_id and entry.bank_account_id and int(row_bank_account_id) == int(entry.bank_account_id):
            score += Decimal("0.12")
            reasons.append("mesma conta bancária")
        elif row_reference:
            bank_signature = FinancialReconciliationService._bank_account_signature(entry)
            if bank_signature and any(token and token in row_reference for token in bank_signature.split()):
                score += Decimal("0.05")
                reasons.append("assinatura bancária")

        return min(score, Decimal("1")), ", ".join(reasons) or "sem critério suficiente"

    @staticmethod
    def auto_match_batch(
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
            FinancialImportRow.processing_status.in_(["staged", "validated", "imported"]),
        ).order_by(FinancialImportRow.row_number.asc()).all()

        suggested = 0
        rejected = 0

        try:
            for row in rows:
                row_context = FinancialReconciliationService._resolve_row_context(company_id, row)
                row.normalized_payload = row_context
                confirmed_match = FinancialReconciliationMatch.query.filter(
                    FinancialReconciliationMatch.company_id == company_id,
                    FinancialReconciliationMatch.import_row_id == row.id,
                    FinancialReconciliationMatch.match_status == "confirmed",
                    FinancialReconciliationMatch.deleted_at.is_(None),
                ).first()
                if confirmed_match or row.created_entry_id:
                    continue

                FinancialReconciliationMatch.query.filter(
                    FinancialReconciliationMatch.company_id == company_id,
                    FinancialReconciliationMatch.import_row_id == row.id,
                    FinancialReconciliationMatch.match_status != "confirmed",
                ).delete(synchronize_session=False)

                candidates = FinancialEntry.query.filter(
                    FinancialEntry.company_id == company_id,
                    FinancialEntry.deleted_at.is_(None),
                    FinancialEntry.movement_nature == row.movement_nature,
                    FinancialEntry.status.in_(["posted", "partially_settled", "settled"]),
                ).order_by(FinancialEntry.competence_date.desc(), FinancialEntry.id.desc()).limit(20).all()

                if row_context.get("counterparty_id"):
                    scoped_candidates = [item for item in candidates if item.counterparty_id == row_context.get("counterparty_id")]
                    if scoped_candidates:
                        candidates = scoped_candidates

                if row_context.get("bank_account_id"):
                    scoped_candidates = [item for item in candidates if item.bank_account_id == row_context.get("bank_account_id")]
                    if scoped_candidates:
                        candidates = scoped_candidates

                best_entry = None
                best_score = Decimal("0")
                best_reason = ""

                for entry in candidates:
                    score, reason = FinancialReconciliationService._score_match(row, entry, row_context=row_context)
                    if score > best_score:
                        best_score = score
                        best_reason = reason
                        best_entry = entry

                threshold = Decimal("0.80")

                if best_entry and best_score >= threshold:
                    match = FinancialReconciliationMatch(
                        company_id=company_id,
                        import_batch_id=batch_id,
                        import_row_id=row.id,
                        financial_entry_id=best_entry.id,
                        match_status="suggested",
                        confidence_score=best_score,
                        match_reason=best_reason,
                        matched_amount=row.amount,
                        matched_date=row.occurred_on or row.due_date,
                        metadata_json={
                            "batch_code": batch.batch_code,
                            "row_context": {
                                "counterparty_id": row_context.get("counterparty_id"),
                                "bank_account_id": row_context.get("bank_account_id"),
                                "chart_account_id": row_context.get("chart_account_id"),
                                "cost_center_id": row_context.get("cost_center_id"),
                                "activity_id": row_context.get("activity_id"),
                                "process_instance_id": row_context.get("process_instance_id"),
                            },
                            "threshold_used": float(threshold),
                        },
                    )
                    db.session.add(match)
                    if row.processing_status != "imported":
                        row.processing_status = "validated"
                    suggested += 1
                else:
                    row.error_message = "Nenhum match automático com confiança mínima."
                    rejected += 1

            db.session.commit()
            matches = FinancialReconciliationMatch.query.filter(
                FinancialReconciliationMatch.company_id == company_id,
                FinancialReconciliationMatch.import_batch_id == batch_id,
                FinancialReconciliationMatch.deleted_at.is_(None),
            ).order_by(FinancialReconciliationMatch.confidence_score.desc(), FinancialReconciliationMatch.id.asc()).all()

            return {
                "batch_id": batch_id,
                "suggested_count": suggested,
                "unmatched_count": rejected,
                "matches": [match.to_dict() for match in matches],
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao conciliar lote financeiro %s", batch_id)
            return None, f"Erro ao executar conciliação automática: {str(exc)}"

    @staticmethod
    def review_match(
        *,
        match_id: int,
        company_id: int,
        decision: str,
        selected_entry_id: Optional[int] = None,
        adjustments: Optional[Dict] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        if decision not in {"confirmed", "rejected"}:
            return None, "Decisão inválida para revisão do match."

        match = FinancialReconciliationMatch.query.filter(
            FinancialReconciliationMatch.id == match_id,
            FinancialReconciliationMatch.company_id == company_id,
            FinancialReconciliationMatch.deleted_at.is_(None),
        ).first()
        if not match:
            return None, "Match de conciliação não encontrado no escopo da empresa."

        try:
            match.match_status = decision
            row = FinancialImportRow.query.filter(
                FinancialImportRow.id == match.import_row_id,
                FinancialImportRow.company_id == company_id,
                FinancialImportRow.deleted_at.is_(None),
            ).first()
            entry = FinancialEntry.query.filter(
                FinancialEntry.id == match.financial_entry_id,
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
            ).first()
            if selected_entry_id:
                selected_entry = FinancialEntry.query.filter(
                    FinancialEntry.id == selected_entry_id,
                    FinancialEntry.company_id == company_id,
                    FinancialEntry.deleted_at.is_(None),
                ).first()
                if not selected_entry:
                    return None, "Lançamento selecionado para conciliação não encontrado no escopo da empresa."
                match.financial_entry_id = selected_entry.id
                entry = selected_entry

            if row and entry:
                if decision == "confirmed":
                    row.normalized_payload = FinancialCatalogService.enrich_reference_payload(
                        company_id=company_id,
                        payload=row.normalized_payload or {},
                        counterparty_text=row.counterparty_name,
                        description_text=row.description,
                        bank_reference=row.bank_reference,
                    )
                    row.matched_entry_id = entry.id
                    row.processing_status = "validated" if row.processing_status != "imported" else row.processing_status
                    entry.review_status = "reviewed"
                else:
                    if row.matched_entry_id == entry.id:
                        row.matched_entry_id = None
                    if entry.review_status == "reviewed":
                        entry.review_status = "pending_review"

            settlement_payload = None
            settlement_error = None
            if decision == "confirmed" and row and entry:
                settlement_payload, settlement_error = FinancialReconciliationService._create_auto_settlement_from_match(
                    company_id=company_id,
                    row=row,
                    entry=entry,
                    match=match,
                    adjustments=adjustments,
                )
            elif decision == "rejected" and entry:
                FinancialService.set_entry_reconciliation_state(
                    entry=entry,
                    reconciled=False,
                    actor_reason=f"Match {match.id} rejeitado na conciliação bancária.",
                )

            db.session.commit()
            result = match.to_dict()
            result["auto_settlement"] = settlement_payload
            result["auto_settlement_error"] = settlement_error
            if decision == "confirmed" and row:
                memory_result, memory_error = FinancialClassificationHybridService.learn_from_confirmed_row(
                    company_id=company_id,
                    import_row_id=row.id,
                    allowed_company_ids=allowed_company_ids,
                )
                result["classification_memory"] = memory_result
                result["classification_memory_error"] = memory_error
            return result, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao revisar match financeiro %s", match_id)
            return None, f"Erro ao revisar match de conciliação: {str(exc)}"

    @staticmethod
    def manually_match_row(
        *,
        row_id: int,
        financial_entry_id: int,
        company_id: int,
        financial_entry_ids: Optional[Sequence[int]] = None,
        adjustments: Optional[Dict] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        row = FinancialImportRow.query.filter(
            FinancialImportRow.id == row_id,
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.deleted_at.is_(None),
        ).first()
        if not row:
            return None, "Linha de extrato não encontrada no escopo da empresa."

        raw_entry_ids = [financial_entry_id, *(financial_entry_ids or [])]
        selected_entry_ids: List[int] = []
        seen_entry_ids = set()
        for raw_id in raw_entry_ids:
            try:
                current_id = int(raw_id or 0)
            except (TypeError, ValueError):
                current_id = 0
            if current_id > 0 and current_id not in seen_entry_ids:
                seen_entry_ids.add(current_id)
                selected_entry_ids.append(current_id)

        if not selected_entry_ids:
            return None, "Selecione ao menos um lançamento do sistema para vincular à linha do extrato."

        adjustments = dict(adjustments or {})
        allocations_payload = adjustments.pop("allocations", []) or []
        allocation_map: Dict[int, Dict] = {}
        for item in allocations_payload:
            try:
                entry_id = int((item or {}).get("financial_entry_id") or 0)
            except (TypeError, ValueError):
                entry_id = 0
            if entry_id > 0:
                allocation_map[entry_id] = dict(item or {})

        batch = FinancialImportBatch.query.filter(
            FinancialImportBatch.id == row.import_batch_id,
            FinancialImportBatch.company_id == company_id,
            FinancialImportBatch.deleted_at.is_(None),
        ).first()
        if not batch:
            return None, "Lote da linha de extrato não encontrado para preparar a conciliação."

        row_context = FinancialReconciliationService._resolve_row_context(company_id, row)
        remaining_row_amount = FinancialReconciliationService._decimal(row.amount or 0)
        confirmations: List[Dict] = []

        for entry_id in selected_entry_ids:
            entry = FinancialEntry.query.filter(
                FinancialEntry.id == entry_id,
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
            ).first()
            if not entry:
                return None, f"Lançamento {entry_id} não encontrado no escopo da empresa."

            match = FinancialReconciliationMatch.query.filter(
                FinancialReconciliationMatch.company_id == company_id,
                FinancialReconciliationMatch.import_row_id == row.id,
                FinancialReconciliationMatch.financial_entry_id == entry_id,
                FinancialReconciliationMatch.deleted_at.is_(None),
            ).first()
            if not match:
                score, reason = FinancialReconciliationService._score_match(
                    row,
                    entry,
                    row_context=row_context,
                )
                match = FinancialReconciliationMatch(
                    company_id=company_id,
                    import_batch_id=batch.id,
                    import_row_id=row.id,
                    financial_entry_id=entry.id,
                    match_status="suggested",
                    confidence_score=score,
                    match_reason=f"match manual: {reason}",
                    matched_amount=row.amount,
                    matched_date=row.occurred_on or row.due_date,
                    metadata_json={"manual_selection": True},
                )
                db.session.add(match)
                db.session.flush()

            remaining_entry_amount = FinancialReconciliationService._get_remaining_principal(entry)
            entry_allocation = allocation_map.get(entry_id, {})
            principal_amount = entry_allocation.get("principal_amount")
            if principal_amount is None:
                principal_amount = min(remaining_entry_amount, remaining_row_amount)
            principal_amount = FinancialReconciliationService._decimal(principal_amount)
            if principal_amount <= 0:
                return None, f"O lançamento {entry_id} não possui saldo elegível para a vinculação manual."
            if principal_amount > remaining_entry_amount:
                return None, f"O valor alocado para o lançamento {entry_id} excede o saldo em aberto."
            if principal_amount > remaining_row_amount:
                return None, "A soma das vinculações excede o valor disponível na linha do extrato."

            confirmation_payload = {
                **adjustments,
                **{k: v for k, v in entry_allocation.items() if k != "financial_entry_id"},
                "principal_amount": principal_amount,
            }
            confirmation, error = FinancialReconciliationService.review_match(
                match_id=match.id,
                company_id=company_id,
                decision="confirmed",
                selected_entry_id=entry_id,
                adjustments=confirmation_payload,
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                return None, error
            confirmations.append(confirmation)
            remaining_row_amount -= principal_amount

        row.matched_entry_id = selected_entry_ids[0]
        row.processing_status = "validated" if row.processing_status != "imported" else row.processing_status
        row.error_message = None
        db.session.commit()

        return {
            "row_id": row.id,
            "match_mode": "1:N" if len(confirmations) > 1 else "1:1",
            "confirmed_matches": confirmations,
            "remaining_row_amount": float(remaining_row_amount),
        }, None

    @staticmethod
    def settle_open_title_from_bank_row(
        *,
        row_id: int,
        financial_entry_id: int,
        financial_schedule_id: Optional[int] = None,
        company_id: int,
        resolution_strategy: Optional[str] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        row = FinancialImportRow.query.filter(
            FinancialImportRow.id == row_id,
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.deleted_at.is_(None),
        ).first()
        if not row:
            return None, "Linha do extrato não encontrada no escopo da empresa."

        resolved_entry_id = int(financial_entry_id or 0)
        if not resolved_entry_id and financial_schedule_id:
            generated_entry_result, generated_entry_error = FinancialScheduleService.create_entry_from_schedule(
                schedule_id=int(financial_schedule_id),
                company_id=company_id,
                allowed_company_ids=allowed_company_ids,
                ignore_bordero_lock=True,
            )
            if generated_entry_error:
                return None, generated_entry_error
            generated_entry_payload = (generated_entry_result or {}).get("entry") if isinstance(generated_entry_result, dict) else None
            resolved_entry_id = int((generated_entry_payload or {}).get("id") or 0)

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == resolved_entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Título financeiro não encontrado no escopo da empresa."
        if entry.entry_type not in {"payable", "receivable"}:
            return None, "A baixa 1x1 desta coluna aceita apenas títulos financeiros."

        existing_confirmed = FinancialReconciliationMatch.query.filter(
            FinancialReconciliationMatch.company_id == company_id,
            FinancialReconciliationMatch.import_row_id == row.id,
            FinancialReconciliationMatch.match_status == "confirmed",
            FinancialReconciliationMatch.deleted_at.is_(None),
        ).first()
        if existing_confirmed or row.created_entry_id:
            return None, "A linha bancária já está conciliada. Cancele a conciliação antes de refazer a baixa."

        row_nature = str(row.movement_nature or "").strip().lower()
        entry_nature = str(entry.movement_nature or "").strip().lower()
        if row_nature and entry_nature and row_nature != entry_nature:
            return None, "A natureza do título financeiro precisa ser a mesma da linha bancária selecionada."

        remaining_principal = FinancialReconciliationService._get_remaining_principal(entry).quantize(Decimal("0.01"))
        if remaining_principal <= 0:
            return None, "O título financeiro selecionado já está totalmente baixado."

        settled_before = FinancialReconciliationService._get_settled_principal(entry).quantize(Decimal("0.01"))
        row_amount = FinancialReconciliationService._decimal(row.amount or 0).quantize(Decimal("0.01"))
        difference = (row_amount - remaining_principal).quantize(Decimal("0.01"))
        tolerance = Decimal("0.01")

        normalized_strategy = str(resolution_strategy or "").strip().lower()
        can_partial = row_amount < remaining_principal
        can_change_original = True
        can_financial_correction = abs(difference) > tolerance

        if abs(difference) > tolerance and normalized_strategy not in {
            "partial_settlement",
            "change_original_amount",
            "financial_correction",
        }:
            return {
                "requires_resolution": True,
                "row_id": row.id,
                "financial_entry_id": entry.id,
                "bank_amount": float(row_amount),
                "title_open_amount": float(remaining_principal),
                "difference": float(difference),
                "can_partial_settlement": can_partial,
                "can_change_original_amount": can_change_original,
                "can_financial_correction": can_financial_correction,
                "message": "Os valores divergem. Escolha como deseja tratar a baixa do título financeiro.",
            }, None

        if normalized_strategy == "partial_settlement" and not can_partial:
            return None, "Baixa parcial só pode ser usada quando o valor do extrato for menor que o saldo em aberto do título."

        batch = FinancialImportBatch.query.filter(
            FinancialImportBatch.id == row.import_batch_id,
            FinancialImportBatch.company_id == company_id,
            FinancialImportBatch.deleted_at.is_(None),
        ).first()
        if not batch:
            return None, "Lote da linha de extrato não encontrado para preparar a baixa do título."

        row_context = FinancialReconciliationService._resolve_row_context(company_id, row)
        match = FinancialReconciliationMatch.query.filter(
            FinancialReconciliationMatch.company_id == company_id,
            FinancialReconciliationMatch.import_row_id == row.id,
            FinancialReconciliationMatch.financial_entry_id == entry.id,
            FinancialReconciliationMatch.deleted_at.is_(None),
        ).first()
        if not match:
            score, reason = FinancialReconciliationService._score_match(row, entry, row_context=row_context)
            match = FinancialReconciliationMatch(
                company_id=company_id,
                import_batch_id=batch.id,
                import_row_id=row.id,
                financial_entry_id=entry.id,
                match_status="suggested",
                confidence_score=score,
                match_reason=f"baixa de título em aberto: {reason}",
                matched_amount=row.amount,
                matched_date=row.occurred_on or row.due_date,
                metadata_json={"manual_selection": True, "open_title_reconciliation": True},
            )
            db.session.add(match)
            db.session.flush()

        adjustments: Dict[str, object] = {
            "principal_amount": row_amount,
        }
        amount_adjustment_snapshot = None

        if abs(difference) <= tolerance:
            normalized_strategy = "exact_match"
        elif normalized_strategy == "partial_settlement":
            adjustments["principal_amount"] = row_amount
        elif normalized_strategy == "change_original_amount":
            target_amount = (settled_before + row_amount).quantize(Decimal("0.01"))
            try:
                amount_adjustment_snapshot = FinancialReconciliationService._adjust_open_title_original_amount(
                    entry=entry,
                    target_amount=target_amount,
                    row=row,
                )
            except ValueError as exc:
                return None, str(exc)
            adjustments["principal_amount"] = row_amount
        elif normalized_strategy == "financial_correction":
            adjustments["principal_amount"] = remaining_principal
            if difference > 0:
                adjustments["other_adjustments_amount"] = difference
            else:
                adjustments["discount_amount"] = abs(difference)

        try:
            match.match_status = "confirmed"
            match.matched_amount = row.amount
            match.matched_date = row.occurred_on or row.due_date
            match.metadata_json = {
                **dict(match.metadata_json or {}),
                "manual_selection": True,
                "open_title_reconciliation": True,
                "resolution_strategy": normalized_strategy,
                "difference": float(difference),
            }

            row.normalized_payload = row_context
            row.matched_entry_id = entry.id
            row.processing_status = "validated" if row.processing_status != "imported" else row.processing_status
            entry.review_status = "reviewed"

            settlement_payload, settlement_error = FinancialReconciliationService._create_auto_settlement_from_match(
                company_id=company_id,
                row=row,
                entry=entry,
                match=match,
                adjustments=adjustments,
            )
            if settlement_error:
                db.session.rollback()
                return None, settlement_error

            db.session.commit()
            memory_result, memory_error = FinancialClassificationHybridService.learn_from_confirmed_row(
                company_id=company_id,
                import_row_id=row.id,
                allowed_company_ids=allowed_company_ids,
            )
            return {
                "row_id": row.id,
                "financial_entry_id": entry.id,
                "match_mode": "1:1",
                "resolution_strategy": normalized_strategy,
                "difference": float(difference),
                "match": match.to_dict(),
                "auto_settlement": settlement_payload,
                "title_amount_adjustment": amount_adjustment_snapshot,
                "classification_memory": memory_result,
                "classification_memory_error": memory_error,
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao baixar título em aberto via conciliação bancária")
            return None, f"Erro ao baixar título em aberto: {str(exc)}"

    @staticmethod
    def reconcile_group(
        *,
        company_id: int,
        bank_row_ids: Sequence[int],
        financial_entry_ids: Sequence[int],
        resolution_strategy: Optional[str] = None,
        complementary_entry: Optional[Dict] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        selected_row_ids = FinancialReconciliationService._normalize_ids(bank_row_ids)
        selected_entry_ids = FinancialReconciliationService._normalize_ids(financial_entry_ids)
        if not selected_row_ids:
            return None, "Selecione ao menos uma linha do extrato bancário."
        if not selected_entry_ids:
            return None, "Selecione ao menos um lançamento do sistema."

        rows = FinancialImportRow.query.filter(
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.id.in_(selected_row_ids),
            FinancialImportRow.deleted_at.is_(None),
        ).order_by(FinancialImportRow.row_number.asc(), FinancialImportRow.id.asc()).all()
        if len(rows) != len(selected_row_ids):
            return None, "Uma ou mais linhas do extrato não foram encontradas no escopo da empresa."

        entries = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.id.in_(selected_entry_ids),
            FinancialEntry.deleted_at.is_(None),
        ).order_by(FinancialEntry.id.asc()).all()
        if len(entries) != len(selected_entry_ids):
            return None, "Um ou mais lançamentos do sistema não foram encontrados no escopo da empresa."

        existing_confirmed = FinancialReconciliationMatch.query.filter(
            FinancialReconciliationMatch.company_id == company_id,
            FinancialReconciliationMatch.import_row_id.in_(selected_row_ids),
            FinancialReconciliationMatch.match_status == "confirmed",
            FinancialReconciliationMatch.deleted_at.is_(None),
        ).first()
        if existing_confirmed or any(row.created_entry_id for row in rows):
            return None, "Há linha bancária selecionada que já está conciliada. Cancele a conciliação antes de refazer o grupo."

        row_natures = {str(row.movement_nature or "").strip().lower() for row in rows}
        entry_natures = {str(entry.movement_nature or "").strip().lower() for entry in entries}
        row_natures.discard("")
        entry_natures.discard("")
        if len(row_natures) != 1 or len(entry_natures) > 1:
            return None, "A conciliação por conjunto nesta versão exige registros da mesma natureza operacional."
        movement_nature = next(iter(row_natures))
        if entry_natures and next(iter(entry_natures)) != movement_nature:
            return None, "A natureza dos lançamentos do sistema precisa ser a mesma das linhas bancárias selecionadas."

        bank_total = sum((FinancialReconciliationService._decimal(row.amount) for row in rows), Decimal("0"))
        entry_remaining: Dict[int, Decimal] = {}
        system_total = Decimal("0")
        for entry in entries:
            remaining = FinancialReconciliationService._get_remaining_principal(entry)
            if remaining <= 0:
                return None, f"O lançamento {entry.id} já está totalmente baixado."
            entry_remaining[int(entry.id)] = remaining
            system_total += remaining

        difference = bank_total - system_total
        resolution_strategy = str(resolution_strategy or "").strip().lower()
        complementary_payload = dict(complementary_entry or {})
        created_complement = None
        tolerance = Decimal("0.01")

        if abs(difference) > tolerance:
            preview = {
                "requires_resolution": True,
                "bank_row_ids": selected_row_ids,
                "financial_entry_ids": selected_entry_ids,
                "bank_total": float(bank_total),
                "system_total": float(system_total),
                "difference": float(difference),
                "can_create_complement": difference > 0,
                "can_edit_entries": True,
                "message": (
                    "O total bancário é maior que os lançamentos selecionados. "
                    "Crie um lançamento complementar ou ajuste a seleção."
                    if difference > 0
                    else "Os lançamentos selecionados excedem o total bancário. Abra o lançamento e corrija o valor antes de conciliar."
                ),
            }
            if resolution_strategy != "create_complement":
                return preview, None
            if difference <= 0:
                return None, "Quando o sistema excede o banco, corrija o lançamento do sistema antes de confirmar."

            first_row = rows[0]
            first_context = FinancialReconciliationService._resolve_row_context(company_id, first_row)
            entry_code = complementary_payload.get("entry_code") or f"REC-GRP-{first_row.id}-{datetime.utcnow().strftime('%H%M%S%f')}"
            fallback_date = first_row.occurred_on or first_row.due_date or datetime.utcnow().date()
            entry_payload = {
                "company_id": company_id,
                "entry_code": entry_code,
                "entry_type": complementary_payload.get("entry_type") or "bank_movement",
                "movement_nature": complementary_payload.get("movement_nature") or movement_nature,
                "origin_type": complementary_payload.get("origin_type") or "manual",
                "status": "posted",
                "review_status": "approved",
                "description": complementary_payload.get("description") or f"Complemento da conciliação bancária linha {first_row.row_number}",
                "document_number": complementary_payload.get("document_number") or first_row.document_number,
                "external_reference": complementary_payload.get("external_reference") or first_row.bank_reference,
                "origin_reference": complementary_payload.get("origin_reference") or f"reconciliation-group:{','.join(map(str, selected_row_ids))}",
                "competence_date": complementary_payload.get("competence_date") or fallback_date,
                "due_date": complementary_payload.get("due_date") or fallback_date,
                "occurred_on": complementary_payload.get("occurred_on") or fallback_date,
                "original_amount": difference,
                "bank_account_id": complementary_payload.get("bank_account_id") or first_context.get("bank_account_id"),
                "counterparty_id": complementary_payload.get("counterparty_id") or first_context.get("counterparty_id"),
                "chart_account_id": complementary_payload.get("chart_account_id") or first_context.get("chart_account_id"),
                "cost_center_id": complementary_payload.get("cost_center_id") or first_context.get("cost_center_id"),
                "notes": complementary_payload.get("notes") or "Criado como complemento de conciliação por conjunto.",
                "metadata_json": {
                    "reconciliation_group_bank_row_ids": selected_row_ids,
                    "reconciliation_group_complement": True,
                    "reconciled": False,
                },
            }
            if not entry_payload["bank_account_id"]:
                return None, "Informe a conta bancária para criar o lançamento complementar."
            created_entry, error = FinancialService.create_entry(payload=entry_payload, allowed_company_ids=allowed_company_ids)
            if error:
                return None, error
            entries.append(created_entry)
            selected_entry_ids.append(int(created_entry.id))
            entry_remaining[int(created_entry.id)] = FinancialReconciliationService._decimal(created_entry.original_amount)
            system_total += FinancialReconciliationService._decimal(created_entry.original_amount)
            created_complement = FinancialService.serialize_entry(created_entry, include_children=False)
            difference = bank_total - system_total

        if abs(difference) > tolerance:
            return None, "O grupo ainda não está balanceado após a resolução escolhida."

        rows_remaining = {int(row.id): FinancialReconciliationService._decimal(row.amount) for row in rows}
        entry_by_id = {int(entry.id): entry for entry in entries}
        allocations_by_row: Dict[int, List[Dict]] = {int(row.id): [] for row in rows}

        for row in rows:
            row_id = int(row.id)
            for entry_id in list(selected_entry_ids):
                if rows_remaining[row_id] <= 0:
                    break
                available = entry_remaining.get(int(entry_id), Decimal("0"))
                if available <= 0:
                    continue
                amount = min(rows_remaining[row_id], available)
                if amount <= 0:
                    continue
                allocations_by_row[row_id].append(
                    {"financial_entry_id": int(entry_id), "principal_amount": amount}
                )
                rows_remaining[row_id] -= amount
                entry_remaining[int(entry_id)] = available - amount

        if any(amount > tolerance for amount in rows_remaining.values()) or any(amount > tolerance for amount in entry_remaining.values()):
            return None, "Não foi possível distribuir automaticamente os valores do grupo selecionado."

        confirmations: List[Dict] = []
        group_key = f"reconciliation-group:{company_id}:{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        try:
            for row in rows:
                row_allocations = allocations_by_row[int(row.id)]
                if not row_allocations:
                    continue
                result, error = FinancialReconciliationService.manually_match_row(
                    row_id=int(row.id),
                    financial_entry_id=int(row_allocations[0]["financial_entry_id"]),
                    financial_entry_ids=[int(item["financial_entry_id"]) for item in row_allocations[1:]],
                    company_id=company_id,
                    adjustments={
                        "allocations": row_allocations,
                        "metadata_json": {
                            "reconciliation_group_key": group_key,
                            "reconciliation_group_bank_row_ids": selected_row_ids,
                            "reconciliation_group_entry_ids": selected_entry_ids,
                        },
                    },
                    allowed_company_ids=allowed_company_ids,
                )
                if error:
                    db.session.rollback()
                    return None, error
                confirmations.append(result)
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao conciliar grupo bancário")
            return None, f"Erro ao conciliar grupo bancário: {str(exc)}"

        return {
            "requires_resolution": False,
            "group_key": group_key,
            "match_mode": "N:N" if len(selected_row_ids) > 1 and len(selected_entry_ids) > 1 else ("N:1" if len(selected_row_ids) > 1 else "1:N"),
            "bank_row_ids": selected_row_ids,
            "financial_entry_ids": selected_entry_ids,
            "bank_total": float(bank_total),
            "system_total": float(system_total),
            "difference": float(bank_total - system_total),
            "created_complement": created_complement,
            "confirmed_groups": confirmations,
        }, None

    @staticmethod
    def cancel_row_reconciliation(
        *,
        row_id: int,
        company_id: int,
        reason: Optional[str] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        row = FinancialImportRow.query.filter(
            FinancialImportRow.id == row_id,
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.deleted_at.is_(None),
        ).first()
        if not row:
            return None, "Linha de extrato não encontrada no escopo da empresa."

        active_matches = (
            FinancialReconciliationMatch.query.filter(
                FinancialReconciliationMatch.company_id == company_id,
                FinancialReconciliationMatch.import_row_id == row.id,
                FinancialReconciliationMatch.deleted_at.is_(None),
                FinancialReconciliationMatch.match_status.in_(["suggested", "confirmed"]),
            )
            .order_by(FinancialReconciliationMatch.id.asc())
            .all()
        )
        if not active_matches and not row.created_entry_id and not row.matched_entry_id:
            return None, "A linha selecionada não possui conciliação ativa para cancelamento."

        reason_text = (reason or "").strip() or "Cancelamento manual da conciliação bancária."
        reverted_settlements = 0
        reverted_matches = 0
        released_entries: List[int] = []

        try:
            for match in active_matches:
                linked_settlements = FinancialSettlement.query.filter(
                    FinancialSettlement.company_id == company_id,
                    FinancialSettlement.external_reference == f"reconciliation-match:{match.id}",
                    FinancialSettlement.deleted_at.is_(None),
                ).all()
                for settlement in linked_settlements:
                    settlement.reconciliation_status = "pending"
                    settlement.settlement_status = "cancelled"
                    settlement.notes = (
                        f"{(settlement.notes or '').strip()}\nCancelamento da conciliação: {reason_text}".strip()
                    )
                    reverted_settlements += 1
                if match.financial_entry_id:
                    entry = FinancialEntry.query.filter(
                        FinancialEntry.id == match.financial_entry_id,
                        FinancialEntry.company_id == company_id,
                        FinancialEntry.deleted_at.is_(None),
                    ).first()
                    if entry:
                        has_other_active_settlements = FinancialSettlement.query.filter(
                            FinancialSettlement.company_id == company_id,
                            FinancialSettlement.financial_entry_id == entry.id,
                            FinancialSettlement.deleted_at.is_(None),
                            FinancialSettlement.settlement_status != "cancelled",
                            FinancialSettlement.reconciliation_status.in_(["matched", "reconciled"]),
                        ).first()
                        FinancialReconciliationService._update_entry_reconciliation_metadata(
                            entry=entry,
                            reconciled=bool(has_other_active_settlements),
                            actor_reason=reason_text,
                        )
                        released_entries.append(entry.id)
                match.match_status = "rejected"
                match.match_reason = f"{(match.match_reason or '').strip()} · cancelado: {reason_text}".strip()[:255]
                match.metadata_json = {
                    **(match.metadata_json or {}),
                    "reconciliation_cancelled": True,
                    "reconciliation_cancel_reason": reason_text,
                }
                reverted_matches += 1

            if row.created_entry_id:
                created_entry = FinancialEntry.query.filter(
                    FinancialEntry.id == row.created_entry_id,
                    FinancialEntry.company_id == company_id,
                    FinancialEntry.deleted_at.is_(None),
                ).first()
                created_settlements = FinancialSettlement.query.filter(
                    FinancialSettlement.company_id == company_id,
                    FinancialSettlement.external_reference == f"reconciliation-row:{row.id}",
                    FinancialSettlement.deleted_at.is_(None),
                ).all()
                for settlement in created_settlements:
                    settlement.reconciliation_status = "pending"
                    settlement.settlement_status = "cancelled"
                    settlement.notes = (
                        f"{(settlement.notes or '').strip()}\nCancelamento da conciliação: {reason_text}".strip()
                    )
                    reverted_settlements += 1
                if created_entry:
                    FinancialReconciliationService._update_entry_reconciliation_metadata(
                        entry=created_entry,
                        reconciled=False,
                        actor_reason=reason_text,
                    )
                    released_entries.append(created_entry.id)
                row.created_entry_id = None

            row.matched_entry_id = None
            row.processing_status = "validated"
            row.error_message = reason_text
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao cancelar conciliação da linha %s", row_id)
            return None, f"Erro ao cancelar conciliação: {str(exc)}"

        return {
            "row_id": row.id,
            "reverted_matches": reverted_matches,
            "reverted_settlements": reverted_settlements,
            "released_entry_ids": sorted(set(released_entries)),
            "reason": reason_text,
        }, None

    @staticmethod
    def cancel_reconciliations_batch(
        *,
        row_ids: Sequence[int],
        company_id: int,
        reason: Optional[str] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        normalized_row_ids = sorted({int(row_id) for row_id in (row_ids or []) if int(row_id or 0) > 0})
        if not normalized_row_ids:
            return None, "Selecione ao menos uma linha conciliada para cancelar."

        succeeded: List[Dict] = []
        failed: List[Dict] = []
        total_matches = 0
        total_settlements = 0
        released_entry_ids: set[int] = set()

        for row_id in normalized_row_ids:
            result, error = FinancialReconciliationService.cancel_row_reconciliation(
                row_id=row_id,
                company_id=company_id,
                reason=reason,
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                failed.append({"row_id": row_id, "error": error})
                continue
            succeeded.append(result or {"row_id": row_id})
            total_matches += int((result or {}).get("reverted_matches") or 0)
            total_settlements += int((result or {}).get("reverted_settlements") or 0)
            released_entry_ids.update(int(item) for item in ((result or {}).get("released_entry_ids") or []) if item is not None)

        if not succeeded:
            first_error = failed[0]["error"] if failed else "Não foi possível cancelar as conciliações selecionadas."
            return None, first_error

        return {
            "processed_rows": len(normalized_row_ids),
            "cancelled_rows": len(succeeded),
            "failed_rows": len(failed),
            "reverted_matches": total_matches,
            "reverted_settlements": total_settlements,
            "released_entry_ids": sorted(released_entry_ids),
            "items": succeeded,
            "errors": failed,
            "reason": (reason or "").strip() or "Cancelamento manual da conciliação bancária.",
        }, None
