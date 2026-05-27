from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import calendar
from pathlib import Path
from typing import Optional
from uuid import uuid4

from flask import current_app
from sqlalchemy import or_
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from models import Company, db
from models.automation import AutomationRegistry, AutomationRule
from models.contracts import (
    Contract,
    ContractBillingItem,
    ContractCatalogItem,
    ContractClause,
    ContractDocument,
    ContractEvent,
    ContractFinancialTerm,
    ContractFiscalTerm,
    ContractItem,
    ContractNativeBilling,
    ContractNativeBillingItem,
    ContractNote,
    ContractParty,
    ContractingLegalEntity,
    ContractRetention,
    ContractTrigger,
)
from models.financial import (
    FinancialBankAccount,
    FinancialCorrectionIndex,
    FinancialCounterparty,
    FinancialChartAccount,
    FinancialCostCenter,
    FinancialPaymentMethod,
)
from services.contracts_catalog_service import ContractsCatalogService


class ContractService:
    ACTIVE_STATUSES = {"active", "signed", "implanting"}
    INACTIVE_STATUSES = {"inactive", "closed", "draft"}
    TAB_REGISTRY = (
        {"key": "cliente", "label": "Cliente", "scope": "core", "description": "Favorecido cliente vinculado ao contrato."},
        {"key": "itens", "label": "Itens do Contrato", "scope": "core", "description": "Escopo, serviços e itens negociados."},
        {"key": "clausulas", "label": "Cláusulas", "scope": "core", "description": "Redação, cláusulas e observações estruturadas do contrato."},
        {"key": "faturamento", "label": "Faturamento", "scope": "core", "description": "Itens e regras de faturamento."},
        {"key": "periodicidade", "label": "Agenda Nativa", "scope": "core", "description": "Datas-base, competência, faturamento e renovação nativos do contrato."},
        {"key": "automacoes", "label": "Automações", "scope": "core", "description": "Automações nativas do contrato com visão simplificada."},
        {"key": "financeiro", "label": "Financeiro", "scope": "core", "description": "Títulos, satélites e regras automáticas do contrato."},
        {"key": "fiscal", "label": "Fiscal", "scope": "core", "description": "Perfil fiscal e retenções."},
        {"key": "observacoes", "label": "Observações", "scope": "core", "description": "Contexto operacional e observações livres."},
        {"key": "historico", "label": "Histórico", "scope": "core", "description": "Linha do tempo do contrato, observações e eventos relevantes."},
        {"key": "gerar_pdf", "label": "Gerar / Editar Contrato", "scope": "capability", "description": "Upload/controle da versão em PDF do contrato."},
        {"key": "contrato_assinado", "label": "Contrato Assinado", "scope": "capability", "description": "Upload da via assinada escaneada."},
        {"key": "documentos", "label": "Documentos / Anexos", "scope": "capability", "description": "Artefatos gerais vinculados ao contrato."},
    )

    @staticmethod
    def _normalize_text(value: object) -> str:
        return str(value or "").strip()

    @staticmethod
    def _normalize_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "on", "yes", "sim"}

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
    def _normalize_int(value: object) -> Optional[int]:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return int(text)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_date(value: object) -> Optional[date]:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.strptime(text, "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def infer_document_type(value: object) -> Optional[str]:
        digits = re.sub(r"\D", "", str(value or ""))
        if len(digits) == 11:
            return "cpf"
        if len(digits) == 14:
            return "cnpj"
        return None

    @staticmethod
    def calculate_total_price(quantity: object, unit_price: object) -> Decimal:
        qty = ContractService._normalize_decimal(quantity)
        price = ContractService._normalize_decimal(unit_price)
        return (qty * price).quantize(Decimal("0.01"))

    @staticmethod
    def _resolve_company_code(company_id: int) -> str:
        company = ContractService.get_company(company_id)
        raw_code = ContractService._normalize_text(getattr(company, "client_code", ""))
        raw_name = ContractService._normalize_text(getattr(company, "name", ""))

        sanitized = re.sub(r"[^A-Z0-9]", "", raw_code.upper())
        if not sanitized and raw_name:
            tokens = [token[0] for token in re.findall(r"[A-Za-z0-9]+", raw_name.upper()) if token]
            sanitized = "".join(tokens)
        if not sanitized:
            sanitized = str(company_id or "XX")

        sanitized = (sanitized[:2] if len(sanitized) >= 2 else sanitized.ljust(2, "X")).upper()
        return sanitized

    @staticmethod
    def _next_structured_code(model, company_id: int, marker: str) -> str:
        company_code = ContractService._resolve_company_code(company_id)
        normalized_marker = re.sub(r"[^A-Z0-9]", "", str(marker or "").upper())[:1] or "X"
        code_prefix = f"{company_code}.{normalized_marker}."
        last_number = 0
        rows = model.query.with_entities(model.code).filter(model.company_id == company_id).all()
        for (code,) in rows:
            normalized_code = str(code or "").strip().upper()
            if not normalized_code.startswith(code_prefix):
                continue
            match = re.search(r"(\d+)$", normalized_code)
            if match:
                last_number = max(last_number, int(match.group(1)))
        return f"{code_prefix}{last_number + 1:03d}"

    @staticmethod
    def get_company(company_id: int) -> Optional[Company]:
        return Company.query.get(company_id)

    @staticmethod
    def get_dashboard(company_id: int) -> dict:
        contracts_query = Contract.query.filter(Contract.company_id == company_id, Contract.deleted_at.is_(None))
        parties_query = ContractParty.query.filter(ContractParty.company_id == company_id, ContractParty.deleted_at.is_(None))
        return {
            "counts": {
                "contracts": contracts_query.count(),
                "drafts": contracts_query.filter(Contract.status == "draft").count(),
                "active": contracts_query.filter(Contract.status.in_(["active", "signed", "implanting"])).count(),
                "parties": parties_query.count(),
            },
            "latest_contracts": contracts_query.order_by(Contract.updated_at.desc()).limit(8).all(),
            "latest_parties": parties_query.order_by(ContractParty.updated_at.desc()).limit(8).all(),
        }

    @staticmethod
    def list_parties(company_id: int):
        ContractService.sync_parties_from_counterparties(company_id)
        return (
            ContractParty.query.filter(ContractParty.company_id == company_id, ContractParty.deleted_at.is_(None))
            .order_by(ContractParty.name.asc())
            .all()
        )

    @staticmethod
    def list_customer_parties(company_id: int):
        ContractService.sync_parties_from_counterparties(company_id, only_customer=True)
        return (
            ContractParty.query.filter(
                ContractParty.company_id == company_id,
                ContractParty.deleted_at.is_(None),
                ContractParty.is_customer.is_(True),
            )
            .order_by(ContractParty.name.asc())
            .all()
        )

    @staticmethod
    def list_contracts(company_id: int):
        ContractService.sync_parties_from_counterparties(company_id)
        return (
            Contract.query.filter(Contract.company_id == company_id, Contract.deleted_at.is_(None))
            .order_by(Contract.updated_at.desc())
            .all()
        )

    @staticmethod
    def list_contracts_filtered(company_id: int, filters: Optional[dict] = None):
        ContractService.sync_parties_from_counterparties(company_id)
        query = Contract.query.filter(Contract.company_id == company_id, Contract.deleted_at.is_(None))
        filters = filters or {}

        status = ContractService._normalize_text(filters.get("status")).lower()
        if status:
            query = query.filter(Contract.status == status)

        party_id = ContractService._normalize_int(filters.get("party_id"))
        if party_id:
            query = query.filter(Contract.party_id == party_id)

        manager_employee_id = ContractService._normalize_int(filters.get("manager_employee_id"))
        if manager_employee_id:
            query = query.filter(Contract.manager_employee_id == manager_employee_id)

        search = ContractService._normalize_text(filters.get("search"))
        if search:
            ilike = f"%{search}%"
            query = query.join(ContractParty, ContractParty.id == Contract.party_id).filter(
                or_(
                    Contract.code.ilike(ilike),
                    Contract.title.ilike(ilike),
                    ContractParty.name.ilike(ilike),
                )
            )

        return query.order_by(Contract.updated_at.desc(), Contract.id.desc()).all()

    @staticmethod
    def get_contracts_kpis(company_id: int) -> dict:
        contracts = ContractService.list_contracts(company_id)
        today = date.today()
        return {
            "total": len(contracts),
            "active": sum(1 for item in contracts if ContractService.get_contract_status_group(item) == "active"),
            "renewing": sum(1 for item in contracts if item.renewal_date and item.renewal_date >= today),
            "pending_billing": sum(1 for item in contracts if not item.last_billing_at and ContractService.get_contract_status_group(item) == "active"),
        }

    @staticmethod
    def get_contract_next_action(contract: Contract) -> dict:
        today = date.today()
        native_schedule = ContractService.get_native_schedule_overview(contract)
        next_event = native_schedule.get("next_event")
        if next_event and next_event.get("date") and next_event["date"] >= today:
            label_map = {
                "billing": "Faturar próxima competência",
                "billing_start": "Iniciar faturamento",
                "renewal": "Renovar contrato",
                "adjustment": "Aplicar reajuste",
                "termination": "Planejar encerramento",
                "alert": "Acompanhar alerta contratual",
            }
            return {"label": label_map.get(next_event["event_type"], next_event["label"]), "tone": next_event.get("tone", "info")}
        if contract.termination_date and contract.termination_date <= today:
            return {"label": "Encerrado", "tone": "neutral"}
        if contract.renewal_date and contract.renewal_date <= today:
            return {"label": "Renovar contrato", "tone": "warning"}
        if contract.last_billing_at is None and ContractService.get_contract_status_group(contract) == "active":
            return {"label": "Faturar primeira competência", "tone": "info"}
        if contract.adjustment_date and contract.adjustment_date <= today:
            return {"label": "Aplicar reajuste", "tone": "warning"}
        return {"label": "Acompanhar execução", "tone": "success"}

    @staticmethod
    def get_native_trigger_type_options() -> list[tuple[str, str]]:
        return [
            ("billing", "Faturamento"),
            ("renewal", "Renovação"),
            ("adjustment", "Reajuste"),
            ("termination", "Encerramento"),
            ("alert", "Alerta geral"),
        ]

    @staticmethod
    def get_reference_date_type_options() -> list[tuple[str, str]]:
        return [
            ("signed_at", "Assinatura"),
            ("service_start_at", "Início dos serviços"),
            ("billing_start_at", "Início do faturamento"),
            ("renewal_date", "Data de renovação"),
            ("adjustment_date", "Data de reajuste"),
            ("termination_date", "Data de finalização"),
            ("manual", "Data manual"),
        ]

    @staticmethod
    def get_contract_type_options() -> list[tuple[str, str]]:
        return [
            ("prestacao", "Prestação de serviços"),
            ("licenciamento", "Licenciamento"),
            ("manutencao_suporte", "Manutenção / suporte"),
            ("fornecimento", "Fornecimento"),
            ("consultoria", "Consultoria"),
            ("outsourcing", "Outsourcing"),
            ("locacao", "Locação"),
            ("parceria", "Parceria"),
        ]

    @staticmethod
    def get_currency_options() -> list[tuple[str, str]]:
        return [
            ("BRL", "BRL · Real"),
            ("USD", "USD · Dólar"),
            ("EUR", "EUR · Euro"),
        ]

    @staticmethod
    def get_periodicity_options() -> list[tuple[str, str]]:
        return [
            ("monthly", "Mensal"),
            ("weekly", "Semanal"),
            ("quarterly", "Trimestral"),
            ("semiannual", "Semestral"),
            ("annual", "Anual"),
        ]

    @staticmethod
    def get_competence_rule_options() -> list[tuple[str, str]]:
        return [
            ("mes atual", "Mês atual"),
            ("mes anterior", "Mês anterior"),
            ("antecipado", "Antecipado"),
            ("sob demanda", "Sob demanda"),
        ]

    @staticmethod
    def get_renewal_rule_options() -> list[tuple[str, str]]:
        return [
            ("manual", "Manual"),
            ("auto", "Automática"),
            ("aditivo", "Por aditivo"),
        ]

    @staticmethod
    def get_due_rule_reference_options() -> list[tuple[str, str]]:
        return [
            ("issue_month", "Mês da emissão"),
            ("issue_month_plus_1", "1º mês após a emissão"),
            ("issue_month_plus_2", "2º mês após a emissão"),
        ]

    @staticmethod
    def build_due_rule(*, reference: object, day: object) -> Optional[str]:
        reference_value = ContractService._normalize_text(reference)
        day_value = ContractService._normalize_int(day)
        if reference_value not in {"issue_month", "issue_month_plus_1", "issue_month_plus_2"} or not day_value:
            return None
        day_value = max(1, min(day_value, 31))
        return f"{reference_value}:{day_value:02d}"

    @staticmethod
    def parse_due_rule(value: object) -> dict:
        raw_value = ContractService._normalize_text(value)
        if ":" in raw_value:
            reference, day_text = raw_value.split(":", 1)
            day_value = ContractService._normalize_int(day_text)
            if reference in {"issue_month", "issue_month_plus_1", "issue_month_plus_2"} and day_value:
                return {
                    "reference": reference,
                    "day": max(1, min(day_value, 31)),
                    "label": f"{dict(ContractService.get_due_rule_reference_options()).get(reference, reference)} · dia {max(1, min(day_value, 31))}",
                    "is_structured": True,
                }
        return {
            "reference": None,
            "day": None,
            "label": raw_value or "-",
            "is_structured": False,
        }

    @staticmethod
    def _add_months(base_date: date, months: int) -> date:
        month_index = (base_date.month - 1) + months
        year = base_date.year + (month_index // 12)
        month = (month_index % 12) + 1
        day = min(base_date.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    @staticmethod
    def resolve_due_date(*, issue_date: date, due_rule: object) -> Optional[date]:
        parsed = ContractService.parse_due_rule(due_rule)
        if not parsed["is_structured"] or not parsed["reference"] or not parsed["day"]:
            return None
        month_offset_map = {
            "issue_month": 0,
            "issue_month_plus_1": 1,
            "issue_month_plus_2": 2,
        }
        target_base = ContractService._add_months(issue_date, month_offset_map[parsed["reference"]])
        last_day = calendar.monthrange(target_base.year, target_base.month)[1]
        return date(target_base.year, target_base.month, min(parsed["day"], last_day))

    @staticmethod
    def get_contract_automation_template_options() -> list[dict]:
        return [
            {
                "key": "generate_billing_monthly",
                "label": "Faturamento mensal",
                "description": "Gera competência nativa mensal do contrato.",
            },
            {
                "key": "renewal_alert_before_date",
                "label": "Alerta de renovação",
                "description": "Avisa antes da data de renovação do contrato.",
            },
            {
                "key": "adjustment_on_date",
                "label": "Reajuste automático",
                "description": "Dispara ação de reajuste na data-base do contrato.",
            },
        ]

    @staticmethod
    def sync_parties_from_counterparties(company_id: int, *, only_customer: bool = False) -> None:
        counterparties = FinancialCounterparty.query.filter(
            FinancialCounterparty.company_id == company_id,
            FinancialCounterparty.deleted_at.is_(None),
        ).all()
        changed = False
        for counterparty in counterparties:
            metadata = dict(counterparty.metadata_json or {})
            is_customer = bool(metadata.get("is_customer"))
            is_supplier = bool(metadata.get("is_supplier"))
            if only_customer and not is_customer:
                continue
            if not is_customer and not is_supplier:
                continue
            party = ContractParty.query.filter(
                ContractParty.company_id == company_id,
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
                    company_id=company_id,
                    code=ContractService._next_structured_code(ContractParty, company_id, "F"),
                )
                ContractService.update_party(party=party, payload=payload, user_id=None, is_new=True)
                db.session.add(party)
                changed = True
                continue
            before = (
                party.name,
                party.legal_name,
                party.document_type,
                party.document_number,
                party.email,
                party.phone,
                bool(party.is_customer),
                bool(party.is_supplier),
                party.status,
                party.notes,
                party.financial_counterparty_id,
            )
            ContractService.update_party(party=party, payload=payload, user_id=None, is_new=True)
            after = (
                party.name,
                party.legal_name,
                party.document_type,
                party.document_number,
                party.email,
                party.phone,
                bool(party.is_customer),
                bool(party.is_supplier),
                party.status,
                party.notes,
                party.financial_counterparty_id,
            )
            if before != after:
                changed = True
        if changed:
            db.session.commit()

    @staticmethod
    def get_contract_start_date(contract: Contract) -> Optional[date]:
        return contract.service_start_at or contract.billing_start_at or contract.signed_at

    @staticmethod
    def get_contract_status_group(contract: Contract) -> str:
        status = ContractService._normalize_text(getattr(contract, "status", "")).lower()
        return "active" if status in ContractService.ACTIVE_STATUSES else "inactive"

    @staticmethod
    def get_contract_status_label(contract: Contract) -> str:
        return "Ativo" if ContractService.get_contract_status_group(contract) == "active" else "Inativo"

    @staticmethod
    def get_contract_workspace_summary(contract: Optional[Contract]) -> dict:
        if contract is None:
            return {}

        contract_items = contract.items.order_by(ContractItem.order_index.asc(), ContractItem.id.asc()).all()
        billing_items = contract.billing_items.order_by(ContractBillingItem.order_index.asc(), ContractBillingItem.id.asc()).all()
        total_contract_value = sum((item.total_price or Decimal("0")) for item in contract_items)
        total_billing_value = sum((item.amount or Decimal("0")) for item in billing_items)

        return {
            "status_group": ContractService.get_contract_status_group(contract),
            "status_label": ContractService.get_contract_status_label(contract),
            "start_date": ContractService.get_contract_start_date(contract),
            "renewal_date": contract.renewal_date,
            "adjustment_date": contract.adjustment_date,
            "termination_date": contract.termination_date,
            "manager_employee_id": contract.manager_employee_id,
            "contract_item_count": len(contract_items),
            "billing_item_count": len(billing_items),
            "clause_count": contract.clauses.count(),
            "note_count": contract.notes_log.count(),
            "event_count": contract.events.count(),
            "total_contract_value": total_contract_value.quantize(Decimal("0.01")) if contract_items else Decimal("0.00"),
            "total_billing_value": total_billing_value.quantize(Decimal("0.01")) if billing_items else Decimal("0.00"),
            "updated_at": contract.updated_at,
            "created_at": contract.created_at,
        }

    @staticmethod
    def build_contract_review_flags(contract: Contract) -> dict:
        financial_terms = ContractFinancialTerm.query.filter_by(contract_id=contract.id, company_id=contract.company_id).first()
        fiscal_terms = ContractFiscalTerm.query.filter_by(contract_id=contract.id, company_id=contract.company_id).first()
        fiscal_ok = bool(
            fiscal_terms
            and contract.contracting_legal_entity_id
            and fiscal_terms.service_code
            and fiscal_terms.service_list_item
            and fiscal_terms.operation_nature
            and fiscal_terms.integration_mode
        )
        return {
            "cliente": bool(contract.party_id),
            "itens": "OK" if contract.items.count() else "Pendente",
            "faturamento": "OK" if contract.billing_items.count() else "Pendente",
            "periodicidade": bool(contract.periodicity or contract.renewal_date or contract.adjustment_date or contract.triggers.count()),
            "fiscal": fiscal_ok,
            "financeiro": bool(financial_terms),
            "cobranca": bool(financial_terms),
            "pdf": "OK" if contract.documents.filter(ContractDocument.document_type == "pdf_gerado").count() else "Pendente",
            "assinado": "OK" if contract.documents.filter(
                or_(ContractDocument.document_type == "contrato_assinado", ContractDocument.is_signed_version.is_(True))
            ).count() else "Pendente",
        }

    @staticmethod
    def _event_date_payload(event_date: Optional[date], label: str, event_type: str, source: str) -> Optional[dict]:
        if not event_date:
            return None
        today = date.today()
        if event_date < today:
            tone = "warning"
        elif event_date == today:
            tone = "info"
        else:
            tone = "success"
        return {
            "event_type": event_type,
            "label": label,
            "date": event_date,
            "date_label": event_date.strftime("%d/%m/%Y"),
            "tone": tone,
            "source": source,
        }

    @staticmethod
    def _resolve_trigger_reference_date(contract: Contract, trigger: ContractTrigger) -> Optional[date]:
        reference_type = ContractService._normalize_text(trigger.reference_date_type)
        if reference_type == "manual":
            return trigger.reference_date_value
        return {
            "signed_at": contract.signed_at,
            "service_start_at": contract.service_start_at,
            "billing_start_at": contract.billing_start_at,
            "renewal_date": contract.renewal_date,
            "adjustment_date": contract.adjustment_date,
            "termination_date": contract.termination_date,
        }.get(reference_type) or trigger.reference_date_value

    @staticmethod
    def get_native_schedule_overview(contract: Contract) -> dict:
        triggers = contract.triggers.filter(ContractTrigger.is_active.is_(True)).order_by(ContractTrigger.reference_date_value.asc().nulls_last(), ContractTrigger.id.asc()).all()
        events = []
        base_events = [
            ContractService._event_date_payload(contract.billing_start_at, "Início da cobrança contratual", "billing_start", "contract"),
            ContractService._event_date_payload(contract.renewal_date, "Janela de renovação", "renewal", "contract"),
            ContractService._event_date_payload(contract.adjustment_date, "Janela de reajuste", "adjustment", "contract"),
            ContractService._event_date_payload(contract.termination_date, "Data de finalização", "termination", "contract"),
        ]
        events.extend(item for item in base_events if item)

        for trigger in triggers:
            reference_date = ContractService._resolve_trigger_reference_date(contract, trigger)
            if reference_date and trigger.offset_days:
                reference_date = reference_date + timedelta(days=int(trigger.offset_days))
            label = {
                "billing": "Gatilho nativo de faturamento",
                "renewal": "Gatilho nativo de renovação",
                "adjustment": "Gatilho nativo de reajuste",
                "termination": "Gatilho nativo de encerramento",
                "alert": "Alerta contratual",
            }.get(trigger.trigger_type, trigger.trigger_type)
            payload = ContractService._event_date_payload(reference_date, label, trigger.trigger_type, "trigger")
            if payload:
                payload["periodicity"] = trigger.periodicity
                payload["alert_before_days"] = trigger.alert_before_days
                payload["reference_date_type"] = trigger.reference_date_type
                payload["reference_date_type_label"] = dict(ContractService.get_reference_date_type_options()).get(trigger.reference_date_type, trigger.reference_date_type)
                events.append(payload)

        events.sort(key=lambda item: item["date"])
        today = date.today()
        next_event = next((item for item in events if item["date"] >= today), events[0] if events else None)
        return {
            "events": events,
            "next_event": next_event,
            "trigger_count": len(triggers),
        }

    @staticmethod
    def _build_contract_automation_next_execution(contract: Contract, template_key: str) -> Optional[datetime]:
        today = date.today()
        if template_key == "generate_billing_monthly":
            anchor = contract.billing_start_at or contract.service_start_at or today
            day = min(max(anchor.day, 1), 28)
            year = today.year
            month = today.month
            candidate = date(year, month, day)
            if candidate <= today:
                if month == 12:
                    candidate = date(year + 1, 1, day)
                else:
                    candidate = date(year, month + 1, day)
            return datetime.combine(candidate, datetime.min.time())
        if template_key == "renewal_alert_before_date" and contract.renewal_date:
            candidate = contract.renewal_date - timedelta(days=30)
            return datetime.combine(candidate, datetime.min.time())
        if template_key == "adjustment_on_date" and contract.adjustment_date:
            return datetime.combine(contract.adjustment_date, datetime.min.time())
        return None

    @staticmethod
    def list_contract_automations(contract: Contract):
        return (
            AutomationRegistry.query.filter(
                AutomationRegistry.company_id == contract.company_id,
                AutomationRegistry.entity_type == "contract",
                AutomationRegistry.entity_id == contract.id,
            )
            .order_by(AutomationRegistry.next_execution_at.asc().nullslast(), AutomationRegistry.name.asc())
            .all()
        )

    @staticmethod
    def create_contract_automation(*, contract: Contract, template_key: str, user_id: Optional[int]):
        template_key = ContractService._normalize_text(template_key)
        template_map = {item["key"]: item for item in ContractService.get_contract_automation_template_options()}
        if template_key not in template_map:
            raise ValueError("Modelo de automação inválido para o contrato.")

        existing = AutomationRegistry.query.filter(
            AutomationRegistry.company_id == contract.company_id,
            AutomationRegistry.entity_type == "contract",
            AutomationRegistry.entity_id == contract.id,
            AutomationRegistry.action_type == template_key,
            AutomationRegistry.is_active.is_(True),
        ).first()
        if existing:
            raise ValueError("Já existe uma automação ativa deste tipo para o contrato.")

        template = template_map[template_key]
        trigger_type = "date"
        action_type = template_key
        execution_mode = "automatic"
        requires_approval = False
        origin_type = "native"
        next_execution_at = ContractService._build_contract_automation_next_execution(contract, template_key)

        if template_key == "renewal_alert_before_date":
            action_type = "send_alert"
        elif template_key == "adjustment_on_date":
            action_type = "apply_adjustment"

        registry = AutomationRegistry(
            company_id=contract.company_id,
            name=template["label"],
            module_key="contracts",
            origin_type=origin_type,
            entity_type="contract",
            entity_id=contract.id,
            trigger_type=trigger_type,
            action_type=action_type,
            execution_mode=execution_mode,
            status="active",
            requires_approval=requires_approval,
            is_active=True,
            next_execution_at=next_execution_at,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        db.session.add(registry)
        db.session.flush()

        if template_key == "generate_billing_monthly":
            trigger_config = {"mode": "monthly", "reference": "billing_start_at"}
            action_config = {"service": "BillingService.generate_from_contract"}
        elif template_key == "renewal_alert_before_date":
            trigger_config = {"mode": "before_date", "reference": "renewal_date", "days_before": 30}
            action_config = {"channel": "in_app", "action": "renewal_alert"}
        else:
            trigger_config = {"mode": "on_date", "reference": "adjustment_date"}
            action_config = {"service": "ContractService.apply_adjustment"}

        db.session.add(
            AutomationRule(
                company_id=contract.company_id,
                automation_registry_id=registry.id,
                rule_code=template_key,
                trigger_config_json=trigger_config,
                action_config_json=action_config,
                policy_config_json={"entity_type": "contract", "entity_id": contract.id},
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
        )
        ContractService.record_event(
            contract=contract,
            event_type="contract.automation_created",
            description=f"Automação '{template['label']}' criada para o contrato.",
            payload={"automation_template_key": template_key, "next_execution_at": next_execution_at.isoformat() if next_execution_at else None},
            user_id=user_id,
            auto_commit=False,
        )
        db.session.commit()
        return registry

    @staticmethod
    def update_contract_automation_status(*, contract: Contract, automation_id: int, activate: bool, user_id: Optional[int]):
        registry = AutomationRegistry.query.filter(
            AutomationRegistry.id == automation_id,
            AutomationRegistry.company_id == contract.company_id,
            AutomationRegistry.entity_type == "contract",
            AutomationRegistry.entity_id == contract.id,
        ).first()
        if not registry:
            raise ValueError("Automação do contrato não localizada.")
        registry.is_active = bool(activate)
        registry.status = "active" if activate else "paused"
        registry.updated_by_user_id = user_id
        ContractService.record_event(
            contract=contract,
            event_type="contract.automation_status_updated",
            description=f"Automação '{registry.name}' {'ativada' if activate else 'pausada'}.",
            payload={"automation_id": registry.id, "status": registry.status},
            user_id=user_id,
            auto_commit=False,
        )
        db.session.commit()
        return registry

    @staticmethod
    def list_customer_contract_tree(company_id: int) -> list[dict]:
        ContractService.sync_parties_from_counterparties(company_id, only_customer=True)
        parties = ContractService.list_customer_parties(company_id)
        contracts = (
            Contract.query.filter(
                Contract.company_id == company_id,
                Contract.deleted_at.is_(None),
            )
            .order_by(ContractParty.name.asc(), Contract.title.asc())
            .join(ContractParty, ContractParty.id == Contract.party_id)
            .all()
        )
        contracts_by_party: dict[int, list[Contract]] = {}
        for contract in contracts:
            contracts_by_party.setdefault(contract.party_id, []).append(contract)

        tree = []
        for party in parties:
            party_contracts = contracts_by_party.get(party.id, [])
            tree.append(
                {
                    "party": party,
                    "contracts": party_contracts,
                    "contract_count": len(party_contracts),
                    "active_count": sum(1 for item in party_contracts if ContractService.get_contract_status_group(item) == "active"),
                }
            )
        return tree

    @staticmethod
    def list_financial_counterparties(company_id: int):
        return (
            FinancialCounterparty.query.filter(
                FinancialCounterparty.company_id == company_id,
                FinancialCounterparty.deleted_at.is_(None),
            )
            .order_by(FinancialCounterparty.name.asc())
            .all()
        )

    @staticmethod
    def list_financial_references(company_id: int) -> dict:
        return {
            "bank_accounts": FinancialBankAccount.query.filter(
                FinancialBankAccount.company_id == company_id,
                FinancialBankAccount.deleted_at.is_(None),
            ).order_by(FinancialBankAccount.name.asc()).all(),
            "payment_methods": FinancialPaymentMethod.query.filter(
                FinancialPaymentMethod.company_id == company_id,
                FinancialPaymentMethod.deleted_at.is_(None),
            ).order_by(FinancialPaymentMethod.name.asc()).all(),
            "chart_accounts": FinancialChartAccount.query.filter(
                FinancialChartAccount.company_id == company_id,
                FinancialChartAccount.deleted_at.is_(None),
            ).order_by(FinancialChartAccount.name.asc()).all(),
            "cost_centers": FinancialCostCenter.query.filter(
                FinancialCostCenter.company_id == company_id,
                FinancialCostCenter.deleted_at.is_(None),
            ).order_by(FinancialCostCenter.name.asc()).all(),
            "correction_indexes": FinancialCorrectionIndex.query.filter(
                FinancialCorrectionIndex.company_id == company_id,
                FinancialCorrectionIndex.deleted_at.is_(None),
            ).order_by(FinancialCorrectionIndex.name.asc()).all(),
        }

    @staticmethod
    def list_contracting_legal_entities(company_id: int):
        return (
            ContractingLegalEntity.query.filter(
                ContractingLegalEntity.company_id == company_id,
                ContractingLegalEntity.is_active.is_(True),
            )
            .order_by(ContractingLegalEntity.legal_name.asc(), ContractingLegalEntity.id.asc())
            .all()
        )

    @staticmethod
    def get_contracting_legal_entity(company_id: int, legal_entity_id: int) -> Optional[ContractingLegalEntity]:
        return ContractingLegalEntity.query.filter(
            ContractingLegalEntity.id == legal_entity_id,
            ContractingLegalEntity.company_id == company_id,
            ContractingLegalEntity.is_active.is_(True),
        ).first()

    @staticmethod
    def get_party(company_id: int, party_id: int) -> Optional[ContractParty]:
        ContractService.sync_parties_from_counterparties(company_id)
        return ContractParty.query.filter(
            ContractParty.id == party_id,
            ContractParty.company_id == company_id,
            ContractParty.deleted_at.is_(None),
        ).first()

    @staticmethod
    def get_party_by_counterparty_id(company_id: int, counterparty_id: int) -> Optional[ContractParty]:
        ContractService.sync_parties_from_counterparties(company_id)
        return ContractParty.query.filter(
            ContractParty.company_id == company_id,
            ContractParty.financial_counterparty_id == counterparty_id,
            ContractParty.deleted_at.is_(None),
        ).first()

    @staticmethod
    def get_contract(company_id: int, contract_id: int) -> Optional[Contract]:
        return Contract.query.filter(
            Contract.id == contract_id,
            Contract.company_id == company_id,
            Contract.deleted_at.is_(None),
        ).first()

    @staticmethod
    def get_tab_registry() -> list[dict]:
        return [dict(item) for item in ContractService.TAB_REGISTRY]

    @staticmethod
    def create_contracting_legal_entity(*, company_id: int, payload: dict):
        entity = ContractingLegalEntity(
            company_id=company_id,
            code=ContractService._normalize_text(payload.get("code")) or ContractService._next_structured_code(ContractingLegalEntity, company_id, "J"),
            is_active=True,
        )
        ContractService.update_contracting_legal_entity(entity=entity, payload=payload, is_new=True)
        db.session.add(entity)
        db.session.commit()
        return entity

    @staticmethod
    def update_contracting_legal_entity(*, entity: ContractingLegalEntity, payload: dict, is_new: bool = False):
        legal_name = ContractService._normalize_text(payload.get("legal_name"))
        cnpj = ContractService._normalize_text(payload.get("cnpj"))
        if legal_name:
            entity.legal_name = legal_name
        if cnpj:
            entity.cnpj = cnpj
        entity.trade_name = ContractService._normalize_text(payload.get("trade_name")) or None
        entity.municipal_registration = ContractService._normalize_text(payload.get("municipal_registration")) or None
        entity.state_registration = ContractService._normalize_text(payload.get("state_registration")) or None
        entity.tax_regime = ContractService._normalize_text(payload.get("tax_regime")) or None
        entity.cnae = ContractService._normalize_text(payload.get("cnae")) or None
        entity.service_city = ContractService._normalize_text(payload.get("service_city")) or None
        entity.city_code_ibge = ContractService._normalize_text(payload.get("city_code_ibge")) or None
        entity.uf = ContractService._normalize_text(payload.get("uf")) or None
        entity.zip_code = ContractService._normalize_text(payload.get("zip_code")) or None
        entity.address_line = ContractService._normalize_text(payload.get("address_line")) or None
        entity.address_number = ContractService._normalize_text(payload.get("address_number")) or None
        entity.district = ContractService._normalize_text(payload.get("district")) or None
        entity.complement = ContractService._normalize_text(payload.get("complement")) or None
        entity.email = ContractService._normalize_text(payload.get("email")) or None
        entity.phone = ContractService._normalize_text(payload.get("phone")) or None
        entity.nfs_provider = ContractService._normalize_text(payload.get("nfs_provider")) or None
        entity.integration_mode = ContractService._normalize_text(payload.get("integration_mode")) or "manual"
        entity.api_profile_id = ContractService._normalize_int(payload.get("api_profile_id"))
        entity.spreadsheet_profile_id = ContractService._normalize_int(payload.get("spreadsheet_profile_id"))
        entity.is_active = ContractService._normalize_bool(payload.get("is_active")) if payload.get("is_active") is not None else True
        if not entity.legal_name:
            raise ValueError("Informe a razão social da PJ contratada.")
        if not entity.cnpj:
            raise ValueError("Informe o CNPJ da PJ contratada.")
        if not is_new:
            db.session.commit()
        return entity

    @staticmethod
    def create_party(*, company_id: int, payload: dict, user_id: Optional[int]):
        party = ContractParty(
            company_id=company_id,
            code=ContractService._next_structured_code(ContractParty, company_id, "F"),
            created_by_user_id=user_id,
        )
        ContractService.update_party(party=party, payload=payload, user_id=user_id, is_new=True)
        db.session.add(party)
        db.session.commit()
        return party

    @staticmethod
    def update_party(*, party: ContractParty, payload: dict, user_id: Optional[int], is_new: bool = False):
        name = ContractService._normalize_text(payload.get("name"))
        if name:
            party.name = name
        party.legal_name = ContractService._normalize_text(payload.get("legal_name")) or None
        party.document_type = ContractService._normalize_text(payload.get("document_type")) or None
        party.document_number = ContractService._normalize_text(payload.get("document_number")) or None
        party.email = ContractService._normalize_text(payload.get("email")) or None
        party.phone = ContractService._normalize_text(payload.get("phone")) or None
        party.is_customer = ContractService._normalize_bool(payload.get("is_customer"))
        party.is_supplier = ContractService._normalize_bool(payload.get("is_supplier"))
        party.status = ContractService._normalize_text(payload.get("status")) or "active"
        party.notes = ContractService._normalize_text(payload.get("notes")) or None
        party.financial_counterparty_id = ContractService._normalize_int(payload.get("financial_counterparty_id"))
        party.updated_by_user_id = user_id
        if not party.is_customer and not party.is_supplier:
            raise ValueError("Selecione ao menos uma classificação: Cliente, Fornecedor ou ambos.")
        if not is_new:
            db.session.commit()
        return party

    @staticmethod
    def create_contract(*, company_id: int, payload: dict, user_id: Optional[int]) -> Contract:
        title = ContractService._normalize_text(payload.get("title"))
        party_id = ContractService._normalize_int(payload.get("party_id"))
        if not title:
            raise ValueError("Informe o título do contrato.")
        if not party_id:
            raise ValueError("Selecione o cliente do contrato.")
        contract = Contract(
            company_id=company_id,
            code=ContractService._next_structured_code(Contract, company_id, "N"),
            title=title,
            party_id=party_id,
            status="draft",
            currency_code="BRL",
            created_by_user_id=user_id,
            version=1,
        )
        ContractService.update_contract_general(contract=contract, payload=payload, user_id=user_id, is_new=True)
        db.session.add(contract)
        db.session.flush()
        ContractService.record_event(
            contract=contract,
            event_type="contract.created",
            description="Contrato criado.",
            payload={"status": contract.status, "party_id": contract.party_id, "title": contract.title},
            user_id=user_id,
            auto_commit=False,
        )
        db.session.commit()
        return contract

    @staticmethod
    def update_contract_general(*, contract: Contract, payload: dict, user_id: Optional[int], is_new: bool = False):
        title = ContractService._normalize_text(payload.get("title"))
        if title:
            contract.title = title
        if "party_id" in payload:
            contract.party_id = ContractService._normalize_int(payload.get("party_id")) or contract.party_id
        if "status" in payload:
            normalized_status = ContractService._normalize_text(payload.get("status")).lower()
            if normalized_status in {"active", "inactive"}:
                contract.status = normalized_status
            elif normalized_status:
                contract.status = normalized_status
            else:
                contract.status = contract.status or "draft"
        if "contract_type" in payload:
            contract.contract_type = ContractService._normalize_text(payload.get("contract_type")) or None
        if "currency_code" in payload:
            contract.currency_code = ContractService._normalize_text(payload.get("currency_code")) or "BRL"
        if "manager_employee_id" in payload:
            contract.manager_employee_id = ContractService._normalize_int(payload.get("manager_employee_id"))
        if "contracting_legal_entity_id" in payload:
            contract.contracting_legal_entity_id = ContractService._normalize_int(payload.get("contracting_legal_entity_id"))
        if "signed_at" in payload:
            contract.signed_at = ContractService._normalize_date(payload.get("signed_at"))
        if "service_start_at" in payload:
            contract.service_start_at = ContractService._normalize_date(payload.get("service_start_at"))
        if "service_end_at" in payload:
            contract.service_end_at = ContractService._normalize_date(payload.get("service_end_at"))
        if "billing_start_at" in payload:
            contract.billing_start_at = ContractService._normalize_date(payload.get("billing_start_at"))
        if "billing_end_at" in payload:
            contract.billing_end_at = ContractService._normalize_date(payload.get("billing_end_at"))
        if "last_billing_at" in payload:
            contract.last_billing_at = ContractService._normalize_date(payload.get("last_billing_at"))
        if "renewal_date" in payload:
            contract.renewal_date = ContractService._normalize_date(payload.get("renewal_date"))
        if "adjustment_date" in payload:
            contract.adjustment_date = ContractService._normalize_date(payload.get("adjustment_date"))
        if "termination_date" in payload:
            contract.termination_date = ContractService._normalize_date(payload.get("termination_date"))
        if "periodicity" in payload:
            contract.periodicity = ContractService._normalize_text(payload.get("periodicity")) or None
        if "competence_rule" in payload:
            contract.competence_rule = ContractService._normalize_text(payload.get("competence_rule")) or None
        if "due_rule" in payload:
            contract.due_rule = ContractService._normalize_text(payload.get("due_rule")) or None
        if "renewal_rule" in payload:
            contract.renewal_rule = ContractService._normalize_text(payload.get("renewal_rule")) or None
        if "end_reason" in payload:
            contract.end_reason = ContractService._normalize_text(payload.get("end_reason")) or None
        if "previous_contract_id" in payload:
            contract.previous_contract_id = ContractService._normalize_int(payload.get("previous_contract_id"))
        if "notes" in payload:
            contract.notes = ContractService._normalize_text(payload.get("notes")) or None
        contract.status = contract.status or "draft"
        contract.currency_code = contract.currency_code or "BRL"
        contract.updated_by_user_id = user_id
        if not is_new:
            ContractService.record_event(
                contract=contract,
                event_type="contract.summary_updated",
                description="Resumo do contrato atualizado.",
                payload=ContractService._build_contract_snapshot(contract),
                user_id=user_id,
                auto_commit=False,
            )
            db.session.commit()
        return contract

    @staticmethod
    def update_contract_summary(*, contract: Contract, payload: dict, user_id: Optional[int]):
        return ContractService.update_contract_general(contract=contract, payload=payload, user_id=user_id)

    @staticmethod
    def update_contract_customer(*, contract: Contract, payload: dict, user_id: Optional[int]):
        party_id = ContractService._normalize_int(payload.get("party_id"))
        if not party_id:
            raise ValueError("Selecione um favorecido cliente para o contrato.")
        contract.party_id = party_id
        contract.updated_by_user_id = user_id
        db.session.commit()
        return contract

    @staticmethod
    def update_contract_schedule(*, contract: Contract, payload: dict, user_id: Optional[int]):
        schedule_payload = {
            "signed_at": payload.get("signed_at"),
            "service_start_at": payload.get("service_start_at"),
            "service_end_at": payload.get("service_end_at"),
            "billing_start_at": payload.get("billing_start_at"),
            "billing_end_at": payload.get("billing_end_at"),
            "last_billing_at": payload.get("last_billing_at"),
            "renewal_date": payload.get("renewal_date"),
            "adjustment_date": payload.get("adjustment_date"),
            "termination_date": payload.get("termination_date"),
            "periodicity": payload.get("periodicity"),
            "competence_rule": payload.get("competence_rule"),
            "due_rule": payload.get("due_rule"),
            "renewal_rule": payload.get("renewal_rule"),
            "end_reason": payload.get("end_reason"),
        }
        return ContractService.update_contract_general(contract=contract, payload=schedule_payload, user_id=user_id)

    @staticmethod
    def update_contract_notes(*, contract: Contract, payload: dict, user_id: Optional[int]):
        updated_contract = ContractService.update_contract_general(
            contract=contract,
            payload={"notes": payload.get("notes")},
            user_id=user_id,
        )
        note_text = ContractService._normalize_text(payload.get("notes"))
        if note_text:
            ContractService.add_contract_note(
                contract=contract,
                payload={"note_type": "general", "note_text": note_text},
                user_id=user_id,
                auto_commit=True,
            )
        return updated_contract

    @staticmethod
    def update_contract_validation(*, contract: Contract, payload: dict, user_id: Optional[int]):
        metadata = dict(contract.metadata_json or {})
        metadata["validation_status"] = ContractService._normalize_text(payload.get("validation_status")) or "pending"
        metadata["validation_notes"] = ContractService._normalize_text(payload.get("validation_notes")) or None
        metadata["last_validation_user_id"] = user_id
        metadata["last_validation_at"] = datetime.utcnow().isoformat()
        contract.metadata_json = metadata
        contract.updated_by_user_id = user_id
        ContractService.record_event(
            contract=contract,
            event_type="contract.validation_updated",
            description="Status de validação do contrato atualizado.",
            payload={"validation_status": metadata["validation_status"]},
            user_id=user_id,
            auto_commit=False,
        )
        db.session.commit()
        return contract

    @staticmethod
    def _build_contract_snapshot(contract: Contract) -> dict:
        return {
            "status": contract.status,
            "party_id": contract.party_id,
            "title": contract.title,
            "manager_employee_id": contract.manager_employee_id,
            "renewal_date": contract.renewal_date.isoformat() if contract.renewal_date else None,
            "adjustment_date": contract.adjustment_date.isoformat() if contract.adjustment_date else None,
            "termination_date": contract.termination_date.isoformat() if contract.termination_date else None,
            "previous_contract_id": contract.previous_contract_id,
        }

    @staticmethod
    def record_event(
        *,
        contract: Contract,
        event_type: str,
        description: Optional[str] = None,
        payload: Optional[dict] = None,
        user_id: Optional[int] = None,
        auto_commit: bool = True,
    ) -> ContractEvent:
        event = ContractEvent(
            company_id=contract.company_id,
            contract_id=contract.id,
            event_type=event_type,
            description=description,
            event_payload=payload or {},
            created_by_user_id=user_id,
        )
        db.session.add(event)
        if auto_commit:
            db.session.commit()
        return event

    @staticmethod
    def list_contract_history(contract: Contract) -> dict:
        return {
            "clauses": contract.clauses.order_by(ContractClause.order_index.asc(), ContractClause.id.asc()).all(),
            "notes": contract.notes_log.order_by(ContractNote.created_at.desc(), ContractNote.id.desc()).all(),
            "events": contract.events.order_by(ContractEvent.created_at.desc(), ContractEvent.id.desc()).all(),
        }

    @staticmethod
    def upsert_contract_clause(*, contract: Contract, payload: dict, user_id: Optional[int], clause_id: Optional[int] = None):
        clause = None
        if clause_id:
            clause = ContractClause.query.filter(
                ContractClause.id == clause_id,
                ContractClause.contract_id == contract.id,
                ContractClause.company_id == contract.company_id,
            ).first()
        if clause is None:
            clause = ContractClause(
                company_id=contract.company_id,
                contract_id=contract.id,
                created_by_user_id=user_id,
            )
            db.session.add(clause)

        clause.clause_type = ContractService._normalize_text(payload.get("clause_type")) or "general"
        clause.title = ContractService._normalize_text(payload.get("title")) or None
        clause.content = ContractService._normalize_text(payload.get("content")) or "Cláusula sem conteúdo."
        clause.order_index = ContractService._normalize_int(payload.get("order_index")) or 0
        clause.updated_by_user_id = user_id
        ContractService.record_event(
            contract=contract,
            event_type="contract.clause_upserted",
            description=f"Cláusula {'atualizada' if clause_id else 'criada'}.",
            payload={"clause_type": clause.clause_type, "title": clause.title},
            user_id=user_id,
            auto_commit=False,
        )
        db.session.commit()
        return clause

    @staticmethod
    def delete_contract_clause(*, contract: Contract, clause_id: int, user_id: Optional[int]):
        clause = ContractClause.query.filter(
            ContractClause.id == clause_id,
            ContractClause.contract_id == contract.id,
            ContractClause.company_id == contract.company_id,
        ).first()
        if not clause:
            raise ValueError("Cláusula não encontrada para este contrato.")
        db.session.delete(clause)
        ContractService.record_event(
            contract=contract,
            event_type="contract.clause_deleted",
            description="Cláusula removida do contrato.",
            payload={"clause_id": clause_id},
            user_id=user_id,
            auto_commit=False,
        )
        db.session.commit()

    @staticmethod
    def add_contract_note(*, contract: Contract, payload: dict, user_id: Optional[int], auto_commit: bool = True):
        note_text = ContractService._normalize_text(payload.get("note_text"))
        if not note_text:
            raise ValueError("Informe um texto para registrar a observação do contrato.")
        note = ContractNote(
            company_id=contract.company_id,
            contract_id=contract.id,
            note_type=ContractService._normalize_text(payload.get("note_type")) or "general",
            note_text=note_text,
            created_by_user_id=user_id,
        )
        db.session.add(note)
        ContractService.record_event(
            contract=contract,
            event_type="contract.note_added",
            description="Observação adicionada ao contrato.",
            payload={"note_type": note.note_type},
            user_id=user_id,
            auto_commit=False,
        )
        if auto_commit:
            db.session.commit()
        return note

    @staticmethod
    def add_contract_item(*, contract: Contract, payload: dict):
        catalog_item_id = ContractService._normalize_int(payload.get("contract_catalog_item_id"))
        catalog_item = None
        if catalog_item_id:
            catalog_item = ContractCatalogItem.query.filter(
                ContractCatalogItem.id == catalog_item_id,
                ContractCatalogItem.company_id == contract.company_id,
                ContractCatalogItem.deleted_at.is_(None),
            ).first()
            if not catalog_item:
                raise ValueError("Item mestre não encontrado para este contrato.")
            if not ContractsCatalogService._is_selectable_level(catalog_item):
                raise ValueError("Somente itens do catálogo podem ser utilizados no contrato.")

        description = ContractService._normalize_text(payload.get("description")) or (catalog_item.name if catalog_item else "Item contratual")
        item_code = ContractService._normalize_text(payload.get("item_code")) or (catalog_item.code if catalog_item else None)
        item_type = ContractService._normalize_text(payload.get("item_type")) or (catalog_item.item_kind if catalog_item else None)
        unit_code = ContractService._normalize_text(payload.get("unit_code")) or (catalog_item.unit_code if catalog_item else None)
        metadata = dict(payload.get("metadata_json") or {})
        if catalog_item:
            metadata["contract_catalog_item_id"] = catalog_item.id
            metadata["catalog_snapshot"] = {
                "code": catalog_item.code,
                "name": catalog_item.name,
                "item_kind": catalog_item.item_kind,
                "unit_code": catalog_item.unit_code,
            }

        item = ContractItem(
            company_id=contract.company_id,
            contract_id=contract.id,
            contract_catalog_item_id=catalog_item.id if catalog_item else None,
            item_code=item_code,
            item_type=item_type,
            description=description,
            quantity=ContractService._normalize_decimal(payload.get("quantity"), default="1"),
            unit_code=unit_code,
            unit_price=ContractService._normalize_decimal(payload.get("unit_price")),
            total_price=ContractService.calculate_total_price(payload.get("quantity"), payload.get("unit_price")),
            order_index=ContractService._normalize_int(payload.get("order_index")) or 0,
            notes=ContractService._normalize_text(payload.get("notes")) or None,
            metadata_json=metadata,
        )
        db.session.add(item)
        db.session.commit()
        return item

    @staticmethod
    def delete_contract_item(*, contract: Contract, item_id: int) -> bool:
        item = ContractItem.query.filter_by(id=item_id, company_id=contract.company_id, contract_id=contract.id).first()
        if not item:
            return False
        db.session.delete(item)
        db.session.commit()
        return True

    @staticmethod
    def add_billing_item(*, contract: Contract, payload: dict):
        item = ContractBillingItem(
            company_id=contract.company_id,
            contract_id=contract.id,
            contract_item_id=ContractService._normalize_int(payload.get("contract_item_id")),
            billing_code=ContractService._normalize_text(payload.get("billing_code")) or None,
            description=ContractService._normalize_text(payload.get("description")) or "Item de faturamento",
            amount=ContractService._normalize_decimal(payload.get("amount")),
            billing_periodicity=ContractService._normalize_text(payload.get("billing_periodicity")) or None,
            competence_rule=ContractService._normalize_text(payload.get("competence_rule")) or None,
            due_rule=ContractService._normalize_text(payload.get("due_rule")) or None,
            trigger_type=ContractService._normalize_text(payload.get("trigger_type")) or None,
            trigger_reference_date=ContractService._normalize_text(payload.get("trigger_reference_date")) or None,
            is_recurring=ContractService._normalize_bool(payload.get("is_recurring")),
            order_index=ContractService._normalize_int(payload.get("order_index")) or 0,
        )
        db.session.add(item)
        db.session.commit()
        return item

    @staticmethod
    def build_native_billing_idempotency_key(*, contract: Contract, competence_start: date, competence_end: date) -> str:
        return f"contract:{contract.company_id}:{contract.id}:{competence_start.isoformat()}:{competence_end.isoformat()}"

    @staticmethod
    def list_native_billings(contract: Contract):
        return contract.native_billings.order_by(ContractNativeBilling.competence_start.desc(), ContractNativeBilling.id.desc()).all()

    @staticmethod
    def preview_native_billing(contract: Contract, payload: dict) -> dict:
        competence_start = ContractService._normalize_date(payload.get("competence_start")) or contract.billing_start_at or date.today()
        competence_end = ContractService._normalize_date(payload.get("competence_end")) or competence_start
        issue_date = ContractService._normalize_date(payload.get("issue_date")) or date.today()
        due_date = ContractService._normalize_date(payload.get("due_date")) or ContractService.resolve_due_date(issue_date=issue_date, due_rule=contract.due_rule)
        items = contract.billing_items.order_by(ContractBillingItem.order_index.asc(), ContractBillingItem.id.asc()).all()
        total_amount = sum((item.amount or Decimal("0")) for item in items)
        return {
            "competence_start": competence_start,
            "competence_end": competence_end,
            "issue_date": issue_date,
            "due_date": due_date,
            "item_count": len(items),
            "gross_amount": total_amount.quantize(Decimal("0.01")) if items else Decimal("0.00"),
        }

    @staticmethod
    def build_contract_fiscal_snapshot(contract: Contract) -> dict:
        fiscal_terms = ContractFiscalTerm.query.filter_by(contract_id=contract.id, company_id=contract.company_id).first()
        legal_entity = None
        if fiscal_terms and fiscal_terms.contracting_legal_entity_id:
            legal_entity = ContractService.get_contracting_legal_entity(contract.company_id, fiscal_terms.contracting_legal_entity_id)
        if legal_entity is None and contract.contracting_legal_entity_id:
            legal_entity = ContractService.get_contracting_legal_entity(contract.company_id, contract.contracting_legal_entity_id)
        return {
            "contracting_legal_entity_id": legal_entity.id if legal_entity else None,
            "issuer_legal_name": legal_entity.legal_name if legal_entity else None,
            "issuer_trade_name": legal_entity.trade_name if legal_entity else None,
            "issuer_cnpj": legal_entity.cnpj if legal_entity else None,
            "issuer_municipal_registration": legal_entity.municipal_registration if legal_entity else None,
            "issuer_tax_regime": legal_entity.tax_regime if legal_entity else None,
            "integration_mode": (fiscal_terms.integration_mode if fiscal_terms else None) or (legal_entity.integration_mode if legal_entity else None),
            "nfs_provider": (fiscal_terms.nfs_provider if fiscal_terms else None) or (legal_entity.nfs_provider if legal_entity else None),
            "default_rps_series": fiscal_terms.default_rps_series if fiscal_terms else None,
            "service_code": fiscal_terms.service_code if fiscal_terms else None,
            "service_list_item": fiscal_terms.service_list_item if fiscal_terms else None,
            "operation_nature": fiscal_terms.operation_nature if fiscal_terms else None,
            "service_city": fiscal_terms.service_city if fiscal_terms else (legal_entity.service_city if legal_entity else None),
            "iss_city": fiscal_terms.iss_city if fiscal_terms else None,
            "withholding_flags": (fiscal_terms.withholding_flags if fiscal_terms else None) or {},
            "fiscal_notes": fiscal_terms.notes if fiscal_terms else None,
        }

    @staticmethod
    def build_native_billing_fiscal_export_payload(native_billing: ContractNativeBilling) -> dict:
        contract = native_billing.contract
        snapshot = dict((native_billing.metadata_json or {}).get("fiscal_snapshot") or {})
        if not snapshot:
            snapshot = ContractService.build_contract_fiscal_snapshot(contract)
        return {
            "billing_code": native_billing.billing_code,
            "contract_code": contract.code if contract else None,
            "customer_name": contract.party.name if contract and contract.party else None,
            "customer_document": contract.party.document_number if contract and contract.party else None,
            "issuer_cnpj": snapshot.get("issuer_cnpj"),
            "issuer_legal_name": snapshot.get("issuer_legal_name"),
            "integration_mode": snapshot.get("integration_mode"),
            "nfs_provider": snapshot.get("nfs_provider"),
            "service_code": snapshot.get("service_code"),
            "service_list_item": snapshot.get("service_list_item"),
            "operation_nature": snapshot.get("operation_nature"),
            "service_city": snapshot.get("service_city"),
            "iss_city": snapshot.get("iss_city"),
            "issue_date": native_billing.issue_date.isoformat() if native_billing.issue_date else None,
            "gross_amount": float(native_billing.gross_amount or 0),
            "net_amount": float(native_billing.net_amount or 0),
            "withholding_flags": snapshot.get("withholding_flags") or {},
            "items": [
                {
                    "description": item.description,
                    "amount": float(item.amount or 0),
                }
                for item in native_billing.items.order_by(ContractNativeBillingItem.id.asc()).all()
            ],
        }

    @staticmethod
    def generate_native_billing(*, contract: Contract, payload: dict, user_id: Optional[int]):
        if not contract.party_id:
            raise ValueError("Defina o cliente do contrato antes de gerar o faturamento nativo.")

        preview = ContractService.preview_native_billing(contract, payload)
        competence_start = preview["competence_start"]
        competence_end = preview["competence_end"]
        issue_date = preview["issue_date"]
        due_date = preview["due_date"]
        billing_items = contract.billing_items.order_by(ContractBillingItem.order_index.asc(), ContractBillingItem.id.asc()).all()

        if not billing_items:
            raise ValueError("Cadastre ao menos um item de faturamento nativo antes de gerar a competência.")

        fiscal_snapshot = ContractService.build_contract_fiscal_snapshot(contract)

        idempotency_key = ContractService.build_native_billing_idempotency_key(
            contract=contract,
            competence_start=competence_start,
            competence_end=competence_end,
        )
        existing = ContractNativeBilling.query.filter_by(
            company_id=contract.company_id,
            idempotency_key=idempotency_key,
        ).first()
        if existing and existing.status != "cancelled":
            raise ValueError("Já existe faturamento nativo gerado para esta competência.")

        native_billing = ContractNativeBilling(
            company_id=contract.company_id,
            contract_id=contract.id,
            party_id=contract.party_id,
            billing_code=ContractService._next_structured_code(ContractNativeBilling, contract.company_id, "B"),
            status="generated",
            source_type="native_contract",
            competence_start=competence_start,
            competence_end=competence_end,
            issue_date=issue_date,
            due_date=due_date,
            gross_amount=preview["gross_amount"],
            net_amount=preview["gross_amount"],
            idempotency_key=idempotency_key,
            generated_by_user_id=user_id,
            metadata_json={
                "contract_version": contract.version,
                "generated_from": "contract_native_module",
                "item_count": len(billing_items),
                "fiscal_snapshot": fiscal_snapshot,
            },
        )
        db.session.add(native_billing)
        db.session.flush()

        for item in billing_items:
            db.session.add(
                ContractNativeBillingItem(
                    company_id=contract.company_id,
                    contract_native_billing_id=native_billing.id,
                    contract_billing_item_id=item.id,
                    contract_item_id=item.contract_item_id,
                    description=item.description,
                    amount=item.amount,
                    competence_rule=item.competence_rule,
                    due_rule=item.due_rule,
                    trigger_type=item.trigger_type,
                    trigger_reference_date=item.trigger_reference_date,
                    metadata_json={
                        "billing_periodicity": item.billing_periodicity,
                        "is_recurring": item.is_recurring,
                    },
                )
            )

        contract.last_billing_at = issue_date
        contract.updated_by_user_id = user_id
        ContractService.record_event(
            contract=contract,
            event_type="contract.billing_generated",
            description="Faturamento nativo gerado a partir do contrato.",
            payload={
                "native_billing_id": native_billing.id,
                "billing_code": native_billing.billing_code,
                "competence_start": competence_start.isoformat(),
                "competence_end": competence_end.isoformat(),
                "gross_amount": float(native_billing.gross_amount or 0),
                "idempotency_key": idempotency_key,
            },
            user_id=user_id,
            auto_commit=False,
        )
        from services.contract_financial_service import ContractFinancialService

        ContractFinancialService.ensure_financial_titles_for_native_billing(
            contract=contract,
            native_billing=native_billing,
            user_id=user_id,
            auto_commit=False,
        )
        db.session.commit()
        return native_billing

    @staticmethod
    def delete_billing_item(*, contract: Contract, item_id: int) -> bool:
        item = ContractBillingItem.query.filter_by(id=item_id, company_id=contract.company_id, contract_id=contract.id).first()
        if not item:
            return False
        db.session.delete(item)
        db.session.commit()
        return True

    @staticmethod
    def upsert_financial_terms(*, contract: Contract, payload: dict, user_id: Optional[int] = None):
        record = ContractFinancialTerm.query.filter_by(contract_id=contract.id, company_id=contract.company_id).first()
        if not record:
            record = ContractFinancialTerm(company_id=contract.company_id, contract_id=contract.id)
            db.session.add(record)
        record.default_bank_account_id = ContractService._normalize_int(payload.get("default_bank_account_id"))
        record.default_payment_method_id = ContractService._normalize_int(payload.get("default_payment_method_id"))
        record.default_chart_account_id = ContractService._normalize_int(payload.get("default_chart_account_id"))
        record.default_cost_center_id = ContractService._normalize_int(payload.get("default_cost_center_id"))
        record.correction_index_id = ContractService._normalize_int(payload.get("correction_index_id"))
        record.payment_term_type = ContractService._normalize_text(payload.get("payment_term_type")) or None
        record.payment_term_days = ContractService._normalize_int(payload.get("payment_term_days"))
        record.billing_method = ContractService._normalize_text(payload.get("billing_method")) or None
        record.pricing_model = ContractService._normalize_text(payload.get("pricing_model")) or None
        record.adjustment_rule = ContractService._normalize_text(payload.get("adjustment_rule")) or None
        record.notes = ContractService._normalize_text(payload.get("notes")) or None
        record.metadata_json = {
            **(record.metadata_json or {}),
            "updated_by_user_id": user_id,
            "financial_defaults": {
                "bank_account_id": record.default_bank_account_id,
                "payment_method_id": record.default_payment_method_id,
                "chart_account_id": record.default_chart_account_id,
                "cost_center_id": record.default_cost_center_id,
                "correction_index_id": record.correction_index_id,
            },
        }
        ContractService.record_event(
            contract=contract,
            event_type="contract.financial_terms_updated",
            description="Condições financeiras do contrato atualizadas.",
            payload={
                "default_bank_account_id": record.default_bank_account_id,
                "default_chart_account_id": record.default_chart_account_id,
                "default_cost_center_id": record.default_cost_center_id,
            },
            user_id=user_id,
            auto_commit=False,
        )
        db.session.commit()
        return record

    @staticmethod
    def upsert_fiscal_terms(*, contract: Contract, payload: dict, user_id: Optional[int] = None):
        record = ContractFiscalTerm.query.filter_by(contract_id=contract.id, company_id=contract.company_id).first()
        if not record:
            record = ContractFiscalTerm(company_id=contract.company_id, contract_id=contract.id)
            db.session.add(record)
        legal_entity_id = ContractService._normalize_int(payload.get("contracting_legal_entity_id")) or contract.contracting_legal_entity_id
        if not legal_entity_id:
            raise ValueError("Selecione a PJ contratada que também emitirá a nota fiscal.")

        legal_entity = ContractService.get_contracting_legal_entity(contract.company_id, legal_entity_id)
        if not legal_entity:
            raise ValueError("PJ contratada inválida para a empresa ativa.")

        legal_entity.municipal_registration = ContractService._normalize_text(payload.get("issuer_municipal_registration")) or legal_entity.municipal_registration
        legal_entity.tax_regime = ContractService._normalize_text(payload.get("issuer_tax_regime")) or legal_entity.tax_regime
        legal_entity.service_city = ContractService._normalize_text(payload.get("issuer_service_city")) or legal_entity.service_city
        legal_entity.nfs_provider = ContractService._normalize_text(payload.get("nfs_provider")) or legal_entity.nfs_provider
        legal_entity.integration_mode = ContractService._normalize_text(payload.get("integration_mode")) or legal_entity.integration_mode or "manual"
        legal_entity.api_profile_id = ContractService._normalize_int(payload.get("api_profile_id")) or legal_entity.api_profile_id
        legal_entity.spreadsheet_profile_id = ContractService._normalize_int(payload.get("spreadsheet_profile_id")) or legal_entity.spreadsheet_profile_id

        integration_mode = legal_entity.integration_mode or "manual"
        api_profile_id = ContractService._normalize_int(payload.get("api_profile_id")) or legal_entity.api_profile_id
        spreadsheet_profile_id = ContractService._normalize_int(payload.get("spreadsheet_profile_id")) or legal_entity.spreadsheet_profile_id
        if integration_mode == "api" and not api_profile_id:
            raise ValueError("Selecione o perfil de API da emissão fiscal.")
        if integration_mode == "spreadsheet" and not spreadsheet_profile_id:
            raise ValueError("Selecione o perfil de planilha da emissão fiscal.")

        withholding_flags = {
            "iss_withheld": ContractService._normalize_bool(payload.get("iss_withheld")),
            "inss_withheld": ContractService._normalize_bool(payload.get("inss_withheld")),
            "irrf_withheld": ContractService._normalize_bool(payload.get("irrf_withheld")),
            "pis_withheld": ContractService._normalize_bool(payload.get("pis_withheld")),
            "cofins_withheld": ContractService._normalize_bool(payload.get("cofins_withheld")),
            "csll_withheld": ContractService._normalize_bool(payload.get("csll_withheld")),
        }

        contract.contracting_legal_entity_id = legal_entity.id
        contract.updated_by_user_id = user_id
        record.contracting_legal_entity_id = legal_entity.id
        record.fiscal_profile_code = ContractService._normalize_text(payload.get("fiscal_profile_code")) or None
        record.integration_mode = integration_mode
        record.nfs_provider = ContractService._normalize_text(payload.get("nfs_provider")) or legal_entity.nfs_provider or None
        record.default_rps_series = ContractService._normalize_text(payload.get("default_rps_series")) or None
        record.service_code = ContractService._normalize_text(payload.get("service_code")) or None
        record.service_list_item = ContractService._normalize_text(payload.get("service_list_item")) or None
        record.operation_nature = ContractService._normalize_text(payload.get("operation_nature")) or None
        record.service_city = ContractService._normalize_text(payload.get("service_city")) or legal_entity.service_city or None
        record.iss_city = ContractService._normalize_text(payload.get("iss_city")) or record.service_city
        record.tax_nature = ContractService._normalize_text(payload.get("tax_nature")) or None
        record.api_profile_id = api_profile_id
        record.spreadsheet_profile_id = spreadsheet_profile_id
        record.withholding_flags = withholding_flags
        record.tax_observation = ContractService._normalize_text(payload.get("tax_observation")) or None
        record.notes = ContractService._normalize_text(payload.get("notes")) or None
        if not record.service_code:
            raise ValueError("Informe o código do serviço da nota fiscal.")
        if not record.service_list_item:
            raise ValueError("Informe o item da lista de serviço.")
        if not record.operation_nature:
            raise ValueError("Informe a natureza da operação fiscal.")
        record.metadata_json = {
            **(record.metadata_json or {}),
            "issuer_cnpj": legal_entity.cnpj,
            "issuer_legal_name": legal_entity.legal_name,
            "compliance_rule": "contracting_legal_entity_equals_nf_issuer",
        }
        ContractService.record_event(
            contract=contract,
            event_type="contract.fiscal_config_updated",
            description="Configuração fiscal do contrato atualizada com PJ contratada vinculada à emissão.",
            payload={
                "contracting_legal_entity_id": legal_entity.id,
                "integration_mode": integration_mode,
                "service_code": record.service_code,
                "service_list_item": record.service_list_item,
            },
            user_id=user_id,
            auto_commit=False,
        )
        db.session.commit()
        return record

    @staticmethod
    def add_retention(*, contract: Contract, payload: dict):
        retention = ContractRetention(
            company_id=contract.company_id,
            contract_id=contract.id,
            retention_type=ContractService._normalize_text(payload.get("retention_type")) or "retencao",
            calculation_mode=ContractService._normalize_text(payload.get("calculation_mode")) or None,
            rate_percent=ContractService._normalize_decimal(payload.get("rate_percent")),
            fixed_amount=ContractService._normalize_decimal(payload.get("fixed_amount")),
            notes=ContractService._normalize_text(payload.get("notes")) or None,
        )
        db.session.add(retention)
        db.session.commit()
        return retention

    @staticmethod
    def delete_retention(*, contract: Contract, retention_id: int) -> bool:
        retention = ContractRetention.query.filter_by(id=retention_id, company_id=contract.company_id, contract_id=contract.id).first()
        if not retention:
            return False
        db.session.delete(retention)
        db.session.commit()
        return True

    @staticmethod
    def add_trigger(*, contract: Contract, payload: dict):
        trigger = ContractTrigger(
            company_id=contract.company_id,
            contract_id=contract.id,
            trigger_type=ContractService._normalize_text(payload.get("trigger_type")) or "alert",
            reference_date_type=ContractService._normalize_text(payload.get("reference_date_type")) or None,
            reference_date_value=ContractService._normalize_date(payload.get("reference_date_value")),
            offset_days=ContractService._normalize_int(payload.get("offset_days")),
            periodicity=ContractService._normalize_text(payload.get("periodicity")) or None,
            alert_before_days=ContractService._normalize_int(payload.get("alert_before_days")),
            is_active=ContractService._normalize_bool(payload.get("is_active")) if payload.get("is_active") not in (None, "") else True,
        )
        db.session.add(trigger)
        db.session.commit()
        return trigger

    @staticmethod
    def delete_trigger(*, contract: Contract, trigger_id: int) -> bool:
        trigger = ContractTrigger.query.filter_by(id=trigger_id, company_id=contract.company_id, contract_id=contract.id).first()
        if not trigger:
            return False
        db.session.delete(trigger)
        db.session.commit()
        return True

    @staticmethod
    def save_document(*, contract: Contract, document_type: str, document_version: str, is_signed_version: bool, file: Optional[FileStorage], uploaded_by_user_id: Optional[int]):
        if file is None or not file.filename:
            raise ValueError("Selecione um arquivo para anexar ao contrato.")
        safe_name = secure_filename(file.filename)
        if not safe_name:
            raise ValueError("Nome de arquivo inválido.")
        relative_dir = Path("contracts") / f"company_{contract.company_id}" / f"contract_{contract.id}"
        target_dir = Path(current_app.config["UPLOAD_FOLDER"]) / relative_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        final_name = f"{uuid4().hex}_{safe_name}"
        target_path = target_dir / final_name
        file.save(target_path)
        record = ContractDocument(
            company_id=contract.company_id,
            contract_id=contract.id,
            document_type=ContractService._normalize_text(document_type) or "documento",
            file_name=safe_name,
            file_path=str((relative_dir / final_name).as_posix()),
            mime_type=file.mimetype,
            document_version=ContractService._normalize_text(document_version) or None,
            source="manual",
            is_signed_version=bool(is_signed_version),
            uploaded_by_user_id=uploaded_by_user_id,
        )
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def delete_document(*, contract: Contract, document_id: int) -> bool:
        document = ContractDocument.query.filter_by(id=document_id, company_id=contract.company_id, contract_id=contract.id).first()
        if not document:
            return False
        file_path = Path(current_app.config["UPLOAD_FOLDER"]) / str(document.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass
        db.session.delete(document)
        db.session.commit()
        return True
