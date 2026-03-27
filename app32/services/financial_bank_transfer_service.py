from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Sequence, Tuple

from models import db
from models.financial import FinancialBankAccount, FinancialBankTransfer, FinancialEntry
from schemas.financial import FinancialBankTransferCreateInput
from services.financial_catalog_service import FinancialCatalogService
from services.financial_service import FinancialService


class FinancialBankTransferService:
    @staticmethod
    def _serialize_transfer(transfer: FinancialBankTransfer, *, include_entries: bool = False) -> Dict[str, Any]:
        payload = transfer.to_dict()
        origin_bank = transfer.origin_bank_account or FinancialBankAccount.query.filter(
            FinancialBankAccount.company_id == transfer.company_id,
            FinancialBankAccount.id == transfer.origin_bank_account_id,
            FinancialBankAccount.deleted_at.is_(None),
        ).first()
        destination_bank = transfer.destination_bank_account or FinancialBankAccount.query.filter(
            FinancialBankAccount.company_id == transfer.company_id,
            FinancialBankAccount.id == transfer.destination_bank_account_id,
            FinancialBankAccount.deleted_at.is_(None),
        ).first()
        payload["origin_bank_account_label"] = FinancialBankTransferService._bank_account_label(origin_bank)
        payload["destination_bank_account_label"] = FinancialBankTransferService._bank_account_label(destination_bank)
        if include_entries:
            payload["origin_entry"] = (
                FinancialService.serialize_entry(transfer.origin_entry) if transfer.origin_entry else None
            )
            payload["destination_entry"] = (
                FinancialService.serialize_entry(transfer.destination_entry) if transfer.destination_entry else None
            )
        return payload

    @staticmethod
    def _bank_account_label(bank: Optional[FinancialBankAccount]) -> Optional[str]:
        if not bank:
            return None
        return f"{bank.code} - {bank.name}" if bank.code else bank.name

    @staticmethod
    def _generate_transfer_code(company_id: int) -> str:
        last_number = 0
        codes = (
            FinancialBankTransfer.query.with_entities(FinancialBankTransfer.transfer_code)
            .filter(
                FinancialBankTransfer.company_id == company_id,
                FinancialBankTransfer.deleted_at.is_(None),
            )
            .all()
        )
        for (code,) in codes:
            digits = "".join(ch for ch in str(code or "") if ch.isdigit())
            if digits:
                last_number = max(last_number, int(digits))
        return f"TRF-{last_number + 1:06d}"

    @staticmethod
    def list_options(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        bank_accounts = FinancialBankAccount.query.filter(
            FinancialBankAccount.company_id == company_id,
            FinancialBankAccount.deleted_at.is_(None),
            FinancialBankAccount.is_active.is_(True),
        ).order_by(FinancialBankAccount.code.asc(), FinancialBankAccount.id.asc()).all()

        return {
            "bank_accounts": [item.to_dict() for item in bank_accounts],
        }, None

    @staticmethod
    def list_transfers(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        query: Optional[str] = None,
        bank_account_id: Optional[int] = None,
    ) -> Tuple[Optional[list[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        transfers_query = FinancialBankTransfer.query.filter(
            FinancialBankTransfer.company_id == company_id,
            FinancialBankTransfer.deleted_at.is_(None),
        )

        if bank_account_id:
            transfers_query = transfers_query.filter(
                db.or_(
                    FinancialBankTransfer.origin_bank_account_id == bank_account_id,
                    FinancialBankTransfer.destination_bank_account_id == bank_account_id,
                )
            )

        text = (query or "").strip().lower()
        if text:
            transfers_query = transfers_query.filter(
                db.or_(
                    db.func.lower(FinancialBankTransfer.transfer_code).like(f"%{text}%"),
                    db.func.lower(FinancialBankTransfer.description).like(f"%{text}%"),
                    db.func.lower(db.func.coalesce(FinancialBankTransfer.document_number, "")).like(f"%{text}%"),
                )
            )

        transfers = transfers_query.order_by(
            FinancialBankTransfer.transfer_date.desc(),
            FinancialBankTransfer.id.desc(),
        ).all()
        return [FinancialBankTransferService._serialize_transfer(item) for item in transfers], None

    @staticmethod
    def get_transfer(
        *,
        company_id: int,
        transfer_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        transfer = FinancialBankTransfer.query.filter(
            FinancialBankTransfer.company_id == company_id,
            FinancialBankTransfer.id == transfer_id,
            FinancialBankTransfer.deleted_at.is_(None),
        ).first()
        if not transfer:
            return None, "Transferência bancária não encontrada."
        return FinancialBankTransferService._serialize_transfer(transfer, include_entries=True), None

    @staticmethod
    def create_transfer(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialBankTransferCreateInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para transferência bancária: {exc}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        for bank_account_id, label in (
            (data.origin_bank_account_id, "origem"),
            (data.destination_bank_account_id, "destino"),
        ):
            ref_error = FinancialCatalogService.validate_reference_ids(
                company_id=data.company_id,
                bank_account_id=bank_account_id,
            )
            if ref_error:
                return None, f"Conta bancária de {label} inválida. {ref_error}"

        transfer_code = FinancialBankTransferService._generate_transfer_code(data.company_id)
        effective_competence_date = data.competence_date or data.transfer_date
        origin_entry, destination_entry = None, None
        try:
            origin_entry, error = FinancialService.create_entry(
                payload=FinancialBankTransferService._build_entry_payload(
                    data=data,
                    transfer_code=transfer_code,
                    competence_date=effective_competence_date,
                    bank_account_id=data.origin_bank_account_id,
                    movement_nature="debit",
                    direction="out",
                ),
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                return None, error

            destination_entry, error = FinancialService.create_entry(
                payload=FinancialBankTransferService._build_entry_payload(
                    data=data,
                    transfer_code=transfer_code,
                    competence_date=effective_competence_date,
                    bank_account_id=data.destination_bank_account_id,
                    movement_nature="credit",
                    direction="in",
                ),
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                FinancialBankTransferService._cleanup_entries(origin_entry, None)
                return None, error

            transfer = FinancialBankTransfer(
                company_id=data.company_id,
                transfer_code=transfer_code,
                transfer_status="posted",
                description=data.description,
                document_number=data.document_number,
                competence_date=effective_competence_date,
                transfer_date=data.transfer_date,
                amount=data.amount,
                origin_bank_account_id=data.origin_bank_account_id,
                destination_bank_account_id=data.destination_bank_account_id,
                origin_entry_id=origin_entry.id,
                destination_entry_id=destination_entry.id,
                created_by_user_id=data.created_by_user_id,
                created_by_employee_id=data.created_by_employee_id,
                created_by_agent=data.created_by_agent,
                notes=data.notes,
                metadata_json=data.metadata_json or {},
            )
            db.session.add(transfer)
            db.session.flush()

            origin_entry.metadata_json = {
                **(origin_entry.metadata_json or {}),
                "bank_transfer_id": transfer.id,
                "transfer_direction": "out",
                "destination_bank_account_id": data.destination_bank_account_id,
            }
            destination_entry.metadata_json = {
                **(destination_entry.metadata_json or {}),
                "bank_transfer_id": transfer.id,
                "transfer_direction": "in",
                "origin_bank_account_id": data.origin_bank_account_id,
            }
            db.session.commit()
            return FinancialBankTransferService._serialize_transfer(transfer, include_entries=True), None
        except Exception as exc:
            db.session.rollback()
            FinancialBankTransferService._cleanup_entries(origin_entry, destination_entry)
            return None, f"Erro ao criar transferência bancária: {exc}"

    @staticmethod
    def _cleanup_entries(
        origin_entry: Optional[FinancialEntry],
        destination_entry: Optional[FinancialEntry],
    ) -> None:
        try:
            if destination_entry and destination_entry.id:
                entry = FinancialEntry.query.get(destination_entry.id)
                if entry:
                    db.session.delete(entry)
            if origin_entry and origin_entry.id:
                entry = FinancialEntry.query.get(origin_entry.id)
                if entry:
                    db.session.delete(entry)
            db.session.commit()
        except Exception:
            db.session.rollback()

    @staticmethod
    def _build_entry_payload(
        *,
        data: FinancialBankTransferCreateInput,
        transfer_code: str,
        competence_date: date,
        bank_account_id: int,
        movement_nature: str,
        direction: str,
    ) -> Dict[str, Any]:
        entry_code = f"{transfer_code}-{direction.upper()}"
        return {
            "company_id": data.company_id,
            "entry_code": entry_code,
            "entry_type": "transfer",
            "movement_nature": movement_nature,
            "origin_type": "manual",
            "status": "settled",
            "review_status": "approved",
            "description": data.description,
            "document_number": data.document_number,
            "external_reference": f"financial_bank_transfer:{transfer_code}:{direction}",
            "origin_reference": transfer_code,
            "competence_date": competence_date,
            "due_date": data.transfer_date,
            "occurred_on": data.transfer_date,
            "original_amount": Decimal(data.amount),
            "bank_account_id": bank_account_id,
            "created_by_user_id": data.created_by_user_id,
            "created_by_employee_id": data.created_by_employee_id,
            "created_by_agent": data.created_by_agent,
            "notes": data.notes,
            "metadata_json": {
                **(data.metadata_json or {}),
                "bank_transfer_code": transfer_code,
                "transfer_direction": direction,
                "transfer_date": data.transfer_date.isoformat(),
            },
        }
