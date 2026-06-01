from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import db
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from models.financial import (
    FinancialBordero,
    FinancialBorderoItem,
    FinancialBorderoSettlement,
    FinancialEntry,
    FinancialSchedule,
    FinancialSettlement,
)
from schemas.financial import (
    FinancialBorderoCreateInput,
    FinancialBorderoSettlementInput,
    FinancialBorderoSettlementUpdateInput,
    FinancialBorderoUpdateInput,
)
from services.financial_catalog_service import FinancialCatalogService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_settlement_composition_service import FinancialSettlementCompositionService
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

        bordero_name = (data.name or data.description or data.notes or "").strip()
        bordero_description = (data.description or data.notes or bordero_name).strip() or bordero_name

        for attempt in range(1, 6):
            total_amount = Decimal("0")
            try:
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
                        return None, f"Título Financeiro {item_input.financial_schedule_id} não encontrado no escopo da empresa."
                    if schedule.entry_type != data.bordero_type:
                        db.session.rollback()
                        return None, "Não é permitido misturar Títulos Financeiros a pagar e a receber no mesmo borderô."

                    snapshot = FinancialBorderoService._build_schedule_snapshot(schedule)
                    operational_state = str(((snapshot.get("summary") or {}).get("operational_state") or "")).strip().lower()
                    if operational_state in {"draft", "cancelled", "forecast"}:
                        db.session.rollback()
                        return None, "Somente Títulos Financeiros operacionais com saldo aberto podem entrar em borderô."

                    lock_error = FinancialBorderoService._ensure_schedule_is_available(
                        company_id=data.company_id,
                        schedule_id=schedule.id,
                        exclude_bordero_id=bordero.id,
                    )
                    if lock_error:
                        db.session.rollback()
                        return None, lock_error

                    open_amount = Decimal(str(snapshot["summary"]["open_total"]))
                    if open_amount <= 0:
                        db.session.rollback()
                        return None, f"O Título Financeiro {schedule.schedule_code} não possui saldo aberto para borderô."

                    selected_amount = item_input.selected_amount if item_input.selected_amount is not None else open_amount
                    selected_amount = Decimal(str(selected_amount)).quantize(Decimal("0.01"))
                    if selected_amount <= 0:
                        db.session.rollback()
                        return None, f"O valor selecionado do Título Financeiro {schedule.schedule_code} deve ser maior que zero."
                    if selected_amount > open_amount:
                        db.session.rollback()
                        return None, (
                            f"O valor selecionado do Título Financeiro {schedule.schedule_code} excede o saldo aberto. "
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
                    total_amount += selected_amount

                bordero.total_amount = total_amount
                bordero.settled_amount = Decimal("0.00")
                bordero.open_amount = total_amount
                db.session.commit()
                return FinancialBorderoService._serialize_bordero(bordero, include_items=True), None
            except IntegrityError as exc:
                db.session.rollback()
                if FinancialBorderoService._is_duplicate_bordero_code_error(exc):
                    logger.warning(
                        "Colisão de código ao criar borderô da empresa %s na tentativa %s; regenerando código.",
                        data.company_id,
                        attempt,
                    )
                    continue
                logger.exception("Erro de integridade ao criar borderô financeiro")
                return None, f"Erro ao criar borderô: {exc}"
            except Exception as exc:
                db.session.rollback()
                logger.exception("Erro ao criar borderô financeiro")
                return None, f"Erro ao criar borderô: {exc}"

        return None, "Erro ao criar borderô: não foi possível gerar um código único para a empresa."

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
            settlement.metadata_json = FinancialBorderoService._build_bordero_settlement_audit_metadata(
                base_metadata=dict(settlement.metadata_json or {}),
                bordero=bordero,
                settlement=settlement,
                gross_amount=gross_amount,
                allocated_total=allocated_total,
                variance_amount=settlement.variance_amount,
                allocation_payload=allocation_payload,
                created_by_user_id=data.created_by_user_id,
                created_by_employee_id=data.created_by_employee_id,
                created_by_agent=data.created_by_agent,
            )

            FinancialBorderoService._sync_bordero_totals_from_items(bordero, items)

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
    def update_settlement(
        *,
        bordero_id: int,
        settlement_id: int,
        company_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialBorderoSettlementUpdateInput(**(payload or {}))
        except Exception as exc:
            return None, f"Payload inválido para atualização da baixa do borderô: {exc}"

        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        bordero, settlement, error = FinancialBorderoService._load_bordero_settlement(
            bordero_id=bordero_id,
            settlement_id=settlement_id,
            company_id=company_id,
        )
        if error:
            return None, error

        merged_payload = {
            "company_id": company_id,
            "settlement_date": data.settlement_date or settlement.settlement_date,
            "gross_amount": data.gross_amount if data.gross_amount is not None else settlement.gross_amount,
            "settlement_status": data.settlement_status or settlement.settlement_status,
            "bank_account_id": data.bank_account_id if data.bank_account_id is not None else settlement.bank_account_id,
            "notes": data.notes if data.notes is not None else settlement.notes,
            "metadata_json": data.metadata_json if data.metadata_json is not None else dict(settlement.metadata_json or {}),
            "created_by_user_id": data.created_by_user_id,
            "created_by_employee_id": data.created_by_employee_id,
            "created_by_agent": data.created_by_agent,
        }

        validated_payload, validation_error = FinancialBorderoService._validate_bordero_settlement_payload(
            bordero=bordero,
            payload=merged_payload,
            available_amount=(
                Decimal(str(bordero.open_amount or 0)).quantize(Decimal("0.01"))
                + Decimal(str(settlement.allocated_amount or 0)).quantize(Decimal("0.01"))
            ),
        )
        if validation_error:
            return None, validation_error

        deleted, delete_error = FinancialBorderoService.delete_settlement(
            bordero_id=bordero_id,
            settlement_id=settlement_id,
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if delete_error:
            return None, delete_error

        created, create_error = FinancialBorderoService.create_settlement(
            bordero_id=bordero_id,
            payload=validated_payload,
            allowed_company_ids=allowed_company_ids,
        )
        if create_error:
            return None, create_error
        return {
            **dict(created or {}),
            "message": "Baixa do borderô atualizada com sucesso.",
            "replaced_settlement_id": settlement_id,
            "deleted": deleted,
        }, None

    @staticmethod
    def delete_settlement(
        *,
        bordero_id: int,
        settlement_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        bordero, settlement, error = FinancialBorderoService._load_bordero_settlement(
            bordero_id=bordero_id,
            settlement_id=settlement_id,
            company_id=company_id,
        )
        if error:
            return None, error

        child_error = FinancialBorderoService._delete_child_financial_settlements(
            company_id=company_id,
            bordero_settlement=settlement,
            allowed_company_ids=allowed_company_ids,
        )
        if child_error:
            return None, child_error

        try:
            deleted_at = datetime.utcnow()
            settlement.deleted_at = deleted_at
            settlement.settlement_status = "cancelled"
            settlement.metadata_json = {
                **dict(settlement.metadata_json or {}),
                "deleted_at": deleted_at.isoformat(),
                "deleted_via": "financial_bordero_service.delete_settlement",
            }

            items = FinancialBorderoItem.query.filter(
                FinancialBorderoItem.company_id == company_id,
                FinancialBorderoItem.bordero_id == bordero.id,
                FinancialBorderoItem.deleted_at.is_(None),
            ).order_by(FinancialBorderoItem.display_order.asc(), FinancialBorderoItem.id.asc()).all()
            FinancialBorderoService._recalculate_item_totals_from_settlements(
                bordero=bordero,
                items=items,
            )
            db.session.commit()
            return {
                "message": "Baixa do borderô removida com sucesso.",
                "id": settlement_id,
                "bordero": FinancialBorderoService._serialize_bordero(
                    bordero,
                    include_items=True,
                    include_settlements=True,
                ),
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao remover baixa do borderô %s", settlement_id)
            return None, f"Erro ao remover baixa do borderô: {exc}"

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
            return f"Título Financeiro já participa do borderô {active_bordero.bordero_code}."
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
        # O código é único por empresa mesmo após exclusão lógica. Não filtrar
        # deleted_at aqui: registros soft-deletados continuam protegidos pela
        # constraint uq_financial_borderos_company_code.
        prefix = "B"
        borderos = (
            FinancialBordero.query.filter(
                FinancialBordero.company_id == company_id,
            )
            .order_by(FinancialBordero.id.desc())
            .all()
        )
        max_number = 0
        for bordero in borderos or []:
            code = str(getattr(bordero, "bordero_code", "") or "").strip().upper()
            if not code.startswith(f"{prefix}-"):
                continue
            try:
                max_number = max(max_number, int(code.split("-")[-1]))
            except Exception:
                max_number = max(max_number, int(getattr(bordero, "id", 0) or 0))
        return f"{prefix}-{max_number + 1}"

    @staticmethod
    def _generate_bordero_settlement_code(company_id: int, bordero_code: str) -> str:
        # Mesma regra do borderô: settlement_code é único por empresa e não
        # pode reutilizar códigos de baixas excluídas logicamente.
        base = f"{bordero_code}-BX"
        settlements = (
            FinancialBorderoSettlement.query.filter(
                FinancialBorderoSettlement.company_id == company_id,
            )
            .order_by(FinancialBorderoSettlement.id.desc())
            .all()
        )
        max_number = 0
        for settlement in settlements or []:
            code = str(getattr(settlement, "settlement_code", "") or "").strip().upper()
            if not code.startswith(f"{base.upper()}-"):
                continue
            try:
                max_number = max(max_number, int(code.split("-")[-1]))
            except Exception:
                max_number = max(max_number, int(getattr(settlement, "id", 0) or 0))
        return f"{base}-{max_number + 1:03d}"

    @staticmethod
    def _is_duplicate_bordero_code_error(exc: IntegrityError) -> bool:
        constraint_name = str(
            getattr(getattr(getattr(exc, "orig", None), "diag", None), "constraint_name", "") or ""
        ).strip()
        if constraint_name == "uq_financial_borderos_company_code":
            return True
        message = str(getattr(exc, "orig", exc) or "").lower()
        return "uq_financial_borderos_company_code" in message

    @staticmethod
    def _build_schedule_snapshot(schedule: FinancialSchedule) -> Dict[str, Any]:
        payload = FinancialScheduleService._serialize_schedule(schedule, include_related_entries=True, include_summary=True)
        payload["captured_at"] = datetime.utcnow().isoformat()
        return payload

    @staticmethod
    def _build_bordero_settlement_audit_metadata(
        *,
        base_metadata: Dict[str, Any],
        bordero: FinancialBordero,
        settlement: FinancialBorderoSettlement,
        gross_amount: Decimal,
        allocated_total: Decimal,
        variance_amount: Decimal,
        allocation_payload: List[Dict[str, Any]],
        created_by_user_id: Optional[int],
        created_by_employee_id: Optional[int],
        created_by_agent: Optional[str],
    ) -> Dict[str, Any]:
        schedules = [item.get("financial_schedule_id") for item in allocation_payload if item.get("financial_schedule_id")]
        entry_allocations = [
            entry_allocation
            for item in allocation_payload
            for entry_allocation in (item.get("entry_allocations") or [])
        ]
        return {
            **dict(base_metadata or {}),
            "bordero_id": bordero.id,
            "bordero_code": bordero.bordero_code,
            "bordero_settlement_id": settlement.id,
            "bordero_settlement_code": settlement.settlement_code,
            "reconcile_via_bordero": True,
            "traceability_contract": "financial_bordero_settlement_v2",
            "allocation_summary": {
                "gross_amount": float(gross_amount or 0),
                "allocated_amount": float(allocated_total or 0),
                "variance_amount": float(variance_amount or 0),
                "title_count": len(set(schedules)),
                "entry_settlement_count": len(entry_allocations),
            },
            "allocations": allocation_payload,
            "audit": {
                "actor": {
                    "user_id": created_by_user_id,
                    "employee_id": created_by_employee_id,
                    "agent": created_by_agent or "app32",
                },
                "tenant_scope": {
                    "company_id": bordero.company_id,
                },
                "channel": "app32",
                "captured_at": datetime.utcnow().isoformat(),
            },
        }

    @staticmethod
    def _sync_bordero_totals_from_items(bordero: FinancialBordero, items: Sequence[FinancialBorderoItem]) -> Dict[str, Any]:
        selected_total = sum((Decimal(str(item.selected_amount or 0)) for item in items), Decimal("0.00")).quantize(Decimal("0.01"))
        settled_total = sum((Decimal(str(item.settled_amount or 0)) for item in items), Decimal("0.00")).quantize(Decimal("0.01"))
        open_total = sum((Decimal(str(item.open_amount or 0)) for item in items), Decimal("0.00")).quantize(Decimal("0.01"))
        if open_total <= Decimal("0.00") and selected_total > Decimal("0.00"):
            status = "settled"
            open_total = Decimal("0.00")
        elif settled_total > Decimal("0.00"):
            status = "partially_settled"
        else:
            status = "open"
        bordero.total_amount = selected_total
        bordero.settled_amount = settled_total
        bordero.open_amount = open_total
        bordero.status = status
        return {
            "total_amount": selected_total,
            "settled_amount": settled_total,
            "open_amount": open_total,
            "status": status,
        }

    @staticmethod
    def _recalculate_item_totals_from_settlements(
        *,
        bordero: FinancialBordero,
        items: Sequence[FinancialBorderoItem],
    ) -> Dict[int, Dict[str, Decimal]]:
        active_settlements = (
            FinancialBorderoSettlement.query.filter(
                FinancialBorderoSettlement.company_id == bordero.company_id,
                FinancialBorderoSettlement.bordero_id == bordero.id,
                FinancialBorderoSettlement.deleted_at.is_(None),
            )
            .order_by(FinancialBorderoSettlement.settlement_date.asc(), FinancialBorderoSettlement.id.asc())
            .all()
        )
        settled_by_item: Dict[int, Decimal] = {
            int(item.id): Decimal("0.00")
            for item in items
            if getattr(item, "id", None) is not None
        }
        for settlement in active_settlements:
            metadata = dict(settlement.metadata_json or {})
            for allocation in list(metadata.get("allocations") or []):
                try:
                    item_id = int(allocation.get("bordero_item_id") or 0)
                except (TypeError, ValueError):
                    continue
                if item_id not in settled_by_item:
                    continue
                settled_by_item[item_id] += Decimal(str(allocation.get("allocated_amount") or 0)).quantize(Decimal("0.01"))

        result: Dict[int, Dict[str, Decimal]] = {}
        for item in items:
            item_id = int(getattr(item, "id", 0) or 0)
            selected_amount = Decimal(str(getattr(item, "selected_amount", 0) or 0)).quantize(Decimal("0.01"))
            settled_amount = min(settled_by_item.get(item_id, Decimal("0.00")), selected_amount).quantize(Decimal("0.01"))
            open_amount = max(selected_amount - settled_amount, Decimal("0.00")).quantize(Decimal("0.01"))
            item.settled_amount = settled_amount
            item.open_amount = open_amount
            result[item_id] = {
                "selected_amount": selected_amount,
                "settled_amount": settled_amount,
                "open_amount": open_amount,
            }
        FinancialBorderoService._sync_bordero_totals_from_items(bordero, items)
        return result

    @staticmethod
    def _validate_bordero_settlement_payload(
        *,
        bordero: FinancialBordero,
        payload: Dict[str, Any],
        available_amount: Optional[Decimal] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialBorderoSettlementInput(**(payload or {}))
        except Exception as exc:
            return None, f"Payload inválido para baixa do borderô: {exc}"

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            bank_account_id=data.bank_account_id or bordero.bank_account_id,
        )
        if reference_error:
            return None, reference_error

        open_amount = Decimal(str(available_amount if available_amount is not None else (bordero.open_amount or 0))).quantize(Decimal("0.01"))
        gross_amount = Decimal(str(data.gross_amount or 0)).quantize(Decimal("0.01"))
        if gross_amount > open_amount:
            return None, f"Baixa excede o saldo em aberto do borderô. Saldo atual: {open_amount}."
        return data.model_dump(), None

    @staticmethod
    def _load_bordero_settlement(
        *,
        bordero_id: int,
        settlement_id: int,
        company_id: int,
    ) -> Tuple[Optional[FinancialBordero], Optional[FinancialBorderoSettlement], Optional[str]]:
        bordero = FinancialBordero.query.filter(
            FinancialBordero.id == bordero_id,
            FinancialBordero.company_id == company_id,
            FinancialBordero.deleted_at.is_(None),
        ).first()
        if not bordero:
            return None, None, "Borderô não encontrado no escopo da empresa."

        settlement = FinancialBorderoSettlement.query.filter(
            FinancialBorderoSettlement.id == settlement_id,
            FinancialBorderoSettlement.company_id == company_id,
            FinancialBorderoSettlement.bordero_id == bordero_id,
            FinancialBorderoSettlement.deleted_at.is_(None),
        ).first()
        if not settlement:
            return bordero, None, "Baixa do borderô não encontrada no escopo da empresa."
        return bordero, settlement, None

    @staticmethod
    def _delete_child_financial_settlements(
        *,
        company_id: int,
        bordero_settlement: FinancialBorderoSettlement,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Optional[str]:
        child_settlements = (
            FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.deleted_at.is_(None),
                or_(
                    FinancialSettlement.external_reference == bordero_settlement.settlement_code,
                    FinancialSettlement.metadata_json.contains(
                        {"bordero_settlement_code": bordero_settlement.settlement_code}
                    ),
                ),
            )
            .order_by(FinancialSettlement.id.asc())
            .all()
        )
        for child in child_settlements:
            _, error = FinancialService.delete_settlement(
                settlement_id=child.id,
                company_id=company_id,
                allowed_company_ids=allowed_company_ids,
                allow_bordero_child_delete=True,
            )
            if error:
                return error
        return None

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
        allocated = Decimal(str(amount or 0)).quantize(Decimal("0.01"))
        if allocated <= Decimal("0.00"):
            return [], None

        title_settlement_metadata = {
            "bordero_id": bordero.id,
            "bordero_code": bordero.bordero_code,
            "bordero_settlement_id": bordero_settlement.id,
            "bordero_settlement_code": bordero_settlement.settlement_code,
            "bordero_item_schedule_id": schedule_id,
            "bordero_allocation_amount": float(allocated),
            "bordero_trace": {
                "source": "bordero_settlement",
                "bordero_id": bordero.id,
                "bordero_code": bordero.bordero_code,
                "bordero_settlement_id": bordero_settlement.id,
                "bordero_settlement_code": bordero_settlement.settlement_code,
                "financial_schedule_id": schedule_id,
            },
            "reconcile_via_bordero": True,
            "traceability_contract": "financial_bordero_settlement_v2",
        }
        result, error = FinancialSettlementCompositionService.create_assisted_settlement(
            company_id=company_id,
            schedule_id=schedule_id,
            payload={
                "settlement_type": "manual",
                "settlement_status": "posted",
                "settlement_date": settlement_date,
                "gross_amount": allocated,
                "bank_account_id": bank_account_id,
                "notes": notes,
                "metadata_json": title_settlement_metadata,
                "created_by_user_id": created_by_user_id,
                "created_by_employee_id": created_by_employee_id,
                "created_by_agent": created_by_agent,
            },
            allowed_company_ids=[company_id],
            ignore_bordero_lock=True,
        )
        if error:
            return None, error

        entry_payload = dict((result or {}).get("entry") or {})
        settlement_payload = dict((result or {}).get("settlement") or {})
        return [
            {
                "financial_entry_id": entry_payload.get("id"),
                "entry_code": entry_payload.get("entry_code") or entry_payload.get("code"),
                "allocated_amount": float(allocated),
                "financial_settlement_id": settlement_payload.get("id"),
                "settlement_code": settlement_payload.get("settlement_code"),
                "financial_title_flow": True,
                "composition": ((result or {}).get("simulation") or {}).get("composition"),
            }
        ], None

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
