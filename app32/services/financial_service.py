import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import FinancialEntry, FinancialEntryAllocation, FinancialSettlement
from models.process import ProcessInstance, ProcessRoutine
from models.routine import Routine
from schemas.financial import (
    FinancialAllocationBatchInput,
    FinancialAllocationInput,
    FinancialEntryCreateInput,
    FinancialEntryUpdateInput,
    FinancialSettlementInput,
)
from services.financial_catalog_service import FinancialCatalogService

logger = logging.getLogger(__name__)


class FinancialService:
    """Serviço determinístico do núcleo financeiro."""

    @staticmethod
    def serialize_entry(entry: FinancialEntry, *, include_children: bool = True) -> Dict[str, Any]:
        payload = entry.to_dict()
        if not include_children:
            return payload

        payload["allocations"] = [
            allocation.to_dict()
            for allocation in FinancialEntryAllocation.query.filter(
                FinancialEntryAllocation.company_id == entry.company_id,
                FinancialEntryAllocation.financial_entry_id == entry.id,
                FinancialEntryAllocation.deleted_at.is_(None),
            )
            .order_by(FinancialEntryAllocation.id.asc())
            .all()
        ]
        payload["settlements"] = [
            settlement.to_dict()
            for settlement in FinancialSettlement.query.filter(
                FinancialSettlement.company_id == entry.company_id,
                FinancialSettlement.financial_entry_id == entry.id,
                FinancialSettlement.deleted_at.is_(None),
            )
            .order_by(FinancialSettlement.settlement_date.asc(), FinancialSettlement.id.asc())
            .all()
        ]
        return payload

    @staticmethod
    def list_entries(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        status: Optional[str] = None,
        entry_type: Optional[str] = None,
        origin_type: Optional[str] = None,
        activity_id: Optional[int] = None,
        process_instance_id: Optional[int] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        query = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        )

        if status:
            query = query.filter(FinancialEntry.status == status)
        if entry_type:
            query = query.filter(FinancialEntry.entry_type == entry_type)
        if origin_type:
            query = query.filter(FinancialEntry.origin_type == origin_type)
        if activity_id:
            query = query.filter(FinancialEntry.activity_id == activity_id)
        if process_instance_id:
            query = query.filter(FinancialEntry.process_instance_id == process_instance_id)

        entries = query.order_by(FinancialEntry.competence_date.desc(), FinancialEntry.id.desc()).all()
        return [FinancialService.serialize_entry(entry, include_children=False) for entry in entries], None

    @staticmethod
    def get_entry(
        *,
        entry_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro não encontrado no escopo da empresa."

        return FinancialService.serialize_entry(entry), None

    @staticmethod
    def _ensure_company_scope(company_id: int, allowed_company_ids: Optional[Sequence[int]]) -> Optional[str]:
        if allowed_company_ids is None:
            return None

        normalized = {int(cid) for cid in allowed_company_ids if cid is not None}
        if not normalized:
            return "Nenhuma empresa autorizada encontrada para a operação financeira."

        if int(company_id) not in normalized:
            return "A operação financeira está fora do escopo da empresa autorizada."

        return None

    @staticmethod
    def _validate_operational_links(company_id: int, activity_id: Optional[int], process_instance_id: Optional[int], routine_id: Optional[int]) -> Optional[str]:
        if activity_id:
            activity = ProcessRoutine.query.filter(
                ProcessRoutine.id == activity_id,
                ProcessRoutine.company_id == company_id,
            ).first()
            if not activity:
                return "Atividade associada não encontrada no escopo da empresa."

        if process_instance_id:
            instance = ProcessInstance.query.filter(
                ProcessInstance.id == process_instance_id,
                ProcessInstance.company_id == company_id,
            ).first()
            if not instance:
                return "Instância associada não encontrada no escopo da empresa."

        if routine_id:
            routine = Routine.query.filter(
                Routine.id == routine_id,
                Routine.company_id == company_id,
            ).first()
            if not routine:
                return "Rotina associada não encontrada no escopo da empresa."

        return None

    @staticmethod
    def create_entry(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[FinancialEntry], Optional[str]]:
        try:
            data = FinancialEntryCreateInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para lançamento financeiro: {str(exc)}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        link_error = FinancialService._validate_operational_links(
            company_id=data.company_id,
            activity_id=data.activity_id,
            process_instance_id=data.process_instance_id,
            routine_id=data.routine_id,
        )
        if link_error:
            return None, link_error

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            bank_account_id=data.bank_account_id,
            chart_account_id=data.chart_account_id,
            cost_center_id=data.cost_center_id,
            counterparty_id=data.counterparty_id,
        )
        if reference_error:
            return None, reference_error

        existing = FinancialEntry.query.filter(
            FinancialEntry.company_id == data.company_id,
            FinancialEntry.entry_code == data.entry_code,
        ).first()
        if existing:
            return None, f"Já existe lançamento com código {data.entry_code} para esta empresa."

        try:
            entry = FinancialEntry(**data.model_dump())
            db.session.add(entry)
            db.session.commit()
            return entry, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar lançamento financeiro")
            return None, f"Erro ao criar lançamento financeiro: {str(exc)}"

    @staticmethod
    def update_entry(
        *,
        entry_id: int,
        company_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[FinancialEntry], Optional[str]]:
        try:
            data = FinancialEntryUpdateInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para atualização do lançamento: {str(exc)}"

        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == entry_id,
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro não encontrado no escopo da empresa."

        merged = data.model_dump(exclude_unset=True)
        activity_id = merged.get("activity_id", entry.activity_id)
        process_instance_id = merged.get("process_instance_id", entry.process_instance_id)
        routine_id = merged.get("routine_id", entry.routine_id)

        link_error = FinancialService._validate_operational_links(
            company_id=company_id,
            activity_id=activity_id,
            process_instance_id=process_instance_id,
            routine_id=routine_id,
        )
        if link_error:
            return None, link_error

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            bank_account_id=merged.get("bank_account_id", entry.bank_account_id),
            chart_account_id=merged.get("chart_account_id", entry.chart_account_id),
            cost_center_id=merged.get("cost_center_id", entry.cost_center_id),
            counterparty_id=merged.get("counterparty_id", entry.counterparty_id),
        )
        if reference_error:
            return None, reference_error

        try:
            for key, value in merged.items():
                setattr(entry, key, value)
            db.session.commit()
            return entry, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao atualizar lançamento financeiro %s", entry_id)
            return None, f"Erro ao atualizar lançamento financeiro: {str(exc)}"

    @staticmethod
    def replace_allocations(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[FinancialEntryAllocation]], Optional[str]]:
        try:
            data = FinancialAllocationBatchInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para rateio: {str(exc)}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == data.financial_entry_id,
            FinancialEntry.company_id == data.company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro não encontrado para rateio."

        normalized_allocations: List[FinancialAllocationInput] = []
        for item in data.allocations:
            if item.company_id != data.company_id or item.financial_entry_id != data.financial_entry_id:
                return None, "Todos os rateios devem pertencer ao mesmo lançamento e empresa."
            link_error = FinancialService._validate_operational_links(
                company_id=data.company_id,
                activity_id=item.activity_id,
                process_instance_id=item.process_instance_id,
                routine_id=item.routine_id,
            )
            if link_error:
                return None, link_error
            normalized_allocations.append(item)

        percentage_total = Decimal("0")
        amount_total = Decimal("0")
        allocation_mode: Optional[str] = None

        for item in normalized_allocations:
            if allocation_mode is None:
                allocation_mode = item.allocation_type
            elif allocation_mode != item.allocation_type:
                return None, "Não é permitido misturar rateio por percentual e por valor no mesmo lançamento."

            if item.allocation_type == "percentage":
                percentage_total += item.percentage or Decimal("0")
            else:
                amount_total += item.allocated_amount or Decimal("0")

        if allocation_mode == "percentage" and percentage_total != Decimal("100"):
            return None, f"Rateio percentual inválido. Soma atual: {percentage_total}."

        if allocation_mode == "amount" and amount_total != (entry.original_amount or Decimal("0")):
            return None, (
                "Rateio por valor inválido. "
                f"Soma atual: {amount_total}. Valor do lançamento: {entry.original_amount}."
            )

        try:
            FinancialEntryAllocation.query.filter(
                FinancialEntryAllocation.financial_entry_id == entry.id,
                FinancialEntryAllocation.company_id == data.company_id,
            ).delete(synchronize_session=False)

            created: List[FinancialEntryAllocation] = []
            for item in normalized_allocations:
                allocation = FinancialEntryAllocation(**item.model_dump())
                db.session.add(allocation)
                created.append(allocation)

            db.session.commit()
            return created, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao substituir rateios do lançamento %s", entry.id)
            return None, f"Erro ao persistir rateio: {str(exc)}"

    @staticmethod
    def create_settlement(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[FinancialSettlement], Optional[str]]:
        try:
            data = FinancialSettlementInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para liquidação: {str(exc)}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        entry = FinancialEntry.query.filter(
            FinancialEntry.id == data.financial_entry_id,
            FinancialEntry.company_id == data.company_id,
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if not entry:
            return None, "Lançamento financeiro não encontrado para liquidação."

        existing = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == data.company_id,
            FinancialSettlement.settlement_code == data.settlement_code,
        ).first()
        if existing:
            return None, f"Já existe liquidação com código {data.settlement_code} para esta empresa."

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            bank_account_id=data.bank_account_id,
        )
        if reference_error:
            return None, reference_error

        try:
            total_liquidated = (
                db.session.query(db.func.coalesce(db.func.sum(FinancialSettlement.principal_amount), 0))
                .filter(
                    FinancialSettlement.company_id == data.company_id,
                    FinancialSettlement.financial_entry_id == data.financial_entry_id,
                    FinancialSettlement.deleted_at.is_(None),
                    FinancialSettlement.settlement_status != "cancelled",
                )
                .scalar()
            ) or Decimal("0")

            projected_total = Decimal(total_liquidated) + data.principal_amount
            if projected_total > Decimal(entry.original_amount or 0):
                return None, (
                    "Liquidação principal excede o valor original do lançamento. "
                    f"Liquidado atual: {total_liquidated}. Original: {entry.original_amount}."
                )

            settlement = FinancialSettlement(**data.model_dump())
            db.session.add(settlement)

            if projected_total == Decimal(entry.original_amount or 0):
                entry.status = "settled"
            elif projected_total > Decimal("0"):
                entry.status = "partially_settled"

            db.session.commit()
            return settlement, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar liquidação para lançamento %s", data.financial_entry_id)
            return None, f"Erro ao criar liquidação: {str(exc)}"
