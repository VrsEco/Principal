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
        entry_date = occurred_on
        actor_user_id = data.created_by_user_id or getattr(current_user, "id", None)
        actor_employee_id = data.created_by_employee_id or getattr(current_user, "employee_id", None)
        actor_name = str(getattr(current_user, "name", "") or getattr(current_user, "email", "") or "").strip() or None

        base_metadata = {
            **(data.metadata_json or {}),
            "is_transfer": True,
            "exclude_from_dre": True,
            "include_in_bank_statement": True,
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

        source_settlement, error = FinancialTransferService._create_transfer_settlement(
            company_id=data.company_id,
            entry=source_entry,
            bank_account_id=source_account.id,
            occurred_on=occurred_on,
            transfer_group_id=transfer_group_id,
            direction="out",
            counterparty_bank_account_id=destination_account.id,
            counterparty_bank_account_name=destination_account.name,
            actor_user_id=actor_user_id,
            actor_employee_id=actor_employee_id,
            created_by_agent=data.created_by_agent or "app32",
        )
        if error:
            FinancialTransferService._cleanup_entry(company_id=data.company_id, entry_id=getattr(destination_entry, "id", None))
            FinancialTransferService._cleanup_entry(company_id=data.company_id, entry_id=getattr(source_entry, "id", None))
            return None, error

        destination_settlement, error = FinancialTransferService._create_transfer_settlement(
            company_id=data.company_id,
            entry=destination_entry,
            bank_account_id=destination_account.id,
            occurred_on=occurred_on,
            transfer_group_id=transfer_group_id,
            direction="in",
            counterparty_bank_account_id=source_account.id,
            counterparty_bank_account_name=source_account.name,
            actor_user_id=actor_user_id,
            actor_employee_id=actor_employee_id,
            created_by_agent=data.created_by_agent or "app32",
        )
        if error:
            FinancialTransferService._cleanup_settlement(company_id=data.company_id, settlement_id=getattr(source_settlement, "id", None))
            FinancialTransferService._cleanup_entry(company_id=data.company_id, entry_id=getattr(destination_entry, "id", None))
            FinancialTransferService._cleanup_entry(company_id=data.company_id, entry_id=getattr(source_entry, "id", None))
            return None, error

        return {
            "transfer_group_id": transfer_group_id,
            "source_entry": FinancialService.serialize_entry(source_entry, include_children=False),
            "destination_entry": FinancialService.serialize_entry(destination_entry, include_children=False),
            "source_settlement": source_settlement.to_dict() if hasattr(source_settlement, "to_dict") else source_settlement,
            "destination_settlement": destination_settlement.to_dict() if hasattr(destination_settlement, "to_dict") else destination_settlement,
            "summary": {
                "company_id": data.company_id,
                "source_bank_account_id": source_account.id,
                "source_bank_account_name": source_account.name,
                "destination_bank_account_id": destination_account.id,
                "destination_bank_account_name": destination_account.name,
                "occurred_on": occurred_on.isoformat() if isinstance(occurred_on, date) else occurred_on,
                "description": data.description,
                "document_number": data.document_number or transfer_group_id.upper(),
                "original_amount": float(Decimal(data.original_amount)),
                "source_entry_url": f"/financial/entries/{source_entry.id}?company_id={data.company_id}",
                "destination_entry_url": f"/financial/entries/{destination_entry.id}?company_id={data.company_id}",
                "source_settlement_code": getattr(source_settlement, "settlement_code", None),
                "destination_settlement_code": getattr(destination_settlement, "settlement_code", None),
            },
        }, None

    @staticmethod
    def _create_transfer_settlement(
        *,
        company_id: int,
        entry: Any,
        bank_account_id: int,
        occurred_on: date,
        transfer_group_id: str,
        direction: str,
        counterparty_bank_account_id: int,
        counterparty_bank_account_name: str,
        actor_user_id: Optional[int],
        actor_employee_id: Optional[int],
        created_by_agent: str,
    ) -> Tuple[Optional[Any], Optional[str]]:
        settlement_payload = {
            "company_id": company_id,
            "financial_entry_id": getattr(entry, "id", None),
            "settlement_code": f"{transfer_group_id}-{direction}-stl",
            "settlement_type": "automatic_process",
            "settlement_status": "posted",
            "settlement_date": occurred_on,
            "bank_account_id": bank_account_id,
            "principal_amount": getattr(entry, "original_amount", None),
            "external_reference": f"transfer:{transfer_group_id}:{direction}",
            "reconciliation_status": "pending",
            "created_by_user_id": actor_user_id,
            "created_by_employee_id": actor_employee_id,
            "created_by_agent": created_by_agent,
            "notes": "Baixa automática gerada para transferência bancária.",
            "metadata_json": {
                "is_transfer": True,
                "include_in_bank_statement": True,
                "transfer_group_id": transfer_group_id,
                "transfer_direction": direction,
                "counterpart_bank_account_id": counterparty_bank_account_id,
                "counterpart_bank_account_name": counterparty_bank_account_name,
                "generated_by": "financial_transfer_service",
            },
        }
        return FinancialService.create_settlement(payload=settlement_payload)

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

    @staticmethod
    def _cleanup_settlement(*, company_id: int, settlement_id: Optional[int]) -> None:
        if not settlement_id:
            return
        try:
            from models.financial import FinancialSettlement

            settlement = FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.id == settlement_id,
            ).first()
            if settlement:
                db.session.delete(settlement)
                db.session.commit()
        except Exception:
            db.session.rollback()
