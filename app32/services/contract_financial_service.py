from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from models import db
from models.contracts import Contract, ContractFinancialTerm, ContractNativeBilling, ContractRetention
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
        "contractual_retention": "Retenção Contratual",
        "financial_retention": "Retenção Financeira",
    }
    SETTLEMENT_TOLERANCE = Decimal("0.01")

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

        metadata_json = {
            "source_module": "contracts",
            "contract_id": contract.id,
            "contract_code": contract.code,
            "contract_native_billing_id": native_billing.id,
            "financial_role": "main",
            "generated_from": "contract_native_billing",
            "payment_method_id": getattr(financial_terms, "default_payment_method_id", None),
            "billing_code": native_billing.billing_code,
            "customer_document": contract.party.document_number if contract.party else None,
            "customer_name": contract.party.name if contract.party else None,
            "issuer_cnpj": dict(native_billing.metadata_json or {}).get("fiscal_snapshot", {}).get("issuer_cnpj"),
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
    def _resolve_satellite_amount(*, retention: ContractRetention, gross_amount: Decimal) -> Decimal:
        fixed_amount = ContractFinancialService._money(getattr(retention, "fixed_amount", None))
        if fixed_amount > Decimal("0"):
            return fixed_amount
        rate_percent = ContractFinancialService._normalize_decimal(getattr(retention, "rate_percent", None))
        if rate_percent > Decimal("0"):
            return (gross_amount * rate_percent / Decimal("100")).quantize(Decimal("0.01"))
        return Decimal("0.00")

    @staticmethod
    def _entry_type_for_satellite(nature: str) -> tuple[str, str]:
        if nature in {"iss_withheld", "inss_withheld", "irrf_withheld", "pis_withheld", "cofins_withheld", "csll_withheld"}:
            return "payable", "debit"
        return "receivable", "credit"

    @staticmethod
    def _resolve_satellite_schedule_payload(
        *,
        contract: Contract,
        native_billing: ContractNativeBilling,
        main_schedule: FinancialSchedule,
        policy: FinancialSatellitePolicy,
        retention: ContractRetention,
        amount: Decimal,
    ) -> dict:
        competence_date = native_billing.competence_start or native_billing.issue_date or date.today()
        due_date = native_billing.due_date or native_billing.issue_date or competence_date
        if due_date < competence_date:
            due_date = competence_date
        entry_type, movement_nature = ContractFinancialService._entry_type_for_satellite(policy.satellite_nature)
        metadata_json = {
            "source_module": "contracts",
            "contract_id": contract.id,
            "contract_code": contract.code,
            "contract_native_billing_id": native_billing.id,
            "financial_role": "satellite",
            "satellite_nature": policy.satellite_nature,
            "parent_schedule_id": main_schedule.id,
            "policy_id": policy.id,
            "retention_id": retention.id,
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
            "notes": retention.notes or policy.notes,
            "metadata_json": metadata_json,
        }

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

            policies = ContractFinancialService.list_contract_satellite_policies(contract)
            retention_by_type = {
                ContractFinancialService._normalize_text(item.retention_type): item
                for item in contract.retentions.order_by(ContractRetention.id.asc()).all()
            }
            satellite_schedule_ids: list[int] = []
            for policy in policies:
                retention = retention_by_type.get(policy.satellite_nature)
                if not retention:
                    continue
                amount = ContractFinancialService._resolve_satellite_amount(
                    retention=retention,
                    gross_amount=ContractFinancialService._money(native_billing.gross_amount),
                )
                if amount <= Decimal("0.00"):
                    continue
                child_payload = ContractFinancialService._resolve_satellite_schedule_payload(
                    contract=contract,
                    native_billing=native_billing,
                    main_schedule=main_schedule,
                    policy=policy,
                    retention=retention,
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
                        metadata_json={
                            "contract_id": contract.id,
                            "contract_native_billing_id": native_billing.id,
                            "created_at": ContractFinancialService._current_timestamp(),
                        },
                    )
                )

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

            parent_compensation = None
            if should_infer_net_settlement and policy.principal_effect_mode == "partial_settlement_by_settlement":
                parent_compensation_payload, parent_error = FinancialScheduleService.create_settlement_from_schedule(
                    schedule_id=parent_schedule.id,
                    company_id=company_id,
                    payload={
                        "settlement_date": settlement.settlement_date,
                        "bank_account_id": policy.bank_account_id or parent_schedule.bank_account_id,
                        "principal_amount": executed_amount,
                        "gross_amount": executed_amount,
                        "net_amount": executed_amount,
                        "notes": f"Compensação automática do principal bruto via satélite {policy.name}.",
                        "metadata_json": {
                            "skip_contract_satellite_engine": True,
                            "contract_satellite_policy_id": policy.id,
                            "trigger_settlement_id": settlement.id,
                            "compensation_role": "parent",
                        },
                    },
                    allowed_company_ids=[company_id],
                )
                if parent_error:
                    continue
                parent_compensation = (parent_compensation_payload or {}).get("settlement")

            child_settlement_payload, child_error = FinancialScheduleService.create_settlement_from_schedule(
                schedule_id=child_schedule.id,
                company_id=company_id,
                payload={
                    "settlement_date": settlement.settlement_date,
                    "bank_account_id": policy.bank_account_id or child_schedule.bank_account_id,
                    "principal_amount": executed_amount,
                    "gross_amount": executed_amount,
                    "net_amount": executed_amount,
                    "notes": f"Liquidação automática do satélite {policy.name}.",
                    "metadata_json": {
                        "skip_contract_satellite_engine": True,
                        "contract_satellite_policy_id": policy.id,
                        "trigger_settlement_id": settlement.id,
                        "compensation_role": "satellite",
                    },
                },
                allowed_company_ids=[company_id],
            )
            if child_error:
                continue

            child_settlement = (child_settlement_payload or {}).get("settlement")
            execution = FinancialSatelliteExecution(
                company_id=company_id,
                policy_id=policy.id,
                parent_schedule_id=parent_schedule.id,
                child_schedule_id=child_schedule.id,
                trigger_settlement_id=settlement.id,
                parent_compensation_settlement_id=(parent_compensation or {}).get("id") if isinstance(parent_compensation, dict) else None,
                child_settlement_id=(child_settlement or {}).get("id") if isinstance(child_settlement, dict) else None,
                trigger_event=event_type,
                executed_amount=executed_amount,
                execution_status="success",
                metadata_json={
                    "satellite_nature": policy.satellite_nature,
                    "parent_open_after_trigger": float(parent_open),
                    "pending_satellite_total": float(pending_satellite_total),
                },
            )
            db.session.add(execution)
            db.session.commit()
            results.append(execution.to_dict())

        return {"executed": len(results), "items": results, "event_type": event_type}
