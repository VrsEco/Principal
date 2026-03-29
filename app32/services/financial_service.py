import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import FinancialEntry, FinancialEntryAllocation, FinancialSettlement
from models.financial_budget import FinancialBudgetContract, FinancialBudgetDocument, FinancialBudgetLine
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
from utils.permissions import is_administrator

logger = logging.getLogger(__name__)


class FinancialService:
    """Serviço determinístico do núcleo financeiro."""

    @staticmethod
    def get_signed_amount(amount: Decimal | float | int | None, movement_nature: str | None) -> float:
        normalized_amount = Decimal(str(amount or 0))
        absolute_amount = abs(normalized_amount)
        signed_amount = -absolute_amount if movement_nature == "debit" else absolute_amount
        return float(signed_amount)

    @staticmethod
    def get_amount_direction(movement_nature: str | None) -> str:
        return "outflow" if movement_nature == "debit" else "inflow"

    @staticmethod
    def enrich_amount_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        movement_nature = payload.get("movement_nature")
        signed_amount = FinancialService.get_signed_amount(payload.get("original_amount"), movement_nature)
        payload["signed_amount"] = signed_amount
        payload["amount_direction"] = FinancialService.get_amount_direction(movement_nature)
        payload["display_variant"] = "negative" if signed_amount < 0 else "positive"
        metadata = payload.get("metadata_json") or {}
        payload["is_reconciled"] = bool(metadata.get("reconciled"))
        return payload

    @staticmethod
    def is_entry_reconciled(entry: FinancialEntry) -> bool:
        metadata = dict(entry.metadata_json or {})
        if metadata.get("reconciled"):
            return True
        return bool(
            FinancialSettlement.query.filter(
                FinancialSettlement.company_id == entry.company_id,
                FinancialSettlement.financial_entry_id == entry.id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
                FinancialSettlement.reconciliation_status.in_(["matched", "reconciled"]),
            ).first()
        )

    @staticmethod
    def set_entry_reconciliation_state(
        *,
        entry: FinancialEntry,
        reconciled: bool,
        actor_reason: Optional[str] = None,
    ) -> None:
        metadata = dict(entry.metadata_json or {})
        metadata["reconciled"] = bool(reconciled)
        metadata["reconciliation_updated_reason"] = actor_reason
        entry.metadata_json = metadata

        target_status = "reconciled" if reconciled else "pending"
        settlements = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == entry.company_id,
            FinancialSettlement.financial_entry_id == entry.id,
            FinancialSettlement.deleted_at.is_(None),
            FinancialSettlement.settlement_status != "cancelled",
        ).all()
        for settlement in settlements:
            settlement.reconciliation_status = target_status

    @staticmethod
    def serialize_entry(entry: FinancialEntry, *, include_children: bool = True) -> Dict[str, Any]:
        payload = FinancialService.enrich_amount_payload(entry.to_dict())
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
    def _merge_budget_metadata(
        metadata_json: Optional[Dict[str, Any]],
        budget_links: Optional[Dict[str, Optional[int]]],
    ) -> Dict[str, Any]:
        metadata = dict(metadata_json or {})
        for key in ("budget_line_id", "budget_contract_id", "budget_document_id"):
            value = (budget_links or {}).get(key)
            if value is None:
                metadata.pop(key, None)
                continue
            metadata[key] = value
        return metadata

    @staticmethod
    def _resolve_budget_links(
        *,
        company_id: int,
        budget_line_id: Optional[int],
        budget_contract_id: Optional[int],
        budget_document_id: Optional[int],
    ) -> Tuple[Optional[Dict[str, Optional[int]]], Optional[str]]:
        def _get_line(line_id: Optional[int]) -> Optional[FinancialBudgetLine]:
            if not line_id:
                return None
            return FinancialBudgetLine.query.filter(
                FinancialBudgetLine.id == int(line_id),
                FinancialBudgetLine.company_id == company_id,
                FinancialBudgetLine.deleted_at.is_(None),
            ).first()

        def _get_contract(contract_id: Optional[int]) -> Optional[FinancialBudgetContract]:
            if not contract_id:
                return None
            return FinancialBudgetContract.query.filter(
                FinancialBudgetContract.id == int(contract_id),
                FinancialBudgetContract.company_id == company_id,
                FinancialBudgetContract.deleted_at.is_(None),
            ).first()

        def _get_document(document_id: Optional[int]) -> Optional[FinancialBudgetDocument]:
            if not document_id:
                return None
            return FinancialBudgetDocument.query.filter(
                FinancialBudgetDocument.id == int(document_id),
                FinancialBudgetDocument.company_id == company_id,
                FinancialBudgetDocument.deleted_at.is_(None),
            ).first()

        line = _get_line(budget_line_id)
        if budget_line_id and not line:
            return None, "Verba orçamentária não encontrada no escopo da empresa."

        contract = _get_contract(budget_contract_id)
        if budget_contract_id and not contract:
            return None, "Contrato orçamentário não encontrado no escopo da empresa."
        if contract:
            if line and contract.budget_line_id != line.id:
                return None, "Contrato orçamentário não pertence à verba informada."
            if not line:
                line = _get_line(contract.budget_line_id)
                if not line:
                    return None, "Verba orçamentária vinculada ao contrato não encontrada no escopo da empresa."

        document = _get_document(budget_document_id)
        if budget_document_id and not document:
            return None, "NF/equivalente orçamentária não encontrada no escopo da empresa."
        if document:
            if contract and document.budget_contract_id != contract.id:
                return None, "NF/equivalente não pertence ao contrato informado."
            if not contract:
                contract = _get_contract(document.budget_contract_id)
                if not contract:
                    return None, "Contrato orçamentário vinculado à NF/equivalente não encontrado no escopo da empresa."
            if line and contract.budget_line_id != line.id:
                return None, "NF/equivalente não pertence à verba informada."
            if not line:
                line = _get_line(contract.budget_line_id)
                if not line:
                    return None, "Verba orçamentária vinculada à NF/equivalente não encontrada no escopo da empresa."

        return {
            "budget_line_id": line.id if line else None,
            "budget_contract_id": contract.id if contract else None,
            "budget_document_id": document.id if document else None,
        }, None

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

        budget_links, budget_error = FinancialService._resolve_budget_links(
            company_id=data.company_id,
            budget_line_id=getattr(data, "budget_line_id", None),
            budget_contract_id=getattr(data, "budget_contract_id", None),
            budget_document_id=getattr(data, "budget_document_id", None),
        )
        if budget_error:
            return None, budget_error

        existing = FinancialEntry.query.filter(
            FinancialEntry.company_id == data.company_id,
            FinancialEntry.entry_code == data.entry_code,
        ).first()
        if existing:
            return None, f"Já existe lançamento com código {data.entry_code} para esta empresa."

        try:
            normalized = data.model_dump()
            normalized.update(budget_links or {})
            normalized["metadata_json"] = FinancialService._merge_budget_metadata(
                normalized.get("metadata_json"),
                budget_links,
            )
            entry = FinancialEntry(**normalized)
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
        from services.financial_bordero_service import FinancialBorderoService

        active_bordero = FinancialBorderoService.get_active_bordero_for_entry(company_id=company_id, entry=entry)
        if active_bordero:
            return None, f"Lançamento bloqueado pelo borderô {active_bordero.bordero_code}."

        merged = data.model_dump(exclude_unset=True)
        unlock_reconciliation = bool(merged.pop("unlock_reconciliation", False))
        requested_reconciled_state = merged.pop("reconciled", None)
        unlock_reason = merged.pop("reconciliation_unlock_reason", None)

        if FinancialService.is_entry_reconciled(entry):
            if unlock_reconciliation or requested_reconciled_state is False:
                if not is_administrator(company_id):
                    return None, (
                        "Lançamento conciliado exige demarcação por usuário com hierarquia administrativa."
                    )
                FinancialService.set_entry_reconciliation_state(
                    entry=entry,
                    reconciled=False,
                    actor_reason=unlock_reason or "Demarcação manual de conciliação.",
                )
            else:
                return None, (
                    "Lançamento conciliado está protegido. "
                    "Para alterar, um administrador deve demarcar a opção de conciliado."
                )

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

        budget_links, budget_error = FinancialService._resolve_budget_links(
            company_id=company_id,
            budget_line_id=merged.get("budget_line_id", getattr(entry, "budget_line_id", None)),
            budget_contract_id=merged.get("budget_contract_id", getattr(entry, "budget_contract_id", None)),
            budget_document_id=merged.get("budget_document_id", getattr(entry, "budget_document_id", None)),
        )
        if budget_error:
            return None, budget_error

        try:
            merged.update(budget_links or {})
            merged["metadata_json"] = FinancialService._merge_budget_metadata(
                merged.get("metadata_json", entry.metadata_json),
                budget_links,
            )
            for key, value in merged.items():
                setattr(entry, key, value)
            if requested_reconciled_state is True:
                FinancialService.set_entry_reconciliation_state(
                    entry=entry,
                    reconciled=True,
                    actor_reason=unlock_reason or "Marcação manual de conciliação.",
                )
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
        from services.financial_bordero_service import FinancialBorderoService

        active_bordero = FinancialBorderoService.get_active_bordero_for_entry(company_id=data.company_id, entry=entry)
        if active_bordero:
            return None, f"Lançamento bloqueado pelo borderô {active_bordero.bordero_code}."

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
        from services.financial_bordero_service import FinancialBorderoService

        active_bordero = FinancialBorderoService.get_active_bordero_for_entry(company_id=data.company_id, entry=entry)
        if active_bordero:
            return None, f"Lançamento bloqueado pelo borderô {active_bordero.bordero_code}. Faça a baixa pelo borderô."

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
