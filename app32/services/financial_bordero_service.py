from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import (
    FinancialBordero,
    FinancialBorderoItem,
    FinancialBorderoSettlement,
    FinancialEntry,
    FinancialSchedule,
    FinancialSettlement,
)
from schemas.financial import FinancialBorderoCreateInput, FinancialBorderoSettlementInput, FinancialBorderoUpdateInput
from services.financial_catalog_service import FinancialCatalogService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_service import FinancialService


logger = logging.getLogger(__name__)


class FinancialBorderoService:
    ACTIVE_STATUSES = {"draft", "open", "partially_settled"}

    @staticmethod
    def list_borderos(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        bordero_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialBordero.query.filter(
            FinancialBordero.company_id == company_id,
            FinancialBordero.deleted_at.is_(None),
        )
        if bordero_type:
            query = query.filter(FinancialBordero.bordero_type == bordero_type)
        if status:
            query = query.filter(FinancialBordero.status == status)

        items = query.order_by(FinancialBordero.id.desc()).all()
        return [FinancialBorderoService._serialize_bordero(bordero) for bordero in items], None

    @staticmethod
    def get_bordero_detail(
        *,
        bordero_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        bordero = FinancialBordero.query.filter(
            FinancialBordero.id == bordero_id,
            FinancialBordero.company_id == company_id,
            FinancialBordero.deleted_at.is_(None),
        ).first()
        if not bordero:
            return None, "Borderô não encontrado no escopo da empresa."

        return FinancialBorderoService._serialize_bordero(bordero, include_items=True, include_settlements=True), None

    @staticmethod
    def create_bordero(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialBorderoCreateInput(**(payload or {}))
        except Exception as exc:
            return None, f"Payload inválido para borderô: {exc}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        created_items: List[FinancialBorderoItem] = []
        total_amount = Decimal("0")
        try:
            bordero_name = (data.name or data.description or data.notes or "").strip()
            bordero_description = (data.description or data.notes or bordero_name).strip() or bordero_name
            bordero = FinancialBordero(
                company_id=data.company_id,
                bordero_code=FinancialBorderoService._generate_bordero_code(data.company_id),
                name=bordero_name,
                bordero_type=data.bordero_type,
                status="open",
                description=bordero_description,
                created_by_user_id=data.created_by_user_id,
                created_by_employee_id=data.created_by_employee_id,
                created_by_agent=data.created_by_agent,
                notes=data.notes or bordero_description,
                metadata_json=dict(data.metadata_json or {}),
                created_at=datetime.combine(data.created_date, datetime.min.time()) if data.created_date else datetime.utcnow(),
            )
            db.session.add(bordero)
            db.session.flush()

            for index, item_input in enumerate(data.items, start=1):
                schedule = FinancialSchedule.query.filter(
                    FinancialSchedule.id == item_input.financial_schedule_id,
                    FinancialSchedule.company_id == data.company_id,
                    FinancialSchedule.deleted_at.is_(None),
                ).first()
                if not schedule:
                    db.session.rollback()
                    return None, f"Agendamento {item_input.financial_schedule_id} não encontrado no escopo da empresa."
                if schedule.entry_type != data.bordero_type:
                    db.session.rollback()
                    return None, "Não é permitido misturar agendamentos a pagar e a receber no mesmo borderô."

                lock_error = FinancialBorderoService._ensure_schedule_is_available(
                    company_id=data.company_id,
                    schedule_id=schedule.id,
                    exclude_bordero_id=bordero.id,
                )
                if lock_error:
                    db.session.rollback()
                    return None, lock_error

                snapshot = FinancialBorderoService._build_schedule_snapshot(schedule)
                open_amount = Decimal(str(snapshot["summary"]["open_total"]))
                if open_amount <= 0:
                    db.session.rollback()
                    return None, f"O agendamento {schedule.schedule_code} não possui saldo aberto para borderô."

                selected_amount = item_input.selected_amount if item_input.selected_amount is not None else open_amount
                selected_amount = Decimal(str(selected_amount)).quantize(Decimal("0.01"))
                if selected_amount <= 0:
                    db.session.rollback()
                    return None, f"O valor selecionado do agendamento {schedule.schedule_code} deve ser maior que zero."
                if selected_amount > open_amount:
                    db.session.rollback()
                    return None, (
                        f"O valor selecionado do agendamento {schedule.schedule_code} excede o saldo aberto. "
                        f"Saldo: {open_amount}."
                    )

                bordero_item = FinancialBorderoItem(
                    company_id=data.company_id,
                    bordero_id=bordero.id,
                    financial_schedule_id=schedule.id,
                    item_code=f"{bordero.bordero_code}-{index:03d}",
                    selected_amount=selected_amount,
                    settled_amount=Decimal("0.00"),
                    open_amount=selected_amount,
                    display_order=index,
                    snapshot_json=snapshot,
                    metadata_json={
                        **dict(item_input.metadata_json or {}),
                        "schedule_code": schedule.schedule_code,
                        "bordero_code": bordero.bordero_code,
                        "frozen_at": datetime.utcnow().isoformat(),
                    },
                )
                db.session.add(bordero_item)
                created_items.append(bordero_item)
                total_amount += selected_amount

            bordero.total_amount = total_amount
            bordero.settled_amount = Decimal("0.00")
            bordero.open_amount = total_amount
            db.session.commit()
            return FinancialBorderoService._serialize_bordero(bordero, include_items=True), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar borderô financeiro")
            return None, f"Erro ao criar borderô: {exc}"

    @staticmethod
    def update_bordero(
        *,
        bordero_id: int,
        company_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialBorderoUpdateInput(**(payload or {}))
        except Exception as exc:
            return None, f"Payload inválido para atualização do borderô: {exc}"

        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        bordero = FinancialBordero.query.filter(
            FinancialBordero.id == bordero_id,
            FinancialBordero.company_id == company_id,
            FinancialBordero.deleted_at.is_(None),
        ).first()
        if not bordero:
            return None, "Borderô não encontrado no escopo da empresa."

        try:
            if "name" in data.model_fields_set and data.name:
                bordero.name = data.name
            if "description" in data.model_fields_set:
                bordero.description = data.description or bordero.name
            if "created_date" in data.model_fields_set and data.created_date:
                bordero.created_at = datetime.combine(data.created_date, datetime.min.time())
            if "notes" in data.model_fields_set:
                bordero.notes = data.notes
            if "metadata_json" in data.model_fields_set and data.metadata_json is not None:
                bordero.metadata_json = dict(data.metadata_json or {})
            db.session.commit()
            return FinancialBorderoService._serialize_bordero(bordero, include_items=True, include_settlements=True), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao atualizar borderô financeiro %s", bordero_id)
            return None, f"Erro ao atualizar borderô: {exc}"

    @staticmethod
    def delete_bordero(
        *,
        bordero_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        bordero = FinancialBordero.query.filter(
            FinancialBordero.id == bordero_id,
            FinancialBordero.company_id == company_id,
            FinancialBordero.deleted_at.is_(None),
        ).first()
        if not bordero:
            return None, "Borderô não encontrado no escopo da empresa."

        has_settlements = (
            FinancialBorderoSettlement.query.filter(
                FinancialBorderoSettlement.company_id == company_id,
                FinancialBorderoSettlement.bordero_id == bordero.id,
                FinancialBorderoSettlement.deleted_at.is_(None),
            ).first()
            is not None
        )
        if has_settlements:
            return None, "Não é possível excluir um borderô que já possui baixa registrada."

        try:
            bordero.deleted_at = datetime.utcnow()
            bordero.status = "cancelled"
            db.session.commit()
            return {"message": "Borderô removido com sucesso.", "id": bordero_id}, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao remover borderô financeiro %s", bordero_id)
            return None, f"Erro ao remover borderô: {exc}"

    @staticmethod
    def create_settlement(
        *,
        bordero_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialBorderoSettlementInput(**(payload or {}))
        except Exception as exc:
            return None, f"Payload inválido para baixa do borderô: {exc}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        bordero = FinancialBordero.query.filter(
            FinancialBordero.id == bordero_id,
            FinancialBordero.company_id == data.company_id,
            FinancialBordero.deleted_at.is_(None),
        ).first()
        if not bordero:
            return None, "Borderô não encontrado no escopo da empresa."
        if bordero.status == "cancelled":
            return None, "Não é possível baixar um borderô cancelado."

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            bank_account_id=data.bank_account_id or bordero.bank_account_id,
        )
        if reference_error:
            return None, reference_error

        open_amount = Decimal(str(bordero.open_amount or 0)).quantize(Decimal("0.01"))
        gross_amount = Decimal(str(data.gross_amount or 0)).quantize(Decimal("0.01"))
        if gross_amount > open_amount:
            return None, f"Baixa excede o saldo em aberto do borderô. Saldo atual: {open_amount}."

        items = FinancialBorderoItem.query.filter(
            FinancialBorderoItem.company_id == data.company_id,
            FinancialBorderoItem.bordero_id == bordero.id,
            FinancialBorderoItem.deleted_at.is_(None),
        ).order_by(FinancialBorderoItem.display_order.asc(), FinancialBorderoItem.id.asc()).all()
        if not items:
            return None, "Borderô sem itens para baixa."

        try:
            settlement = FinancialBorderoSettlement(
                company_id=data.company_id,
                bordero_id=bordero.id,
                settlement_code=FinancialBorderoService._generate_bordero_settlement_code(data.company_id, bordero.bordero_code),
                settlement_status=data.settlement_status,
                settlement_date=data.settlement_date,
                bank_account_id=data.bank_account_id or bordero.bank_account_id,
                gross_amount=gross_amount,
                allocated_amount=Decimal("0.00"),
                variance_amount=Decimal("0.00"),
                notes=data.notes,
                metadata_json=dict(data.metadata_json or {}),
                created_by_user_id=data.created_by_user_id,
                created_by_employee_id=data.created_by_employee_id,
                created_by_agent=data.created_by_agent,
            )
            db.session.add(settlement)
            db.session.flush()

            item_allocations = FinancialBorderoService._allocate_amount(
                gross_amount,
                [
                    {
                        "id": item.id,
                        "weight": Decimal(str(item.open_amount or 0)),
                    }
                    for item in items
                ],
            )

            allocation_payload: List[Dict[str, Any]] = []
            allocated_total = Decimal("0.00")
            for item in items:
                allocated_to_item = item_allocations.get(item.id, Decimal("0.00"))
                if allocated_to_item <= 0:
                    continue

                entry_allocations, error = FinancialBorderoService._allocate_to_schedule_entries(
                    company_id=data.company_id,
                    schedule_id=item.financial_schedule_id,
                    bordero=bordero,
                    bordero_settlement=settlement,
                    amount=allocated_to_item,
                    settlement_date=data.settlement_date,
                    bank_account_id=data.bank_account_id or bordero.bank_account_id,
                    created_by_user_id=data.created_by_user_id,
                    created_by_employee_id=data.created_by_employee_id,
                    created_by_agent=data.created_by_agent,
                    notes=data.notes,
                )
                if error:
                    db.session.rollback()
                    return None, error

                item.settled_amount = Decimal(str(item.settled_amount or 0)) + allocated_to_item
                item.open_amount = max(Decimal(str(item.selected_amount or 0)) - Decimal(str(item.settled_amount or 0)), Decimal("0.00"))
                allocated_total += allocated_to_item
                allocation_payload.append(
                    {
                        "bordero_item_id": item.id,
                        "financial_schedule_id": item.financial_schedule_id,
                        "allocated_amount": float(allocated_to_item),
                        "entry_allocations": entry_allocations,
                    }
                )

            settlement.allocated_amount = allocated_total
            settlement.variance_amount = max(gross_amount - allocated_total, Decimal("0.00"))
            settlement.metadata_json = {
                **dict(settlement.metadata_json or {}),
                "bordero_code": bordero.bordero_code,
                "allocations": allocation_payload,
                "reconcile_via_bordero": True,
            }

            bordero.settled_amount = Decimal(str(bordero.settled_amount or 0)) + allocated_total
            bordero.open_amount = max(Decimal(str(bordero.total_amount or 0)) - Decimal(str(bordero.settled_amount or 0)), Decimal("0.00"))
            if bordero.open_amount == Decimal("0.00"):
                bordero.status = "settled"
            elif bordero.settled_amount > Decimal("0.00"):
                bordero.status = "partially_settled"
            else:
                bordero.status = "open"

            db.session.commit()
            return {
                "bordero": FinancialBorderoService._serialize_bordero(bordero, include_items=True),
                "settlement": settlement.to_dict(),
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao registrar baixa do borderô %s", bordero_id)
            return None, f"Erro ao registrar baixa do borderô: {exc}"

    @staticmethod
    def get_active_bordero_for_schedule(*, company_id: int, schedule_id: int) -> Optional[FinancialBordero]:
        return (
            FinancialBordero.query.join(
                FinancialBorderoItem,
                FinancialBorderoItem.bordero_id == FinancialBordero.id,
            )
            .filter(
                FinancialBordero.company_id == company_id,
                FinancialBordero.deleted_at.is_(None),
                FinancialBordero.status.in_(tuple(FinancialBorderoService.ACTIVE_STATUSES)),
                FinancialBorderoItem.company_id == company_id,
                FinancialBorderoItem.financial_schedule_id == schedule_id,
                FinancialBorderoItem.deleted_at.is_(None),
            )
            .order_by(FinancialBordero.id.desc())
            .first()
        )

    @staticmethod
    def get_active_bordero_for_entry(*, company_id: int, entry: FinancialEntry) -> Optional[FinancialBordero]:
        schedule_id = FinancialBorderoService._extract_schedule_id_from_entry(entry)
        if not schedule_id:
            return None
        return FinancialBorderoService.get_active_bordero_for_schedule(company_id=company_id, schedule_id=schedule_id)

    @staticmethod
    def _ensure_schedule_is_available(*, company_id: int, schedule_id: int, exclude_bordero_id: Optional[int] = None) -> Optional[str]:
        active_bordero = FinancialBorderoService.get_active_bordero_for_schedule(company_id=company_id, schedule_id=schedule_id)
        if active_bordero and active_bordero.id != exclude_bordero_id:
            return f"Agendamento já participa do borderô {active_bordero.bordero_code}."
        return None

    @staticmethod
    def _serialize_bordero(
        bordero: FinancialBordero,
        *,
        include_items: bool = False,
        include_settlements: bool = False,
    ) -> Dict[str, Any]:
        payload = bordero.to_dict()
        items_query = FinancialBorderoItem.query.filter(
            FinancialBorderoItem.company_id == bordero.company_id,
            FinancialBorderoItem.bordero_id == bordero.id,
            FinancialBorderoItem.deleted_at.is_(None),
        ).order_by(FinancialBorderoItem.display_order.asc(), FinancialBorderoItem.id.asc())
        settlements_query = FinancialBorderoSettlement.query.filter(
            FinancialBorderoSettlement.company_id == bordero.company_id,
            FinancialBorderoSettlement.bordero_id == bordero.id,
            FinancialBorderoSettlement.deleted_at.is_(None),
        ).order_by(FinancialBorderoSettlement.settlement_date.asc(), FinancialBorderoSettlement.id.asc())
        payload["item_count"] = items_query.count()
        payload["settlement_count"] = settlements_query.count()
        payload["can_delete"] = payload["settlement_count"] == 0
        payload["can_settle"] = payload["status"] != "cancelled" and Decimal(str(bordero.open_amount or 0)) > Decimal("0.00")
        payload["signed_total_amount"] = FinancialService.get_signed_amount(bordero.total_amount, "credit" if bordero.bordero_type == "receivable" else "debit")
        payload["signed_settled_amount"] = FinancialService.get_signed_amount(bordero.settled_amount, "credit" if bordero.bordero_type == "receivable" else "debit")
        payload["signed_open_amount"] = FinancialService.get_signed_amount(bordero.open_amount, "credit" if bordero.bordero_type == "receivable" else "debit")
        if include_items:
            payload["items"] = [item.to_dict() for item in items_query.all()]
        if include_settlements:
            payload["settlements"] = [item.to_dict() for item in settlements_query.all()]
        return payload

    @staticmethod
    def _generate_bordero_code(company_id: int) -> str:
        prefix = "B"
        last = (
            FinancialBordero.query.filter(
                FinancialBordero.company_id == company_id,
                FinancialBordero.deleted_at.is_(None),
                FinancialBordero.bordero_code.like(f"{prefix}-%"),
            )
            .order_by(FinancialBordero.id.desc())
            .first()
        )
        next_number = 1
        if last and last.bordero_code:
            try:
                next_number = int(str(last.bordero_code).split("-")[-1]) + 1
            except Exception:
                next_number = last.id + 1
        return f"{prefix}-{next_number}"

    @staticmethod
    def _generate_bordero_settlement_code(company_id: int, bordero_code: str) -> str:
        base = f"{bordero_code}-BX"
        last = (
            FinancialBorderoSettlement.query.filter(
                FinancialBorderoSettlement.company_id == company_id,
                FinancialBorderoSettlement.deleted_at.is_(None),
                FinancialBorderoSettlement.settlement_code.like(f"{base}-%"),
            )
            .order_by(FinancialBorderoSettlement.id.desc())
            .first()
        )
        next_number = 1
        if last and last.settlement_code:
            try:
                next_number = int(str(last.settlement_code).split("-")[-1]) + 1
            except Exception:
                next_number = last.id + 1
        return f"{base}-{next_number:03d}"

    @staticmethod
    def _build_schedule_snapshot(schedule: FinancialSchedule) -> Dict[str, Any]:
        payload = FinancialScheduleService._serialize_schedule(schedule, include_related_entries=True, include_summary=True)
        payload["captured_at"] = datetime.utcnow().isoformat()
        return payload

    @staticmethod
    def _extract_schedule_id_from_entry(entry: FinancialEntry) -> Optional[int]:
        external_reference = str(entry.external_reference or "").strip()
        prefix = "financial_schedule:"
        if not external_reference.startswith(prefix):
            return None
        try:
            return int(external_reference.split(":", 1)[1])
        except Exception:
            return None

    @staticmethod
    def _allocate_to_schedule_entries(
        *,
        company_id: int,
        schedule_id: int,
        bordero: FinancialBordero,
        bordero_settlement: FinancialBorderoSettlement,
        amount: Decimal,
        settlement_date,
        bank_account_id: Optional[int],
        created_by_user_id: Optional[int],
        created_by_employee_id: Optional[int],
        created_by_agent: Optional[str],
        notes: Optional[str],
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        entries = FinancialBorderoService._list_open_entries_for_schedule(company_id=company_id, schedule_id=schedule_id)
        if not entries:
            generated, error = FinancialScheduleService.create_entry_from_schedule(
                schedule_id=schedule_id,
                company_id=company_id,
                allowed_company_ids=[company_id],
                ignore_bordero_lock=True,
            )
            if error:
                return None, error
            entries = FinancialBorderoService._list_open_entries_for_schedule(company_id=company_id, schedule_id=schedule_id)

        if not entries:
            return None, "Não foi possível localizar ou gerar lançamento para baixa do borderô."

        outstanding_items: List[Dict[str, Any]] = []
        for entry in entries:
            outstanding = FinancialBorderoService._entry_open_amount(entry)
            if outstanding > Decimal("0.00"):
                outstanding_items.append({"id": entry.id, "weight": outstanding, "entry": entry})
        if not outstanding_items:
            return None, "Os lançamentos do agendamento selecionado não possuem saldo aberto para baixa."

        allocations = FinancialBorderoService._allocate_amount(amount, outstanding_items)
        created_payload: List[Dict[str, Any]] = []
        for item in outstanding_items:
            allocated = allocations.get(item["id"], Decimal("0.00"))
            if allocated <= 0:
                continue

            entry = item["entry"]
            settlement = FinancialSettlement(
                company_id=company_id,
                financial_entry_id=entry.id,
                settlement_code=f"{bordero_settlement.settlement_code}-E{entry.id}",
                settlement_type="manual",
                settlement_status="posted",
                settlement_date=settlement_date,
                bank_account_id=bank_account_id,
                principal_amount=allocated,
                interest_amount=Decimal("0.00"),
                penalty_amount=Decimal("0.00"),
                discount_amount=Decimal("0.00"),
                fee_amount=Decimal("0.00"),
                other_adjustments_amount=Decimal("0.00"),
                net_amount=allocated,
                external_reference=bordero_settlement.settlement_code,
                import_batch_id=None,
                reconciliation_status="pending",
                notes=notes,
                metadata_json={
                    "bordero_id": bordero.id,
                    "bordero_code": bordero.bordero_code,
                    "bordero_settlement_id": bordero_settlement.id,
                    "bordero_settlement_code": bordero_settlement.settlement_code,
                    "reconcile_via_bordero": True,
                },
                created_by_user_id=created_by_user_id,
                created_by_employee_id=created_by_employee_id,
                created_by_agent=created_by_agent,
            )
            db.session.add(settlement)

            projected_total = FinancialBorderoService._entry_settled_amount(entry) + allocated
            if projected_total >= Decimal(str(entry.original_amount or 0)):
                entry.status = "settled"
            elif projected_total > Decimal("0.00"):
                entry.status = "partially_settled"

            created_payload.append(
                {
                    "financial_entry_id": entry.id,
                    "entry_code": entry.entry_code,
                    "allocated_amount": float(allocated),
                    "settlement_code": settlement.settlement_code,
                }
            )
        return created_payload, None

    @staticmethod
    def _list_open_entries_for_schedule(*, company_id: int, schedule_id: int) -> List[FinancialEntry]:
        return (
            FinancialEntry.query.filter(
                FinancialEntry.company_id == company_id,
                FinancialEntry.external_reference == f"financial_schedule:{schedule_id}",
                FinancialEntry.deleted_at.is_(None),
            )
            .order_by(FinancialEntry.competence_date.asc(), FinancialEntry.id.asc())
            .all()
        )

    @staticmethod
    def _entry_settled_amount(entry: FinancialEntry) -> Decimal:
        total = (
            db.session.query(db.func.coalesce(db.func.sum(FinancialSettlement.principal_amount), 0))
            .filter(
                FinancialSettlement.company_id == entry.company_id,
                FinancialSettlement.financial_entry_id == entry.id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            )
            .scalar()
        ) or 0
        return Decimal(str(total or 0)).quantize(Decimal("0.01"))

    @staticmethod
    def _entry_open_amount(entry: FinancialEntry) -> Decimal:
        original_amount = Decimal(str(entry.original_amount or 0)).quantize(Decimal("0.01"))
        settled_amount = FinancialBorderoService._entry_settled_amount(entry)
        return max(original_amount - settled_amount, Decimal("0.00"))

    @staticmethod
    def _allocate_amount(total_amount: Decimal, weighted_items: List[Dict[str, Any]]) -> Dict[int, Decimal]:
        normalized_total = Decimal(str(total_amount or 0)).quantize(Decimal("0.01"))
        if normalized_total <= 0 or not weighted_items:
            return {}

        total_weight = sum(Decimal(str(item["weight"] or 0)) for item in weighted_items)
        if total_weight <= 0:
            return {}

        cents = (normalized_total * 100).quantize(Decimal("1"))
        allocation_cents: Dict[int, int] = {}
        remainders: List[Tuple[int, Decimal]] = []
        consumed = 0

        for item in weighted_items:
            weight = Decimal(str(item["weight"] or 0))
            raw = (cents * weight / total_weight) if total_weight else Decimal("0")
            floor_value = int(raw.quantize(Decimal("1"), rounding=ROUND_DOWN))
            allocation_cents[item["id"]] = floor_value
            consumed += floor_value
            remainders.append((item["id"], raw - Decimal(floor_value)))

        remaining = int(cents) - consumed
        for item_id, _ in sorted(remainders, key=lambda entry: entry[1], reverse=True):
            if remaining <= 0:
                break
            allocation_cents[item_id] += 1
            remaining -= 1

        return {
            item_id: (Decimal(value) / Decimal("100")).quantize(Decimal("0.01"))
            for item_id, value in allocation_cents.items()
            if value > 0
        }
