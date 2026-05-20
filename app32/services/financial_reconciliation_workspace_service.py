from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import (
    FinancialBankAccount,
    FinancialEntry,
    FinancialImportBatch,
    FinancialImportRow,
    FinancialReconciliationMatch,
    FinancialSchedule,
    FinancialSettlement,
)
from services.financial_reconciliation_service import FinancialReconciliationService
from services.financial_service import FinancialService


class FinancialReconciliationWorkspaceService:
    @staticmethod
    def _group_matches_by_row(matches: Sequence[FinancialReconciliationMatch]) -> Dict[int, List[FinancialReconciliationMatch]]:
        grouped: Dict[int, List[FinancialReconciliationMatch]] = {}
        for match in matches or []:
            grouped.setdefault(int(match.import_row_id), []).append(match)
        for row_matches in grouped.values():
            row_matches.sort(
                key=lambda item: (
                    0 if str(item.match_status or "").lower() == "confirmed" else 1,
                    -(float(item.confidence_score or 0)),
                    item.id,
                )
            )
        return grouped

    @staticmethod
    def _get_primary_match(row_matches: Sequence[FinancialReconciliationMatch]) -> Optional[FinancialReconciliationMatch]:
        if not row_matches:
            return None
        return next(
            (item for item in row_matches if str(item.match_status or "").lower() == "confirmed"),
            row_matches[0],
        )

    @staticmethod
    def _build_row_match_snapshot(row_matches: Sequence[FinancialReconciliationMatch]) -> Dict:
        items = [match.to_dict() for match in row_matches or []]
        confirmed = [item for item in items if str(item.get("match_status") or "").lower() == "confirmed"]
        suggested = [item for item in items if str(item.get("match_status") or "").lower() == "suggested"]
        rejected = [item for item in items if str(item.get("match_status") or "").lower() == "rejected"]
        linked_entry_ids = [
            int(item["financial_entry_id"])
            for item in items
            if item.get("financial_entry_id") is not None and str(item.get("match_status") or "").lower() != "rejected"
        ]
        return {
            "all_matches": items,
            "confirmed_matches": confirmed,
            "suggested_matches": suggested,
            "rejected_matches": rejected,
            "linked_entry_ids": linked_entry_ids,
            "confirmed_count": len(confirmed),
            "suggested_count": len(suggested),
            "rejected_count": len(rejected),
            "match_mode": (
                "1:N" if len(confirmed) > 1 else
                "1:1" if len(confirmed) == 1 else
                "suggested" if suggested else
                "unmatched"
            ),
        }

    @staticmethod
    def _entry_remaining_amount(entry: FinancialEntry) -> Decimal:
        settled_amount = (
            db.session.query(db.func.coalesce(db.func.sum(FinancialSettlement.principal_amount), 0))
            .filter(
                FinancialSettlement.company_id == entry.company_id,
                FinancialSettlement.financial_entry_id == entry.id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            )
            .scalar()
        ) or Decimal("0")
        remaining = Decimal(entry.original_amount or 0) - Decimal(settled_amount)
        return remaining if remaining > 0 else Decimal("0")

    @staticmethod
    def _serialize_system_entry(
        entry: FinancialEntry,
        *,
        linked_row_ids: Optional[Sequence[int]] = None,
    ) -> Dict:
        payload = FinancialService.serialize_entry(entry, include_children=False)
        linked_row_ids = [int(item) for item in (linked_row_ids or [])]
        payload["remaining_amount"] = float(FinancialReconciliationWorkspaceService._entry_remaining_amount(entry))
        payload["is_reconciled"] = FinancialService.is_entry_reconciled(entry)
        payload["linked_row_ids"] = linked_row_ids
        payload["linked_rows_count"] = len(linked_row_ids)
        payload["match_mode"] = "N:1" if len(linked_row_ids) > 1 else ("1:1" if len(linked_row_ids) == 1 else "unmatched")
        return payload

    @staticmethod
    def _serialize_open_title(
        entry: FinancialEntry,
        *,
        linked_row_ids: Optional[Sequence[int]] = None,
    ) -> Dict:
        payload = FinancialReconciliationWorkspaceService._serialize_system_entry(
            entry,
            linked_row_ids=linked_row_ids,
        )
        schedule = None
        if entry.financial_schedule_id:
            schedule = FinancialSchedule.query.filter(
                FinancialSchedule.id == entry.financial_schedule_id,
                FinancialSchedule.company_id == entry.company_id,
                FinancialSchedule.deleted_at.is_(None),
            ).first()
        payload["title"] = {
            "schedule_id": getattr(schedule, "id", None),
            "schedule_code": getattr(schedule, "schedule_code", None),
            "name": getattr(schedule, "name", None) or payload.get("description"),
            "status": getattr(schedule, "status", None) or payload.get("status"),
            "next_due_date": (
                getattr(schedule, "next_due_date", None).isoformat()
                if getattr(schedule, "next_due_date", None)
                else payload.get("due_date")
            ),
            "template_amount": float(getattr(schedule, "template_amount", 0) or payload.get("original_amount") or 0),
            "source": "schedule" if schedule else "entry",
        }
        payload["can_title_settle"] = payload["remaining_amount"] > 0
        return payload

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
    def _serialize_row(row: FinancialImportRow, row_matches: Optional[Sequence[FinancialReconciliationMatch]] = None) -> Dict:
        payload = row.to_dict()
        row_matches = list(row_matches or [])
        match = FinancialReconciliationWorkspaceService._get_primary_match(row_matches)
        match_snapshot = FinancialReconciliationWorkspaceService._build_row_match_snapshot(row_matches)
        created_entry = None
        if row.created_entry_id:
            created_entry = FinancialEntry.query.filter(
                FinancialEntry.id == row.created_entry_id,
                FinancialEntry.company_id == row.company_id,
                FinancialEntry.deleted_at.is_(None),
            ).first()
        payload["match"] = match.to_dict() if match else None
        payload["matches"] = match_snapshot
        payload["created_entry"] = FinancialService.serialize_entry(created_entry, include_children=False) if created_entry else None
        payload["can_create_entry"] = not bool(row.created_entry_id)
        payload["is_fully_reconciled"] = bool(match_snapshot["confirmed_count"] or row.created_entry_id)
        payload["needs_manual_action"] = not payload["is_fully_reconciled"]
        return payload

    @staticmethod
    def _load_workspace_entries(
        *,
        company_id: int,
        bank_account_id: int,
        rows: Sequence[FinancialImportRow],
    ) -> List[FinancialEntry]:
        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.status.in_(["scheduled", "posted", "partially_settled", "settled"]),
            FinancialEntry.bank_account_id == bank_account_id,
        )

        reference_dates = [item.occurred_on or item.due_date for item in rows if item.occurred_on or item.due_date]
        if reference_dates:
            start_date = min(reference_dates)
            end_date = max(reference_dates)
            query = query.filter(
                db.or_(
                    FinancialEntry.occurred_on.between(start_date, end_date),
                    FinancialEntry.due_date.between(start_date, end_date),
                    FinancialEntry.competence_date.between(start_date, end_date),
                )
            )

        return (
            query.order_by(
                FinancialEntry.occurred_on.desc(),
                FinancialEntry.due_date.desc(),
                FinancialEntry.id.desc(),
            )
            .limit(200)
            .all()
        )

    @staticmethod
    def _load_open_titles(
        *,
        company_id: int,
        rows: Sequence[FinancialImportRow],
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
    ) -> List[FinancialEntry]:
        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.entry_type.in_(["payable", "receivable"]),
            FinancialEntry.status.in_(["scheduled", "posted", "partially_settled"]),
        )

        if due_date_from:
            query = query.filter(FinancialEntry.due_date >= due_date_from)
        if due_date_to:
            query = query.filter(FinancialEntry.due_date <= due_date_to)

        reference_dates = [item.occurred_on or item.due_date for item in rows if item.occurred_on or item.due_date]
        has_explicit_due_date_filter = bool(due_date_from or due_date_to)
        if reference_dates and not has_explicit_due_date_filter:
            start_date = min(reference_dates) - timedelta(days=120)
            end_date = max(reference_dates) + timedelta(days=120)
            query = query.filter(
                db.or_(
                    FinancialEntry.occurred_on.between(start_date, end_date),
                    FinancialEntry.due_date.between(start_date, end_date),
                    FinancialEntry.competence_date.between(start_date, end_date),
                )
            )

        movement_natures = {
            str(item.movement_nature or "").strip().lower()
            for item in rows
            if str(item.movement_nature or "").strip()
        }
        if len(movement_natures) == 1:
            query = query.filter(FinancialEntry.movement_nature == next(iter(movement_natures)))

        candidates = (
            query.order_by(
                FinancialEntry.due_date.asc(),
                FinancialEntry.competence_date.asc(),
                FinancialEntry.id.desc(),
            )
            .limit(200)
            .all()
        )
        return [
            entry
            for entry in candidates
            if FinancialReconciliationWorkspaceService._entry_remaining_amount(entry) > 0
        ]

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
            match_groups = {
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
                if not row.created_entry_id and not (
                    match_groups.get(row.id) and str(match_groups[row.id].match_status or "").lower() == "confirmed"
                )
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
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
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
        match_groups = FinancialReconciliationWorkspaceService._group_matches_by_row(matches)
        rows_payload = [
            FinancialReconciliationWorkspaceService._serialize_row(row, match_groups.get(int(row.id), []))
            for row in rows
        ]
        pending_rows = [row for row in rows_payload if row.get("needs_manual_action")]
        suggested_rows = [row for row in rows_payload if (row.get("matches") or {}).get("suggested_count")]
        confirmed_rows = [row for row in rows_payload if (row.get("matches") or {}).get("confirmed_count") or row.get("created_entry_id")]

        linked_entry_ids: Dict[int, List[int]] = {}
        for row in rows_payload:
            row_id = int(row["id"])
            if row.get("created_entry_id"):
                linked_entry_ids.setdefault(int(row["created_entry_id"]), []).append(row_id)
            for entry_id in (row.get("matches") or {}).get("linked_entry_ids", []):
                linked_entry_ids.setdefault(int(entry_id), []).append(row_id)

        system_entries = FinancialReconciliationWorkspaceService._load_workspace_entries(
            company_id=company_id,
            bank_account_id=bank_account_id,
            rows=rows,
        )
        system_rows = [
            FinancialReconciliationWorkspaceService._serialize_system_entry(
                entry,
                linked_row_ids=linked_entry_ids.get(int(entry.id), []),
            )
            for entry in system_entries
        ]
        system_unmatched_rows = [
            item for item in system_rows
            if not item["linked_rows_count"] and not item["is_reconciled"]
        ]

        open_titles = FinancialReconciliationWorkspaceService._load_open_titles(
            company_id=company_id,
            rows=rows,
            due_date_from=due_date_from,
            due_date_to=due_date_to,
        )
        open_title_rows = [
            FinancialReconciliationWorkspaceService._serialize_open_title(
                entry,
                linked_row_ids=linked_entry_ids.get(int(entry.id), []),
            )
            for entry in open_titles
        ]
        open_title_unmatched_rows = [
            item for item in open_title_rows
            if item.get("can_title_settle") and not item["is_reconciled"]
        ]

        return {
            "bank_account": account.to_dict(),
            "selected_batch": selected_batch.to_dict() if selected_batch else None,
            "available_batches": [batch.to_dict() for batch in batches],
            "rows": rows_payload,
            "bank_rows": rows_payload,
            "bank_rows_without_link": pending_rows,
            "bank_rows_with_suggestion": suggested_rows,
            "bank_rows_reconciled": confirmed_rows,
            "system_rows": system_rows,
            "system_rows_without_link": system_unmatched_rows,
            "open_title_rows": open_title_rows,
            "open_title_rows_without_link": open_title_unmatched_rows,
            "summary": {
                "total_rows": len(rows),
                "pending_rows": len(pending_rows),
                "confirmed_matches": sum(1 for item in matches if item.match_status == "confirmed"),
                "suggested_matches": sum(1 for item in matches if item.match_status == "suggested"),
                "unmatched_bank_rows": len(pending_rows),
                "unmatched_system_rows": len(system_unmatched_rows),
                "system_rows": len(system_rows),
                "open_titles": len(open_title_rows),
            },
            "filters": {
                "due_date_from": due_date_from.isoformat() if due_date_from else None,
                "due_date_to": due_date_to.isoformat() if due_date_to else None,
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
