from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from models import db
from models.contracts import Contract, ContractFinancialTerm, ContractNativeBilling, ContractNativeBillingItem
from models.financial import (
    FinancialCounterparty,
    FinancialSatelliteExecution,
    FinancialSatellitePolicy,
    FinancialSchedule,
    FinancialScheduleLink,
    FinancialSettlement,
)
from services.financial_schedule_service import FinancialScheduleService
from services.financial_title_balance_service import FinancialTitleBalanceService


class ContractFinancialService:
    SATELLITE_NATURE_LABELS = {
        "iss_withheld": "ISS Retido",
        "inss_withheld": "INSS Retido",
        "irrf_withheld": "IRRF Retido",
        "pis_withheld": "PIS Retido",
        "cofins_withheld": "COFINS Retido",
        "csll_withheld": "CSLL Retida",
        "other_withheld": "Outras Retenções",
        "contractual_retention": "Retenção Contratual",
        "financial_retention": "Retenção Financeira",
    }
    SETTLEMENT_TOLERANCE = Decimal("0.01")
    RETENTION_KIND_TO_SATELLITE_NATURE = {
        "iss": "iss_withheld",
        "irrf": "irrf_withheld",
        "inss": "inss_withheld",
        "csrf": "csrf_withheld",
        "other": "other_withheld",
    }
    TRIGGER_TO_POLICY_EVENT = {
        "baixa": "on_partial_settlement",
        "emissao": "on_issue_date",
        "vencimento": "on_due_date",
    }

    @staticmethod
    def _normalize_text(value: object) -> str:
        return str(value or "").strip()

    @staticmethod
    def _normalize_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "on", "yes", "sim"}

    @staticmethod
    def _normalize_int(value: object) -> Optional[int]:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return int(text)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_decimal(value: object, *, default: str = "0") -> Decimal:
        raw = str(value if value not in (None, "") else default).strip()
        if "," in raw:
            raw = raw.replace(".", "").replace(",", ".")
        try:
            return Decimal(raw)
        except (InvalidOperation, TypeError, ValueError):
            return Decimal(default)

    @staticmethod
    def _money(value: object) -> Decimal:
        return ContractFinancialService._normalize_decimal(value).quantize(Decimal("0.01"))

    @staticmethod
    def _current_timestamp() -> str:
        return datetime.utcnow().isoformat()

    @staticmethod
    def _sanitize_json(value):
        return FinancialScheduleService._sanitize_json(value)

    @staticmethod
    def get_satellite_policy_template_options() -> list[dict]:
        return [
            {
                "key": "settle_iss_withheld_on_settlement",
                "label": "ISS retido por baixa",
                "satellite_nature": "iss_withheld",
                "principal_effect_mode": "partial_settlement_by_settlement",
                "satellite_effect_mode": "settle_by_settlement",
                "trigger_event": "on_partial_settlement",
                "settlement_scope": "full",
                "description": "Baixa o principal bruto via compensação e liquida o satélite do ISS na baixa do líquido.",
            },
            {
                "key": "manual_contractual_retention_release",
                "label": "Retenção contratual manual",
                "satellite_nature": "contractual_retention",
                "principal_effect_mode": "none",
                "satellite_effect_mode": "open_until_manual",
                "trigger_event": "on_manual_release",
                "settlement_scope": "full",
                "description": "Mantém a retenção em aberto até liberação manual.",
            },
            {
                "key": "settle_satellite_on_full_settlement",
                "label": "Satélite na quitação total",
                "satellite_nature": "financial_retention",
                "principal_effect_mode": "none",
                "satellite_effect_mode": "settle_by_settlement",
                "trigger_event": "on_full_settlement",
                "settlement_scope": "full",
                "description": "Liquida o satélite quando o título principal for totalmente baixado.",
            },
        ]

    @staticmethod
    def _template_defaults(template_key: str) -> dict:
        template_map = {
            item["key"]: item for item in ContractFinancialService.get_satellite_policy_template_options()
        }
        return dict(template_map.get(template_key) or {})

    @staticmethod
    def _build_policy_code(contract: Contract) -> str:
        return f"{contract.code or 'CTR'}-SAT-{datetime.utcnow().strftime('%H%M%S%f')}"

    @staticmethod
    def _retention_label(retention_type: str) -> str:
        return ContractFinancialService.SATELLITE_NATURE_LABELS.get(retention_type, retention_type.replace("_", " ").title())

    @staticmethod
    def _retention_detail_satellite_nature(retention_detail: dict) -> str:
        kind = ContractFinancialService._normalize_text((retention_detail or {}).get("kind")).lower()
        return ContractFinancialService.RETENTION_KIND_TO_SATELLITE_NATURE.get(kind, f"{kind}_withheld" if kind else "financial_retention")

    @staticmethod
    def _is_contract_managed_schedule(schedule: Optional[FinancialSchedule]) -> bool:
        metadata = dict(getattr(schedule, "metadata_json", None) or {})
        return bool(metadata.get("managed_by_contract_billing"))

    @staticmethod
    def list_contract_satellite_policies(contract: Contract):
        return (
            FinancialSatellitePolicy.query.filter(
                FinancialSatellitePolicy.company_id == contract.company_id,
                FinancialSatellitePolicy.contract_id == contract.id,
                FinancialSatellitePolicy.deleted_at.is_(None),
            )
            .order_by(FinancialSatellitePolicy.name.asc(), FinancialSatellitePolicy.id.asc())
            .all()
        )

    @staticmethod
    def upsert_contract_satellite_policy(
        *,
        contract: Contract,
        payload: dict,
        user_id: Optional[int] = None,
        policy_id: Optional[int] = None,
        auto_commit: bool = True,
    ):
        template_key = ContractFinancialService._normalize_text(payload.get("satellite_policy_template_key"))
        template = ContractFinancialService._template_defaults(template_key)

        if policy_id:
            policy = FinancialSatellitePolicy.query.filter(
                FinancialSatellitePolicy.id == policy_id,
                FinancialSatellitePolicy.company_id == contract.company_id,
                FinancialSatellitePolicy.contract_id == contract.id,
                FinancialSatellitePolicy.deleted_at.is_(None),
            ).first()
            if not policy:
                raise ValueError("Regra financeira do satélite não encontrada para o contrato.")
        else:
            policy = FinancialSatellitePolicy(
                company_id=contract.company_id,
                contract_id=contract.id,
                policy_code=ContractFinancialService._build_policy_code(contract),
            )
            db.session.add(policy)

        satellite_nature = (
            ContractFinancialService._normalize_text(payload.get("satellite_nature"))
            or template.get("satellite_nature")
        )
        if not satellite_nature:
            raise ValueError("Informe a natureza do título satélite.")

        policy.name = (
            ContractFinancialService._normalize_text(payload.get("policy_name"))
            or template.get("label")
            or ContractFinancialService._retention_label(satellite_nature)
        )
        policy.satellite_nature = satellite_nature
        policy.principal_effect_mode = (
            ContractFinancialService._normalize_text(payload.get("principal_effect_mode"))
            or template.get("principal_effect_mode")
            or "none"
        )
        policy.satellite_effect_mode = (
            ContractFinancialService._normalize_text(payload.get("satellite_effect_mode"))
            or template.get("satellite_effect_mode")
            or "open_until_manual"
        )
        policy.trigger_event = (
            ContractFinancialService._normalize_text(payload.get("trigger_event"))
            or template.get("trigger_event")
            or "on_manual_release"
        )
        policy.settlement_scope = (
            ContractFinancialService._normalize_text(payload.get("settlement_scope"))
            or template.get("settlement_scope")
            or "full"
        )
        policy.auto_apply = (
            ContractFinancialService._normalize_bool(payload.get("auto_apply"))
            if payload.get("auto_apply") not in (None, "")
            else True
        )
        policy.bank_account_id = ContractFinancialService._normalize_int(payload.get("bank_account_id"))
        policy.chart_account_id = ContractFinancialService._normalize_int(payload.get("chart_account_id"))
        policy.notes = ContractFinancialService._normalize_text(payload.get("notes")) or template.get("description")
        policy.metadata_json = {
            **dict(policy.metadata_json or {}),
            "template_key": template_key or None,
            "updated_by_user_id": user_id,
        }

        from services.contracts_service import ContractService

        ContractService.record_event(
            contract=contract,
            event_type="contract.financial_policy_upserted",
            description="Regra financeira de satélite atualizada no contrato.",
            payload={
                "policy_code": policy.policy_code,
                "satellite_nature": policy.satellite_nature,
                "principal_effect_mode": policy.principal_effect_mode,
                "satellite_effect_mode": policy.satellite_effect_mode,
                "trigger_event": policy.trigger_event,
            },
            user_id=user_id,
            auto_commit=False,
        )
        if auto_commit:
            db.session.commit()
        else:
            db.session.flush()
        return policy

    @staticmethod
    def delete_contract_satellite_policy(*, contract: Contract, policy_id: int, user_id: Optional[int] = None) -> bool:
        policy = FinancialSatellitePolicy.query.filter(
            FinancialSatellitePolicy.id == policy_id,
            FinancialSatellitePolicy.company_id == contract.company_id,
            FinancialSatellitePolicy.contract_id == contract.id,
            FinancialSatellitePolicy.deleted_at.is_(None),
        ).first()
        if not policy:
            return False
        policy.deleted_at = datetime.utcnow()
        from services.contracts_service import ContractService

        ContractService.record_event(
            contract=contract,
            event_type="contract.financial_policy_deleted",
            description="Regra financeira de satélite removida do contrato.",
            payload={"policy_code": policy.policy_code},
            user_id=user_id,
            auto_commit=False,
        )
        db.session.commit()
        return True

    @staticmethod
    def _resolve_financial_term(contract: Contract) -> Optional[ContractFinancialTerm]:
        return ContractFinancialTerm.query.filter_by(
            company_id=contract.company_id,
            contract_id=contract.id,
        ).first()

    @staticmethod
    def _resolve_counterparty(contract: Contract) -> Optional[FinancialCounterparty]:
        party = getattr(contract, "party", None)
        counterparty_id = getattr(party, "financial_counterparty_id", None) if party else None
        if not counterparty_id:
            return None
        return FinancialCounterparty.query.filter(
            FinancialCounterparty.id == counterparty_id,
            FinancialCounterparty.company_id == contract.company_id,
            FinancialCounterparty.deleted_at.is_(None),
        ).first()

    @staticmethod
    def _resolve_main_schedule_payload(*, contract: Contract, native_billing: ContractNativeBilling, financial_terms: Optional[ContractFinancialTerm]) -> dict:
        counterparty = ContractFinancialService._resolve_counterparty(contract)
        competence_date = native_billing.competence_start or native_billing.issue_date or date.today()
        due_date = native_billing.due_date or native_billing.issue_date or competence_date
        if due_date < competence_date:
            due_date = competence_date

        chart_account_id = (
            getattr(financial_terms, "default_chart_account_id", None)
            or getattr(counterparty, "default_chart_account_id", None)
        )
        cost_center_id = (
            getattr(financial_terms, "default_cost_center_id", None)
            or getattr(counterparty, "default_cost_center_id", None)
        )

        item_allocations = []
        for billing_item in native_billing.items.order_by(ContractNativeBillingItem.id.asc()).all():
            item_metadata = dict(billing_item.metadata_json or {})
            allocation = dict(item_metadata.get("allocation") or {})
            amount = ContractFinancialService._money(item_metadata.get("gross_amount") or billing_item.amount)
            project_id = allocation.get("project_id")
            item_allocations.append(
                {
                    "chart_account_id": allocation.get("chart_account_id") or chart_account_id,
                    "cost_center_id": allocation.get("cost_center_id") or cost_center_id,
                    "allocation_type": "amount",
                    "percentage": None,
                    "allocated_amount": float(amount),
                    "notes": f"Contrato {contract.code} · {billing_item.description}",
                    "domain_type": "project" if project_id else None,
                    "domain_source_kind": "manual" if project_id else None,
                    "domain_source_id": project_id,
                    "domain_label": f"{allocation.get('project_code') or ''} · {allocation.get('project_name') or ''}".strip(" ·") or None,
                    "domain_value": f"manual:project:{project_id}" if project_id else None,
                    "metadata_json": {
                        "contract_item_id": billing_item.contract_item_id,
                        "contract_native_billing_item_id": billing_item.id,
                    },
                }
            )

        metadata_json = {
            "source_module": "contracts",
            "contract_id": contract.id,
            "contract_code": contract.code,
            "contract_native_billing_id": native_billing.id,
            "financial_role": "main",
            "generated_from": "contract_native_billing",
            "managed_by_contract_billing": True,
            "contract_management_url": f"/contracts/list?company_id={contract.company_id}&contract_id={contract.id}&tab=faturamento",
            "payment_method_id": getattr(financial_terms, "default_payment_method_id", None),
            "billing_code": native_billing.billing_code,
            "customer_document": contract.party.document_number if contract.party else None,
            "customer_name": contract.party.name if contract.party else None,
            "issuer_cnpj": dict(native_billing.metadata_json or {}).get("fiscal_snapshot", {}).get("issuer_cnpj"),
            "retention_amount": float(native_billing.metadata_json.get("retention_amount") or 0) if native_billing.metadata_json else 0,
            "allocations": item_allocations,
        }
        return {
            "company_id": contract.company_id,
            "name": f"{contract.code} · {native_billing.billing_code}",
            "entry_type": "receivable",
            "movement_nature": "credit",
            "origin_type": "manual",
            "status": "active",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": competence_date,
            "competence_date": competence_date,
            "first_due_date": due_date,
            "next_due_date": due_date,
            "description": f"Faturamento contratual {native_billing.billing_code}",
            "memo": f"Contrato {contract.code} · competência {competence_date.strftime('%m/%Y')}",
            "document_number_prefix": native_billing.billing_code,
            "template_amount": ContractFinancialService._money(native_billing.gross_amount),
            "bank_account_id": getattr(financial_terms, "default_bank_account_id", None),
            "counterparty_id": getattr(counterparty, "id", None),
            "chart_account_id": chart_account_id,
            "cost_center_id": cost_center_id,
            "notes": getattr(financial_terms, "notes", None) if financial_terms else None,
            "metadata_json": metadata_json,
        }

    @staticmethod
    def _retention_policy_code(*, contract: Contract, contract_item_id: Optional[int], retention_kind: str) -> str:
        item_key = contract_item_id or 0
        normalized_kind = ContractFinancialService._normalize_text(retention_kind).lower() or "ret"
        return f"{contract.code or 'CTR'}-ITEM-{item_key}-{normalized_kind}".upper()

    @staticmethod
    def _extract_native_billing_retention_details(native_billing: ContractNativeBilling) -> list[dict]:
        details: list[dict] = []
        for billing_item in native_billing.items.order_by(ContractNativeBillingItem.id.asc()).all():
            item_metadata = dict(billing_item.metadata_json or {})
            for detail in list(item_metadata.get("retention_details") or []):
                normalized = dict(detail or {})
                amount = ContractFinancialService._money(normalized.get("calculated_amount"))
                if amount <= Decimal("0.00"):
                    continue
                normalized["calculated_amount"] = amount
                normalized["contract_item_id"] = normalized.get("contract_item_id") or billing_item.contract_item_id
                normalized["contract_native_billing_item_id"] = billing_item.id
                normalized["billing_item_description"] = billing_item.description
                normalized["item_amount"] = ContractFinancialService._money(
                    item_metadata.get("gross_amount") or billing_item.amount
                )
                details.append(normalized)
        return details

    @staticmethod
    def _upsert_policy_from_retention_detail(*, contract: Contract, retention_detail: dict) -> FinancialSatellitePolicy:
        contract_item_id = ContractFinancialService._normalize_int(retention_detail.get("contract_item_id"))
        retention_kind = ContractFinancialService._normalize_text(retention_detail.get("kind")).lower()
        policy_code = ContractFinancialService._retention_policy_code(
            contract=contract,
            contract_item_id=contract_item_id,
            retention_kind=retention_kind,
        )
        policy = FinancialSatellitePolicy.query.filter(
            FinancialSatellitePolicy.company_id == contract.company_id,
            FinancialSatellitePolicy.policy_code == policy_code,
            FinancialSatellitePolicy.deleted_at.is_(None),
        ).first()
        if not policy:
            policy = FinancialSatellitePolicy(
                company_id=contract.company_id,
                contract_id=contract.id,
                policy_code=policy_code,
            )
            db.session.add(policy)

        trigger_key = ContractFinancialService._normalize_text(retention_detail.get("trigger")).lower() or "baixa"
        trigger_event = ContractFinancialService.TRIGGER_TO_POLICY_EVENT.get(trigger_key, "on_partial_settlement")
        satellite_nature = ContractFinancialService._retention_detail_satellite_nature(retention_detail)
        policy.name = (
            f"{ContractFinancialService._retention_label(satellite_nature)} · "
            f"Item {contract_item_id or '-'}"
        )
        policy.satellite_nature = satellite_nature
        policy.principal_effect_mode = "partial_settlement_by_settlement"
        policy.satellite_effect_mode = "settle_by_settlement"
        policy.trigger_event = trigger_event
        policy.settlement_scope = "full"
        policy.auto_apply = True
        policy.bank_account_id = ContractFinancialService._normalize_int(
            retention_detail.get("bank_account_id") or retention_detail.get("asset_account_id")
        )
        policy.chart_account_id = ContractFinancialService._normalize_int(retention_detail.get("chart_account_id"))
        policy.notes = (
            f"Retenção {retention_kind.upper()} do item {contract_item_id or '-'} "
            f"gerida automaticamente pelo faturamento contratual."
        )
        policy.metadata_json = {
            **dict(policy.metadata_json or {}),
            "contract_item_id": contract_item_id,
            "retention_kind": retention_kind,
            "trigger_key": trigger_key,
            "generated_from_contract_item": True,
        }
        db.session.flush()
        return policy

    @staticmethod
    def _entry_type_for_satellite(nature: str) -> tuple[str, str]:
        if nature in {"iss_withheld", "inss_withheld", "irrf_withheld", "pis_withheld", "cofins_withheld", "csll_withheld", "other_withheld"}:
            return "payable", "debit"
        return "receivable", "credit"

    @staticmethod
    def _resolve_satellite_schedule_payload(
        *,
        contract: Contract,
        native_billing: ContractNativeBilling,
        main_schedule: FinancialSchedule,
        policy: FinancialSatellitePolicy,
        retention_detail: dict,
        amount: Decimal,
    ) -> dict:
        competence_date = native_billing.competence_start or native_billing.issue_date or date.today()
        due_date = native_billing.due_date or native_billing.issue_date or competence_date
        if due_date < competence_date:
            due_date = competence_date
        entry_type, movement_nature = ContractFinancialService._entry_type_for_satellite(policy.satellite_nature)
        retention_kind = ContractFinancialService._normalize_text(retention_detail.get("kind")).lower()
        allocation_notes = f"{ContractFinancialService._retention_label(policy.satellite_nature)} · {native_billing.billing_code}"
        domain_type = "project" if ContractFinancialService._normalize_int(retention_detail.get("project_id")) else None
        domain_source_id = ContractFinancialService._normalize_int(retention_detail.get("project_id"))
        domain_label = (
            f"{ContractFinancialService._normalize_text(retention_detail.get('project_code'))} · "
            f"{ContractFinancialService._normalize_text(retention_detail.get('project_name'))}"
        ).strip(" ·") or None
        child_allocations = [
            {
                "chart_account_id": policy.chart_account_id or main_schedule.chart_account_id,
                "cost_center_id": main_schedule.cost_center_id,
                "allocation_type": "amount",
                "percentage": 100,
                "allocated_amount": float(amount),
                "notes": allocation_notes,
                "domain_type": domain_type,
                "domain_source_kind": "manual" if domain_source_id else None,
                "domain_source_id": domain_source_id,
                "domain_label": domain_label,
                "domain_value": f"manual:project:{domain_source_id}" if domain_source_id else None,
                "metadata_json": {
                    "contract_item_id": ContractFinancialService._normalize_int(retention_detail.get("contract_item_id")),
                    "contract_native_billing_item_id": ContractFinancialService._normalize_int(retention_detail.get("contract_native_billing_item_id")),
                    "retention_kind": retention_kind,
                },
            }
        ]
        metadata_json = {
            "source_module": "contracts",
            "contract_id": contract.id,
            "contract_code": contract.code,
            "contract_native_billing_id": native_billing.id,
            "financial_role": "satellite",
            "satellite_nature": policy.satellite_nature,
            "parent_schedule_id": main_schedule.id,
            "policy_id": policy.id,
            "root_schedule_id": main_schedule.id,
            "managed_by_contract_billing": True,
            "contract_management_url": f"/contracts/list?company_id={contract.company_id}&contract_id={contract.id}&tab=faturamento",
            "contract_satellite_engine_managed": True,
            "retention_kind": retention_kind,
            "trigger_key": ContractFinancialService._normalize_text(retention_detail.get("trigger")).lower() or "baixa",
            "retention_detail": ContractFinancialService._sanitize_json({
                **dict(retention_detail or {}),
                "calculated_amount": float(amount),
            }),
            "allocations": child_allocations,
            "generated_from": "contract_native_billing",
        }
        return {
            "company_id": contract.company_id,
            "name": f"{ContractFinancialService._retention_label(policy.satellite_nature)} · {native_billing.billing_code}",
            "entry_type": entry_type,
            "movement_nature": movement_nature,
            "origin_type": "manual",
            "status": "active",
            "frequency": "one_time",
            "interval_value": 1,
            "start_date": competence_date,
            "competence_date": competence_date,
            "first_due_date": due_date,
            "next_due_date": due_date,
            "description": f"{ContractFinancialService._retention_label(policy.satellite_nature)} do faturamento {native_billing.billing_code}",
            "memo": policy.notes or retention.notes,
            "document_number_prefix": f"{native_billing.billing_code}-{policy.satellite_nature[:8].upper()}",
            "template_amount": amount,
            "bank_account_id": policy.bank_account_id or main_schedule.bank_account_id,
            "counterparty_id": main_schedule.counterparty_id,
            "chart_account_id": policy.chart_account_id or main_schedule.chart_account_id,
            "cost_center_id": main_schedule.cost_center_id,
            "notes": policy.notes,
            "metadata_json": metadata_json,
        }

    @staticmethod
    def _build_execution_metadata(
        *,
        trigger_event: str,
        retention_detail: dict,
        parent_open: Decimal,
        pending_satellite_total: Decimal,
    ) -> dict:
        return {
            "satellite_nature": ContractFinancialService._retention_detail_satellite_nature(retention_detail),
            "retention_kind": ContractFinancialService._normalize_text(retention_detail.get("kind")).lower(),
            "trigger_key": ContractFinancialService._normalize_text(retention_detail.get("trigger")).lower() or "baixa",
            "trigger_event": trigger_event,
            "parent_open_after_trigger": float(parent_open),
            "pending_satellite_total": float(pending_satellite_total),
            "contract_item_id": ContractFinancialService._normalize_int(retention_detail.get("contract_item_id")),
            "contract_native_billing_item_id": ContractFinancialService._normalize_int(retention_detail.get("contract_native_billing_item_id")),
        }

    @staticmethod
    def _execute_satellite_pair(
        *,
        company_id: int,
        parent_schedule: FinancialSchedule,
        child_schedule: FinancialSchedule,
        policy: FinancialSatellitePolicy,
        executed_amount: Decimal,
        settlement_date: date,
        trigger_event: str,
        trigger_settlement_id: Optional[int],
        retention_detail: dict,
    ) -> Optional[FinancialSatelliteExecution]:
        execution_query = FinancialSatelliteExecution.query.filter(
            FinancialSatelliteExecution.company_id == company_id,
            FinancialSatelliteExecution.policy_id == policy.id,
            FinancialSatelliteExecution.child_schedule_id == child_schedule.id,
            FinancialSatelliteExecution.trigger_event == trigger_event,
            FinancialSatelliteExecution.reversed_at.is_(None),
        )
        if trigger_settlement_id:
            execution_query = execution_query.filter(
                FinancialSatelliteExecution.trigger_settlement_id == trigger_settlement_id,
            )
        else:
            execution_query = execution_query.filter(FinancialSatelliteExecution.trigger_settlement_id.is_(None))
        if execution_query.first():
            return None

        parent_compensation = None
        parent_compensation_payload, parent_error = FinancialScheduleService.create_settlement_from_schedule(
            schedule_id=parent_schedule.id,
            company_id=company_id,
            payload={
                "settlement_date": settlement_date,
                "bank_account_id": policy.bank_account_id or parent_schedule.bank_account_id,
                "principal_amount": executed_amount,
                "gross_amount": executed_amount,
                "net_amount": executed_amount,
                "notes": f"Compensação automática do principal bruto via satélite {policy.name}.",
                "metadata_json": {
                    "skip_contract_satellite_engine": True,
                    "contract_satellite_engine_managed": True,
                    "contract_satellite_policy_id": policy.id,
                    "trigger_settlement_id": trigger_settlement_id,
                    "compensation_role": "parent",
                },
            },
            allowed_company_ids=[company_id],
        )
        if parent_error:
            raise ValueError(parent_error)
        parent_compensation = (parent_compensation_payload or {}).get("settlement")

        child_settlement_payload, child_error = FinancialScheduleService.create_settlement_from_schedule(
            schedule_id=child_schedule.id,
            company_id=company_id,
            payload={
                "settlement_date": settlement_date,
                "bank_account_id": policy.bank_account_id or child_schedule.bank_account_id,
                "principal_amount": executed_amount,
                "gross_amount": executed_amount,
                "net_amount": executed_amount,
                "notes": f"Liquidação automática do satélite {policy.name}.",
                "metadata_json": {
                    "skip_contract_satellite_engine": True,
                    "contract_satellite_engine_managed": True,
                    "contract_satellite_policy_id": policy.id,
                    "trigger_settlement_id": trigger_settlement_id,
                    "compensation_role": "satellite",
                },
            },
            allowed_company_ids=[company_id],
        )
        if child_error:
            raise ValueError(child_error)

        parent_balance = FinancialTitleBalanceService.calculate_for_schedule(schedule=parent_schedule)
        child_links = FinancialScheduleLink.query.filter(
            FinancialScheduleLink.company_id == company_id,
            FinancialScheduleLink.parent_schedule_id == parent_schedule.id,
            FinancialScheduleLink.deleted_at.is_(None),
        ).all()
        pending_total = Decimal("0.00")
        for link in child_links:
            linked_child = link.child_schedule or ContractFinancialService._resolve_schedule_by_id(company_id, link.child_schedule_id)
            if linked_child is not None:
                pending_total += ContractFinancialService._resolve_child_open_amount(linked_child)

        child_settlement = (child_settlement_payload or {}).get("settlement")
        execution = FinancialSatelliteExecution(
            company_id=company_id,
            policy_id=policy.id,
            parent_schedule_id=parent_schedule.id,
            child_schedule_id=child_schedule.id,
            trigger_settlement_id=trigger_settlement_id,
            parent_compensation_settlement_id=(parent_compensation or {}).get("id") if isinstance(parent_compensation, dict) else None,
            child_settlement_id=(child_settlement or {}).get("id") if isinstance(child_settlement, dict) else None,
            trigger_event=trigger_event,
            executed_amount=executed_amount,
            execution_status="success",
            metadata_json=ContractFinancialService._build_execution_metadata(
                trigger_event=trigger_event,
                retention_detail=retention_detail,
                parent_open=ContractFinancialService._money(parent_balance.get("principal_open")),
                pending_satellite_total=pending_total,
            ),
        )
        db.session.add(execution)
        db.session.flush()
        return execution

    @staticmethod
    def ensure_financial_titles_for_native_billing(
        *,
        contract: Contract,
        native_billing: ContractNativeBilling,
        user_id: Optional[int] = None,
        auto_commit: bool = True,
    ) -> dict:
        try:
            metadata = dict(native_billing.metadata_json or {})
            integration = dict(metadata.get("financial_integration") or {})
            existing_main_schedule_id = ContractFinancialService._normalize_int(integration.get("main_schedule_id"))
            if existing_main_schedule_id:
                existing_schedule = FinancialSchedule.query.filter(
                    FinancialSchedule.id == existing_main_schedule_id,
                    FinancialSchedule.company_id == contract.company_id,
                    FinancialSchedule.deleted_at.is_(None),
                ).first()
                if existing_schedule:
                    return {
                        "main_schedule_id": existing_schedule.id,
                        "created": False,
                        "satellite_count": len(integration.get("satellite_schedule_ids") or []),
                    }

            financial_terms = ContractFinancialService._resolve_financial_term(contract)
            main_payload = ContractFinancialService._resolve_main_schedule_payload(
                contract=contract,
                native_billing=native_billing,
                financial_terms=financial_terms,
            )
            main_payload["created_by_user_id"] = user_id
            main_payload["notes"] = main_payload.get("notes") or f"Gerado do contrato {contract.code}"

            main_schedule_payload, error = FinancialScheduleService.create_schedule(
                payload=main_payload,
                allowed_company_ids=[contract.company_id],
                auto_commit=False,
            )
            if error or not main_schedule_payload:
                raise ValueError(error or "Falha ao criar o título principal do faturamento.")

            main_schedule = FinancialSchedule.query.filter(
                FinancialSchedule.id == int(main_schedule_payload["id"]),
                FinancialSchedule.company_id == contract.company_id,
                FinancialSchedule.deleted_at.is_(None),
            ).first()
            if not main_schedule:
                raise ValueError("Título principal gerado não localizado para o contrato.")

            satellite_schedule_ids: list[int] = []
            immediate_policies: list[tuple[FinancialSchedule, FinancialSatellitePolicy, dict]] = []
            for retention_detail in ContractFinancialService._extract_native_billing_retention_details(native_billing):
                amount = ContractFinancialService._money(retention_detail.get("calculated_amount"))
                if amount <= Decimal("0.00"):
                    continue
                policy = ContractFinancialService._upsert_policy_from_retention_detail(
                    contract=contract,
                    retention_detail=retention_detail,
                )
                child_payload = ContractFinancialService._resolve_satellite_schedule_payload(
                    contract=contract,
                    native_billing=native_billing,
                    main_schedule=main_schedule,
                    policy=policy,
                    retention_detail=retention_detail,
                    amount=amount,
                )
                child_payload["created_by_user_id"] = user_id
                child_schedule_payload, child_error = FinancialScheduleService.create_schedule(
                    payload=child_payload,
                    allowed_company_ids=[contract.company_id],
                    auto_commit=False,
                )
                if child_error or not child_schedule_payload:
                    raise ValueError(child_error or f"Falha ao criar o satélite {policy.name}.")
                child_schedule_id = int(child_schedule_payload["id"])
                satellite_schedule_ids.append(child_schedule_id)
                db.session.add(
                    FinancialScheduleLink(
                        company_id=contract.company_id,
                        parent_schedule_id=main_schedule.id,
                        child_schedule_id=child_schedule_id,
                        policy_id=policy.id,
                        link_type="satellite",
                        title_nature=policy.satellite_nature,
                        metadata_json=ContractFinancialService._sanitize_json({
                            "contract_id": contract.id,
                            "contract_native_billing_id": native_billing.id,
                            "contract_item_id": ContractFinancialService._normalize_int(retention_detail.get("contract_item_id")),
                            "contract_native_billing_item_id": ContractFinancialService._normalize_int(retention_detail.get("contract_native_billing_item_id")),
                            "retention_kind": ContractFinancialService._normalize_text(retention_detail.get("kind")).lower(),
                            "trigger_key": ContractFinancialService._normalize_text(retention_detail.get("trigger")).lower() or "baixa",
                            "retention_detail": {
                                **dict(retention_detail or {}),
                                "calculated_amount": float(amount),
                            },
                            "created_at": ContractFinancialService._current_timestamp(),
                        }),
                    )
                )
                child_schedule = FinancialSchedule.query.filter(
                    FinancialSchedule.id == child_schedule_id,
                    FinancialSchedule.company_id == contract.company_id,
                    FinancialSchedule.deleted_at.is_(None),
                ).first()
                trigger_key = ContractFinancialService._normalize_text(retention_detail.get("trigger")).lower()
                if child_schedule is not None and trigger_key in {"emissao", "vencimento"}:
                    immediate_policies.append((child_schedule, policy, retention_detail))

            main_schedule.metadata_json = {
                **dict(main_schedule.metadata_json or {}),
                "root_schedule_id": main_schedule.id,
                "satellite_schedule_ids": satellite_schedule_ids,
            }
            metadata["financial_integration"] = {
                "linked_at": ContractFinancialService._current_timestamp(),
                "main_schedule_id": main_schedule.id,
                "main_schedule_code": main_schedule.schedule_code,
                "satellite_schedule_ids": satellite_schedule_ids,
                "satellite_count": len(satellite_schedule_ids),
            }
            native_billing.metadata_json = metadata

            for child_schedule, policy, retention_detail in immediate_policies:
                trigger_key = ContractFinancialService._normalize_text(retention_detail.get("trigger")).lower()
                trigger_event = ContractFinancialService.TRIGGER_TO_POLICY_EVENT.get(trigger_key, "on_partial_settlement")
                settlement_date = native_billing.issue_date if trigger_key == "emissao" else (native_billing.due_date or native_billing.issue_date or date.today())
                ContractFinancialService._execute_satellite_pair(
                    company_id=contract.company_id,
                    parent_schedule=main_schedule,
                    child_schedule=child_schedule,
                    policy=policy,
                    executed_amount=ContractFinancialService._money(retention_detail.get("calculated_amount")),
                    settlement_date=settlement_date,
                    trigger_event=trigger_event,
                    trigger_settlement_id=None,
                    retention_detail=retention_detail,
                )

            from services.contracts_service import ContractService

            ContractService.record_event(
                contract=contract,
                event_type="contract.financial_titles_generated",
                description="Títulos financeiros gerados a partir do faturamento nativo.",
                payload={
                    "native_billing_id": native_billing.id,
                    "main_schedule_id": main_schedule.id,
                    "satellite_count": len(satellite_schedule_ids),
                },
                user_id=user_id,
                auto_commit=False,
            )
            if auto_commit:
                db.session.commit()
            else:
                db.session.flush()
            return {
                "main_schedule_id": main_schedule.id,
                "created": True,
                "satellite_count": len(satellite_schedule_ids),
            }
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def list_contract_financial_titles(contract: Contract) -> list[dict]:
        schedules = (
            FinancialSchedule.query.filter(
                FinancialSchedule.company_id == contract.company_id,
                FinancialSchedule.deleted_at.is_(None),
            )
            .order_by(FinancialSchedule.first_due_date.asc(), FinancialSchedule.id.asc())
            .all()
        )
        main_schedules = [
            item
            for item in schedules
            if dict(item.metadata_json or {}).get("source_module") == "contracts"
            and dict(item.metadata_json or {}).get("contract_id") == contract.id
            and dict(item.metadata_json or {}).get("financial_role") == "main"
        ]
        if not main_schedules:
            return []
        links = (
            FinancialScheduleLink.query.filter(
                FinancialScheduleLink.company_id == contract.company_id,
                FinancialScheduleLink.parent_schedule_id.in_([item.id for item in main_schedules]),
                FinancialScheduleLink.deleted_at.is_(None),
            )
            .order_by(FinancialScheduleLink.id.asc())
            .all()
        )
        child_ids = [item.child_schedule_id for item in links]
        children_by_id = {
            item.id: item
            for item in schedules
            if item.id in child_ids
        }
        payload = []
        for schedule in main_schedules:
            main_balance = FinancialTitleBalanceService.calculate_for_schedule(schedule=schedule)
            schedule_links = [item for item in links if item.parent_schedule_id == schedule.id]
            satellites = []
            for link in schedule_links:
                child = children_by_id.get(link.child_schedule_id)
                if not child:
                    continue
                satellites.append(
                    {
                        "schedule": child,
                        "balance": FinancialTitleBalanceService.calculate_for_schedule(schedule=child),
                        "link": link,
                        "policy": link.policy,
                    }
                )
            payload.append(
                {
                    "main_schedule": schedule,
                    "main_balance": main_balance,
                    "satellites": satellites,
                    "link_count": len(satellites),
                }
            )
        return payload

    @staticmethod
    def build_contract_financial_summary(contract: Contract) -> dict:
        title_groups = ContractFinancialService.list_contract_financial_titles(contract)
        gross_total = Decimal("0.00")
        open_total = Decimal("0.00")
        settled_total = Decimal("0.00")
        satellite_total = Decimal("0.00")
        for group in title_groups:
            main_balance = group["main_balance"]
            principal_amount = ContractFinancialService._money(main_balance.get("principal_amount"))
            principal_open = ContractFinancialService._money(main_balance.get("principal_open"))
            gross_total += principal_amount
            open_total += principal_open
            settled_total += ContractFinancialService._money(main_balance.get("principal_settled"))
            for satellite in group["satellites"]:
                satellite_total += ContractFinancialService._money(satellite["balance"].get("principal_amount"))
        return {
            "title_count": len(title_groups),
            "gross_total": gross_total.quantize(Decimal("0.01")),
            "open_total": open_total.quantize(Decimal("0.01")),
            "settled_total": settled_total.quantize(Decimal("0.01")),
            "satellite_total": satellite_total.quantize(Decimal("0.01")),
        }

    @staticmethod
    def _build_settlement_payload(*, company_id: int, entry_id: int, settlement_date: date, amount: Decimal, bank_account_id: Optional[int], notes: str, metadata_json: Optional[dict] = None) -> dict:
        return {
            "company_id": company_id,
            "financial_entry_id": entry_id,
            "settlement_type": "automatic_rule",
            "settlement_status": "posted",
            "settlement_date": settlement_date,
            "bank_account_id": bank_account_id,
            "principal_amount": amount,
            "interest_amount": Decimal("0.00"),
            "penalty_amount": Decimal("0.00"),
            "discount_amount": Decimal("0.00"),
            "fee_amount": Decimal("0.00"),
            "other_adjustments_amount": Decimal("0.00"),
            "gross_amount": amount,
            "net_amount": amount,
            "notes": notes,
            "metadata_json": metadata_json or {},
        }

    @staticmethod
    def _resolve_schedule_by_id(company_id: int, schedule_id: Optional[int]) -> Optional[FinancialSchedule]:
        if not schedule_id:
            return None
        return FinancialSchedule.query.filter(
            FinancialSchedule.id == schedule_id,
            FinancialSchedule.company_id == company_id,
            FinancialSchedule.deleted_at.is_(None),
        ).first()

    @staticmethod
    def _resolve_child_open_amount(child_schedule: FinancialSchedule) -> Decimal:
        balance = FinancialTitleBalanceService.calculate_for_schedule(schedule=child_schedule)
        return ContractFinancialService._money(balance.get("principal_open"))

    @staticmethod
    def handle_schedule_settlement_event(
        *,
        company_id: int,
        schedule_id: int,
        settlement: FinancialSettlement,
    ) -> dict:
        settlement_metadata = dict(getattr(settlement, "metadata_json", None) or {})
        if settlement_metadata.get("skip_contract_satellite_engine"):
            return {"executed": 0, "reason": "skip_flag"}

        parent_schedule = ContractFinancialService._resolve_schedule_by_id(company_id, schedule_id)
        if not parent_schedule:
            return {"executed": 0, "reason": "schedule_not_found"}

        links = (
            FinancialScheduleLink.query.filter(
                FinancialScheduleLink.company_id == company_id,
                FinancialScheduleLink.parent_schedule_id == schedule_id,
                FinancialScheduleLink.deleted_at.is_(None),
            )
            .order_by(FinancialScheduleLink.id.asc())
            .all()
        )
        if not links:
            return {"executed": 0, "reason": "no_satellites"}

        parent_balance = FinancialTitleBalanceService.calculate_for_schedule(schedule=parent_schedule)
        parent_open = ContractFinancialService._money(parent_balance.get("principal_open"))
        parent_total = ContractFinancialService._money(parent_balance.get("principal_amount"))
        event_type = "on_full_settlement" if parent_open <= ContractFinancialService.SETTLEMENT_TOLERANCE else "on_partial_settlement"

        child_open_map: dict[int, Decimal] = {}
        pending_satellite_total = Decimal("0.00")
        for link in links:
            child_schedule = link.child_schedule or ContractFinancialService._resolve_schedule_by_id(company_id, link.child_schedule_id)
            if child_schedule is None:
                continue
            child_open = ContractFinancialService._resolve_child_open_amount(child_schedule)
            child_open_map[child_schedule.id] = child_open
            pending_satellite_total += child_open

        results = []
        for link in links:
            policy = link.policy
            child_schedule = link.child_schedule or ContractFinancialService._resolve_schedule_by_id(company_id, link.child_schedule_id)
            if not policy or child_schedule is None or policy.deleted_at is not None:
                continue
            if not policy.auto_apply:
                continue
            if policy.trigger_event != event_type:
                continue
            child_open = child_open_map.get(child_schedule.id, Decimal("0.00"))
            if child_open <= ContractFinancialService.SETTLEMENT_TOLERANCE:
                continue

            should_infer_net_settlement = (
                event_type == "on_partial_settlement"
                and policy.principal_effect_mode == "partial_settlement_by_settlement"
                and parent_open > Decimal("0.00")
                and parent_open <= pending_satellite_total + ContractFinancialService.SETTLEMENT_TOLERANCE
            )
            if event_type == "on_partial_settlement" and not should_infer_net_settlement and policy.settlement_scope != "proportional":
                continue

            execution_already_exists = FinancialSatelliteExecution.query.filter(
                FinancialSatelliteExecution.company_id == company_id,
                FinancialSatelliteExecution.policy_id == policy.id,
                FinancialSatelliteExecution.child_schedule_id == child_schedule.id,
                FinancialSatelliteExecution.trigger_settlement_id == settlement.id,
                FinancialSatelliteExecution.trigger_event == event_type,
            ).first()
            if execution_already_exists:
                continue

            executed_amount = child_open
            if event_type == "on_partial_settlement" and policy.settlement_scope == "proportional" and parent_total > Decimal("0.00"):
                settled_ratio = (
                    ContractFinancialService._money(parent_balance.get("principal_settled")) / parent_total
                )
                desired_total = (ContractFinancialService._money(child_schedule.template_amount) * settled_ratio).quantize(Decimal("0.01"))
                prior_executed = ContractFinancialService._money(
                    db.session.query(db.func.coalesce(db.func.sum(FinancialSatelliteExecution.executed_amount), 0))
                    .filter(
                        FinancialSatelliteExecution.company_id == company_id,
                        FinancialSatelliteExecution.policy_id == policy.id,
                        FinancialSatelliteExecution.child_schedule_id == child_schedule.id,
                        FinancialSatelliteExecution.reversed_at.is_(None),
                    )
                    .scalar()
                )
                executed_amount = max(desired_total - prior_executed, Decimal("0.00")).quantize(Decimal("0.01"))
            if executed_amount <= ContractFinancialService.SETTLEMENT_TOLERANCE:
                continue

            retention_detail = dict(link.metadata_json or {}).get("retention_detail") or {
                "kind": dict(link.metadata_json or {}).get("retention_kind"),
                "trigger": dict(link.metadata_json or {}).get("trigger_key"),
                "contract_item_id": dict(link.metadata_json or {}).get("contract_item_id"),
                "contract_native_billing_item_id": dict(link.metadata_json or {}).get("contract_native_billing_item_id"),
                "calculated_amount": float(executed_amount),
            }
            execution = ContractFinancialService._execute_satellite_pair(
                company_id=company_id,
                parent_schedule=parent_schedule,
                child_schedule=child_schedule,
                policy=policy,
                executed_amount=executed_amount,
                settlement_date=settlement.settlement_date,
                trigger_event=event_type,
                trigger_settlement_id=settlement.id,
                retention_detail=retention_detail,
            )
            if execution is None:
                continue
            db.session.commit()
            results.append(execution.to_dict())

        return {"executed": len(results), "items": results, "event_type": event_type}
