from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import (
    FinancialBankAccount,
    FinancialBudgetContract,
    FinancialBudgetDocument,
    FinancialBudgetLine,
    FinancialBudgetVersion,
    FinancialCounterparty,
    FinancialEntry,
    FinancialSchedule,
    db,
)
from models.financial_budget import (
    BUDGET_CONTRACT_STATUS_VALUES,
    BUDGET_DOCUMENT_STATUS_VALUES,
    BUDGET_DOCUMENT_TYPE_VALUES,
)
from schemas.financial_budget import (
    FinancialBudgetContractCreateInput,
    FinancialBudgetContractUpdateInput,
    FinancialBudgetDocumentCreateInput,
    FinancialBudgetDocumentScheduleBatchInput,
    FinancialBudgetDocumentUpdateInput,
    FinancialBudgetLineCreate,
    FinancialBudgetLineUpdate,
)
from services.financial_budget_service import FinancialBudgetService
from services.financial_catalog_service import FinancialCatalogService
from services.financial_schedule_service import FinancialScheduleService
from services.financial_service import FinancialService


_DECIMAL_ZERO = Decimal("0")
_DECIMAL_TOLERANCE = Decimal("0.01")


class FinancialBudgetWorkspaceService:
    @staticmethod
    def get_planning_workspace(
        *,
        company_id: int,
        version_id: Optional[int] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        versions, error = FinancialBudgetService.list_versions(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        version = FinancialBudgetWorkspaceService._resolve_version(
            company_id=company_id,
            version_id=version_id,
        )
        if version_id and not version:
            return None, "Orçamento não encontrado no escopo da empresa."

        if not version:
            return {
                "versions": versions or [],
                "selected_version_id": None,
                "version": None,
                "summary": FinancialBudgetWorkspaceService._empty_summary(),
                "lines": [],
            }, None

        lines = FinancialBudgetWorkspaceService._list_lines_for_version(
            company_id=company_id,
            version_id=version.id,
        )
        payload_lines = [FinancialBudgetWorkspaceService._serialize_line(line) for line in lines]

        return {
            "versions": versions or [],
            "selected_version_id": version.id,
            "version": version.to_dict(),
            "summary": FinancialBudgetWorkspaceService._build_version_summary(lines),
            "lines": payload_lines,
        }, None

    @staticmethod
    def get_execution_workspace(
        *,
        company_id: int,
        version_id: Optional[int] = None,
        line_id: Optional[int] = None,
        contract_id: Optional[int] = None,
        document_id: Optional[int] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        versions, error = FinancialBudgetService.list_versions(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        version = FinancialBudgetWorkspaceService._resolve_version(
            company_id=company_id,
            version_id=version_id,
        )
        if version_id and not version:
            return None, "Orçamento não encontrado no escopo da empresa."

        if not version:
            return {
                "versions": versions or [],
                "selected_version_id": None,
                "version": None,
                "summary": FinancialBudgetWorkspaceService._empty_summary(),
                "lines": [],
                "selected_line_id": None,
                "selected_contract_id": None,
                "selected_document_id": None,
                "contracts": [],
                "documents": [],
                "schedules": [],
            }, None

        lines = FinancialBudgetWorkspaceService._list_lines_for_version(
            company_id=company_id,
            version_id=version.id,
        )
        selected_line = FinancialBudgetWorkspaceService._resolve_selected_line(lines=lines, line_id=line_id)
        if line_id and not selected_line:
            return None, "Verba orçamentária não encontrada para o orçamento selecionado."

        contracts = (
            FinancialBudgetWorkspaceService._list_contracts_for_line(company_id=company_id, line_id=selected_line.id)
            if selected_line
            else []
        )
        selected_contract = FinancialBudgetWorkspaceService._resolve_selected_contract(
            contracts=contracts,
            contract_id=contract_id,
        )
        if contract_id and not selected_contract:
            return None, "Contrato não encontrado para a verba selecionada."

        documents = (
            FinancialBudgetWorkspaceService._list_documents_for_contract(
                company_id=company_id,
                contract_id=selected_contract.id,
            )
            if selected_contract
            else []
        )
        selected_document = FinancialBudgetWorkspaceService._resolve_selected_document(
            documents=documents,
            document_id=document_id,
        )
        if document_id and not selected_document:
            return None, "Documento não encontrado para o contrato selecionado."

        schedules = (
            FinancialBudgetWorkspaceService._list_schedules_for_document(
                company_id=company_id,
                document_id=selected_document.id,
            )
            if selected_document
            else []
        )

        return {
            "versions": versions or [],
            "selected_version_id": version.id,
            "version": version.to_dict(),
            "summary": FinancialBudgetWorkspaceService._build_version_summary(lines),
            "lines": [FinancialBudgetWorkspaceService._serialize_line(line) for line in lines],
            "selected_line_id": selected_line.id if selected_line else None,
            "selected_line": FinancialBudgetWorkspaceService._serialize_line(selected_line) if selected_line else None,
            "contracts": [FinancialBudgetWorkspaceService._serialize_contract(contract) for contract in contracts],
            "selected_contract_id": selected_contract.id if selected_contract else None,
            "selected_contract": FinancialBudgetWorkspaceService._serialize_contract(selected_contract) if selected_contract else None,
            "documents": [FinancialBudgetWorkspaceService._serialize_document(document) for document in documents],
            "selected_document_id": selected_document.id if selected_document else None,
            "selected_document": FinancialBudgetWorkspaceService._serialize_document(selected_document) if selected_document else None,
            "schedules": [FinancialBudgetWorkspaceService._serialize_schedule(schedule) for schedule in schedules],
        }, None

    @staticmethod
    def list_options(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        base_options, error = FinancialBudgetService.list_options(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        counterparties = (
            FinancialCounterparty.query.filter(
                FinancialCounterparty.company_id == company_id,
                FinancialCounterparty.deleted_at.is_(None),
                FinancialCounterparty.is_active.is_(True),
            )
            .order_by(FinancialCounterparty.name.asc(), FinancialCounterparty.id.asc())
            .all()
        )
        bank_accounts = (
            FinancialBankAccount.query.filter(
                FinancialBankAccount.company_id == company_id,
                FinancialBankAccount.deleted_at.is_(None),
                FinancialBankAccount.is_active.is_(True),
            )
            .order_by(FinancialBankAccount.name.asc(), FinancialBankAccount.id.asc())
            .all()
        )

        return {
            **(base_options or {}),
            "counterparties": [
                {
                    "id": item.id,
                    "code": item.code,
                    "name": item.name,
                    "legal_name": item.legal_name,
                    "default_chart_account_id": item.default_chart_account_id,
                    "default_cost_center_id": item.default_cost_center_id,
                }
                for item in counterparties
            ],
            "bank_accounts": [
                {
                    "id": item.id,
                    "code": item.code,
                    "name": item.name,
                    "bank_name": item.bank_name,
                }
                for item in bank_accounts
            ],
            "contract_statuses": list(BUDGET_CONTRACT_STATUS_VALUES),
            "document_statuses": list(BUDGET_DOCUMENT_STATUS_VALUES),
            "document_types": list(BUDGET_DOCUMENT_TYPE_VALUES),
        }, None

    @staticmethod
    def create_line(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        data = FinancialBudgetLineCreate.model_validate(payload)
        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        version = FinancialBudgetWorkspaceService._get_version(
            company_id=data.company_id,
            version_id=data.budget_version_id,
        )
        if not version:
            return None, "Orçamento não encontrado no escopo da empresa."

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            chart_account_id=data.chart_account_id,
            cost_center_id=data.cost_center_id,
        )
        if reference_error:
            return None, reference_error

        duplicate = FinancialBudgetLine.query.filter(
            FinancialBudgetLine.company_id == data.company_id,
            FinancialBudgetLine.budget_version_id == data.budget_version_id,
            FinancialBudgetLine.line_code == data.line_code,
            FinancialBudgetLine.deleted_at.is_(None),
        ).first()
        if duplicate:
            return None, f"Já existe verba orçamentária com código {data.line_code} neste orçamento."

        item = FinancialBudgetLine(**data.model_dump())
        db.session.add(item)
        try:
            db.session.commit()
            return FinancialBudgetWorkspaceService._serialize_line(item), None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível criar a verba orçamentária: {exc}"

    @staticmethod
    def update_line(
        *,
        company_id: int,
        line_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        data = FinancialBudgetLineUpdate.model_validate(payload)
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        item = FinancialBudgetWorkspaceService._get_line(company_id=company_id, line_id=line_id)
        if not item:
            return None, "Verba orçamentária não encontrada no escopo da empresa."

        merged = data.model_dump(exclude_unset=True)
        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            chart_account_id=merged.get("chart_account_id", item.chart_account_id),
            cost_center_id=merged.get("cost_center_id", item.cost_center_id),
        )
        if reference_error:
            return None, reference_error

        new_code = merged.get("line_code")
        if new_code and new_code != item.line_code:
            duplicate = FinancialBudgetLine.query.filter(
                FinancialBudgetLine.company_id == company_id,
                FinancialBudgetLine.budget_version_id == item.budget_version_id,
                FinancialBudgetLine.line_code == new_code,
                FinancialBudgetLine.id != item.id,
                FinancialBudgetLine.deleted_at.is_(None),
            ).first()
            if duplicate:
                return None, f"Já existe verba orçamentária com código {new_code} neste orçamento."

        try:
            for key, value in merged.items():
                setattr(item, key, value)
            db.session.commit()
            return FinancialBudgetWorkspaceService._serialize_line(item), None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível atualizar a verba orçamentária: {exc}"

    @staticmethod
    def delete_line(
        *,
        company_id: int,
        line_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        item = FinancialBudgetWorkspaceService._get_line(company_id=company_id, line_id=line_id)
        if not item:
            return None, "Verba orçamentária não encontrada no escopo da empresa."

        schedule_ids = FinancialBudgetWorkspaceService._collect_line_schedule_ids(item)
        if FinancialBudgetWorkspaceService._has_generated_entries(company_id=company_id, schedule_ids=schedule_ids):
            return None, "Existem agendamentos já convertidos em lançamentos. Exclua/cancele os lançamentos vinculados antes de remover a verba."

        now = datetime.utcnow()
        try:
            item.deleted_at = now
            for contract in item.contracts.filter(FinancialBudgetContract.deleted_at.is_(None)).all():
                contract.deleted_at = now
                for document in contract.documents.filter(FinancialBudgetDocument.deleted_at.is_(None)).all():
                    document.deleted_at = now
                    for schedule in FinancialBudgetWorkspaceService._list_schedules_for_document(
                        company_id=company_id,
                        document_id=document.id,
                    ):
                        schedule.deleted_at = now
            for amount in item.amounts.filter_by(deleted_at=None).all():
                amount.deleted_at = now
            db.session.commit()
            return {"message": "Verba orçamentária removida com sucesso.", "id": line_id}, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível remover a verba orçamentária: {exc}"

    @staticmethod
    def create_contract(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        data = FinancialBudgetContractCreateInput.model_validate(payload)
        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        line = FinancialBudgetWorkspaceService._get_line(company_id=data.company_id, line_id=data.budget_line_id)
        if not line:
            return None, "Verba orçamentária não encontrada no escopo da empresa."

        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            counterparty_id=data.counterparty_id,
        )
        if reference_error:
            return None, reference_error

        duplicate = FinancialBudgetContract.query.filter(
            FinancialBudgetContract.company_id == data.company_id,
            FinancialBudgetContract.contract_code == data.contract_code,
            FinancialBudgetContract.deleted_at.is_(None),
        ).first()
        if duplicate:
            return None, f"Já existe contrato com código {data.contract_code} para esta empresa."

        item = FinancialBudgetContract(**data.model_dump())
        db.session.add(item)
        try:
            db.session.commit()
            return FinancialBudgetWorkspaceService._serialize_contract(item), None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível criar o contrato: {exc}"

    @staticmethod
    def update_contract(
        *,
        company_id: int,
        contract_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        data = FinancialBudgetContractUpdateInput.model_validate(payload)
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        item = FinancialBudgetWorkspaceService._get_contract(company_id=company_id, contract_id=contract_id)
        if not item:
            return None, "Contrato não encontrado no escopo da empresa."

        merged = data.model_dump(exclude_unset=True)
        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            counterparty_id=merged.get("counterparty_id", item.counterparty_id),
        )
        if reference_error:
            return None, reference_error

        start_date = merged.get("start_date", item.start_date)
        end_date = merged.get("end_date", item.end_date)
        if start_date and end_date and end_date < start_date:
            return None, "end_date não pode ser menor que start_date."

        new_code = merged.get("contract_code")
        if new_code and new_code != item.contract_code:
            duplicate = FinancialBudgetContract.query.filter(
                FinancialBudgetContract.company_id == company_id,
                FinancialBudgetContract.contract_code == new_code,
                FinancialBudgetContract.id != item.id,
                FinancialBudgetContract.deleted_at.is_(None),
            ).first()
            if duplicate:
                return None, f"Já existe contrato com código {new_code} para esta empresa."

        try:
            for key, value in merged.items():
                setattr(item, key, value)
            db.session.commit()
            return FinancialBudgetWorkspaceService._serialize_contract(item), None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível atualizar o contrato: {exc}"

    @staticmethod
    def delete_contract(
        *,
        company_id: int,
        contract_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        item = FinancialBudgetWorkspaceService._get_contract(company_id=company_id, contract_id=contract_id)
        if not item:
            return None, "Contrato não encontrado no escopo da empresa."

        schedule_ids = FinancialBudgetWorkspaceService._collect_contract_schedule_ids(item)
        if FinancialBudgetWorkspaceService._has_generated_entries(company_id=company_id, schedule_ids=schedule_ids):
            return None, "Existem agendamentos deste contrato já convertidos em lançamentos. Faça o saneamento antes de remover o contrato."

        now = datetime.utcnow()
        try:
            item.deleted_at = now
            for document in item.documents.filter(FinancialBudgetDocument.deleted_at.is_(None)).all():
                document.deleted_at = now
                for schedule in FinancialBudgetWorkspaceService._list_schedules_for_document(
                    company_id=company_id,
                    document_id=document.id,
                ):
                    schedule.deleted_at = now
            db.session.commit()
            return {"message": "Contrato removido com sucesso.", "id": contract_id}, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível remover o contrato: {exc}"

    @staticmethod
    def create_document(
        *,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        data = FinancialBudgetDocumentCreateInput.model_validate(payload)
        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        contract = FinancialBudgetWorkspaceService._get_contract(
            company_id=data.company_id,
            contract_id=data.budget_contract_id,
        )
        if not contract:
            return None, "Contrato não encontrado no escopo da empresa."

        counterparty_id = data.counterparty_id or contract.counterparty_id
        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=data.company_id,
            counterparty_id=counterparty_id,
        )
        if reference_error:
            return None, reference_error

        duplicate = FinancialBudgetDocument.query.filter(
            FinancialBudgetDocument.company_id == data.company_id,
            FinancialBudgetDocument.document_code == data.document_code,
            FinancialBudgetDocument.deleted_at.is_(None),
        ).first()
        if duplicate:
            return None, f"Já existe NF/equivalente com código {data.document_code} para esta empresa."

        normalized = data.model_dump()
        normalized["counterparty_id"] = counterparty_id
        item = FinancialBudgetDocument(**normalized)
        db.session.add(item)
        try:
            db.session.commit()
            return FinancialBudgetWorkspaceService._serialize_document(item), None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível criar a NF/equivalente: {exc}"

    @staticmethod
    def update_document(
        *,
        company_id: int,
        document_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        data = FinancialBudgetDocumentUpdateInput.model_validate(payload)
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        item = FinancialBudgetWorkspaceService._get_document(company_id=company_id, document_id=document_id)
        if not item:
            return None, "NF/equivalente não encontrada no escopo da empresa."

        merged = data.model_dump(exclude_unset=True)
        reference_error = FinancialCatalogService.validate_reference_ids(
            company_id=company_id,
            counterparty_id=merged.get("counterparty_id", item.counterparty_id),
        )
        if reference_error:
            return None, reference_error

        new_code = merged.get("document_code")
        if new_code and new_code != item.document_code:
            duplicate = FinancialBudgetDocument.query.filter(
                FinancialBudgetDocument.company_id == company_id,
                FinancialBudgetDocument.document_code == new_code,
                FinancialBudgetDocument.id != item.id,
                FinancialBudgetDocument.deleted_at.is_(None),
            ).first()
            if duplicate:
                return None, f"Já existe NF/equivalente com código {new_code} para esta empresa."

        requested_amount = Decimal(str(merged.get("document_amount", item.document_amount or 0)))
        scheduled_total = FinancialBudgetWorkspaceService._sum_schedule_amounts(
            FinancialBudgetWorkspaceService._list_schedules_for_document(company_id=company_id, document_id=item.id)
        )
        if requested_amount + _DECIMAL_TOLERANCE < scheduled_total:
            return None, "O valor do documento não pode ser menor que o total já agendado."

        try:
            for key, value in merged.items():
                setattr(item, key, value)
            FinancialBudgetWorkspaceService._refresh_document_status(item)
            db.session.commit()
            return FinancialBudgetWorkspaceService._serialize_document(item), None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível atualizar a NF/equivalente: {exc}"

    @staticmethod
    def delete_document(
        *,
        company_id: int,
        document_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        item = FinancialBudgetWorkspaceService._get_document(company_id=company_id, document_id=document_id)
        if not item:
            return None, "NF/equivalente não encontrada no escopo da empresa."

        schedule_ids = [
            schedule.id
            for schedule in FinancialBudgetWorkspaceService._list_schedules_for_document(
                company_id=company_id,
                document_id=item.id,
            )
        ]
        if FinancialBudgetWorkspaceService._has_generated_entries(company_id=company_id, schedule_ids=schedule_ids):
            return None, "Existem agendamentos desta NF já convertidos em lançamentos. Faça o saneamento antes de remover a NF."

        now = datetime.utcnow()
        try:
            item.deleted_at = now
            for schedule in FinancialBudgetWorkspaceService._list_schedules_for_document(
                company_id=company_id,
                document_id=item.id,
            ):
                schedule.deleted_at = now
            db.session.commit()
            return {"message": "NF/equivalente removida com sucesso.", "id": document_id}, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível remover a NF/equivalente: {exc}"

    @staticmethod
    def list_document_schedules(
        *,
        company_id: int,
        document_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        item = FinancialBudgetWorkspaceService._get_document(company_id=company_id, document_id=document_id)
        if not item:
            return None, "NF/equivalente não encontrada no escopo da empresa."

        schedules = FinancialBudgetWorkspaceService._list_schedules_for_document(company_id=company_id, document_id=item.id)
        return [FinancialBudgetWorkspaceService._serialize_schedule(schedule) for schedule in schedules], None

    @staticmethod
    def create_document_schedules(
        *,
        company_id: int,
        document_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        normalized_payload = dict(payload or {})
        normalized_payload["company_id"] = company_id
        data = FinancialBudgetDocumentScheduleBatchInput.model_validate(normalized_payload)

        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        document = FinancialBudgetWorkspaceService._get_document(company_id=company_id, document_id=document_id)
        if not document:
            return None, "NF/equivalente não encontrada no escopo da empresa."

        contract = FinancialBudgetWorkspaceService._get_contract(
            company_id=company_id,
            contract_id=document.budget_contract_id,
        )
        if not contract:
            return None, "Contrato vinculado ao documento não encontrado."

        line = FinancialBudgetWorkspaceService._get_line(company_id=company_id, line_id=contract.budget_line_id)
        if not line:
            return None, "Verba orçamentária vinculada ao documento não encontrada."

        if not line.chart_account_id or not line.cost_center_id:
            return None, "A verba precisa ter plano de contas e centro de resultado para gerar agendamentos financeiros."

        current_schedules = FinancialBudgetWorkspaceService._list_schedules_for_document(
            company_id=company_id,
            document_id=document.id,
        )
        existing_total = FinancialBudgetWorkspaceService._sum_schedule_amounts(current_schedules)
        batch_total = sum((Decimal(str(item.amount)) for item in data.installments), _DECIMAL_ZERO)
        document_total = Decimal(str(document.document_amount or 0))

        if existing_total + batch_total > document_total + _DECIMAL_TOLERANCE:
            return None, "A soma das parcelas ultrapassa o valor executado da NF/equivalente."

        entry_type = "receivable" if line.movement_nature == "credit" else "payable"
        counterparty = document.counterparty or contract.counterparty
        created_items: List[Dict[str, Any]] = []
        total_installments = len(data.installments)

        try:
            for index, installment in enumerate(data.installments, start=1):
                label = installment.label or f"Parcela {index}/{total_installments}"
                amount = Decimal(str(installment.amount))
                schedule_payload = {
                    "company_id": company_id,
                    "budget_document_id": document.id,
                    "name": f"{label} - {document.title}",
                    "entry_type": entry_type,
                    "movement_nature": line.movement_nature,
                    "origin_type": "manual",
                    "status": "active",
                    "frequency": "one_time",
                    "interval_value": 1,
                    "start_date": installment.due_date,
                    "first_due_date": installment.due_date,
                    "next_due_date": installment.due_date,
                    "description": f"{label} | {document.title}",
                    "memo": data.notes or document.notes or contract.notes,
                    "document_number_prefix": document.document_number or document.document_code,
                    "template_amount": amount,
                    "counterparty_id": counterparty.id if counterparty else None,
                    "chart_account_id": line.chart_account_id,
                    "cost_center_id": line.cost_center_id,
                    "activity_id": line.activity_id,
                    "process_instance_id": line.process_instance_id,
                    "routine_id": line.routine_id,
                    "notes": data.notes or label,
                    "auto_post": data.auto_post,
                    "metadata_json": {
                        "document_number": document.document_number or document.document_code,
                        "competence_mode": "same_as_due",
                        "counterparty_name": counterparty.name if counterparty else None,
                        "budget_version_id": line.budget_version_id,
                        "budget_line_id": line.id,
                        "budget_contract_id": contract.id,
                        "budget_document_id": document.id,
                        "budget_document_title": document.title,
                        "contract_name": contract.name,
                        "allocations": [
                            {
                                "chart_account_id": line.chart_account_id,
                                "cost_center_id": line.cost_center_id,
                                "allocation_type": "percentage",
                                "percentage": 100,
                                "allocated_amount": float(amount),
                                "domain_type": "financial_budget_document",
                                "domain_source_id": document.id,
                                "domain_label": document.title,
                            }
                        ],
                    },
                }
                result, error = FinancialScheduleService.create_schedule(
                    payload=schedule_payload,
                    allowed_company_ids=allowed_company_ids,
                )
                if error:
                    db.session.rollback()
                    return None, error
                created_items.append(result)

            FinancialBudgetWorkspaceService._refresh_document_status(document)
            db.session.commit()
            refreshed_schedules = FinancialBudgetWorkspaceService._list_schedules_for_document(
                company_id=company_id,
                document_id=document.id,
            )
            return {
                "document": FinancialBudgetWorkspaceService._serialize_document(document),
                "created_schedules": created_items,
                "schedules": [FinancialBudgetWorkspaceService._serialize_schedule(item) for item in refreshed_schedules],
            }, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível gerar os agendamentos financeiros: {exc}"

    @staticmethod
    def delete_document_schedule(
        *,
        company_id: int,
        document_id: int,
        schedule_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        document = FinancialBudgetWorkspaceService._get_document(company_id=company_id, document_id=document_id)
        if not document:
            return None, "NF/equivalente não encontrada no escopo da empresa."

        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.budget_document_id == document.id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Agendamento financeiro não encontrado para a NF/equivalente informada."

        refs = [f"financial_schedule:{schedule.id}"]
        generated_entry = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.external_reference.in_(refs),
            FinancialEntry.deleted_at.is_(None),
        ).first()
        if generated_entry:
            return None, "Este agendamento já gerou lançamento financeiro e não pode ser removido por aqui."

        try:
            schedule.deleted_at = datetime.utcnow()
            FinancialBudgetWorkspaceService._refresh_document_status(document)
            db.session.commit()
            return {
                "message": "Agendamento removido com sucesso.",
                "id": schedule_id,
                "document": FinancialBudgetWorkspaceService._serialize_document(document),
            }, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível remover o agendamento financeiro: {exc}"

    @staticmethod
    def _resolve_version(*, company_id: int, version_id: Optional[int]) -> Optional[FinancialBudgetVersion]:
        if version_id:
            return FinancialBudgetWorkspaceService._get_version(company_id=company_id, version_id=version_id)

        return (
            FinancialBudgetVersion.query.filter(
                FinancialBudgetVersion.company_id == company_id,
                FinancialBudgetVersion.deleted_at.is_(None),
            )
            .order_by(
                db.case((FinancialBudgetVersion.status == "active", 0), else_=1),
                FinancialBudgetVersion.period_start.desc(),
                FinancialBudgetVersion.id.desc(),
            )
            .first()
        )

    @staticmethod
    def _get_version(*, company_id: int, version_id: int) -> Optional[FinancialBudgetVersion]:
        return FinancialBudgetVersion.query.filter(
            FinancialBudgetVersion.id == version_id,
            FinancialBudgetVersion.company_id == company_id,
            FinancialBudgetVersion.deleted_at.is_(None),
        ).first()

    @staticmethod
    def _get_line(*, company_id: int, line_id: int) -> Optional[FinancialBudgetLine]:
        return FinancialBudgetLine.query.filter(
            FinancialBudgetLine.id == line_id,
            FinancialBudgetLine.company_id == company_id,
            FinancialBudgetLine.deleted_at.is_(None),
        ).first()

    @staticmethod
    def _get_contract(*, company_id: int, contract_id: int) -> Optional[FinancialBudgetContract]:
        return FinancialBudgetContract.query.filter(
            FinancialBudgetContract.id == contract_id,
            FinancialBudgetContract.company_id == company_id,
            FinancialBudgetContract.deleted_at.is_(None),
        ).first()

    @staticmethod
    def _get_document(*, company_id: int, document_id: int) -> Optional[FinancialBudgetDocument]:
        return FinancialBudgetDocument.query.filter(
            FinancialBudgetDocument.id == document_id,
            FinancialBudgetDocument.company_id == company_id,
            FinancialBudgetDocument.deleted_at.is_(None),
        ).first()

    @staticmethod
    def _list_lines_for_version(*, company_id: int, version_id: int) -> List[FinancialBudgetLine]:
        return (
            FinancialBudgetLine.query.filter(
                FinancialBudgetLine.company_id == company_id,
                FinancialBudgetLine.budget_version_id == version_id,
                FinancialBudgetLine.deleted_at.is_(None),
            )
            .order_by(FinancialBudgetLine.line_order.asc(), FinancialBudgetLine.id.asc())
            .all()
        )

    @staticmethod
    def _list_contracts_for_line(*, company_id: int, line_id: int) -> List[FinancialBudgetContract]:
        return (
            FinancialBudgetContract.query.filter(
                FinancialBudgetContract.company_id == company_id,
                FinancialBudgetContract.budget_line_id == line_id,
                FinancialBudgetContract.deleted_at.is_(None),
            )
            .order_by(FinancialBudgetContract.created_at.desc(), FinancialBudgetContract.id.desc())
            .all()
        )

    @staticmethod
    def _list_documents_for_contract(*, company_id: int, contract_id: int) -> List[FinancialBudgetDocument]:
        return (
            FinancialBudgetDocument.query.filter(
                FinancialBudgetDocument.company_id == company_id,
                FinancialBudgetDocument.budget_contract_id == contract_id,
                FinancialBudgetDocument.deleted_at.is_(None),
            )
            .order_by(
                db.case((FinancialBudgetDocument.issue_date.is_(None), 1), else_=0),
                FinancialBudgetDocument.issue_date.desc(),
                FinancialBudgetDocument.id.desc(),
            )
            .all()
        )

    @staticmethod
    def _list_schedules_for_document(*, company_id: int, document_id: int) -> List[FinancialSchedule]:
        return (
            FinancialSchedule.query.filter(
                FinancialSchedule.company_id == company_id,
                FinancialSchedule.budget_document_id == document_id,
                FinancialSchedule.deleted_at.is_(None),
            )
            .order_by(FinancialSchedule.first_due_date.asc(), FinancialSchedule.id.asc())
            .all()
        )

    @staticmethod
    def _resolve_selected_line(*, lines: List[FinancialBudgetLine], line_id: Optional[int]) -> Optional[FinancialBudgetLine]:
        if not lines:
            return None
        if line_id is None:
            return lines[0]
        return next((item for item in lines if item.id == line_id), None)

    @staticmethod
    def _resolve_selected_contract(
        *,
        contracts: List[FinancialBudgetContract],
        contract_id: Optional[int],
    ) -> Optional[FinancialBudgetContract]:
        if not contracts:
            return None
        if contract_id is None:
            return contracts[0]
        return next((item for item in contracts if item.id == contract_id), None)

    @staticmethod
    def _resolve_selected_document(
        *,
        documents: List[FinancialBudgetDocument],
        document_id: Optional[int],
    ) -> Optional[FinancialBudgetDocument]:
        if not documents:
            return None
        if document_id is None:
            return documents[0]
        return next((item for item in documents if item.id == document_id), None)

    @staticmethod
    def _serialize_line(line: Optional[FinancialBudgetLine]) -> Optional[Dict[str, Any]]:
        if not line:
            return None
        contracts = FinancialBudgetWorkspaceService._list_contracts_for_line(company_id=line.company_id, line_id=line.id)
        contracted_total = sum((Decimal(str(item.contract_amount or 0)) for item in contracts), _DECIMAL_ZERO)
        documents = [
            document
            for contract in contracts
            for document in FinancialBudgetWorkspaceService._list_documents_for_contract(
                company_id=line.company_id,
                contract_id=contract.id,
            )
        ]
        executed_total = sum((Decimal(str(item.document_amount or 0)) for item in documents), _DECIMAL_ZERO)
        schedules = [
            schedule
            for document in documents
            for schedule in FinancialBudgetWorkspaceService._list_schedules_for_document(
                company_id=line.company_id,
                document_id=document.id,
            )
        ]
        scheduled_total = FinancialBudgetWorkspaceService._sum_schedule_amounts(schedules)

        payload = line.to_dict()
        payload.update(
            {
                "chart_account_name": line.chart_account.name if line.chart_account else None,
                "cost_center_name": line.cost_center.name if line.cost_center else None,
                "summary": {
                    "planned_total": float(Decimal(str(line.planned_amount or 0))),
                    "contracted_total": float(contracted_total),
                    "executed_total": float(executed_total),
                    "scheduled_total": float(scheduled_total),
                    "available_to_contract": float(Decimal(str(line.planned_amount or 0)) - contracted_total),
                    "contracts_count": len(contracts),
                    "documents_count": len(documents),
                    "schedules_count": len(schedules),
                },
            }
        )
        return payload

    @staticmethod
    def _serialize_contract(contract: Optional[FinancialBudgetContract]) -> Optional[Dict[str, Any]]:
        if not contract:
            return None
        documents = FinancialBudgetWorkspaceService._list_documents_for_contract(
            company_id=contract.company_id,
            contract_id=contract.id,
        )
        executed_total = sum((Decimal(str(item.document_amount or 0)) for item in documents), _DECIMAL_ZERO)
        schedules = [
            schedule
            for document in documents
            for schedule in FinancialBudgetWorkspaceService._list_schedules_for_document(
                company_id=contract.company_id,
                document_id=document.id,
            )
        ]
        scheduled_total = FinancialBudgetWorkspaceService._sum_schedule_amounts(schedules)
        payload = contract.to_dict()
        payload.update(
            {
                "counterparty_name": contract.counterparty.name if contract.counterparty else None,
                "summary": {
                    "contract_amount": float(Decimal(str(contract.contract_amount or 0))),
                    "executed_total": float(executed_total),
                    "scheduled_total": float(scheduled_total),
                    "available_to_execute": float(Decimal(str(contract.contract_amount or 0)) - executed_total),
                    "documents_count": len(documents),
                    "schedules_count": len(schedules),
                },
            }
        )
        return payload

    @staticmethod
    def _serialize_document(document: Optional[FinancialBudgetDocument]) -> Optional[Dict[str, Any]]:
        if not document:
            return None
        schedules = FinancialBudgetWorkspaceService._list_schedules_for_document(
            company_id=document.company_id,
            document_id=document.id,
        )
        scheduled_total = FinancialBudgetWorkspaceService._sum_schedule_amounts(schedules)
        payload = document.to_dict()
        payload.update(
            {
                "counterparty_name": document.counterparty.name if document.counterparty else None,
                "summary": {
                    "document_amount": float(Decimal(str(document.document_amount or 0))),
                    "scheduled_total": float(scheduled_total),
                    "available_to_schedule": float(Decimal(str(document.document_amount or 0)) - scheduled_total),
                    "schedules_count": len(schedules),
                },
            }
        )
        return payload

    @staticmethod
    def _serialize_schedule(schedule: FinancialSchedule) -> Dict[str, Any]:
        payload = schedule.to_dict()
        payload["signed_template_amount"] = FinancialService.get_signed_amount(
            payload.get("template_amount"),
            schedule.movement_nature,
        )
        payload["display_variant"] = "negative" if payload["signed_template_amount"] < 0 else "positive"
        return payload

    @staticmethod
    def _build_version_summary(lines: List[FinancialBudgetLine]) -> Dict[str, Any]:
        planned_total = _DECIMAL_ZERO
        contracted_total = _DECIMAL_ZERO
        executed_total = _DECIMAL_ZERO
        scheduled_total = _DECIMAL_ZERO
        contracts_count = 0
        documents_count = 0
        schedules_count = 0

        for line in lines:
            planned_total += Decimal(str(line.planned_amount or 0))
            contracts = FinancialBudgetWorkspaceService._list_contracts_for_line(
                company_id=line.company_id,
                line_id=line.id,
            )
            contracts_count += len(contracts)
            for contract in contracts:
                contracted_total += Decimal(str(contract.contract_amount or 0))
                documents = FinancialBudgetWorkspaceService._list_documents_for_contract(
                    company_id=line.company_id,
                    contract_id=contract.id,
                )
                documents_count += len(documents)
                for document in documents:
                    executed_total += Decimal(str(document.document_amount or 0))
                    schedules = FinancialBudgetWorkspaceService._list_schedules_for_document(
                        company_id=line.company_id,
                        document_id=document.id,
                    )
                    schedules_count += len(schedules)
                    scheduled_total += FinancialBudgetWorkspaceService._sum_schedule_amounts(schedules)

        return {
            "planned_total": float(planned_total),
            "contracted_total": float(contracted_total),
            "executed_total": float(executed_total),
            "scheduled_total": float(scheduled_total),
            "available_to_contract": float(planned_total - contracted_total),
            "lines_count": len(lines),
            "contracts_count": contracts_count,
            "documents_count": documents_count,
            "schedules_count": schedules_count,
        }

    @staticmethod
    def _sum_schedule_amounts(schedules: List[FinancialSchedule]) -> Decimal:
        return sum((Decimal(str(item.template_amount or 0)) for item in schedules), _DECIMAL_ZERO)

    @staticmethod
    def _refresh_document_status(document: FinancialBudgetDocument) -> None:
        if document.status == "cancelled":
            return

        schedules = FinancialBudgetWorkspaceService._list_schedules_for_document(
            company_id=document.company_id,
            document_id=document.id,
        )
        scheduled_total = FinancialBudgetWorkspaceService._sum_schedule_amounts(schedules)
        document_total = Decimal(str(document.document_amount or 0))

        if scheduled_total <= _DECIMAL_TOLERANCE:
            document.status = "registered" if document.status != "draft" else "draft"
            return

        if scheduled_total + _DECIMAL_TOLERANCE >= document_total:
            document.status = "fully_scheduled"
            return

        document.status = "partially_scheduled"

    @staticmethod
    def _collect_line_schedule_ids(line: FinancialBudgetLine) -> List[int]:
        ids: List[int] = []
        for contract in line.contracts.filter(FinancialBudgetContract.deleted_at.is_(None)).all():
            ids.extend(FinancialBudgetWorkspaceService._collect_contract_schedule_ids(contract))
        return ids

    @staticmethod
    def _collect_contract_schedule_ids(contract: FinancialBudgetContract) -> List[int]:
        ids: List[int] = []
        for document in contract.documents.filter(FinancialBudgetDocument.deleted_at.is_(None)).all():
            ids.extend(
                [
                    schedule.id
                    for schedule in FinancialBudgetWorkspaceService._list_schedules_for_document(
                        company_id=contract.company_id,
                        document_id=document.id,
                    )
                ]
            )
        return ids

    @staticmethod
    def _has_generated_entries(*, company_id: int, schedule_ids: List[int]) -> bool:
        if not schedule_ids:
            return False
        refs = [f"financial_schedule:{item}" for item in schedule_ids]
        existing = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.external_reference.in_(refs),
            FinancialEntry.deleted_at.is_(None),
        ).first()
        return existing is not None

    @staticmethod
    def _empty_summary() -> Dict[str, Any]:
        return {
            "planned_total": 0.0,
            "contracted_total": 0.0,
            "executed_total": 0.0,
            "scheduled_total": 0.0,
            "available_to_contract": 0.0,
            "lines_count": 0,
            "contracts_count": 0,
            "documents_count": 0,
            "schedules_count": 0,
        }
