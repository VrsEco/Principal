from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence

from models import db
from models.financial import FinancialEntry, FinancialImportRow, FinancialSettlement
from services.financial_service import FinancialService


class FinancialBankStatementRepairService:
    """Reparos idempotentes para movimentos que devem compor o Extrato Bancário."""

    @staticmethod
    def repair_missing_bank_accounts_from_reconciliation(
        *,
        company_id: int,
        apply: bool = False,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        query = (
            db.session.query(FinancialSettlement, FinancialEntry)
            .join(FinancialEntry, FinancialEntry.id == FinancialSettlement.financial_entry_id)
            .filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.bank_account_id.is_(None),
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
                FinancialEntry.company_id == company_id,
                FinancialEntry.deleted_at.is_(None),
            )
            .order_by(FinancialSettlement.id.asc())
        )
        if limit:
            query = query.limit(int(limit))

        scanned = 0
        updated = 0
        skipped = 0
        samples = []
        for settlement, entry in query.all():
            scanned += 1
            if not FinancialBankStatementRepairService._looks_like_reconciliation_settlement(settlement):
                skipped += 1
                continue

            bank_account_id = FinancialBankStatementRepairService._resolve_reconciliation_bank_account_id(
                company_id=company_id,
                settlement=settlement,
                entry=entry,
            )
            if not bank_account_id:
                skipped += 1
                samples.append(
                    {
                        "settlement_id": getattr(settlement, "id", None),
                        "entry_id": getattr(entry, "id", None),
                        "reason": "bank_account_not_resolved",
                    }
                )
                continue

            updated += 1
            samples.append(
                {
                    "settlement_id": getattr(settlement, "id", None),
                    "entry_id": getattr(entry, "id", None),
                    "bank_account_id": bank_account_id,
                }
            )
            if apply:
                settlement.bank_account_id = bank_account_id
                metadata = dict(getattr(settlement, "metadata_json", {}) or {})
                settlement.metadata_json = {
                    **metadata,
                    "bank_statement_repair": {
                        **dict(metadata.get("bank_statement_repair") or {}),
                        "bank_account_backfilled": True,
                        "source": "reconciliation_row_or_entry",
                    },
                }

        if apply:
            db.session.commit()
        else:
            db.session.rollback()

        return {
            "company_id": company_id,
            "apply": apply,
            "scanned": scanned,
            "updated": updated,
            "skipped": skipped,
            "samples": samples[:20],
        }

    @staticmethod
    def backfill_missing_transfer_settlements(
        *,
        company_id: int,
        apply: bool = False,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.entry_type == "transfer",
            FinancialEntry.status != "cancelled",
        ).order_by(FinancialEntry.id.asc())
        if limit:
            query = query.limit(int(limit))

        scanned = 0
        created = 0
        skipped = 0
        errors = []
        samples = []

        for entry in query.all():
            scanned += 1
            if not FinancialBankStatementRepairService._looks_like_transfer_entry(entry):
                skipped += 1
                continue
            if FinancialBankStatementRepairService._has_active_settlement(company_id=company_id, entry_id=entry.id):
                skipped += 1
                continue

            payload, reason = FinancialBankStatementRepairService._build_transfer_settlement_payload(company_id=company_id, entry=entry)
            if reason:
                skipped += 1
                samples.append({"entry_id": getattr(entry, "id", None), "reason": reason})
                continue

            samples.append(
                {
                    "entry_id": getattr(entry, "id", None),
                    "settlement_code": payload["settlement_code"],
                    "bank_account_id": payload["bank_account_id"],
                    "principal_amount": str(payload["principal_amount"]),
                }
            )
            if apply:
                settlement, error = FinancialService.create_settlement(payload=payload, allowed_company_ids=[company_id])
                if error:
                    errors.append({"entry_id": getattr(entry, "id", None), "error": error})
                    db.session.rollback()
                    continue
                created += 1
            else:
                created += 1

        if not apply:
            db.session.rollback()

        return {
            "company_id": company_id,
            "apply": apply,
            "scanned": scanned,
            "created": created,
            "skipped": skipped,
            "errors": errors[:20],
            "samples": samples[:20],
        }

    @staticmethod
    def repair_bank_statement_movements(
        *,
        company_id: int,
        apply: bool = False,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        return {
            "company_id": company_id,
            "apply": apply,
            "reconciliation_bank_accounts": FinancialBankStatementRepairService.repair_missing_bank_accounts_from_reconciliation(
                company_id=company_id,
                apply=apply,
                limit=limit,
            ),
            "transfer_settlements": FinancialBankStatementRepairService.backfill_missing_transfer_settlements(
                company_id=company_id,
                apply=apply,
                limit=limit,
            ),
        }

    @staticmethod
    def _looks_like_reconciliation_settlement(settlement: Any) -> bool:
        metadata = dict(getattr(settlement, "metadata_json", {}) or {})
        external_reference = str(getattr(settlement, "external_reference", "") or "")
        mode = str(metadata.get("mode") or "").strip().lower()
        return (
            external_reference.startswith("reconciliation-match:")
            or external_reference.startswith("reconciliation-row:")
            or mode in {"auto_settlement_from_reconciliation", "created_from_bank_reconciliation"}
            or bool(metadata.get("reconciliation_match_id"))
            or bool(metadata.get("import_row_id"))
        )

    @staticmethod
    def _resolve_reconciliation_bank_account_id(*, company_id: int, settlement: Any, entry: Any) -> Optional[int]:
        metadata = dict(getattr(settlement, "metadata_json", {}) or {})
        row_id = metadata.get("import_row_id") or metadata.get("reconciliation_created_from_row_id")
        if row_id:
            row = FinancialImportRow.query.filter(
                FinancialImportRow.company_id == company_id,
                FinancialImportRow.id == int(row_id),
                FinancialImportRow.deleted_at.is_(None),
            ).first()
            row_payload = dict(getattr(row, "normalized_payload", {}) or {}) if row else {}
            bank_account_id = row_payload.get("bank_account_id")
            if bank_account_id:
                return int(bank_account_id)
        entry_bank_account_id = getattr(entry, "bank_account_id", None)
        return int(entry_bank_account_id) if entry_bank_account_id else None

    @staticmethod
    def _looks_like_transfer_entry(entry: Any) -> bool:
        metadata = dict(getattr(entry, "metadata_json", {}) or {})
        return getattr(entry, "entry_type", None) == "transfer" or bool(metadata.get("is_transfer"))

    @staticmethod
    def _has_active_settlement(*, company_id: int, entry_id: int) -> bool:
        return (
            FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.financial_entry_id == entry_id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            ).first()
            is not None
        )

    @staticmethod
    def _build_transfer_settlement_payload(*, company_id: int, entry: Any) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        bank_account_id = getattr(entry, "bank_account_id", None)
        if not bank_account_id:
            return None, "missing_bank_account"

        principal_amount = Decimal(str(getattr(entry, "original_amount", None) or "0"))
        if principal_amount <= Decimal("0"):
            return None, "invalid_amount"

        settlement_date = (
            getattr(entry, "occurred_on", None)
            or getattr(entry, "due_date", None)
            or getattr(entry, "competence_date", None)
        )
        if not isinstance(settlement_date, date):
            return None, "missing_settlement_date"

        metadata = dict(getattr(entry, "metadata_json", {}) or {})
        transfer_group_id = metadata.get("transfer_group_id") or str(getattr(entry, "entry_code", "") or f"entry-{entry.id}")
        direction = metadata.get("transfer_direction") or ("out" if getattr(entry, "movement_nature", None) == "debit" else "in")
        settlement_code = f"{str(getattr(entry, 'entry_code', '') or f'TRF-{entry.id}')[:42]}-stl"

        return {
            "company_id": company_id,
            "financial_entry_id": entry.id,
            "settlement_code": settlement_code,
            "settlement_type": "automatic_process",
            "settlement_status": "posted",
            "settlement_date": settlement_date,
            "bank_account_id": int(bank_account_id),
            "principal_amount": principal_amount,
            "external_reference": f"transfer:{transfer_group_id}:{direction}",
            "reconciliation_status": "pending",
            "created_by_user_id": getattr(entry, "created_by_user_id", None),
            "created_by_employee_id": getattr(entry, "created_by_employee_id", None),
            "created_by_agent": getattr(entry, "created_by_agent", None) or "bank_statement_repair",
            "notes": "Baixa automática histórica gerada para transferência bancária.",
            "metadata_json": {
                "is_transfer": True,
                "include_in_bank_statement": True,
                "transfer_group_id": transfer_group_id,
                "transfer_direction": direction,
                "counterpart_bank_account_id": metadata.get("counterpart_bank_account_id"),
                "counterpart_bank_account_name": metadata.get("counterpart_bank_account_name"),
                "generated_by": "financial_bank_statement_repair_service",
                "bank_statement_repair": {"transfer_settlement_backfilled": True},
            },
        }, None
