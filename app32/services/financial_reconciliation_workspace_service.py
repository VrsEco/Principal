from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import (
    FinancialBankAccount,
    FinancialEntry,
    FinancialImportBatch,
    FinancialImportRow,
    FinancialReconciliationMatch,
    FinancialSettlement,
)
from services.financial_reconciliation_service import FinancialReconciliationService
from services.financial_service import FinancialService


class FinancialReconciliationWorkspaceService:
    @staticmethod
    def _batch_matches_bank_account(batch: FinancialImportBatch, bank_account_id: int) -> bool:
        metadata_bank_id = (batch.metadata_json or {}).get("bank_account_id")
        if metadata_bank_id and int(metadata_bank_id) == int(bank_account_id):
            return True
        rows = FinancialImportRow.query.filter(
            FinancialImportRow.company_id == batch.company_id,
            FinancialImportRow.import_batch_id == batch.id,
            FinancialImportRow.deleted_at.is_(None),
        ).all()
        return any(int((row.normalized_payload or {}).get("bank_account_id") or 0) == int(bank_account_id) for row in rows)

    @staticmethod
    def _list_batches_for_bank_account(company_id: int, bank_account_id: int) -> List[FinancialImportBatch]:
        batches = FinancialImportBatch.query.filter(
            FinancialImportBatch.company_id == company_id,
            FinancialImportBatch.deleted_at.is_(None),
        ).order_by(FinancialImportBatch.imported_at.desc(), FinancialImportBatch.id.desc()).all()
        return [batch for batch in batches if FinancialReconciliationWorkspaceService._batch_matches_bank_account(batch, bank_account_id)]

    @staticmethod
    def _resolve_batch_rows(company_id: int, batch_id: int, bank_account_id: int) -> List[FinancialImportRow]:
        rows = FinancialImportRow.query.filter(
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.import_batch_id == batch_id,
            FinancialImportRow.deleted_at.is_(None),
        ).order_by(FinancialImportRow.row_number.asc()).all()
        return [
            row
            for row in rows
            if int((row.normalized_payload or {}).get("bank_account_id") or bank_account_id) == int(bank_account_id)
        ]

    @staticmethod
    def _serialize_row(row: FinancialImportRow, match_map: Dict[int, FinancialReconciliationMatch]) -> Dict:
        payload = row.to_dict()
        match = match_map.get(row.id)
        created_entry = None
        if row.created_entry_id:
            created_entry = FinancialEntry.query.filter(
                FinancialEntry.id == row.created_entry_id,
                FinancialEntry.company_id == row.company_id,
                FinancialEntry.deleted_at.is_(None),
            ).first()
        payload["match"] = match.to_dict() if match else None
        payload["created_entry"] = FinancialService.serialize_entry(created_entry, include_children=False) if created_entry else None
        payload["can_create_entry"] = not bool(row.created_entry_id)
        payload["needs_manual_action"] = not bool(match and match.match_status == "confirmed") and not bool(row.created_entry_id)
        return payload

    @staticmethod
    def _build_status_message(
        *,
        last_reconciled_date: Optional[date],
        statement_end: Optional[date],
        pending_count: int,
        has_batch: bool,
    ) -> str:
        if not has_batch:
            return "Falta upload do extrato do banco."
        if pending_count == 0 and statement_end:
            return f"Conciliação ok até {statement_end.strftime('%d/%m/%Y')}."
        if last_reconciled_date:
            return (
                f"Conciliação feita até {last_reconciled_date.strftime('%d/%m/%Y')} "
                f"· {pending_count} registro(s) a conciliar."
            )
        if statement_end:
            return (
                f"Extrato importado até {statement_end.strftime('%d/%m/%Y')} "
                f"· {pending_count} registro(s) pendentes."
            )
        return f"{pending_count} registro(s) a conciliar."

    @staticmethod
    def get_overview(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        bank_accounts = FinancialBankAccount.query.filter(
            FinancialBankAccount.company_id == company_id,
            FinancialBankAccount.deleted_at.is_(None),
            FinancialBankAccount.is_active.is_(True),
        ).order_by(FinancialBankAccount.name.asc(), FinancialBankAccount.id.asc()).all()

        items: List[Dict] = []
        for account in bank_accounts:
            batches = FinancialReconciliationWorkspaceService._list_batches_for_bank_account(company_id, account.id)
            latest_batch = batches[0] if batches else None
            rows = (
                FinancialReconciliationWorkspaceService._resolve_batch_rows(company_id, latest_batch.id, account.id)
                if latest_batch
                else []
            )
            statement_dates = [row.occurred_on or row.due_date for row in rows if row.occurred_on or row.due_date]
            statement_end = max(statement_dates) if statement_dates else None
            match_map = {
                item.import_row_id: item
                for item in FinancialReconciliationMatch.query.filter(
                    FinancialReconciliationMatch.company_id == company_id,
                    FinancialReconciliationMatch.import_batch_id == latest_batch.id if latest_batch else -1,
                    FinancialReconciliationMatch.deleted_at.is_(None),
                ).all()
            } if latest_batch else {}
            pending_count = sum(
                1
                for row in rows
                if not row.created_entry_id and not (match_map.get(row.id) and match_map[row.id].match_status == "confirmed")
            )
            last_reconciled = (
                FinancialSettlement.query.filter(
                    FinancialSettlement.company_id == company_id,
                    FinancialSettlement.bank_account_id == account.id,
                    FinancialSettlement.deleted_at.is_(None),
                    FinancialSettlement.settlement_status != "cancelled",
                    FinancialSettlement.reconciliation_status == "reconciled",
                )
                .order_by(FinancialSettlement.settlement_date.desc(), FinancialSettlement.id.desc())
                .first()
            )
            items.append(
                {
                    "bank_account": account.to_dict(),
                    "latest_batch": latest_batch.to_dict() if latest_batch else None,
                    "last_reconciled_date": last_reconciled.settlement_date.isoformat() if last_reconciled and last_reconciled.settlement_date else None,
                    "pending_count": pending_count,
                    "statement_end": statement_end.isoformat() if statement_end else None,
                    "status_message": FinancialReconciliationWorkspaceService._build_status_message(
                        last_reconciled_date=last_reconciled.settlement_date if last_reconciled else None,
                        statement_end=statement_end,
                        pending_count=pending_count,
                        has_batch=bool(latest_batch),
                    ),
                    "api_preparation": {
                        "status": "prepared",
                        "message": "Estrutura preparada para acoplamento futuro via API bancária.",
                    },
                }
            )

        return {"items": items, "count": len(items)}, None

    @staticmethod
    def get_workspace(
        *,
        company_id: int,
        bank_account_id: int,
        batch_id: Optional[int] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        if not bank_account_id:
            return None, "Conta bancária é obrigatória para abrir a conciliação."

        account = FinancialBankAccount.query.filter(
            FinancialBankAccount.id == bank_account_id,
            FinancialBankAccount.company_id == company_id,
            FinancialBankAccount.deleted_at.is_(None),
        ).first()
        if not account:
            return None, "Conta bancária não encontrada no escopo da empresa."

        batches = FinancialReconciliationWorkspaceService._list_batches_for_bank_account(company_id, bank_account_id)
        selected_batch = next((item for item in batches if item.id == batch_id), None) if batch_id else None
        selected_batch = selected_batch or (batches[0] if batches else None)
        rows = (
            FinancialReconciliationWorkspaceService._resolve_batch_rows(company_id, selected_batch.id, bank_account_id)
            if selected_batch
            else []
        )
        matches = (
            FinancialReconciliationMatch.query.filter(
                FinancialReconciliationMatch.company_id == company_id,
                FinancialReconciliationMatch.import_batch_id == selected_batch.id,
                FinancialReconciliationMatch.deleted_at.is_(None),
            ).order_by(FinancialReconciliationMatch.id.asc()).all()
            if selected_batch
            else []
        )
        match_map = {item.import_row_id: item for item in matches}

        return {
            "bank_account": account.to_dict(),
            "selected_batch": selected_batch.to_dict() if selected_batch else None,
            "available_batches": [batch.to_dict() for batch in batches],
            "rows": [FinancialReconciliationWorkspaceService._serialize_row(row, match_map) for row in rows],
            "summary": {
                "total_rows": len(rows),
                "pending_rows": sum(1 for row in rows if not row.created_entry_id and not (match_map.get(row.id) and match_map[row.id].match_status == "confirmed")),
                "confirmed_matches": sum(1 for item in matches if item.match_status == "confirmed"),
                "suggested_matches": sum(1 for item in matches if item.match_status == "suggested"),
            },
        }, None

    @staticmethod
    def list_row_candidates(
        *,
        company_id: int,
        row_id: int,
        limit: int = 8,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
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

        row_context = FinancialReconciliationService._resolve_row_context(company_id, row)
        candidates = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.movement_nature == (row.movement_nature or "debit"),
            FinancialEntry.status.in_(["posted", "partially_settled", "settled"]),
        ).order_by(FinancialEntry.competence_date.desc(), FinancialEntry.id.desc()).limit(50).all()

        ranked: List[Dict] = []
        for entry in candidates:
            score, reason = FinancialReconciliationService._score_match(row, entry, row_context=row_context)
            ranked.append(
                {
                    "score": float(score),
                    "reason": reason,
                    "entry": FinancialService.serialize_entry(entry, include_children=False),
                }
            )
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:limit], None

    @staticmethod
    def create_entry_from_row(
        *,
        company_id: int,
        row_id: int,
        payload: Dict,
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

        batch = FinancialImportBatch.query.filter(
            FinancialImportBatch.id == row.import_batch_id,
            FinancialImportBatch.company_id == company_id,
            FinancialImportBatch.deleted_at.is_(None),
        ).first()
        if not batch:
            return None, "Lote de conciliação não encontrado no escopo da empresa."

        entry_payload = {
            "company_id": company_id,
            "entry_code": f"REC-ROW-{row.id}",
            "entry_type": payload.get("entry_type") or "bank_movement",
            "movement_nature": payload.get("movement_nature") or row.movement_nature or "debit",
            "origin_type": batch.source_type,
            "status": "posted",
            "review_status": "approved",
            "description": payload.get("description") or row.description or f"Conciliação linha {row.row_number}",
            "document_number": payload.get("document_number") or row.document_number,
            "external_reference": payload.get("external_reference") or row.bank_reference,
            "origin_reference": batch.batch_code,
            "competence_date": payload.get("competence_date") or row.occurred_on or row.due_date or batch.imported_at.date(),
            "due_date": payload.get("due_date") or row.due_date or row.occurred_on or batch.imported_at.date(),
            "occurred_on": payload.get("occurred_on") or row.occurred_on or row.due_date or batch.imported_at.date(),
            "original_amount": payload.get("original_amount") or row.amount or Decimal("0"),
            "bank_account_id": payload.get("bank_account_id") or (row.normalized_payload or {}).get("bank_account_id"),
            "counterparty_id": payload.get("counterparty_id"),
            "chart_account_id": payload.get("chart_account_id"),
            "cost_center_id": payload.get("cost_center_id"),
            "notes": payload.get("notes"),
            "metadata_json": {
                "reconciliation_created_from_row_id": row.id,
                "reconciliation_batch_id": batch.id,
                "reconciled": True,
            },
        }
        if not entry_payload["bank_account_id"]:
            return None, "A linha do extrato precisa estar vinculada a uma conta bancária para criar o lançamento."
        entry, error = FinancialService.create_entry(payload=entry_payload, allowed_company_ids=allowed_company_ids)
        if error:
            return None, error

        settlement_payload = {
            "company_id": company_id,
            "financial_entry_id": entry.id,
            "settlement_code": f"RECROW-{row.id}",
            "settlement_type": "bank_import",
            "settlement_status": "posted",
            "settlement_date": row.occurred_on or row.due_date or batch.imported_at.date(),
            "bank_account_id": entry.bank_account_id,
            "principal_amount": entry.original_amount,
            "external_reference": f"reconciliation-row:{row.id}",
            "reconciliation_status": "reconciled",
            "metadata_json": {
                "import_batch_id": batch.id,
                "import_row_id": row.id,
                "mode": "created_from_bank_reconciliation",
            },
        }
        settlement, error = FinancialService.create_settlement(payload=settlement_payload, allowed_company_ids=allowed_company_ids)
        if error:
            entry.deleted_at = db.func.now()
            row.error_message = error
            db.session.commit()
            return None, error

        row.created_entry_id = entry.id
        row.matched_entry_id = entry.id
        row.processing_status = "imported"
        row.error_message = None
        FinancialService.set_entry_reconciliation_state(
            entry=entry,
            reconciled=True,
            actor_reason=f"Lançamento criado a partir da linha {row.id} na conciliação bancária.",
        )
        db.session.commit()
        return {
            "entry": FinancialService.serialize_entry(entry),
            "settlement": settlement.to_dict(),
            "row": row.to_dict(),
        }, None
