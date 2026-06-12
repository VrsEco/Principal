from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import uuid4

from flask_login import current_user

from models import db
from models.financial import FinancialBankAccount, FinancialEntry, FinancialSettlement
from schemas.financial import FinancialTransferCreateInput, FinancialTransferUpdateInput
from services.financial_service import FinancialService


class FinancialTransferService:
    @staticmethod
    def list_transfers(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        search_query: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        bank_account_id: Optional[int] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.entry_type == "transfer",
            FinancialEntry.deleted_at.is_(None),
        )
        if date_from is not None:
            query = query.filter(FinancialEntry.occurred_on >= date_from)
        if date_to is not None:
            query = query.filter(FinancialEntry.occurred_on <= date_to)
        if bank_account_id:
            query = query.filter(FinancialEntry.bank_account_id == bank_account_id)

        entries = query.order_by(FinancialEntry.occurred_on.desc(), FinancialEntry.id.desc()).all()
        grouped = FinancialTransferService._group_transfer_entries(entries)
        items = [FinancialTransferService._serialize_transfer_group(group_id, group_entries) for group_id, group_entries in grouped.items()]

        normalized_search = str(search_query or "").strip().lower()
        if normalized_search:
            items = [
                item for item in items
                if normalized_search in str(item.get("description") or "").lower()
                or normalized_search in str(item.get("transfer_group_id") or "").lower()
                or normalized_search in str(item.get("source_bank_account_name") or "").lower()
                or normalized_search in str(item.get("destination_bank_account_name") or "").lower()
                or normalized_search in str(item.get("document_number") or "").lower()
            ]

        items.sort(key=lambda item: (str(item.get("occurred_on") or ""), int(item.get("source_entry_id") or 0)), reverse=True)
        return {"items": items, "count": len(items)}, None

    @staticmethod
    def get_transfer(
        *,
        transfer_group_id: str,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entries = FinancialTransferService._load_transfer_entries(
            company_id=company_id,
            transfer_group_id=transfer_group_id,
        )
        if not entries:
            return None, "Transferência bancária não encontrada no escopo da empresa."
        return FinancialTransferService._serialize_transfer_group(transfer_group_id, entries, include_entries=True), None

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
    def update_transfer(
        *,
        transfer_group_id: str,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialTransferUpdateInput.model_validate(payload or {})
        except Exception as exc:
            return None, f"Payload inválido para atualização da transferência bancária: {exc}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error
        if data.source_bank_account_id == data.destination_bank_account_id:
            return None, "Selecione contas bancárias diferentes para origem e destino."

        entries = FinancialTransferService._load_transfer_entries(
            company_id=data.company_id,
            transfer_group_id=transfer_group_id,
        )
        source_entry, destination_entry = FinancialTransferService._resolve_direction_entries(entries)
        if not source_entry or not destination_entry:
            return None, "Transferência bancária incompleta ou não encontrada."

        source_account = FinancialTransferService._load_account(company_id=data.company_id, bank_account_id=data.source_bank_account_id)
        if not source_account:
            return None, "Conta bancária de origem não encontrada no escopo da empresa."
        destination_account = FinancialTransferService._load_account(company_id=data.company_id, bank_account_id=data.destination_bank_account_id)
        if not destination_account:
            return None, "Conta bancária de destino não encontrada no escopo da empresa."

        try:
            actor_payload = {
                "updated_by_user_id": data.updated_by_user_id,
                "updated_by_employee_id": data.updated_by_employee_id,
                "updated_by_agent": data.updated_by_agent or "app32",
                "updated_at": datetime.utcnow().isoformat(),
            }
            FinancialTransferService._apply_entry_update(
                entry=source_entry,
                description=data.description,
                occurred_on=data.occurred_on,
                amount=data.original_amount,
                bank_account=source_account,
                counterpart_account=destination_account,
                notes=data.notes,
                direction="out",
                audit=actor_payload,
            )
            FinancialTransferService._apply_entry_update(
                entry=destination_entry,
                description=data.description,
                occurred_on=data.occurred_on,
                amount=data.original_amount,
                bank_account=destination_account,
                counterpart_account=source_account,
                notes=data.notes,
                direction="in",
                audit=actor_payload,
            )
            FinancialTransferService._sync_transfer_settlements(
                company_id=data.company_id,
                transfer_group_id=transfer_group_id,
                source_entry=source_entry,
                destination_entry=destination_entry,
                occurred_on=data.occurred_on,
                amount=data.original_amount,
                source_account=source_account,
                destination_account=destination_account,
                actor_payload=actor_payload,
            )
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao atualizar transferência bancária: {exc}"

        return FinancialTransferService._serialize_transfer_group(transfer_group_id, [source_entry, destination_entry], include_entries=True), None

    @staticmethod
    def delete_transfer(
        *,
        transfer_group_id: str,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entries = FinancialTransferService._load_transfer_entries(company_id=company_id, transfer_group_id=transfer_group_id)
        if not entries:
            return None, "Transferência bancária não encontrada no escopo da empresa."

        try:
            deleted_at = datetime.utcnow()
            entry_ids = [entry.id for entry in entries]
            settlements = FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.financial_entry_id.in_(entry_ids),
                FinancialSettlement.deleted_at.is_(None),
            ).all()
            for settlement in settlements:
                settlement.deleted_at = deleted_at
                settlement.metadata_json = {
                    **dict(settlement.metadata_json or {}),
                    "deleted_at": deleted_at.isoformat(),
                    "deleted_via": "financial_transfer_service.delete_transfer",
                }
            for entry in entries:
                entry.deleted_at = deleted_at
                entry.metadata_json = {
                    **dict(entry.metadata_json or {}),
                    "deleted_at": deleted_at.isoformat(),
                    "deleted_via": "financial_transfer_service.delete_transfer",
                }
            db.session.commit()
            return {
                "message": "Transferência bancária excluída com sucesso.",
                "transfer_group_id": transfer_group_id,
                "entries_deleted": len(entries),
                "settlements_deleted": len(settlements),
            }, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao excluir transferência bancária: {exc}"

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
    def _load_transfer_entries(*, company_id: int, transfer_group_id: str) -> List[FinancialEntry]:
        normalized_group_id = str(transfer_group_id or "").strip()
        if not normalized_group_id:
            return []
        entries = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.entry_type == "transfer",
            FinancialEntry.deleted_at.is_(None),
        ).order_by(FinancialEntry.id.asc()).all()
        return [
            entry for entry in entries
            if str((dict(getattr(entry, "metadata_json", {}) or {})).get("transfer_group_id") or "").strip() == normalized_group_id
        ]

    @staticmethod
    def _group_transfer_entries(entries: Sequence[FinancialEntry]) -> Dict[str, List[FinancialEntry]]:
        grouped: Dict[str, List[FinancialEntry]] = {}
        for entry in entries or []:
            metadata = dict(getattr(entry, "metadata_json", {}) or {})
            group_id = str(metadata.get("transfer_group_id") or "").strip()
            if not group_id:
                continue
            grouped.setdefault(group_id, []).append(entry)
        return grouped

    @staticmethod
    def _resolve_direction_entries(entries: Sequence[FinancialEntry]) -> Tuple[Optional[FinancialEntry], Optional[FinancialEntry]]:
        source_entry = None
        destination_entry = None
        for entry in entries or []:
            metadata = dict(getattr(entry, "metadata_json", {}) or {})
            direction = str(metadata.get("transfer_direction") or "").strip().lower()
            if direction == "out":
                source_entry = entry
            elif direction == "in":
                destination_entry = entry
        return source_entry, destination_entry

    @staticmethod
    def _serialize_transfer_group(
        transfer_group_id: str,
        entries: Sequence[FinancialEntry],
        *,
        include_entries: bool = False,
    ) -> Dict[str, Any]:
        source_entry, destination_entry = FinancialTransferService._resolve_direction_entries(entries)
        reference = source_entry or destination_entry or (entries[0] if entries else None)
        metadata = dict(getattr(reference, "metadata_json", {}) or {}) if reference is not None else {}
        source_metadata = dict(getattr(source_entry, "metadata_json", {}) or {}) if source_entry is not None else {}
        destination_metadata = dict(getattr(destination_entry, "metadata_json", {}) or {}) if destination_entry is not None else {}
        source_attachments = list((dict(getattr(source_entry, "metadata_json", {}) or {})).get("attachments") or []) if source_entry is not None else []
        destination_attachments = list((dict(getattr(destination_entry, "metadata_json", {}) or {})).get("attachments") or []) if destination_entry is not None else []

        payload: Dict[str, Any] = {
            "transfer_group_id": transfer_group_id,
            "description": getattr(reference, "description", None),
            "document_number": getattr(reference, "document_number", None),
            "occurred_on": reference.occurred_on.isoformat() if getattr(reference, "occurred_on", None) else None,
            "original_amount": float(Decimal(str(getattr(reference, "original_amount", 0) or 0))),
            "notes": getattr(reference, "notes", None),
            "source_entry_id": getattr(source_entry, "id", None),
            "destination_entry_id": getattr(destination_entry, "id", None),
            "source_bank_account_id": getattr(source_entry, "bank_account_id", None),
            "destination_bank_account_id": getattr(destination_entry, "bank_account_id", None),
            "source_bank_account_name": None,
            "destination_bank_account_name": None,
            "attachments_count": len(source_attachments) + len(destination_attachments),
            "is_complete": bool(source_entry and destination_entry),
            "metadata_json": metadata,
        }
        if source_entry is not None:
            account = FinancialBankAccount.query.filter(
                FinancialBankAccount.company_id == source_entry.company_id,
                FinancialBankAccount.id == source_entry.bank_account_id,
            ).first()
            payload["source_bank_account_name"] = getattr(account, "name", None)
        if destination_entry is not None:
            account = FinancialBankAccount.query.filter(
                FinancialBankAccount.company_id == destination_entry.company_id,
                FinancialBankAccount.id == destination_entry.bank_account_id,
            ).first()
            payload["destination_bank_account_name"] = getattr(account, "name", None)
        if include_entries:
            payload["source_entry"] = FinancialService.serialize_entry(source_entry, include_children=False) if source_entry is not None else None
            payload["destination_entry"] = FinancialService.serialize_entry(destination_entry, include_children=False) if destination_entry is not None else None
            payload["attachments"] = {
                "source": source_attachments,
                "destination": destination_attachments,
            }
        return payload

    @staticmethod
    def _apply_entry_update(
        *,
        entry: FinancialEntry,
        description: str,
        occurred_on: date,
        amount: Decimal,
        bank_account: FinancialBankAccount,
        counterpart_account: FinancialBankAccount,
        notes: Optional[str],
        direction: str,
        audit: Dict[str, Any],
    ) -> None:
        entry.description = description
        entry.original_amount = amount
        entry.competence_date = occurred_on
        entry.due_date = occurred_on
        entry.occurred_on = occurred_on
        entry.bank_account_id = bank_account.id
        entry.notes = notes
        entry.metadata_json = {
            **dict(entry.metadata_json or {}),
            "transfer_direction": direction,
            "counterpart_bank_account_id": counterpart_account.id,
            "counterpart_bank_account_name": counterpart_account.name,
            "include_in_bank_statement": True,
            "exclude_from_dre": True,
            "updated_audit": audit,
        }

    @staticmethod
    def _sync_transfer_settlements(
        *,
        company_id: int,
        transfer_group_id: str,
        source_entry: FinancialEntry,
        destination_entry: FinancialEntry,
        occurred_on: date,
        amount: Decimal,
        source_account: FinancialBankAccount,
        destination_account: FinancialBankAccount,
        actor_payload: Dict[str, Any],
    ) -> None:
        settlement_by_entry_id = {
            settlement.financial_entry_id: settlement
            for settlement in FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.financial_entry_id.in_([source_entry.id, destination_entry.id]),
                FinancialSettlement.deleted_at.is_(None),
            ).all()
        }
        for entry, account, counterpart, direction in (
            (source_entry, source_account, destination_account, "out"),
            (destination_entry, destination_account, source_account, "in"),
        ):
            settlement = settlement_by_entry_id.get(entry.id)
            if settlement is None:
                continue
            settlement.settlement_date = occurred_on
            settlement.bank_account_id = account.id
            settlement.principal_amount = amount
            settlement.gross_amount = amount
            settlement.net_amount = amount
            settlement.metadata_json = {
                **dict(settlement.metadata_json or {}),
                "is_transfer": True,
                "include_in_bank_statement": True,
                "transfer_group_id": transfer_group_id,
                "transfer_direction": direction,
                "counterpart_bank_account_id": counterpart.id,
                "counterpart_bank_account_name": counterpart.name,
                "updated_audit": actor_payload,
            }

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
