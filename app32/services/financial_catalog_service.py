from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Sequence, Tuple, Type

from sqlalchemy.exc import IntegrityError

from models import Employee, db
from models.financial import (
    FinancialAccountCategory,
    FinancialAssetAccount,
    FinancialBankAccount,
    FinancialChartAccount,
    FinancialCorrectionIndex,
    FinancialCostCenter,
    FinancialCounterparty,
    FinancialDiscountRule,
    FinancialPaymentMethod,
)
from schemas.financial import (
    FinancialAccountCategoryInput,
    FinancialAccountCategoryUpdateInput,
    FinancialAssetAccountInput,
    FinancialAssetAccountUpdateInput,
    FinancialBankAccountInput,
    FinancialBankAccountUpdateInput,
    FinancialChartAccountInput,
    FinancialChartAccountUpdateInput,
    FinancialCorrectionIndexInput,
    FinancialCorrectionIndexUpdateInput,
    FinancialCostCenterInput,
    FinancialCostCenterUpdateInput,
    FinancialCounterpartyInput,
    FinancialCounterpartyUpdateInput,
    FinancialDiscountRuleInput,
    FinancialDiscountRuleUpdateInput,
    FinancialPaymentMethodInput,
    FinancialPaymentMethodUpdateInput,
)


logger = logging.getLogger(__name__)


