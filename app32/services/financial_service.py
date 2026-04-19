import logging
import os
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from flask import current_app
from models import db
from models.financial import (
    FinancialBankAccount,
    FinancialCounterparty,
    FinancialEntry,
    FinancialEntryAllocation,
    FinancialSchedule,
    FinancialSettlement,
    FinancialSettlementComponent,
    FinancialTitleCalculationLog,
)
from models.financial_budget import FinancialBudgetContract, FinancialBudgetDocument, FinancialBudgetLine
from models.process import ProcessInstance, ProcessRoutine
from models.routine import Routine
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from schemas.financial import (
    FinancialAllocationBatchInput,
    FinancialAllocationInput,
    FinancialEntryCreateInput,
    FinancialEntryUpdateInput,
    FinancialSettlementInput,
)
from services.financial_catalog_service import FinancialCatalogService
from services.financial_title_amount_service import FinancialTitleAmountService
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
    def serialize_entry_list(entries: Sequence[FinancialEntry]) -> List[Dict[str, Any]]:
        serialized_items = [FinancialService.enrich_amount_payload(entry.to_dict()) for entry in entries]
        if not serialized_items:
            return []

        entry_ids = [int(item["id"]) for item in serialized_items]
        company_ids = {int(item["company_id"]) for item in serialized_items if item.get("company_id") is not None}

        settlements = (
            FinancialSettlement.query.filter(
                FinancialSettlement.company_id.in_(company_ids),
                FinancialSettlement.financial_entry_id.in_(entry_ids),
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            )
            .order_by(
                FinancialSettlement.financial_entry_id.asc(),
                FinancialSettlement.settlement_date.desc(),
                FinancialSettlement.id.desc(),
            )
            .all()
        )

        settlement_summary_by_entry: Dict[int, Dict[str, Any]] = {}
        related_bank_account_ids = {
            int(item["bank_account_id"])
            for item in serialized_items
            if item.get("bank_account_id") is not None
        }
        related_counterparty_ids = {
            int(item["counterparty_id"])
            for item in serialized_items
            if item.get("counterparty_id") is not None
        }

        for settlement in settlements:
            if settlement.bank_account_id is not None:
                related_bank_account_ids.add(int(settlement.bank_account_id))
            summary = settlement_summary_by_entry.setdefault(
                int(settlement.financial_entry_id),
                {
                    "settled_principal_amount": 0.0,
                    "settled_net_amount": 0.0,
                    "settlement_count": 0,
                    "latest_settlement_date": settlement.settlement_date.isoformat() if settlement.settlement_date else None,
                    "latest_settlement_bank_account_id": settlement.bank_account_id,
                },
            )
            summary["settled_principal_amount"] += float(settlement.principal_amount or 0)
            summary["settled_net_amount"] += float(getattr(settlement, "gross_amount", None) or settlement.net_amount or 0)
            summary["settlement_count"] += 1

        bank_accounts = {
            item.id: item
            for item in FinancialBankAccount.query.filter(
                FinancialBankAccount.company_id.in_(company_ids),
                FinancialBankAccount.id.in_(related_bank_account_ids or {-1}),
                FinancialBankAccount.deleted_at.is_(None),
            ).all()
        }
        counterparties = {
            item.id: item
            for item in FinancialCounterparty.query.filter(
                FinancialCounterparty.company_id.in_(company_ids),
                FinancialCounterparty.id.in_(related_counterparty_ids or {-1}),
                FinancialCounterparty.deleted_at.is_(None),
            ).all()
        }

        for item in serialized_items:
            entry_id = int(item["id"])
            counterparty = counterparties.get(item.get("counterparty_id"))
            entry_bank_account = bank_accounts.get(item.get("bank_account_id"))
            settlement_summary = settlement_summary_by_entry.get(entry_id, {})
            settlement_bank_account = bank_accounts.get(settlement_summary.get("latest_settlement_bank_account_id"))
            external_reference = str(item.get("external_reference") or "")
            schedule_id = None
            if external_reference.startswith("financial_schedule:"):
                raw_schedule_id = external_reference.split(":", 1)[1].strip()
                if raw_schedule_id.isdigit():
                    schedule_id = int(raw_schedule_id)

            item["display_code"] = str(entry_id)
            item["schedule_id"] = schedule_id
            item["schedule_url"] = f"/financial/schedules/{schedule_id}" if schedule_id else None
            item["counterparty_name"] = counterparty.name if counterparty else None
            item["entry_bank_account_name"] = entry_bank_account.name if entry_bank_account else None
            item["settlement_bank_account_name"] = (
                settlement_bank_account.name if settlement_bank_account else None
            )
            item["bank_account_name"] = (
                item["settlement_bank_account_name"]
                or item["entry_bank_account_name"]
            )
            item["settled_principal_amount"] = float(settlement_summary.get("settled_principal_amount", 0) or 0)
            item["settled_amount"] = float(settlement_summary.get("settled_net_amount", 0) or 0)
            item["settled_signed_amount"] = FinancialService.get_signed_amount(
                item["settled_amount"],
                item.get("movement_nature"),
            )
            item["latest_settlement_date"] = settlement_summary.get("latest_settlement_date")
            item["settlement_count"] = int(settlement_summary.get("settlement_count", 0) or 0)

        return serialized_items

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
        if "entry_code" in merged:
            if merged["entry_code"] != entry.entry_code:
                return None, "O código do lançamento não pode ser alterado após a criação."
            merged.pop("entry_code", None)
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
                adjustment_kind = str((item.metadata_json or {}).get("adjustment_kind") or "").strip().lower()
                if adjustment_kind == "discount" and (item.allocated_amount or Decimal("0")) > 0:
                    return None, "Rateio de desconto deve possuir valor negativo."
                if adjustment_kind != "discount" and (item.allocated_amount or Decimal("0")) < 0:
                    return None, "Somente rateios de desconto podem possuir valor negativo."
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
    def _build_title_settlement_snapshot(
        *,
        entry: FinancialEntry,
        settlement_data: FinancialSettlementInput,
        total_liquidated_before: Decimal,
    ) -> Optional[Dict[str, Any]]:
        schedule_id = getattr(entry, "financial_schedule_id", None)
        if not schedule_id:
            return None

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == entry.company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None

        due_date = schedule.next_due_date or schedule.first_due_date or schedule.start_date
        amount_totals = FinancialTitleAmountService.calculate(
            company_id=schedule.company_id,
            template_amount=schedule.template_amount,
            metadata_json=schedule.metadata_json,
            due_date=due_date,
            reference_date=settlement_data.settlement_date or date.today(),
        )
        title_amount = Decimal(str(amount_totals.get("updated_amount") or schedule.template_amount or 0))
        settled_before = Decimal(total_liquidated_before or 0)
        settled_after = settled_before + Decimal(settlement_data.principal_amount or 0)
        open_after = max(title_amount - settled_after, Decimal("0"))
        return {
            "financial_schedule_id": schedule.id,
            "schedule_code": schedule.schedule_code,
            "calculation_date": (settlement_data.settlement_date or date.today()).isoformat(),
            "competence_date": schedule.competence_date.isoformat() if schedule.competence_date else None,
            "due_date": due_date.isoformat() if due_date else None,
            "template_amount": amount_totals.get("template_amount"),
            "correction_amount": amount_totals.get("correction_amount"),
            "discount_amount": amount_totals.get("discount_amount"),
            "updated_amount": amount_totals.get("updated_amount"),
            "settled_principal_before": float(settled_before.quantize(Decimal("0.01"))),
            "settled_principal_current": float(Decimal(settlement_data.principal_amount or 0).quantize(Decimal("0.01"))),
            "settled_principal_after": float(settled_after.quantize(Decimal("0.01"))),
            "open_principal_after": float(open_after.quantize(Decimal("0.01"))),
        }


    @staticmethod
    def _build_title_calculation_log_payload(
        *,
        entry: FinancialEntry,
        settlement: FinancialSettlement,
        snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "company_id": entry.company_id,
            "financial_schedule_id": int(snapshot["financial_schedule_id"]),
            "financial_entry_id": entry.id,
            "financial_settlement_id": getattr(settlement, "id", None),
            "event_type": "settlement_posted",
            "calculation_date": settlement.settlement_date,
            "template_amount": Decimal(str(snapshot.get("template_amount") or 0)),
            "correction_amount": Decimal(str(snapshot.get("correction_amount") or 0)),
            "discount_amount": Decimal(str(snapshot.get("discount_amount") or 0)),
            "updated_amount": Decimal(str(snapshot.get("updated_amount") or 0)),
            "settled_principal_before": Decimal(str(snapshot.get("settled_principal_before") or 0)),
            "settled_principal_current": Decimal(str(snapshot.get("settled_principal_current") or 0)),
            "settled_principal_after": Decimal(str(snapshot.get("settled_principal_after") or 0)),
            "open_principal_after": Decimal(str(snapshot.get("open_principal_after") or 0)),
            "metadata_json": {
                "source": "create_settlement",
                "settlement_code": settlement.settlement_code,
                "snapshot": snapshot,
            },
        }

    @staticmethod
    def _resolve_settlement_schedule_context(
        *,
        entry: FinancialEntry,
        title_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[int], Optional[date], Optional[date]]:
        schedule_id = getattr(entry, "financial_schedule_id", None)
        competence_date = None
        due_date = None

        snapshot = dict(title_snapshot or {})
        if not schedule_id and snapshot.get("financial_schedule_id") is not None:
            try:
                schedule_id = int(snapshot.get("financial_schedule_id"))
            except (TypeError, ValueError):
                schedule_id = None

        raw_competence = snapshot.get("competence_date")
        raw_due_date = snapshot.get("due_date")
        if raw_competence:
            try:
                competence_date = date.fromisoformat(str(raw_competence))
            except ValueError:
                competence_date = None
        if raw_due_date:
            try:
                due_date = date.fromisoformat(str(raw_due_date))
            except ValueError:
                due_date = None

        return schedule_id, competence_date, due_date

    @staticmethod
    def _build_settlement_component_payloads(
        *,
        entry: FinancialEntry,
        settlement_data: FinancialSettlementInput,
        title_snapshot: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        schedule_id, title_competence_date, title_due_date = FinancialService._resolve_settlement_schedule_context(
            entry=entry,
            title_snapshot=title_snapshot,
        )
        default_competence_date = settlement_data.settlement_date or title_competence_date or date.today()
        default_due_date = title_due_date or settlement_data.settlement_date

        if settlement_data.settlement_components:
            payloads: List[Dict[str, Any]] = []
            for component in settlement_data.settlement_components:
                component_due_date = component.due_date or default_due_date
                payloads.append(
                    {
                        "company_id": settlement_data.company_id,
                        "financial_schedule_id": schedule_id,
                        "component_type": component.component_type,
                        "amount": Decimal(str(component.amount or 0)).quantize(Decimal("0.01")),
                        "competence_date": component.competence_date or default_competence_date,
                        "due_date": component_due_date,
                        "source": component.source or "system",
                        "origin_adjustment_id": component.origin_adjustment_id,
                        "metadata_json": dict(component.metadata_json or {}),
                    }
                )
            return payloads

        amount_map = (
            ("principal", settlement_data.principal_amount, title_competence_date or default_competence_date, default_due_date),
            ("interest", settlement_data.interest_amount, settlement_data.settlement_date or default_competence_date, settlement_data.settlement_date or default_due_date),
            ("fine", settlement_data.penalty_amount, settlement_data.settlement_date or default_competence_date, settlement_data.settlement_date or default_due_date),
            ("discount", settlement_data.discount_amount, settlement_data.settlement_date or default_competence_date, settlement_data.settlement_date or default_due_date),
            ("manual_adjustment", settlement_data.fee_amount + settlement_data.other_adjustments_amount, settlement_data.settlement_date or default_competence_date, settlement_data.settlement_date or default_due_date),
        )
        payloads = []
        for component_type, raw_amount, competence_date_value, due_date_value in amount_map:
            amount = Decimal(str(raw_amount or 0)).quantize(Decimal("0.01"))
            if amount <= Decimal("0"):
                continue
            payloads.append(
                {
                    "company_id": settlement_data.company_id,
                    "financial_schedule_id": schedule_id,
                    "component_type": component_type,
                    "amount": amount,
                    "competence_date": competence_date_value or default_competence_date,
                    "due_date": due_date_value,
                    "source": "system",
                    "origin_adjustment_id": None,
                    "metadata_json": {"source_context": "aggregated_settlement_fields"},
                }
            )
        return payloads


    @staticmethod
    def create_settlement(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[FinancialSettlement], Optional[str]]:
        normalized_payload = dict(payload or {})
        company_id = normalized_payload.get("company_id")
        if company_id and not normalized_payload.get("settlement_code"):
            normalized_payload["settlement_code"] = FinancialService._generate_settlement_code(int(company_id))

        try:
            data = FinancialSettlementInput(**normalized_payload)
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

            if data.principal_amount <= Decimal("0"):
                return None, "Baixa inválida: o valor principal deve ser maior que zero."

            projected_total = Decimal(total_liquidated) + data.principal_amount
            if projected_total > Decimal(entry.original_amount or 0):
                return None, (
                    "Liquidação principal excede o valor original do lançamento. "
                    f"Liquidado atual: {total_liquidated}. Original: {entry.original_amount}."
                )

            settlement_payload = data.model_dump(exclude={"settlement_components"})
            title_snapshot = FinancialService._build_title_settlement_snapshot(
                entry=entry,
                settlement_data=data,
                total_liquidated_before=Decimal(total_liquidated),
            )
            component_payloads = FinancialService._build_settlement_component_payloads(
                entry=entry,
                settlement_data=data,
                title_snapshot=title_snapshot,
            )
            if title_snapshot:
                settlement_payload["metadata_json"] = {
                    **dict(settlement_payload.get("metadata_json") or {}),
                    "financial_title_snapshot": title_snapshot,
                }
            if component_payloads:
                settlement_payload["metadata_json"] = {
                    **dict(settlement_payload.get("metadata_json") or {}),
                    "settlement_component_count": len(component_payloads),
                }

            settlement = FinancialSettlement(**settlement_payload)
            db.session.add(settlement)
            flush = getattr(db.session, "flush", None)
            if callable(flush):
                flush()
            for component_payload in component_payloads:
                db.session.add(
                    FinancialSettlementComponent(
                        financial_settlement_id=getattr(settlement, "id", None),
                        **component_payload,
                    )
                )
            if title_snapshot:
                db.session.add(
                    FinancialTitleCalculationLog(
                        **FinancialService._build_title_calculation_log_payload(
                            entry=entry,
                            settlement=settlement,
                            snapshot=title_snapshot,
                        )
                    )
                )

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

    @staticmethod
    def _generate_settlement_code(company_id: int) -> str:
        prefix = "LIQ"
        last = (
            FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_code.like(f"{prefix}-%"),
            )
            .order_by(FinancialSettlement.id.desc())
            .first()
        )
        next_number = 1
        if last and getattr(last, "settlement_code", None):
            try:
                next_number = int(str(last.settlement_code).split("-")[-1]) + 1
            except Exception:
                next_number = int(getattr(last, "id", 0) or 0) + 1 or 1
        return f"{prefix}-{next_number:06d}"

    @staticmethod
    def upload_settlement_attachment(
        *,
        settlement_id: int,
        company_id: int,
        file: FileStorage,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        settlement = FinancialSettlement.query.filter(
            FinancialSettlement.id == settlement_id,
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
        ).first()
        if not settlement:
            return None, "Liquidação financeira não encontrada no escopo da empresa."

        if not file or not file.filename:
            return None, "Nenhum arquivo informado."

        original_name = secure_filename(file.filename) or "anexo"
        attachment_id = uuid.uuid4().hex
        stored_name = f"{attachment_id}_{original_name}"
        relative_dir = os.path.join("financial_settlements", str(company_id), str(settlement.id))
        absolute_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], relative_dir)
        os.makedirs(absolute_dir, exist_ok=True)
        absolute_path = os.path.join(absolute_dir, stored_name)
        file.save(absolute_path)

        metadata = dict(settlement.metadata_json or {})
        attachments = list(metadata.get("attachments") or [])
        attachment = {
            "id": attachment_id,
            "name": original_name,
            "stored_name": stored_name,
            "content_type": file.mimetype,
            "size": os.path.getsize(absolute_path),
            "uploaded_at": datetime.utcnow().isoformat(),
            "url": f"/uploads/{relative_dir.replace(os.sep, '/')}/{stored_name}",
        }
        attachments.append(attachment)
        metadata["attachments"] = attachments
        settlement.metadata_json = metadata
        db.session.commit()
        return attachment, None

    @staticmethod
    def delete_settlement_attachment(
        *,
        settlement_id: int,
        company_id: int,
        attachment_id: str,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        settlement = FinancialSettlement.query.filter(
            FinancialSettlement.id == settlement_id,
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
        ).first()
        if not settlement:
            return None, "Liquidação financeira não encontrada no escopo da empresa."

        metadata = dict(settlement.metadata_json or {})
        attachments = list(metadata.get("attachments") or [])
        remaining: List[Dict[str, Any]] = []
        removed: Optional[Dict[str, Any]] = None
        for item in attachments:
            if str(item.get("id")) == str(attachment_id):
                removed = item
            else:
                remaining.append(item)

        if not removed:
            return None, "Anexo não encontrado para a liquidação."

        metadata["attachments"] = remaining
        settlement.metadata_json = metadata
        db.session.commit()

        stored_name = removed.get("stored_name")
        if stored_name:
            absolute_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"],
                "financial_settlements",
                str(company_id),
                str(settlement.id),
                stored_name,
            )
            if os.path.exists(absolute_path):
                os.remove(absolute_path)

        return removed, None
