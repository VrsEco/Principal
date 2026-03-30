from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import (
    Company,
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
from services.financial_budget_code_service import FinancialBudgetCodeService
from services.financial_budget_schedule_policy import FinancialBudgetSchedulePolicy
from schemas.financial_budget import (
    FinancialBudgetContractCreateInput,
    FinancialBudgetContractUpdateInput,
    FinancialBudgetDocumentCreateInput,
    FinancialBudgetDocumentScheduleBatchInput,
    FinancialBudgetDocumentScheduleUpdateInput,
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
        budget_cycle: Optional[str] = None,
        budget_category: Optional[str] = None,
        budget_group: Optional[str] = None,
        consolidated: bool = False,
        group_by_cycle: bool = False,
        group_by_category: bool = False,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        versions_result, error = FinancialBudgetService.list_versions(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
            budget_cycle=budget_cycle,
            budget_category=budget_category,
            budget_group=budget_group,
            consolidated=consolidated,
            group_by_cycle=group_by_cycle,
            group_by_category=group_by_category,
            include_summary=True,
        )
        if error:
            return None, error

        version_payloads = FinancialBudgetWorkspaceService._extract_version_payloads(versions_result)
        if version_id:
            selected_version_payload = FinancialBudgetWorkspaceService._resolve_selected_version_payload(
                version_payloads=version_payloads,
                version_id=version_id,
            )
        else:
            selected_version_payload = FinancialBudgetWorkspaceService._resolve_selected_version_payload(
                version_payloads=version_payloads,
                version_id=None,
            )

        if version_id and not selected_version_payload:
            return None, "Orçamento não encontrado no escopo da empresa."

        if not selected_version_payload:
            return {
                "versions": version_payloads,
                "budgets": version_payloads,
                "selected_version_id": None,
                "version": None,
                "summary": FinancialBudgetWorkspaceService._empty_summary(),
                "consolidated_summary": FinancialBudgetWorkspaceService._empty_summary(),
                "lines": [],
                "cycle_groups": versions_result.get("cycles") if isinstance(versions_result, dict) else [],
                "filters": versions_result.get("filters") if isinstance(versions_result, dict) else {},
            }, None

        version = FinancialBudgetWorkspaceService._get_version(
            company_id=company_id,
            version_id=int(selected_version_payload["id"]),
        )
        if not version:
            return None, "Versão orçamentária não encontrada no escopo da empresa."

        lines = FinancialBudgetWorkspaceService._list_lines_for_version(
            company_id=company_id,
            version_id=version.id,
        )
        payload_lines = [FinancialBudgetWorkspaceService._serialize_line(line) for line in lines]
        consolidated_summary = (
            FinancialBudgetCodeService.summarize_version_payloads(version_payloads)
            if version_payloads
            else FinancialBudgetWorkspaceService._empty_summary()
        )
        cycle_groups = versions_result.get("cycles") if isinstance(versions_result, dict) else []
        category_groups = versions_result.get("groups") if isinstance(versions_result, dict) else []

        return {
            "versions": version_payloads,
            "budgets": version_payloads,
            "selected_version_id": version.id,
            "version": FinancialBudgetCodeService.enrich_version_payload(version),
            "summary": FinancialBudgetWorkspaceService._build_version_summary(lines),
            "consolidated_summary": consolidated_summary,
            "lines": payload_lines,
            "cycle_groups": cycle_groups,
            "category_groups": category_groups,
            "filters": versions_result.get("filters") if isinstance(versions_result, dict) else {},
        }, None

    @staticmethod
    def get_execution_workspace(
        *,
        company_id: int,
        version_id: Optional[int] = None,
        line_id: Optional[int] = None,
        contract_id: Optional[int] = None,
        document_id: Optional[int] = None,
        schedule_id: Optional[int] = None,
        budget_cycle: Optional[str] = None,
        budget_category: Optional[str] = None,
        budget_group: Optional[str] = None,
        consolidated: bool = False,
        group_by_cycle: bool = False,
        group_by_category: bool = False,
        include_operational_queue: bool = False,
        queue_limit: int = 50,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        versions_result, error = FinancialBudgetService.list_versions(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
            budget_cycle=budget_cycle,
            budget_category=budget_category,
            budget_group=budget_group,
            consolidated=consolidated,
            group_by_cycle=group_by_cycle,
            group_by_category=group_by_category,
            include_summary=True,
        )
        if error:
            return None, error

        version_payloads = FinancialBudgetWorkspaceService._extract_version_payloads(versions_result)
        if version_id:
            selected_version_payload = FinancialBudgetWorkspaceService._resolve_selected_version_payload(
                version_payloads=version_payloads,
                version_id=version_id,
            )
        else:
            selected_version_payload = FinancialBudgetWorkspaceService._resolve_selected_version_payload(
                version_payloads=version_payloads,
                version_id=None,
            )

        if version_id and not selected_version_payload:
            return None, "Orçamento não encontrado no escopo da empresa."

        if not selected_version_payload:
            return {
                "versions": version_payloads,
                "budgets": version_payloads,
                "selected_version_id": None,
                "version": None,
                "summary": FinancialBudgetWorkspaceService._empty_summary(),
                "consolidated_summary": FinancialBudgetWorkspaceService._empty_summary(),
                "lines": [],
                "selected_line_id": None,
                "selected_contract_id": None,
                "selected_document_id": None,
                "selected_schedule_id": None,
                "contracts": [],
                "documents": [],
                "schedules": [],
                "cycle_groups": versions_result.get("cycles") if isinstance(versions_result, dict) else [],
                "category_groups": versions_result.get("groups") if isinstance(versions_result, dict) else [],
                "filters": versions_result.get("filters") if isinstance(versions_result, dict) else {},
            }, None

        version = FinancialBudgetWorkspaceService._get_version(
            company_id=company_id,
            version_id=int(selected_version_payload["id"]),
        )
        if not version:
            return None, "Versão orçamentária não encontrada no escopo da empresa."

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
        selected_schedule = FinancialBudgetWorkspaceService._resolve_selected_schedule(
            schedules=schedules,
            schedule_id=schedule_id,
        )
        if schedule_id and not selected_schedule:
            selected_schedule = schedules[0] if schedules else None
        operational_queue = (
            FinancialBudgetWorkspaceService._list_operational_queue(
                company_id=company_id,
                budget_cycle=budget_cycle,
                budget_category=budget_category,
                budget_group=budget_group,
                limit=queue_limit,
            )
            if include_operational_queue
            else []
        )

        return {
            "versions": version_payloads,
            "budgets": version_payloads,
            "selected_version_id": version.id,
            "version": FinancialBudgetCodeService.enrich_version_payload(version),
            "summary": FinancialBudgetWorkspaceService._build_version_summary(lines),
            "consolidated_summary": FinancialBudgetCodeService.summarize_version_payloads(version_payloads),
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
            "selected_schedule_id": selected_schedule.id if selected_schedule else None,
            "selected_schedule": FinancialBudgetWorkspaceService._serialize_schedule(selected_schedule) if selected_schedule else None,
            "operational_queue": operational_queue,
            "cycle_groups": versions_result.get("cycles") if isinstance(versions_result, dict) else [],
            "category_groups": versions_result.get("groups") if isinstance(versions_result, dict) else [],
            "filters": versions_result.get("filters") if isinstance(versions_result, dict) else {},
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
            "collaborators": list((base_options or {}).get("employees") or []),
            "budget_categories": [
                {"code": "CAPEX", "label": "CAPEX"},
                {"code": "OPEX", "label": "OPEX"},
                {"code": "CAPEX_EXTRA", "label": "CAPEX Extra"},
                {"code": "GENERAL", "label": "Geral"},
            ],
            "budget_cycle_modes": [
                {"code": "annual", "label": "Anual"},
                {"code": "quarterly", "label": "Trimestral"},
                {"code": "monthly", "label": "Mensal"},
            ],
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
            "default_suggestions": FinancialBudgetWorkspaceService._build_default_suggestions(company_id=company_id),
        }, None

    @staticmethod
    def _build_default_suggestions(*, company_id: int) -> Dict[str, Any]:
        default_document = (
            FinancialBudgetDocument.query.filter(
                FinancialBudgetDocument.company_id == company_id,
                FinancialBudgetDocument.deleted_at.is_(None),
                FinancialBudgetDocument.is_default_suggestion.is_(True),
            )
            .order_by(FinancialBudgetDocument.updated_at.desc(), FinancialBudgetDocument.id.desc())
            .first()
        )
        if not default_document:
            return {}

        contract = FinancialBudgetWorkspaceService._get_contract(
            company_id=company_id,
            contract_id=default_document.budget_contract_id,
        )
        line = (
            FinancialBudgetWorkspaceService._get_line(company_id=company_id, line_id=contract.budget_line_id)
            if contract
            else None
        )
        version = (
            FinancialBudgetWorkspaceService._get_version(company_id=company_id, version_id=line.budget_version_id)
            if line
            else None
        )
        return {
            "budget_version_id": version.id if version else None,
            "budget_line_id": line.id if line else None,
            "budget_contract_id": contract.id if contract else None,
            "budget_document_id": default_document.id,
            "budget_document_label": default_document.title,
        }

    @staticmethod
    def _clear_default_document_suggestions(*, company_id: int, exclude_document_id: Optional[int] = None) -> None:
        query = FinancialBudgetDocument.query.filter(
            FinancialBudgetDocument.company_id == company_id,
            FinancialBudgetDocument.deleted_at.is_(None),
            FinancialBudgetDocument.is_default_suggestion.is_(True),
        )
        if exclude_document_id:
            query = query.filter(FinancialBudgetDocument.id != exclude_document_id)
        for item in query.all():
            item.is_default_suggestion = False

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
            employee_id=data.responsible_employee_id,
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

        normalized = FinancialBudgetWorkspaceService._apply_line_code_defaults(
            company_id=data.company_id,
            version=version,
            payload=data.model_dump(),
        )
        item = FinancialBudgetLine(**normalized)
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
            employee_id=merged.get("responsible_employee_id", item.responsible_employee_id),
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

        requested_amount = Decimal(str(merged.get("planned_amount", item.planned_amount or 0)))
        contracted_total = FinancialBudgetWorkspaceService._sum_line_contracts(item)
        if requested_amount + _DECIMAL_TOLERANCE < contracted_total:
            return None, "O valor da verba não pode ser menor que o total já contratado."

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

        has_contracts = item.contracts.filter(FinancialBudgetContract.deleted_at.is_(None)).first()
        if has_contracts:
            return None, "Esta verba possui contratos vinculados e não pode ser excluída."

        schedule_ids = FinancialBudgetWorkspaceService._collect_line_schedule_ids(item)
        if FinancialBudgetWorkspaceService._has_generated_entries(company_id=company_id, schedule_ids=schedule_ids):
            return None, "Existem agendamentos já convertidos em lançamentos. Exclua/cancele os lançamentos vinculados antes de remover a verba."

        now = datetime.utcnow()
        try:
            item.deleted_at = now
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
            employee_id=data.responsible_employee_id,
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

        normalized = FinancialBudgetWorkspaceService._apply_contract_code_defaults(
            company_id=data.company_id,
            line=line,
            payload=data.model_dump(),
        )
        item = FinancialBudgetContract(**normalized)
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
            employee_id=merged.get("responsible_employee_id", item.responsible_employee_id),
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

        requested_amount = Decimal(str(merged.get("contract_amount", item.contract_amount or 0)))
        executed_total = FinancialBudgetWorkspaceService._sum_contract_documents(item)
        if requested_amount + _DECIMAL_TOLERANCE < executed_total:
            return None, "O valor do contrato não pode ser menor que o total já executado em NF/equivalentes."

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

        has_documents = item.documents.filter(FinancialBudgetDocument.deleted_at.is_(None)).first()
        if has_documents:
            return None, "Este contrato possui NF/equivalentes vinculados e não pode ser excluído."

        schedule_ids = FinancialBudgetWorkspaceService._collect_contract_schedule_ids(item)
        if FinancialBudgetWorkspaceService._has_generated_entries(company_id=company_id, schedule_ids=schedule_ids):
            return None, "Existem agendamentos deste contrato já convertidos em lançamentos. Faça o saneamento antes de remover o contrato."

        now = datetime.utcnow()
        try:
            item.deleted_at = now
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
        normalized = FinancialBudgetWorkspaceService._apply_document_code_defaults(
            company_id=data.company_id,
            contract=contract,
            payload=normalized,
        )
        item = FinancialBudgetDocument(**normalized)
        db.session.add(item)
        try:
            if item.is_default_suggestion:
                db.session.flush()
                FinancialBudgetWorkspaceService._clear_default_document_suggestions(
                    company_id=data.company_id,
                    exclude_document_id=item.id,
                )
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
            if item.is_default_suggestion:
                FinancialBudgetWorkspaceService._clear_default_document_suggestions(
                    company_id=company_id,
                    exclude_document_id=item.id,
                )
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
        if schedule_ids:
            return None, "Esta NF/equivalente possui agendamentos vinculados e não pode ser excluída."
        if FinancialBudgetWorkspaceService._has_generated_entries(company_id=company_id, schedule_ids=schedule_ids):
            return None, "Existem agendamentos desta NF já convertidos em lançamentos. Faça o saneamento antes de remover a NF."

        now = datetime.utcnow()
        try:
            if item.is_default_suggestion:
                item.is_default_suggestion = False
            item.deleted_at = now
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

        schedule_context, context_error = FinancialBudgetWorkspaceService._get_document_schedule_context(
            company_id=company_id,
            document_id=document_id,
            allowed_company_ids=allowed_company_ids,
        )
        if context_error:
            return None, context_error
        assert schedule_context is not None

        document = schedule_context["document"]
        capacity, capacity_error = FinancialBudgetSchedulePolicy.get_document_capacity(
            company_id=company_id,
            budget_document_id=document.id,
            allowed_company_ids=allowed_company_ids,
        )
        if capacity_error:
            return None, capacity_error
        assert capacity is not None
        batch_total = sum((Decimal(str(item.amount)) for item in data.installments), _DECIMAL_ZERO)
        if FinancialBudgetSchedulePolicy.would_exceed_document_capacity(
            scheduled_total=capacity["scheduled_total"],
            requested_amount=batch_total,
            document_total=capacity["document_total"],
        ):
            return None, FinancialBudgetSchedulePolicy.CAPACITY_EXCEEDED_MESSAGE

        created_items: List[Dict[str, Any]] = []

        try:
            total_installments = len(data.installments)
            for index, installment in enumerate(data.installments, start=1):
                date_error = FinancialBudgetWorkspaceService._validate_workspace_schedule_due_date(
                    due_date=installment.due_date,
                    context=schedule_context,
                )
                if date_error:
                    return None, f"Parcela {index}/{total_installments}: {date_error}"
                schedule_payload = FinancialBudgetWorkspaceService._build_document_schedule_payload(
                    company_id=company_id,
                    context=schedule_context,
                    label=installment.label or f"Parcela {index}/{total_installments}",
                    amount=Decimal(str(installment.amount)),
                    due_date=installment.due_date,
                    competence_date=installment.competence_date or installment.due_date,
                    notes=data.notes,
                    status="active",
                    auto_post=data.auto_post,
                )
                result, error = FinancialScheduleService.create_schedule(
                    payload=schedule_payload,
                    allowed_company_ids=allowed_company_ids,
                    auto_commit=False,
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
    def update_document_schedule(
        *,
        company_id: int,
        document_id: int,
        schedule_id: int,
        payload: Dict[str, Any],
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        normalized_payload = dict(payload or {})
        data = FinancialBudgetDocumentScheduleUpdateInput.model_validate(normalized_payload)

        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        schedule_context, context_error = FinancialBudgetWorkspaceService._get_document_schedule_context(
            company_id=company_id,
            document_id=document_id,
            allowed_company_ids=allowed_company_ids,
        )
        if context_error:
            return None, context_error
        assert schedule_context is not None

        document = schedule_context["document"]
        schedule = FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.budget_document_id == document.id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()
        if not schedule:
            return None, "Agendamento financeiro não encontrado para a NF/equivalente informada."

        if FinancialBudgetWorkspaceService._has_generated_entries(company_id=company_id, schedule_ids=[schedule.id]):
            return None, "Este agendamento já possui baixa/lançamento financeiro vinculado e não pode ser editado por aqui."

        requested_amount = Decimal(str(data.amount))
        capacity_error = FinancialBudgetSchedulePolicy.validate_document_schedule_amount(
            company_id=company_id,
            budget_document_id=document.id,
            requested_amount=requested_amount,
            allowed_company_ids=allowed_company_ids,
            exclude_schedule_id=schedule.id,
        )
        if capacity_error:
            return None, capacity_error

        date_error = FinancialBudgetWorkspaceService._validate_workspace_schedule_due_date(
            due_date=data.due_date,
            context=schedule_context,
            current_schedule=schedule,
        )
        if date_error:
            return None, date_error

        schedule_payload = FinancialBudgetWorkspaceService._build_document_schedule_payload(
            company_id=company_id,
            context=schedule_context,
            label=data.label,
            amount=requested_amount,
            due_date=data.due_date,
            competence_date=data.competence_date or data.due_date,
            notes=data.notes,
            status=data.status,
            auto_post=data.auto_post,
            current_schedule=schedule,
        )

        result, error = FinancialScheduleService.update_schedule(
            schedule_id=schedule.id,
            company_id=company_id,
            payload=schedule_payload,
            allowed_company_ids=allowed_company_ids,
            auto_commit=False,
        )
        if error:
            return None, error

        try:
            FinancialBudgetWorkspaceService._refresh_document_status(document)
            db.session.commit()
            refreshed_schedules = FinancialBudgetWorkspaceService._list_schedules_for_document(
                company_id=company_id,
                document_id=document.id,
            )
            selected_schedule = next((item for item in refreshed_schedules if item.id == schedule.id), None)
            return {
                "id": schedule.id,
                "document": FinancialBudgetWorkspaceService._serialize_document(document),
                "schedule": FinancialBudgetWorkspaceService._serialize_schedule(selected_schedule) if selected_schedule else result,
                "schedules": [FinancialBudgetWorkspaceService._serialize_schedule(item) for item in refreshed_schedules],
            }, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível atualizar o agendamento financeiro: {exc}"

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
            refreshed_schedules = FinancialBudgetWorkspaceService._list_schedules_for_document(
                company_id=company_id,
                document_id=document.id,
            )
            return {
                "message": "Agendamento removido com sucesso.",
                "id": schedule_id,
                "document": FinancialBudgetWorkspaceService._serialize_document(document),
                "schedules": [FinancialBudgetWorkspaceService._serialize_schedule(item) for item in refreshed_schedules],
            }, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Não foi possível remover o agendamento financeiro: {exc}"

    @staticmethod
    def _resolve_workspace_correction_index_id(
        *,
        context: Dict[str, Any],
        current_schedule: Optional[FinancialSchedule] = None,
    ) -> Optional[int]:
        existing_metadata = dict(getattr(current_schedule, "metadata_json", None) or {})
        correction_index_id = existing_metadata.get("correction_index_id") or context.get("default_correction_index_id")
        if correction_index_id in ("", None):
            return None
        try:
            return int(correction_index_id)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _validate_workspace_schedule_due_date(
        *,
        due_date: Optional[date],
        context: Dict[str, Any],
        current_schedule: Optional[FinancialSchedule] = None,
    ) -> Optional[str]:
        return None

    @staticmethod
    def _get_document_schedule_context(
        *,
        company_id: int,
        document_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
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

        default_suggestions, _ = FinancialScheduleService.list_default_suggestions(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        default_suggestions = default_suggestions or {}
        line_metadata = dict(line.metadata_json or {})
        contract_metadata = dict(contract.metadata_json or {})
        document_metadata = dict(document.metadata_json or {})
        entry_type = "receivable" if line.movement_nature == "credit" else "payable"
        default_correction_index_id = (
            default_suggestions.get("receivable_correction_index_id")
            if entry_type == "receivable"
            else default_suggestions.get("payable_correction_index_id")
        )
        domain_type = (
            line_metadata.get("domain_type")
            or contract_metadata.get("domain_type")
            or document_metadata.get("domain_type")
            or default_suggestions.get("domain_type")
        )
        domain_source_id = (
            line_metadata.get("domain_source_id")
            or contract_metadata.get("domain_source_id")
            or document_metadata.get("domain_source_id")
            or default_suggestions.get("domain_source_id")
        )
        domain_label = (
            line_metadata.get("domain_label")
            or contract_metadata.get("domain_label")
            or document_metadata.get("domain_label")
            or default_suggestions.get("domain_label")
            or document.title
        )
        return {
            "document": document,
            "contract": contract,
            "line": line,
            "entry_type": entry_type,
            "counterparty": document.counterparty or contract.counterparty,
            "default_suggestions": default_suggestions,
            "default_correction_index_id": default_correction_index_id,
            "line_metadata": line_metadata,
            "contract_metadata": contract_metadata,
            "document_metadata": document_metadata,
            "domain_type": domain_type,
            "domain_source_id": domain_source_id,
            "domain_label": domain_label,
        }, None

    @staticmethod
    def _build_document_schedule_payload(
        *,
        company_id: int,
        context: Dict[str, Any],
        label: str,
        amount: Decimal,
        due_date: Any,
        competence_date: Any,
        notes: Optional[str],
        status: str,
        auto_post: Optional[bool],
        current_schedule: Optional[FinancialSchedule] = None,
    ) -> Dict[str, Any]:
        return FinancialScheduleService.build_budget_document_schedule_payload(
            company_id=company_id,
            document=context["document"],
            contract=context["contract"],
            line=context["line"],
            label=label,
            amount=amount,
            due_date=due_date,
            competence_date=competence_date,
            notes=notes,
            status=status,
            auto_post=auto_post,
            current_schedule=current_schedule,
            default_suggestions=context.get("default_suggestions"),
            default_correction_index_id=context.get("default_correction_index_id"),
            domain_type=context.get("domain_type"),
            domain_source_id=context.get("domain_source_id"),
            domain_label=context.get("domain_label"),
        )

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
    def _extract_version_payloads(versions_result: Any) -> List[Dict[str, Any]]:
        if isinstance(versions_result, dict):
            return list(versions_result.get("items") or [])
        return list(versions_result or [])

    @staticmethod
    def _resolve_selected_version_payload(
        *,
        version_payloads: List[Dict[str, Any]],
        version_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        if not version_payloads:
            return None
        if version_id is None:
            return version_payloads[0]
        return next((item for item in version_payloads if int(item.get("id")) == int(version_id)), None)

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
    def _resolve_selected_schedule(
        *,
        schedules: List[FinancialSchedule],
        schedule_id: Optional[int],
    ) -> Optional[FinancialSchedule]:
        if not schedules:
            return None
        if schedule_id is None:
            return schedules[0]
        return next((item for item in schedules if item.id == schedule_id), None)

    @staticmethod
    def _apply_line_code_defaults(
        *,
        company_id: int,
        version: FinancialBudgetVersion,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = dict(payload)
        company_code = FinancialBudgetCodeService.get_company_code(company_id)
        line_seq = normalized.get("line_seq") or FinancialBudgetWorkspaceService._next_line_sequence(
            company_id=company_id,
            version_id=version.id,
        )
        code = f"{company_code}.O.{version.budget_seq or FinancialBudgetWorkspaceService._extract_last_sequence(version.code)}.{line_seq}"
        normalized["line_seq"] = line_seq
        normalized["line_code"] = code
        normalized["full_code"] = code
        normalized["company_code_snapshot"] = company_code
        return normalized

    @staticmethod
    def _apply_contract_code_defaults(
        *,
        company_id: int,
        line: FinancialBudgetLine,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = dict(payload)
        contract_seq = normalized.get("contract_seq") or FinancialBudgetWorkspaceService._next_contract_sequence(
            company_id=company_id,
            line_id=line.id,
        )
        code = f"{line.line_code}.{contract_seq}"
        normalized["contract_seq"] = contract_seq
        normalized["contract_code"] = code
        normalized["full_code"] = code
        normalized["company_code_snapshot"] = FinancialBudgetCodeService.get_company_code(company_id)
        return normalized

    @staticmethod
    def _apply_document_code_defaults(
        *,
        company_id: int,
        contract: FinancialBudgetContract,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = dict(payload)
        document_seq = normalized.get("document_seq") or FinancialBudgetWorkspaceService._next_document_sequence(
            company_id=company_id,
            contract_id=contract.id,
        )
        code = f"{contract.contract_code}.{document_seq}"
        normalized["document_seq"] = document_seq
        normalized["document_code"] = code
        normalized["full_code"] = code
        normalized["company_code_snapshot"] = FinancialBudgetCodeService.get_company_code(company_id)
        return normalized

    @staticmethod
    def _next_line_sequence(*, company_id: int, version_id: int) -> int:
        items = FinancialBudgetLine.query.filter(
            FinancialBudgetLine.company_id == company_id,
            FinancialBudgetLine.budget_version_id == version_id,
            FinancialBudgetLine.deleted_at.is_(None),
        ).all()
        highest = max((int(item.line_seq or 0) for item in items), default=0)
        return highest + 1

    @staticmethod
    def _next_contract_sequence(*, company_id: int, line_id: int) -> int:
        items = FinancialBudgetContract.query.filter(
            FinancialBudgetContract.company_id == company_id,
            FinancialBudgetContract.budget_line_id == line_id,
            FinancialBudgetContract.deleted_at.is_(None),
        ).all()
        highest = max((int(item.contract_seq or 0) for item in items), default=0)
        return highest + 1

    @staticmethod
    def _next_document_sequence(*, company_id: int, contract_id: int) -> int:
        items = FinancialBudgetDocument.query.filter(
            FinancialBudgetDocument.company_id == company_id,
            FinancialBudgetDocument.budget_contract_id == contract_id,
            FinancialBudgetDocument.deleted_at.is_(None),
        ).all()
        highest = max((int(item.document_seq or 0) for item in items), default=0)
        return highest + 1

    @staticmethod
    def _extract_last_sequence(code: Optional[str]) -> int:
        try:
            return int(str(code or "").rsplit(".", 1)[-1])
        except Exception:
            return 0

    @staticmethod
    def _sum_line_contracts(line: FinancialBudgetLine) -> Decimal:
        return sum(
            (Decimal(str(item.contract_amount or 0)) for item in line.contracts.filter(FinancialBudgetContract.deleted_at.is_(None)).all()),
            _DECIMAL_ZERO,
        )

    @staticmethod
    def _sum_contract_documents(contract: FinancialBudgetContract) -> Decimal:
        return sum(
            (Decimal(str(item.document_amount or 0)) for item in contract.documents.filter(FinancialBudgetDocument.deleted_at.is_(None)).all()),
            _DECIMAL_ZERO,
        )

    @staticmethod
    def _serialize_line(line: Optional[FinancialBudgetLine]) -> Optional[Dict[str, Any]]:
        if not line:
            return None
        version_context = FinancialBudgetCodeService.enrich_version_payload(line.version) if getattr(line, "version", None) else None
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
                "budget_version_code": version_context.get("code") if version_context else None,
                "budget_cycle": version_context.get("budget_cycle") if version_context else None,
                "budget_category": version_context.get("budget_category") if version_context else None,
                "budget_group": version_context.get("budget_group") if version_context else None,
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
        version_context = FinancialBudgetCodeService.enrich_version_payload(contract.budget_line.version) if getattr(contract, "budget_line", None) and getattr(contract.budget_line, "version", None) else None
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
                "budget_version_code": version_context.get("code") if version_context else None,
                "budget_cycle": version_context.get("budget_cycle") if version_context else None,
                "budget_category": version_context.get("budget_category") if version_context else None,
                "budget_group": version_context.get("budget_group") if version_context else None,
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
        version_context = FinancialBudgetCodeService.enrich_version_payload(document.budget_contract.budget_line.version) if getattr(document, "budget_contract", None) and getattr(document.budget_contract, "budget_line", None) and getattr(document.budget_contract.budget_line, "version", None) else None
        schedules = FinancialBudgetWorkspaceService._list_schedules_for_document(
            company_id=document.company_id,
            document_id=document.id,
        )
        scheduled_total = FinancialBudgetWorkspaceService._sum_schedule_amounts(schedules)
        payload = document.to_dict()
        payload.update(
            {
                "counterparty_name": document.counterparty.name if document.counterparty else None,
                "is_default_suggestion": bool(getattr(document, "is_default_suggestion", False)),
                "budget_version_code": version_context.get("code") if version_context else None,
                "budget_cycle": version_context.get("budget_cycle") if version_context else None,
                "budget_category": version_context.get("budget_category") if version_context else None,
                "budget_group": version_context.get("budget_group") if version_context else None,
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
        version_context = FinancialBudgetWorkspaceService._resolve_schedule_budget_context(schedule)
        payload["signed_template_amount"] = FinancialService.get_signed_amount(
            payload.get("template_amount"),
            schedule.movement_nature,
        )
        payload["display_variant"] = "negative" if payload["signed_template_amount"] < 0 else "positive"
        payload["budget_version_code"] = version_context.get("code") if version_context else None
        payload["budget_cycle"] = version_context.get("budget_cycle") if version_context else None
        payload["budget_category"] = version_context.get("budget_category") if version_context else None
        payload["budget_group"] = version_context.get("budget_group") if version_context else None
        return payload

    @staticmethod
    def _resolve_schedule_budget_context(schedule: FinancialSchedule) -> Optional[Dict[str, Any]]:
        budget_document = getattr(schedule, "budget_document", None)
        budget_contract = getattr(budget_document, "budget_contract", None) if budget_document else None
        budget_line = getattr(budget_contract, "budget_line", None) if budget_contract else None
        budget_version = getattr(budget_line, "version", None) if budget_line else None
        if not budget_version:
            return None
        return FinancialBudgetCodeService.enrich_version_payload(budget_version)

    @staticmethod
    def _list_operational_queue(
        *,
        company_id: int,
        budget_cycle: Optional[str] = None,
        budget_category: Optional[str] = None,
        budget_group: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit or 50), 200))
        schedules = (
            FinancialSchedule.query.filter(
                FinancialSchedule.company_id == company_id,
                FinancialSchedule.deleted_at.is_(None),
            )
            .order_by(
                FinancialSchedule.next_due_date.asc(),
                FinancialSchedule.id.asc(),
            )
            .limit(limit)
            .all()
        )
        payloads: List[Dict[str, Any]] = []
        for schedule in schedules:
            version_context = FinancialBudgetWorkspaceService._resolve_schedule_budget_context(schedule)
            if budget_cycle is not None:
                if not version_context:
                    continue
                if not FinancialBudgetCodeService.matches_filters(
                    version_context,
                    budget_cycle=budget_cycle,
                    budget_category=budget_category,
                    budget_group=budget_group,
                ):
                    continue
            elif budget_category is not None or budget_group is not None:
                if not version_context:
                    continue
                if not FinancialBudgetCodeService.matches_filters(
                    version_context,
                    budget_cycle=None,
                    budget_category=budget_category,
                    budget_group=budget_group,
                ):
                    continue
            else:
                # sem filtro orçamentário: mostrar tudo, inclusive agendamentos fora do orçamento
                pass
            payloads.append(FinancialBudgetWorkspaceService._serialize_schedule(schedule))
        return payloads

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