class FinancialCatalogService:
    CATALOGS: Dict[str, Dict[str, object]] = {
        "bank_accounts": {
            "model": FinancialBankAccount,
            "create_schema": FinancialBankAccountInput,
            "update_schema": FinancialBankAccountUpdateInput,
            "code_field": "code",
            "company_fk_fields": [],
        },
        "chart_accounts": {
            "model": FinancialChartAccount,
            "create_schema": FinancialChartAccountInput,
            "update_schema": FinancialChartAccountUpdateInput,
            "code_field": "code",
            "company_fk_fields": ["parent_id"],
        },
        "cost_centers": {
            "model": FinancialCostCenter,
            "create_schema": FinancialCostCenterInput,
            "update_schema": FinancialCostCenterUpdateInput,
            "code_field": "code",
            "company_fk_fields": ["parent_id"],
        },
        "counterparties": {
            "model": FinancialCounterparty,
            "create_schema": FinancialCounterpartyInput,
            "update_schema": FinancialCounterpartyUpdateInput,
            "code_field": "code",
            "company_fk_fields": ["default_chart_account_id", "default_cost_center_id"],
        },
        "account_categories": {
            "model": FinancialAccountCategory,
            "create_schema": FinancialAccountCategoryInput,
            "update_schema": FinancialAccountCategoryUpdateInput,
            "code_field": "code",
            "company_fk_fields": [],
        },
        "asset_accounts": {
            "model": FinancialAssetAccount,
            "create_schema": FinancialAssetAccountInput,
            "update_schema": FinancialAssetAccountUpdateInput,
            "code_field": "code",
            "company_fk_fields": [],
        },
        "correction_indexes": {
            "model": FinancialCorrectionIndex,
            "create_schema": FinancialCorrectionIndexInput,
            "update_schema": FinancialCorrectionIndexUpdateInput,
            "code_field": "code",
            "company_fk_fields": [],
        },
        "discount_rules": {
            "model": FinancialDiscountRule,
            "create_schema": FinancialDiscountRuleInput,
            "update_schema": FinancialDiscountRuleUpdateInput,
            "code_field": "code",
            "company_fk_fields": [],
        },
        "payment_methods": {
            "model": FinancialPaymentMethod,
            "create_schema": FinancialPaymentMethodInput,
            "update_schema": FinancialPaymentMethodUpdateInput,
            "code_field": "code",
            "company_fk_fields": [],
        },
    }

    @staticmethod
    def _get_catalog_config(catalog_type: str) -> Optional[Dict[str, object]]:
        return FinancialCatalogService.CATALOGS.get(str(catalog_type or "").strip().lower())

    @staticmethod
    def _validate_scope(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Optional[str]:
        from services.financial_service import FinancialService

        return FinancialService._ensure_company_scope(company_id, allowed_company_ids)

    @staticmethod
    def _generate_counterparty_code(company_id: int) -> str:
        from services.contracts_service import ContractService

        return ContractService._next_structured_code(FinancialCounterparty, company_id, "F")

    @staticmethod
    def _generate_bank_account_code(company_id: int) -> str:
        last_number = 0
        codes = (
            FinancialBankAccount.query.with_entities(FinancialBankAccount.code)
            .filter(
                FinancialBankAccount.company_id == company_id,
                FinancialBankAccount.deleted_at.is_(None),
            )
            .all()
        )
        for (code,) in codes:
            text = str(code or "").strip()
            if text.isdigit():
                last_number = max(last_number, int(text))
        return f"{last_number + 1:03d}"

    @staticmethod
    def _generate_simple_catalog_code(model, company_id: int) -> str:
        last_number = 0
        codes = (
            model.query.with_entities(model.code)
            .filter(
                model.company_id == company_id,
                model.deleted_at.is_(None),
            )
            .all()
        )
        for (code,) in codes:
            text = str(code or "").strip()
            if text.isdigit():
                last_number = max(last_number, int(text))
        return f"{last_number + 1:03d}"

    @staticmethod
    def _compose_hierarchical_code(
        *,
        catalog_type: str,
        company_id: int,
        parent_id: Optional[int],
        code_suffix: Optional[str],
    ) -> Optional[str]:
        suffix = str(code_suffix or "").strip()
        if not suffix:
            return None

        parent_model = FinancialChartAccount if catalog_type == "chart_accounts" else FinancialCostCenter
        if not parent_id:
            return suffix

        parent = parent_model.query.filter(
            parent_model.id == parent_id,
            parent_model.company_id == company_id,
            parent_model.deleted_at.is_(None),
        ).first()
        if not parent:
            return None
        return f"{parent.code}.{suffix}"

    @staticmethod
    def _would_create_cycle(
        *,
        model,
        company_id: int,
        item_id: Optional[int],
        parent_id: Optional[int],
    ) -> bool:
        if not item_id or not parent_id:
            return False
        if item_id == parent_id:
            return True

        current_parent_id = parent_id
        while current_parent_id:
            parent = model.query.filter(
                model.id == current_parent_id,
                model.company_id == company_id,
                model.deleted_at.is_(None),
            ).first()
            if not parent:
                return False
            if parent.id == item_id:
                return True
            current_parent_id = getattr(parent, "parent_id", None)
        return False

    @staticmethod
    def _sanitize_metadata_json(value):
        if isinstance(value, dict):
            return {
                key: FinancialCatalogService._sanitize_metadata_json(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [FinancialCatalogService._sanitize_metadata_json(item) for item in value]
        if isinstance(value, Decimal):
            return float(value)
        return value

    @staticmethod
    def _extract_counterparty_roles(data: Dict) -> tuple[Optional[bool], Optional[bool]]:
        metadata = dict(data.get("metadata_json") or {})
        is_customer = data.get("is_customer")
        is_supplier = data.get("is_supplier")
        if is_customer is None and "is_customer" in metadata:
            is_customer = bool(metadata.get("is_customer"))
        if is_supplier is None and "is_supplier" in metadata:
            is_supplier = bool(metadata.get("is_supplier"))
        return is_customer, is_supplier

    @staticmethod
    def _sync_contract_party_projection(counterparty: FinancialCounterparty) -> None:
        from models.contracts import ContractParty
        from services.contracts_service import ContractService

        metadata = dict(counterparty.metadata_json or {})
        is_customer = bool(metadata.get("is_customer"))
        is_supplier = bool(metadata.get("is_supplier"))
        if not is_customer and not is_supplier:
            return

        party = ContractParty.query.filter(
            ContractParty.company_id == counterparty.company_id,
            ContractParty.financial_counterparty_id == counterparty.id,
            ContractParty.deleted_at.is_(None),
        ).first()

        payload = {
            "name": counterparty.name,
            "legal_name": counterparty.legal_name,
            "document_type": ContractService.infer_document_type(counterparty.document_number),
            "document_number": counterparty.document_number,
            "email": counterparty.email,
            "phone": counterparty.phone,
            "is_customer": is_customer,
            "is_supplier": is_supplier,
            "status": "active" if counterparty.is_active else "inactive",
            "notes": counterparty.notes,
            "financial_counterparty_id": counterparty.id,
        }

        if party is None:
            party = ContractParty(
                company_id=counterparty.company_id,
                code=ContractService._next_structured_code(ContractParty, counterparty.company_id, "F"),
            )
            ContractService.update_party(party=party, payload=payload, user_id=None, is_new=True)
            db.session.add(party)
            return

        ContractService.update_party(party=party, payload=payload, user_id=None, is_new=True)

    @staticmethod
    def _clear_default_cost_center_suggestions(*, company_id: int, exclude_item_id: Optional[int] = None) -> None:
        query = FinancialCostCenter.query.filter(
            FinancialCostCenter.company_id == company_id,
            FinancialCostCenter.deleted_at.is_(None),
            FinancialCostCenter.is_default_suggestion.is_(True),
        )
        if exclude_item_id:
            query = query.filter(FinancialCostCenter.id != exclude_item_id)
        for item in query.all():
            item.is_default_suggestion = False

    @staticmethod
    def _clear_default_payment_method_suggestions(*, company_id: int, exclude_item_id: Optional[int] = None) -> None:
        query = FinancialPaymentMethod.query.filter(
            FinancialPaymentMethod.company_id == company_id,
            FinancialPaymentMethod.deleted_at.is_(None),
            FinancialPaymentMethod.is_default_suggestion.is_(True),
        )
        if exclude_item_id:
            query = query.filter(FinancialPaymentMethod.id != exclude_item_id)
        for item in query.all():
            item.is_default_suggestion = False

    @staticmethod
    def _validate_cost_center_default_rule(data: Dict) -> Optional[str]:
        if not bool(data.get("is_default_suggestion")):
            return None
        if data.get("accepts_posting") is False:
            return "Somente centros de custo analíticos podem ser definidos como padrão."
        return None

    @staticmethod
    def _clear_default_correction_index_flags(
        *,
        company_id: int,
        exclude_item_id: Optional[int] = None,
        clear_receivable: bool = False,
        clear_payable: bool = False,
    ) -> None:
        if not clear_receivable and not clear_payable:
            return

        query = FinancialCorrectionIndex.query.filter(
            FinancialCorrectionIndex.company_id == company_id,
            FinancialCorrectionIndex.deleted_at.is_(None),
        )
        if exclude_item_id:
            query = query.filter(FinancialCorrectionIndex.id != exclude_item_id)

        for item in query.all():
            metadata = dict(item.metadata_json or {})
            changed = False
            if clear_receivable and bool(metadata.get("is_default_receivable")):
                metadata["is_default_receivable"] = False
                changed = True
            if clear_payable and bool(metadata.get("is_default_payable")):
                metadata["is_default_payable"] = False
                changed = True
            if changed:
                item.metadata_json = FinancialCatalogService._sanitize_metadata_json(metadata)

    @staticmethod
    def _clear_default_discount_rule_flags(
        *,
        company_id: int,
        exclude_item_id: Optional[int] = None,
        clear_receivable: bool = False,
        clear_payable: bool = False,
    ) -> None:
        if not clear_receivable and not clear_payable:
            return

        query = FinancialDiscountRule.query.filter(
            FinancialDiscountRule.company_id == company_id,
            FinancialDiscountRule.deleted_at.is_(None),
        )
        if exclude_item_id:
            query = query.filter(FinancialDiscountRule.id != exclude_item_id)

        for item in query.all():
            metadata = dict(item.metadata_json or {})
            changed = False
            if clear_receivable and bool(metadata.get("is_default_receivable")):
                metadata["is_default_receivable"] = False
                changed = True
            if clear_payable and bool(metadata.get("is_default_payable")):
                metadata["is_default_payable"] = False
                changed = True
            if changed:
                item.metadata_json = FinancialCatalogService._sanitize_metadata_json(metadata)

    @staticmethod
    def _prepare_catalog_payload(
        *,
        catalog_type: str,
        company_id: int,
        data: Dict,
    ) -> Dict:
        prepared = dict(data or {})
        metadata = dict(prepared.get("metadata_json") or {})

        if catalog_type in {"chart_accounts", "cost_centers"}:
            has_code_suffix = "code_suffix" in prepared
            has_reduced_code = "reduced_code" in prepared
            has_external_code = "external_code" in prepared
            code_suffix = prepared.pop("code_suffix", None)
            reduced_code = prepared.pop("reduced_code", None)
            external_code = prepared.pop("external_code", None)
            generated_code = FinancialCatalogService._compose_hierarchical_code(
                catalog_type=catalog_type,
                company_id=company_id,
                parent_id=prepared.get("parent_id"),
                code_suffix=code_suffix,
            )
            if generated_code:
                prepared["code"] = generated_code
            if has_code_suffix:
                metadata["code_suffix"] = code_suffix
            if has_reduced_code:
                metadata["reduced_code"] = reduced_code
            if has_external_code:
                metadata["external_code"] = external_code

        if catalog_type in {"chart_accounts", "cost_centers"}:
            has_level_type = "account_level_type" in prepared
            account_level_type = prepared.pop("account_level_type", None)
            if account_level_type:
                prepared["accepts_posting"] = account_level_type == "analytic"
                metadata["account_level_type"] = account_level_type
            elif has_level_type:
                metadata["account_level_type"] = None
            elif "accepts_posting" in prepared:
                metadata["account_level_type"] = "analytic" if prepared["accepts_posting"] else "synthetic"

        if catalog_type == "asset_accounts":
            prepared.pop("manual_value", None)
            metadata.pop("manual_value", None)

        if catalog_type == "bank_accounts":
            for field_name in ("overdraft_limit",):
                if field_name in prepared:
                    metadata[field_name] = prepared.pop(field_name)

        if catalog_type == "counterparties":
            for field_name in ("is_customer", "is_supplier"):
                if field_name in prepared:
                    metadata[field_name] = bool(prepared.pop(field_name))

        if catalog_type in {
            "account_categories",
            "asset_accounts",
            "correction_indexes",
            "discount_rules",
            "payment_methods",
        }:
            for field_name in (
                "external_code",
                "installment_count",
                "interval_days",
                "patrimonial_type",
                "account_class",
                "category_id",
                "chart_account_ids",
                "config_mode",
                "due_scope",
                "due_in_days",
                "bank_account_ids",
                "manual_value",
                "chart_account_id",
                "is_default_receivable",
                "is_default_payable",
                "interest_rate",
                "interest_period",
                "penalty_rate",
                "penalty_period",
                "penalty_limit_rate",
                "value",
                "discount_type",
                "operation_type",
                "settlement_days",
            ):
                if field_name in prepared:
                    metadata[field_name] = prepared.pop(field_name)

        if metadata:
            prepared["metadata_json"] = FinancialCatalogService._sanitize_metadata_json(metadata)

        return prepared

    @staticmethod
    def _normalize_legacy_payload(*, catalog_type: str, payload: Dict) -> Dict:
        normalized = dict(payload or {})

        if catalog_type == "chart_accounts":
            normalized.pop("account_kind", None)

        return normalized

    @staticmethod
    def _validate_related_scope(
        *,
        catalog_type: str,
        company_id: int,
        data: Dict,
    ) -> Optional[str]:
        if catalog_type == "chart_accounts" and data.get("parent_id"):
            parent = FinancialChartAccount.query.filter(
                FinancialChartAccount.id == data["parent_id"],
                FinancialChartAccount.company_id == company_id,
                FinancialChartAccount.deleted_at.is_(None),
            ).first()
            if not parent:
                return "Conta pai fora do escopo da empresa."
            if parent.accepts_posting:
                return "Conta analítica não pode ser usada como conta pai."
            if FinancialCatalogService._would_create_cycle(
                model=FinancialChartAccount,
                company_id=company_id,
                item_id=data.get("id"),
                parent_id=data["parent_id"],
            ):
                return "A conta pai selecionada cria um ciclo inválido na hierarquia."

        if catalog_type == "cost_centers" and data.get("parent_id"):
            parent = FinancialCostCenter.query.filter(
                FinancialCostCenter.id == data["parent_id"],
                FinancialCostCenter.company_id == company_id,
                FinancialCostCenter.deleted_at.is_(None),
            ).first()
            if not parent:
                return "Centro pai fora do escopo da empresa."
            if parent.accepts_posting:
                return "Centro analítico não pode ser usado como centro pai."
            if FinancialCatalogService._would_create_cycle(
                model=FinancialCostCenter,
                company_id=company_id,
                item_id=data.get("id"),
                parent_id=data["parent_id"],
            ):
                return "O centro pai selecionado cria um ciclo inválido na hierarquia."

        if catalog_type == "counterparties" and data.get("default_chart_account_id"):
            chart = FinancialChartAccount.query.filter(
                FinancialChartAccount.id == data["default_chart_account_id"],
                FinancialChartAccount.company_id == company_id,
                FinancialChartAccount.deleted_at.is_(None),
            ).first()
            if not chart:
                return "Conta padrão fora do escopo da empresa."

        if catalog_type == "counterparties" and data.get("default_cost_center_id"):
            center = FinancialCostCenter.query.filter(
                FinancialCostCenter.id == data["default_cost_center_id"],
                FinancialCostCenter.company_id == company_id,
                FinancialCostCenter.deleted_at.is_(None),
            ).first()
            if not center:
                return "Centro padrão fora do escopo da empresa."

        if catalog_type == "counterparties":
            is_customer, is_supplier = FinancialCatalogService._extract_counterparty_roles(data)
            if is_customer is False and is_supplier is False:
                return "Selecione ao menos uma classificação para o favorecido: Cliente, Fornecedor ou ambos."

        if catalog_type == "discount_rules" and data.get("chart_account_id"):
            chart = FinancialChartAccount.query.filter(
                FinancialChartAccount.id == data["chart_account_id"],
                FinancialChartAccount.company_id == company_id,
                FinancialChartAccount.deleted_at.is_(None),
            ).first()
            if not chart:
                return "Plano de contas do desconto fora do escopo da empresa."
            if not chart.accepts_posting:
                return "O desconto deve apontar para uma conta analítica do plano de contas."

        if catalog_type == "correction_indexes" and data.get("chart_account_id"):
            chart = FinancialChartAccount.query.filter(
                FinancialChartAccount.id == data["chart_account_id"],
                FinancialChartAccount.company_id == company_id,
                FinancialChartAccount.deleted_at.is_(None),
            ).first()
            if not chart:
                return "Plano de contas da correção financeira fora do escopo da empresa."
            if not chart.accepts_posting:
                return "A correção financeira deve apontar para uma conta analítica do plano de contas."

        if catalog_type == "asset_accounts":
            category_id = data.get("category_id")
            if category_id:
                category = FinancialAccountCategory.query.filter(
                    FinancialAccountCategory.id == category_id,
                    FinancialAccountCategory.company_id == company_id,
                    FinancialAccountCategory.deleted_at.is_(None),
                ).first()
                if not category:
                    return "Categoria da conta patrimonial fora do escopo da empresa."

            for chart_account_id in data.get("chart_account_ids") or []:
                chart = FinancialChartAccount.query.filter(
                    FinancialChartAccount.id == chart_account_id,
                    FinancialChartAccount.company_id == company_id,
                    FinancialChartAccount.deleted_at.is_(None),
                ).first()
                if not chart:
                    return "Um dos planos de contas vinculados está fora do escopo da empresa."
                if not chart.accepts_posting:
                    return "As contas patrimoniais devem apontar apenas para contas analíticas."

            for bank_account_id in data.get("bank_account_ids") or []:
                bank = FinancialBankAccount.query.filter(
                    FinancialBankAccount.id == bank_account_id,
                    FinancialBankAccount.company_id == company_id,
                    FinancialBankAccount.deleted_at.is_(None),
                ).first()
                if not bank:
                    return "Uma das contas bancárias vinculadas está fora do escopo da empresa."

        return None

    @staticmethod
    def validate_reference_ids(
        *,
        company_id: int,
        bank_account_id: Optional[int] = None,
        chart_account_id: Optional[int] = None,
        cost_center_id: Optional[int] = None,
        counterparty_id: Optional[int] = None,
        employee_id: Optional[int] = None,
    ) -> Optional[str]:
        if bank_account_id:
            bank_account = FinancialBankAccount.query.filter(
                FinancialBankAccount.id == bank_account_id,
                FinancialBankAccount.company_id == company_id,
                FinancialBankAccount.deleted_at.is_(None),
            ).first()
            if not bank_account:
                return "Conta bancária não encontrada no escopo da empresa."

        if chart_account_id:
            chart = FinancialChartAccount.query.filter(
                FinancialChartAccount.id == chart_account_id,
                FinancialChartAccount.company_id == company_id,
                FinancialChartAccount.deleted_at.is_(None),
            ).first()
            if not chart:
                return "Plano de contas não encontrado no escopo da empresa."
            if not bool(chart.accepts_posting):
                return "Selecione uma conta analítica do plano de contas."

        if cost_center_id:
            center = FinancialCostCenter.query.filter(
                FinancialCostCenter.id == cost_center_id,
                FinancialCostCenter.company_id == company_id,
                FinancialCostCenter.deleted_at.is_(None),
            ).first()
            if not center:
                return "Centro de custo não encontrado no escopo da empresa."
            if not bool(center.accepts_posting):
                return "Selecione um centro de resultado analítico."

        if counterparty_id:
            counterparty = FinancialCounterparty.query.filter(
                FinancialCounterparty.id == counterparty_id,
                FinancialCounterparty.company_id == company_id,
                FinancialCounterparty.deleted_at.is_(None),
            ).first()
            if not counterparty:
                return "Favorecido não encontrado no escopo da empresa."

        if employee_id:
            employee = Employee.query.filter(
                Employee.id == employee_id,
                Employee.company_id == company_id,
            ).first()
            if not employee:
                return "Colaborador responsável não encontrado no escopo da empresa."

        return None

    @staticmethod
    def enrich_reference_payload(
        *,
        company_id: int,
        payload: Dict,
        counterparty_text: Optional[str] = None,
        description_text: Optional[str] = None,
        bank_reference: Optional[str] = None,
    ) -> Dict:
        normalized = dict(payload or {})

        if not normalized.get("counterparty_id"):
            hint = str(
                normalized.get("counterparty_hint")
                or counterparty_text
                or ""
            ).strip()
            if hint:
                lower_hint = hint.lower()
                counterparties = FinancialCounterparty.query.filter(
                    FinancialCounterparty.company_id == company_id,
                    FinancialCounterparty.is_active.is_(True),
                    FinancialCounterparty.deleted_at.is_(None),
                ).all()
                match = next(
                    (
                        item for item in counterparties
                        if lower_hint == str(item.name or "").strip().lower()
                        or lower_hint == str(item.legal_name or "").strip().lower()
                        or lower_hint == str(item.document_number or "").strip().lower()
                    ),
                    None,
                )
                if not match:
                    match = next(
                        (
                            item for item in counterparties
                            if lower_hint in str(item.name or "").strip().lower()
                            or lower_hint in str(item.legal_name or "").strip().lower()
                        ),
                        None,
                    )
                if match:
                    normalized["counterparty_id"] = match.id
                    normalized["counterparty_hint"] = match.name
                    if not normalized.get("chart_account_id") and match.default_chart_account_id:
                        normalized["chart_account_id"] = match.default_chart_account_id
                    if not normalized.get("cost_center_id") and match.default_cost_center_id:
                        normalized["cost_center_id"] = match.default_cost_center_id

        if not normalized.get("bank_account_id"):
            reference_text = " ".join(
                filter(
                    None,
                    [
                        str(bank_reference or "").strip(),
                        str(description_text or "").strip(),
                    ],
                )
            ).lower()
            if reference_text:
                accounts = FinancialBankAccount.query.filter(
                    FinancialBankAccount.company_id == company_id,
                    FinancialBankAccount.is_active.is_(True),
                    FinancialBankAccount.deleted_at.is_(None),
                ).all()
                match = next(
                    (
                        item for item in accounts
                        if str(item.code or "").strip().lower() in reference_text
                        or str(item.name or "").strip().lower() in reference_text
                        or str(item.bank_name or "").strip().lower() in reference_text
                        or str(item.account_number or "").strip().lower() in reference_text
                    ),
                    None,
                )
                if match:
                    normalized["bank_account_id"] = match.id

        return normalized

    @staticmethod
    def list_items(
        *,
        catalog_type: str,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[list[Dict]], Optional[str]]:
        scope_error = FinancialCatalogService._validate_scope(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if scope_error:
            return None, scope_error

        config = FinancialCatalogService._get_catalog_config(catalog_type)
        if not config:
            return None, "Tipo de cadastro financeiro inválido."

        model = config["model"]
        items = model.query.filter(
            model.company_id == company_id,
            model.deleted_at.is_(None),
        ).order_by(model.is_active.desc(), model.code.asc(), model.id.asc()).all()
        return [item.to_dict() for item in items], None

    @staticmethod
    def create_item(
        *,
        catalog_type: str,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        config = FinancialCatalogService._get_catalog_config(catalog_type)
        if not config:
            return None, "Tipo de cadastro financeiro inválido."

        schema_cls: Type = config["create_schema"]
        payload = FinancialCatalogService._normalize_legacy_payload(
            catalog_type=catalog_type,
            payload=payload,
        )
        try:
            data = schema_cls(**payload).model_dump()
        except Exception as exc:
            return None, f"Payload inválido para cadastro financeiro: {str(exc)}"

        data = FinancialCatalogService._prepare_catalog_payload(
            catalog_type=catalog_type,
            company_id=data["company_id"],
            data=data,
        )

        if catalog_type == "counterparties" and not data.get("code"):
            data["code"] = FinancialCatalogService._generate_counterparty_code(data["company_id"])
        if catalog_type == "bank_accounts" and not data.get("code"):
            data["code"] = FinancialCatalogService._generate_bank_account_code(data["company_id"])
        if catalog_type in {
            "correction_indexes",
            "discount_rules",
            "payment_methods",
        } and not data.get("code"):
            data["code"] = FinancialCatalogService._generate_simple_catalog_code(
                config["model"],
                data["company_id"],
            )
        if catalog_type in {"chart_accounts", "cost_centers"} and not data.get("code"):
            return None, "Selecione a conta pai e informe o complemento do código."

        scope_error = FinancialCatalogService._validate_scope(
            company_id=data["company_id"],
            allowed_company_ids=allowed_company_ids,
        )
        if scope_error:
            return None, scope_error

        related_error = FinancialCatalogService._validate_related_scope(
            catalog_type=catalog_type,
            company_id=data["company_id"],
            data=data,
        )
        if related_error:
            return None, related_error

        if catalog_type == "cost_centers":
            default_rule_error = FinancialCatalogService._validate_cost_center_default_rule(data)
            if default_rule_error:
                return None, default_rule_error

        model = config["model"]
        existing = model.query.filter(
            model.company_id == data["company_id"],
            model.code == data["code"],
            model.deleted_at.is_(None),
        ).first()
        if existing:
            return None, "Já existe cadastro financeiro com este código na empresa."

        try:
            item = model(**data)
            db.session.add(item)
            if catalog_type == "counterparties":
                db.session.flush()
                FinancialCatalogService._sync_contract_party_projection(item)
            if catalog_type == "cost_centers" and bool(data.get("is_default_suggestion")):
                db.session.flush()
                FinancialCatalogService._clear_default_cost_center_suggestions(
                    company_id=data["company_id"],
                    exclude_item_id=item.id,
                )
            if catalog_type == "payment_methods" and bool(data.get("is_default_suggestion")):
                db.session.flush()
                FinancialCatalogService._clear_default_payment_method_suggestions(
                    company_id=data["company_id"],
                    exclude_item_id=item.id,
                )
            if catalog_type == "correction_indexes":
                db.session.flush()
                metadata = dict(item.metadata_json or {})
                FinancialCatalogService._clear_default_correction_index_flags(
                    company_id=data["company_id"],
                    exclude_item_id=item.id,
                    clear_receivable=bool(metadata.get("is_default_receivable")),
                    clear_payable=bool(metadata.get("is_default_payable")),
                )
            if catalog_type == "discount_rules":
                db.session.flush()
                metadata = dict(item.metadata_json or {})
                FinancialCatalogService._clear_default_discount_rule_flags(
                    company_id=data["company_id"],
                    exclude_item_id=item.id,
                    clear_receivable=bool(metadata.get("is_default_receivable")),
                    clear_payable=bool(metadata.get("is_default_payable")),
                )
            db.session.commit()
            return item.to_dict(), None
        except IntegrityError:
            db.session.rollback()
            return None, "Já existe cadastro financeiro com este código na empresa."
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar cadastro financeiro %s", catalog_type)
            return None, f"Erro ao criar cadastro financeiro: {str(exc)}"

    @staticmethod
    def update_item(
        *,
        catalog_type: str,
        item_id: int,
        company_id: int,
        payload: Dict,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialCatalogService._validate_scope(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if scope_error:
            return None, scope_error

        config = FinancialCatalogService._get_catalog_config(catalog_type)
        if not config:
            return None, "Tipo de cadastro financeiro inválido."

        schema_cls: Type = config["update_schema"]
        payload = FinancialCatalogService._normalize_legacy_payload(
            catalog_type=catalog_type,
            payload=payload,
        )
        try:
            data = schema_cls(**payload).model_dump(exclude_unset=True)
        except Exception as exc:
            return None, f"Payload inválido para atualização do cadastro: {str(exc)}"

        data["id"] = item_id
        data = FinancialCatalogService._prepare_catalog_payload(
            catalog_type=catalog_type,
            company_id=company_id,
            data=data,
        )

        if catalog_type in {"counterparties", "bank_accounts"}:
            data.pop("code", None)

        related_error = FinancialCatalogService._validate_related_scope(
            catalog_type=catalog_type,
            company_id=company_id,
            data=data,
        )
        if related_error:
            return None, related_error

        model = config["model"]
        item = model.query.filter(
            model.id == item_id,
            model.company_id == company_id,
            model.deleted_at.is_(None),
        ).first()
        if not item:
            return None, "Cadastro financeiro não encontrado no escopo da empresa."

        if "code" in data:
            duplicate = model.query.filter(
                model.company_id == company_id,
                model.code == data["code"],
                model.id != item_id,
                model.deleted_at.is_(None),
            ).first()
            if duplicate:
                return None, "Já existe outro cadastro financeiro com este código na empresa."

        if catalog_type == "cost_centers":
            validation_data = {
                "is_default_suggestion": data.get("is_default_suggestion", getattr(item, "is_default_suggestion", False)),
                "accepts_posting": data.get("accepts_posting", getattr(item, "accepts_posting", True)),
            }
            default_rule_error = FinancialCatalogService._validate_cost_center_default_rule(validation_data)
            if default_rule_error:
                return None, default_rule_error

        try:
            for key, value in data.items():
                setattr(item, key, value)
            if catalog_type == "counterparties":
                FinancialCatalogService._sync_contract_party_projection(item)
            if catalog_type == "cost_centers" and bool(getattr(item, "is_default_suggestion", False)):
                FinancialCatalogService._clear_default_cost_center_suggestions(
                    company_id=company_id,
                    exclude_item_id=item.id,
                )
            if catalog_type == "payment_methods" and bool(getattr(item, "is_default_suggestion", False)):
                FinancialCatalogService._clear_default_payment_method_suggestions(
                    company_id=company_id,
                    exclude_item_id=item.id,
                )
            if catalog_type == "correction_indexes":
                metadata = dict(item.metadata_json or {})
                FinancialCatalogService._clear_default_correction_index_flags(
                    company_id=company_id,
                    exclude_item_id=item.id,
                    clear_receivable=bool(metadata.get("is_default_receivable")),
                    clear_payable=bool(metadata.get("is_default_payable")),
                )
            if catalog_type == "discount_rules":
                metadata = dict(item.metadata_json or {})
                FinancialCatalogService._clear_default_discount_rule_flags(
                    company_id=company_id,
                    exclude_item_id=item.id,
                    clear_receivable=bool(metadata.get("is_default_receivable")),
                    clear_payable=bool(metadata.get("is_default_payable")),
                )
            db.session.commit()
            return item.to_dict(), None
        except IntegrityError:
            db.session.rollback()
            return None, "Já existe outro cadastro financeiro com este código na empresa."
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao atualizar cadastro financeiro %s/%s", catalog_type, item_id)
            return None, f"Erro ao atualizar cadastro financeiro: {str(exc)}"

    @staticmethod
    def toggle_item(
        *,
        catalog_type: str,
        item_id: int,
        company_id: int,
        is_active: bool,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialCatalogService._validate_scope(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if scope_error:
            return None, scope_error

        config = FinancialCatalogService._get_catalog_config(catalog_type)
        if not config:
            return None, "Tipo de cadastro financeiro inválido."

        model = config["model"]
        item = model.query.filter(
            model.id == item_id,
            model.company_id == company_id,
            model.deleted_at.is_(None),
        ).first()
        if not item:
            return None, "Cadastro financeiro não encontrado no escopo da empresa."

        try:
            item.is_active = bool(is_active)
            if catalog_type == "counterparties":
                FinancialCatalogService._sync_contract_party_projection(item)
            if not item.is_active and catalog_type == "cost_centers" and getattr(item, "is_default_suggestion", False):
                item.is_default_suggestion = False
            if not item.is_active and catalog_type == "payment_methods" and getattr(item, "is_default_suggestion", False):
                item.is_default_suggestion = False
            if not item.is_active and catalog_type == "correction_indexes":
                metadata = dict(item.metadata_json or {})
                metadata["is_default_receivable"] = False
                metadata["is_default_payable"] = False
                item.metadata_json = FinancialCatalogService._sanitize_metadata_json(metadata)
            if not item.is_active and catalog_type == "discount_rules":
                metadata = dict(item.metadata_json or {})
                metadata["is_default_receivable"] = False
                metadata["is_default_payable"] = False
                item.metadata_json = FinancialCatalogService._sanitize_metadata_json(metadata)
            db.session.commit()
            return item.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao alterar status do cadastro financeiro %s/%s", catalog_type, item_id)
            return None, f"Erro ao alterar status do cadastro financeiro: {str(exc)}"

    @staticmethod
    def delete_item(
        *,
        catalog_type: str,
        item_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialCatalogService._validate_scope(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if scope_error:
            return None, scope_error

        config = FinancialCatalogService._get_catalog_config(catalog_type)
        if not config:
            return None, "Tipo de cadastro financeiro inválido."

        model = config["model"]
        item = model.query.filter(
            model.id == item_id,
            model.company_id == company_id,
            model.deleted_at.is_(None),
        ).first()
        if not item:
            return None, "Cadastro financeiro não encontrado no escopo da empresa."

        if catalog_type == "chart_accounts":
            has_children = FinancialChartAccount.query.filter(
                FinancialChartAccount.parent_id == item_id,
                FinancialChartAccount.company_id == company_id,
                FinancialChartAccount.deleted_at.is_(None),
            ).first()
            if has_children:
                return None, "Não é possível excluir uma conta que possui contas filhas."

        if catalog_type == "cost_centers":
            has_children = FinancialCostCenter.query.filter(
                FinancialCostCenter.parent_id == item_id,
                FinancialCostCenter.company_id == company_id,
                FinancialCostCenter.deleted_at.is_(None),
            ).first()
            if has_children:
                return None, "Não é possível excluir um centro que possui centros filhos."

        try:
            if catalog_type == "cost_centers" and getattr(item, "is_default_suggestion", False):
                item.is_default_suggestion = False
            if catalog_type == "payment_methods" and getattr(item, "is_default_suggestion", False):
                item.is_default_suggestion = False
            item.deleted_at = datetime.utcnow()
            db.session.commit()
            return {"id": item_id, "deleted": True}, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao excluir cadastro financeiro %s/%s", catalog_type, item_id)
            return None, f"Erro ao excluir cadastro financeiro: {str(exc)}"
