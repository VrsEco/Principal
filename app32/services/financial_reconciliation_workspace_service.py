from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import (
    FinancialBankAccount,
    FinancialChartAccount,
    FinancialCounterparty,
    FinancialEntry,
    FinancialImportBatch,
    FinancialImportRow,
    FinancialReconciliationMatch,
    FinancialSchedule,
    FinancialSettlement,
)
from services.financial_reconciliation_service import FinancialReconciliationService
from services.financial_direct_entry_service import FinancialDirectEntryService
from services.financial_import_service import FinancialImportService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_service import FinancialService
from services.financial_title_balance_service import FinancialTitleBalanceService


class FinancialReconciliationWorkspaceService:
    @staticmethod
    def _chart_account_label(company_id: int, chart_account_id: Optional[int]) -> Optional[str]:
        if not chart_account_id:
            return None
        account = FinancialChartAccount.query.filter(
            FinancialChartAccount.company_id == company_id,
            FinancialChartAccount.id == chart_account_id,
            FinancialChartAccount.deleted_at.is_(None),
        ).first()
        if not account:
            return str(chart_account_id)
        return f"{account.code} - {account.name}" if account.code else account.name

    @staticmethod
    def _counterparty_name(company_id: int, counterparty_id: Optional[int]) -> Optional[str]:
        if not counterparty_id:
            return None
        counterparty = FinancialCounterparty.query.filter(
            FinancialCounterparty.company_id == company_id,
            FinancialCounterparty.id == counterparty_id,
            FinancialCounterparty.deleted_at.is_(None),
        ).first()
        return counterparty.name if counterparty else None

    @staticmethod
    def _normalize_search_term(search_query: Optional[str]) -> str:
        return str(search_query or "").strip().lower()

    @staticmethod
    def _normalize_amount_filter(amount: Optional[Decimal]) -> Optional[Decimal]:
        if amount is None:
            return None
        try:
            return abs(Decimal(str(amount))).quantize(Decimal("0.01"))
        except Exception:
            return None

    @staticmethod
    def _amount_matches_filter(value, amount_filter: Optional[Decimal]) -> bool:
        if amount_filter is None:
            return True
        try:
            current = abs(Decimal(str(value or 0))).quantize(Decimal("0.01"))
        except Exception:
            return False
        return current == amount_filter

    @staticmethod
    def _movement_matches_filter(value, movement_nature: Optional[str]) -> bool:
        if not movement_nature:
            return True
        return str(value or "").strip().lower() == movement_nature

    @staticmethod
    def _text_matches_filter(values: Sequence[object], search_query: str) -> bool:
        if not search_query:
            return True
        haystack = " ".join(str(value or "").strip().lower() for value in values if value is not None)
        return search_query in haystack

    @staticmethod
    def _date_matches_range(value, start: Optional[date] = None, end: Optional[date] = None) -> bool:
        if not start and not end:
            return True
        if not value:
            return False
        if isinstance(value, str):
            try:
                current_value = date.fromisoformat(value[:10])
            except ValueError:
                return False
        else:
            current_value = value
        if start and current_value < start:
            return False
        if end and current_value > end:
            return False
        return True

    @staticmethod
    def _entry_latest_settlement_date(entry: FinancialEntry) -> Optional[date]:
        latest_settlement = (
            FinancialSettlement.query.filter(
                FinancialSettlement.company_id == entry.company_id,
                FinancialSettlement.financial_entry_id == entry.id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            )
            .order_by(FinancialSettlement.settlement_date.desc(), FinancialSettlement.id.desc())
            .first()
        )
        return getattr(latest_settlement, "settlement_date", None)

    @staticmethod
    def _bank_row_matches_filters(
        row: Dict,
        *,
        amount_filter: Optional[Decimal] = None,
        movement_nature: Optional[str] = None,
        search_query: str = "",
        bank_date_from: Optional[date] = None,
        bank_date_to: Optional[date] = None,
    ) -> bool:
        bank_date = row.get("occurred_on") or row.get("due_date")
        return (
            FinancialReconciliationWorkspaceService._amount_matches_filter(
                row.get("remaining_amount", row.get("original_amount", row.get("amount"))),
                amount_filter,
            )
            and FinancialReconciliationWorkspaceService._movement_matches_filter(
                row.get("movement_nature"),
                movement_nature,
            )
            and FinancialReconciliationWorkspaceService._date_matches_range(
                bank_date,
                bank_date_from,
                bank_date_to,
            )
            and FinancialReconciliationWorkspaceService._text_matches_filter(
                [
                    row.get("description"),
                    row.get("document_number"),
                    row.get("bank_reference"),
                    row.get("counterparty_name"),
                    row.get("row_number"),
                ],
                search_query,
            )
        )

    @staticmethod
    def _system_row_matches_filters(
        row: Dict,
        *,
        amount_filter: Optional[Decimal] = None,
        movement_nature: Optional[str] = None,
        search_query: str = "",
        settlement_date_from: Optional[date] = None,
        settlement_date_to: Optional[date] = None,
    ) -> bool:
        return (
            FinancialReconciliationWorkspaceService._amount_matches_filter(
                row.get("remaining_amount", row.get("original_amount", row.get("amount"))),
                amount_filter,
            )
            and FinancialReconciliationWorkspaceService._movement_matches_filter(
                row.get("movement_nature"),
                movement_nature,
            )
            and FinancialReconciliationWorkspaceService._date_matches_range(
                row.get("latest_settlement_date"),
                settlement_date_from,
                settlement_date_to,
            )
            and FinancialReconciliationWorkspaceService._text_matches_filter(
                [
                    row.get("entry_code"),
                    row.get("description"),
                    row.get("document_number"),
                    row.get("external_reference"),
                    row.get("origin_reference"),
                ],
                search_query,
            )
        )

    @staticmethod
    def _open_title_matches_filters(
        row: Dict,
        *,
        amount_filter: Optional[Decimal] = None,
        movement_nature: Optional[str] = None,
        search_query: str = "",
    ) -> bool:
        title = row.get("title") or {}
        return (
            FinancialReconciliationWorkspaceService._amount_matches_filter(
                row.get("remaining_amount", row.get("original_amount", row.get("amount"))),
                amount_filter,
            )
            and FinancialReconciliationWorkspaceService._movement_matches_filter(
                row.get("movement_nature"),
                movement_nature,
            )
            and FinancialReconciliationWorkspaceService._text_matches_filter(
                [
                    row.get("entry_code"),
                    row.get("description"),
                    row.get("document_number"),
                    title.get("schedule_code"),
                    title.get("name"),
                ],
                search_query,
            )
        )

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
    def _settlement_reconciliation_amount(settlement: FinancialSettlement) -> Decimal:
        amount = Decimal(settlement.net_amount or 0)
        if amount > 0:
            return amount
        amount = Decimal(settlement.gross_amount or 0)
        if amount > 0:
            return amount
        return Decimal(settlement.principal_amount or 0)

    @staticmethod
    def _serialize_system_entry(
        entry: FinancialEntry,
        *,
        linked_row_ids: Optional[Sequence[int]] = None,
    ) -> Dict:
        payload = FinancialService.serialize_entry(entry, include_children=False)
        linked_row_ids = [int(item) for item in (linked_row_ids or [])]
        latest_settlement_date = FinancialReconciliationWorkspaceService._entry_latest_settlement_date(entry)
        payload["remaining_amount"] = float(FinancialReconciliationWorkspaceService._entry_remaining_amount(entry))
        payload["is_reconciled"] = FinancialService.is_entry_reconciled(entry)
        payload["latest_settlement_date"] = latest_settlement_date.isoformat() if latest_settlement_date else None
        payload["linked_row_ids"] = linked_row_ids
        payload["linked_rows_count"] = len(linked_row_ids)
        payload["match_mode"] = "N:1" if len(linked_row_ids) > 1 else ("1:1" if len(linked_row_ids) == 1 else "unmatched")
        return payload

    @staticmethod
    def _serialize_system_settlement(
        settlement: FinancialSettlement,
        entry: FinancialEntry,
        *,
        linked_row_ids: Optional[Sequence[int]] = None,
    ) -> Dict:
        payload = FinancialService.serialize_entry(entry, include_children=False)
        linked_row_ids = [int(item) for item in (linked_row_ids or [])]
        reconciliation_amount = FinancialReconciliationWorkspaceService._settlement_reconciliation_amount(settlement)
        title_original_amount = Decimal(entry.original_amount or 0)
        title_remaining_amount = FinancialReconciliationWorkspaceService._entry_remaining_amount(entry)
        is_reconciled = str(settlement.reconciliation_status or "").lower() in {"matched", "reconciled"}
        payload.update(
            {
                "id": -int(settlement.id),
                "financial_entry_id": entry.id,
                "financial_settlement_id": settlement.id,
                "source_type": "settlement",
                "entry_code": settlement.settlement_code or payload.get("entry_code"),
                "description": payload.get("description") or settlement.notes or "-",
                "occurred_on": settlement.settlement_date.isoformat() if settlement.settlement_date else None,
                "due_date": settlement.settlement_date.isoformat() if settlement.settlement_date else None,
                "competence_date": settlement.settlement_date.isoformat() if settlement.settlement_date else None,
                "original_amount": float(reconciliation_amount),
                "remaining_amount": float(reconciliation_amount),
                "amount": float(reconciliation_amount),
                "settlement_amount": float(reconciliation_amount),
                "title_original_amount": float(title_original_amount),
                "title_remaining_amount": float(title_remaining_amount),
                "settlement_code": settlement.settlement_code,
                "settlement_status": settlement.settlement_status,
                "reconciliation_status": settlement.reconciliation_status,
                "is_reconciled": is_reconciled,
                "latest_settlement_date": settlement.settlement_date.isoformat() if settlement.settlement_date else None,
                "linked_row_ids": linked_row_ids,
                "linked_rows_count": len(linked_row_ids),
                "match_mode": "N:1" if len(linked_row_ids) > 1 else ("1:1" if len(linked_row_ids) == 1 else "unmatched"),
                "navigation_url": f"/financial/entries/{entry.id}?company_id={entry.company_id}",
                "counterparty_name": FinancialReconciliationWorkspaceService._counterparty_name(
                    entry.company_id,
                    entry.counterparty_id,
                ),
                "chart_account_label": FinancialReconciliationWorkspaceService._chart_account_label(
                    entry.company_id,
                    entry.chart_account_id,
                ),
            }
        )
        return payload

    @staticmethod
    def _serialize_open_title(
        entry: FinancialEntry | FinancialSchedule,
        *,
        linked_row_ids: Optional[Sequence[int]] = None,
    ) -> Dict:
        if isinstance(entry, FinancialSchedule):
            balance = FinancialTitleBalanceService.calculate_for_schedule(schedule=entry)
            remaining_amount = float(balance.get("total_open") or balance.get("principal_open") or 0)
            payload = {
                "id": -int(entry.id),
                "financial_entry_id": None,
                "financial_schedule_id": entry.id,
                "entry_code": entry.schedule_code,
                "description": entry.description or entry.name,
                "document_number": None,
                "entry_type": entry.entry_type,
                "movement_nature": entry.movement_nature,
                "status": entry.status,
                "due_date": entry.next_due_date.isoformat() if entry.next_due_date else None,
                "occurred_on": None,
                "competence_date": entry.competence_date.isoformat() if entry.competence_date else None,
                "original_amount": float(entry.template_amount or 0),
                "remaining_amount": remaining_amount,
                "is_reconciled": False,
                "linked_row_ids": [],
                "linked_rows_count": 0,
                "match_mode": "schedule_open",
                "navigation_url": f"/financial/schedules/{entry.id}?company_id={entry.company_id}",
                "chart_account_id": getattr(entry, "chart_account_id", None),
                "counterparty_id": getattr(entry, "counterparty_id", None),
                "counterparty_name": FinancialReconciliationWorkspaceService._counterparty_name(
                    entry.company_id,
                    getattr(entry, "counterparty_id", None),
                ),
                "chart_account_label": FinancialReconciliationWorkspaceService._chart_account_label(
                    entry.company_id,
                    getattr(entry, "chart_account_id", None),
                ),
            }
            payload["title"] = {
                "schedule_id": entry.id,
                "schedule_code": entry.schedule_code,
                "name": entry.name or payload.get("description"),
                "status": entry.status,
                "next_due_date": entry.next_due_date.isoformat() if entry.next_due_date else None,
                "template_amount": float(entry.template_amount or 0),
                "source": "schedule",
            }
            payload["can_title_settle"] = remaining_amount > 0
            return payload

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
        counterparty_id = getattr(entry, "counterparty_id", None) or getattr(schedule, "counterparty_id", None)
        chart_account_id = getattr(entry, "chart_account_id", None) or getattr(schedule, "chart_account_id", None)
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
        payload["financial_schedule_id"] = getattr(schedule, "id", None)
        if payload.get("financial_schedule_id"):
            payload["navigation_url"] = f"/financial/schedules/{payload['financial_schedule_id']}?company_id={entry.company_id}"
        else:
            payload["navigation_url"] = f"/financial/entries/{entry.id}?company_id={entry.company_id}"
        payload["latest_settlement_date"] = payload.get("latest_settlement_date")
        payload["can_title_settle"] = payload["remaining_amount"] > 0
        payload["counterparty_id"] = counterparty_id
        payload["counterparty_name"] = payload.get("counterparty_name") or FinancialReconciliationWorkspaceService._counterparty_name(
            entry.company_id,
            counterparty_id,
        )
        payload["chart_account_id"] = chart_account_id
        payload["chart_account_label"] = payload.get("chart_account_label") or FinancialReconciliationWorkspaceService._chart_account_label(
            entry.company_id,
            chart_account_id,
        )
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
    def _load_workspace_settlements(
        *,
        company_id: int,
        bank_account_id: int,
        rows: Sequence[FinancialImportRow],
        movement_nature: Optional[str] = None,
    ) -> List[Tuple[FinancialSettlement, FinancialEntry]]:
        query = (
            db.session.query(FinancialSettlement, FinancialEntry)
            .join(FinancialEntry, FinancialEntry.id == FinancialSettlement.financial_entry_id)
            .filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.bank_account_id == bank_account_id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
            )
        )
        if movement_nature:
            query = query.filter(FinancialEntry.movement_nature == movement_nature)

        reference_dates = [item.occurred_on or item.due_date for item in rows if item.occurred_on or item.due_date]
        if reference_dates:
            start_date = min(reference_dates)
            end_date = max(reference_dates)
            query = query.filter(FinancialSettlement.settlement_date.between(start_date, end_date))

        return (
            query.order_by(
                FinancialSettlement.settlement_date.desc(),
                FinancialSettlement.id.desc(),
            )
            .limit(300)
            .all()
        )

    @staticmethod
    def _load_workspace_entries(
        *,
        company_id: int,
        bank_account_id: int,
        rows: Sequence[FinancialImportRow],
        movement_nature: Optional[str] = None,
    ) -> List[FinancialEntry]:
        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.status.in_(["scheduled", "posted", "partially_settled", "settled"]),
            FinancialEntry.bank_account_id == bank_account_id,
        )
        if movement_nature:
            query = query.filter(FinancialEntry.movement_nature == movement_nature)

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
        movement_nature: Optional[str] = None,
    ) -> List[FinancialEntry]:
        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.entry_type.in_(["payable", "receivable"]),
            FinancialEntry.status.in_(["scheduled", "posted", "partially_settled"]),
        )
        if movement_nature:
            query = query.filter(FinancialEntry.movement_nature == movement_nature)

        if due_date_from:
            query = query.filter(FinancialEntry.due_date >= due_date_from)
        if due_date_to:
            query = query.filter(FinancialEntry.due_date <= due_date_to)

        entry_candidates = (
            query.order_by(
                FinancialEntry.due_date.asc(),
                FinancialEntry.competence_date.asc(),
                FinancialEntry.id.desc(),
            )
            .limit(200)
            .all()
        )
        open_entry_candidates = [
            entry
            for entry in entry_candidates
            if FinancialReconciliationWorkspaceService._entry_remaining_amount(entry) > 0
        ]
        represented_schedule_ids = {
            int(entry.financial_schedule_id)
            for entry in open_entry_candidates
            if getattr(entry, "financial_schedule_id", None)
        }

        schedule_query = FinancialSchedule.query.filter(
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
            FinancialSchedule.entry_type.in_(["payable", "receivable"]),
            FinancialSchedule.status == "active",
        )
        if movement_nature:
            schedule_query = schedule_query.filter(FinancialSchedule.movement_nature == movement_nature)
        if due_date_from:
            schedule_query = schedule_query.filter(FinancialSchedule.next_due_date >= due_date_from)
        if due_date_to:
            schedule_query = schedule_query.filter(FinancialSchedule.next_due_date <= due_date_to)

        open_schedule_candidates = []
        for schedule in (
            schedule_query.order_by(
                FinancialSchedule.next_due_date.asc(),
                FinancialSchedule.id.desc(),
            )
            .limit(200)
            .all()
        ):
            if schedule.id in represented_schedule_ids:
                continue
            balance = FinancialTitleBalanceService.calculate_for_schedule(schedule=schedule)
            if float(balance.get("total_open") or balance.get("principal_open") or 0) <= 0:
                continue
            open_schedule_candidates.append(schedule)

        combined_candidates = [*open_entry_candidates, *open_schedule_candidates]
        combined_candidates.sort(
            key=lambda item: (
                getattr(item, "next_due_date", None)
                or getattr(item, "due_date", None)
                or getattr(item, "competence_date", None)
                or date.max,
                -int(getattr(item, "id", 0) or 0),
            )
        )
        return combined_candidates[:200]

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
        amount: Optional[Decimal] = None,
        movement_nature: Optional[str] = None,
        search_query: Optional[str] = None,
        bank_date_from: Optional[date] = None,
        bank_date_to: Optional[date] = None,
        settlement_date_from: Optional[date] = None,
        settlement_date_to: Optional[date] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        if not bank_account_id:
            return None, "Conta bancária é obrigatória para abrir a conciliação."
        amount_filter = FinancialReconciliationWorkspaceService._normalize_amount_filter(amount)
        movement_filter = movement_nature if movement_nature in {"credit", "debit"} else None
        normalized_search_query = FinancialReconciliationWorkspaceService._normalize_search_term(search_query)

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
        filtered_rows_payload = [
            row
            for row in rows_payload
            if FinancialReconciliationWorkspaceService._bank_row_matches_filters(
                row,
                amount_filter=amount_filter,
                movement_nature=movement_filter,
                search_query=normalized_search_query,
                bank_date_from=bank_date_from,
                bank_date_to=bank_date_to,
            )
        ]
        pending_rows = [row for row in filtered_rows_payload if row.get("needs_manual_action")]
        suggested_rows = [row for row in filtered_rows_payload if (row.get("matches") or {}).get("suggested_count")]
        confirmed_rows = [row for row in filtered_rows_payload if (row.get("matches") or {}).get("confirmed_count") or row.get("created_entry_id")]

        linked_entry_ids: Dict[int, List[int]] = {}
        linked_settlement_ids: Dict[int, List[int]] = {}
        for row in rows_payload:
            row_id = int(row["id"])
            if row.get("created_entry_id"):
                linked_entry_ids.setdefault(int(row["created_entry_id"]), []).append(row_id)
            for match in (row.get("matches") or {}).get("all_matches", []):
                metadata = match.get("metadata_json") or {}
                settlement_id = metadata.get("financial_settlement_id")
                if settlement_id and str(match.get("match_status") or "").lower() != "rejected":
                    linked_settlement_ids.setdefault(int(settlement_id), []).append(row_id)
            for entry_id in (row.get("matches") or {}).get("linked_entry_ids", []):
                linked_entry_ids.setdefault(int(entry_id), []).append(row_id)

        system_settlements = FinancialReconciliationWorkspaceService._load_workspace_settlements(
            company_id=company_id,
            bank_account_id=bank_account_id,
            rows=rows,
            movement_nature=movement_filter,
        )
        system_rows = [
            FinancialReconciliationWorkspaceService._serialize_system_settlement(
                settlement,
                entry,
                linked_row_ids=linked_settlement_ids.get(int(settlement.id), []),
            )
            for settlement, entry in system_settlements
        ]
        system_rows = [
            item
            for item in system_rows
            if FinancialReconciliationWorkspaceService._system_row_matches_filters(
                item,
                amount_filter=amount_filter,
                movement_nature=movement_filter,
                search_query=normalized_search_query,
                settlement_date_from=settlement_date_from,
                settlement_date_to=settlement_date_to,
            )
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
            movement_nature=movement_filter,
        )
        open_title_rows = [
            FinancialReconciliationWorkspaceService._serialize_open_title(
                entry,
                linked_row_ids=linked_entry_ids.get(int(entry.id), []),
            )
            for entry in open_titles
        ]
        open_title_rows = [
            item
            for item in open_title_rows
            if FinancialReconciliationWorkspaceService._open_title_matches_filters(
                item,
                amount_filter=amount_filter,
                movement_nature=movement_filter,
                search_query=normalized_search_query,
            )
        ]
        open_title_unmatched_rows = [
            item for item in open_title_rows
            if item.get("can_title_settle") and not item["is_reconciled"]
        ]

        return {
            "bank_account": account.to_dict(),
            "selected_batch": FinancialImportService.serialize_import_batch(selected_batch) if selected_batch else None,
            "available_batches": [FinancialImportService.serialize_import_batch(batch) for batch in batches],
            "rows": filtered_rows_payload,
            "bank_rows": filtered_rows_payload,
            "bank_rows_without_link": pending_rows,
            "bank_rows_with_suggestion": suggested_rows,
            "bank_rows_reconciled": confirmed_rows,
            "system_rows": system_rows,
            "system_rows_without_link": system_unmatched_rows,
            "open_title_rows": open_title_rows,
            "open_title_rows_without_link": open_title_unmatched_rows,
            "summary": {
                "total_rows": len(filtered_rows_payload),
                "pending_rows": len(pending_rows),
                "confirmed_matches": sum((item.get("matches") or {}).get("confirmed_count", 0) for item in filtered_rows_payload),
                "suggested_matches": sum((item.get("matches") or {}).get("suggested_count", 0) for item in filtered_rows_payload),
                "unmatched_bank_rows": len(pending_rows),
                "unmatched_system_rows": len(system_unmatched_rows),
                "system_rows": len(system_rows),
                "open_titles": len(open_title_rows),
            },
            "filters": {
                "due_date_from": due_date_from.isoformat() if due_date_from else None,
                "due_date_to": due_date_to.isoformat() if due_date_to else None,
                "amount": str(amount_filter) if amount_filter is not None else None,
                "movement_nature": movement_filter,
                "search_query": normalized_search_query or None,
                "bank_date_from": bank_date_from.isoformat() if bank_date_from else None,
                "bank_date_to": bank_date_to.isoformat() if bank_date_to else None,
                "settlement_date_from": settlement_date_from.isoformat() if settlement_date_from else None,
                "settlement_date_to": settlement_date_to.isoformat() if settlement_date_to else None,
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

        direct_payload = {
            "company_id": company_id,
            "entry_type": payload.get("entry_type")
            or ("receivable" if (payload.get("movement_nature") or row.movement_nature) == "credit" else "payable"),
            "description": payload.get("description") or row.description or f"Conciliação linha {row.row_number}",
            "document_number": payload.get("document_number") or row.document_number,
            "competence_date": payload.get("competence_date") or row.occurred_on or row.due_date or batch.imported_at.date(),
            "due_date": payload.get("due_date") or row.due_date or row.occurred_on or batch.imported_at.date(),
            "occurred_on": payload.get("occurred_on") or row.occurred_on or row.due_date or batch.imported_at.date(),
            "original_amount": abs(Decimal(str(payload.get("original_amount") or row.amount or Decimal("0")))),
            "bank_account_id": payload.get("bank_account_id") or (row.normalized_payload or {}).get("bank_account_id"),
            "counterparty_id": payload.get("counterparty_id"),
            "chart_account_id": payload.get("chart_account_id"),
            "cost_center_id": payload.get("cost_center_id"),
            "notes": payload.get("notes"),
            "allocations": payload.get("allocations") or [],
            "metadata_json": {
                **dict(payload.get("metadata_json") or {}),
                "reconciliation_created_from_row_id": row.id,
                "reconciliation_batch_id": batch.id,
                "reconciliation_batch_code": batch.batch_code,
                "reconciliation_bank_reference": row.bank_reference,
                "origin_type": batch.source_type,
                "origin_reference": batch.batch_code,
                "reconciled": True,
            },
        }
        if not direct_payload["bank_account_id"]:
            return None, "A linha do extrato precisa estar vinculada a uma conta bancária para criar o lançamento."

        result, error = FinancialDirectEntryService.create_direct_entry(
            payload=direct_payload,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            row.error_message = error
            db.session.commit()
            return None, error

        entry_payload = dict((result or {}).get("entry") or {})
        settlement_payload = dict((result or {}).get("settlement") or {})
        entry_id = entry_payload.get("id")
        settlement_id = settlement_payload.get("id")
        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        settlement = FinancialSettlement.query.filter(
            FinancialSettlement.id == settlement_id,
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
        ).first()
        if not entry or not settlement:
            row.error_message = "Falha ao localizar título/baixa criados para a conciliação."
            db.session.commit()
            return None, row.error_message

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
