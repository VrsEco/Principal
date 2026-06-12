from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence, Tuple
from uuid import uuid4

from flask_login import current_user

from models import db
from models.financial import FinancialBankAccount, FinancialEntry
from schemas.financial import FinancialTransferCreateInput
from services.financial_service import FinancialService


class FinancialTransferService:
    @staticmethod
    def create_transfer(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialTransferCreateInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para transferência bancária: {exc}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        if data.source_bank_account_id == data.destination_bank_account_id:
            return None, "Selecione contas bancárias diferentes para origem e destino."

        source_account = FinancialTransferService._load_account(
            company_id=data.company_id,
            bank_account_id=data.source_bank_account_id,
        )
        if not source_account:
            return None, "Conta bancária de origem não encontrada no escopo da empresa."

        destination_account = FinancialTransferService._load_account(
            company_id=data.company_id,
            bank_account_id=data.destination_bank_account_id,
        )
        if not destination_account:
            return None, "Conta bancária de destino não encontrada no escopo da empresa."

        transfer_group_id = f"trf-{uuid4().hex[:12]}"
        occurred_on = data.occurred_on
        entry_date = data.competence_date or occurred_on
        actor_user_id = data.created_by_user_id or getattr(current_user, "id", None)
        actor_employee_id = data.created_by_employee_id or getattr(current_user, "employee_id", None)
        actor_name = str(getattr(current_user, "name", "") or getattr(current_user, "email", "") or "").strip() or None

        base_metadata = {
            **(data.metadata_json or {}),
            "is_transfer": True,
            "transfer_group_id": transfer_group_id,
            "transfer_scope": "bank_account_to_bank_account",
            "transfer_document_number": data.document_number,
            "audit": {
                "actor": {
                    "user_id": actor_user_id,
                    "employee_id": actor_employee_id,
                    "user_name": actor_name,
                    "agent": data.created_by_agent or "app32",
                }
            },
        }

        out_payload = {
            "company_id": data.company_id,
            "entry_code": f"{transfer_group_id}-out",
            "entry_type": "transfer",
            "movement_nature": "debit",
            "origin_type": "manual",
            "status": "posted",
            "review_status": "approved",
            "description": data.description,
            "document_number": data.document_number or transfer_group_id.upper(),
            "competence_date": entry_date,
            "due_date": occurred_on,
            "occurred_on": occurred_on,
            "original_amount": data.original_amount,
            "bank_account_id": source_account.id,
            "created_by_user_id": actor_user_id,
            "created_by_employee_id": actor_employee_id,
            "created_by_agent": data.created_by_agent or "app32",
            "notes": data.notes,
            "metadata_json": {
                **base_metadata,
                "transfer_direction": "out",
                "counterpart_bank_account_id": destination_account.id,
                "counterpart_bank_account_name": destination_account.name,
            },
        }
        in_payload = {
            "company_id": data.company_id,
            "entry_code": f"{transfer_group_id}-in",
            "entry_type": "transfer",
            "movement_nature": "credit",
            "origin_type": "manual",
            "status": "posted",
            "review_status": "approved",
            "description": data.description,
            "document_number": data.document_number or transfer_group_id.upper(),
            "competence_date": entry_date,
            "due_date": occurred_on,
            "occurred_on": occurred_on,
            "original_amount": data.original_amount,
            "bank_account_id": destination_account.id,
            "created_by_user_id": actor_user_id,
            "created_by_employee_id": actor_employee_id,
            "created_by_agent": data.created_by_agent or "app32",
            "notes": data.notes,
            "metadata_json": {
                **base_metadata,
                "transfer_direction": "in",
                "counterpart_bank_account_id": source_account.id,
                "counterpart_bank_account_name": source_account.name,
            },
        }

        source_entry, error = FinancialService.create_entry(
            payload=out_payload,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        destination_entry, error = FinancialService.create_entry(
            payload=in_payload,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            FinancialTransferService._cleanup_entry(company_id=data.company_id, entry_id=getattr(source_entry, "id", None))
            return None, error

        return {
            "transfer_group_id": transfer_group_id,
            "source_entry": FinancialService.serialize_entry(source_entry, include_children=False),
            "destination_entry": FinancialService.serialize_entry(destination_entry, include_children=False),
            "summary": {
                "company_id": data.company_id,
                "source_bank_account_id": source_account.id,
                "source_bank_account_name": source_account.name,
                "destination_bank_account_id": destination_account.id,
                "destination_bank_account_name": destination_account.name,
                "occurred_on": occurred_on.isoformat() if isinstance(occurred_on, date) else occurred_on,
                "competence_date": entry_date.isoformat() if isinstance(entry_date, date) else entry_date,
                "description": data.description,
                "document_number": data.document_number or transfer_group_id.upper(),
                "original_amount": float(Decimal(data.original_amount)),
                "source_entry_url": f"/financial/entries/{source_entry.id}?company_id={data.company_id}",
                "destination_entry_url": f"/financial/entries/{destination_entry.id}?company_id={data.company_id}",
            },
        }, None

    @staticmethod
    def _load_account(*, company_id: int, bank_account_id: int) -> Optional[FinancialBankAccount]:
        return FinancialBankAccount.query.filter(
            FinancialBankAccount.company_id == company_id,
            FinancialBankAccount.id == bank_account_id,
            FinancialBankAccount.deleted_at.is_(None),
            FinancialBankAccount.is_active.is_(True),
        ).first()

    @staticmethod
    def _cleanup_entry(*, company_id: int, entry_id: Optional[int]) -> None:
        if not entry_id:
            return
        try:
            entry = FinancialEntry.query.filter(
                FinancialEntry.company_id == company_id,
                FinancialEntry.id == entry_id,
            ).first()
            if entry:
                db.session.delete(entry)
                db.session.commit()
        except Exception:
            db.session.rollback()
