from __future__ import annotations

import logging
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
    FinancialSettlement,
)
from services.financial_catalog_service import FinancialCatalogService
from services.financial_service import FinancialService
from services.financial_classification_hybrid_service import FinancialClassificationHybridService


logger = logging.getLogger(__name__)


class FinancialReconciliationService:
    """Motor determinístico inicial de matching entre staging e ledger."""

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
            return None, "Linha conciliada sem valor elegível para liquidação automática."
        if remaining_principal <= 0:
            return None, "Lançamento já está totalmente liquidado."
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
            "notes": f"Liquidação automática gerada pela confirmação do match {match.id}.",
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
                FinancialReconciliationMatch.query.filter(
                    FinancialReconciliationMatch.company_id == company_id,
                    FinancialReconciliationMatch.import_row_id == row.id,
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

                threshold = Decimal("0.68") if row_context.get("counterparty_id") or row_context.get("bank_account_id") else Decimal("0.72")

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

        match = FinancialReconciliationMatch.query.filter(
            FinancialReconciliationMatch.company_id == company_id,
            FinancialReconciliationMatch.import_row_id == row.id,
            FinancialReconciliationMatch.financial_entry_id == financial_entry_id,
            FinancialReconciliationMatch.deleted_at.is_(None),
        ).first()
        if not match:
            batch = FinancialImportBatch.query.filter(
                FinancialImportBatch.id == row.import_batch_id,
                FinancialImportBatch.company_id == company_id,
                FinancialImportBatch.deleted_at.is_(None),
            ).first()
            entry = FinancialEntry.query.filter(
                FinancialEntry.id == financial_entry_id,
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
            ).first()
            if not batch or not entry:
                return None, "Não foi possível preparar o match manual para a linha selecionada."
            score, reason = FinancialReconciliationService._score_match(
                row,
                entry,
                row_context=FinancialReconciliationService._resolve_row_context(company_id, row),
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

        return FinancialReconciliationService.review_match(
            match_id=match.id,
            company_id=company_id,
            decision="confirmed",
            selected_entry_id=financial_entry_id,
            adjustments=adjustments,
            allowed_company_ids=allowed_company_ids,
        )
