from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from models import Company, db
from models.contracts import (
    Contract,
    ContractBillingItem,
    ContractDocument,
    ContractFinancialTerm,
    ContractFiscalTerm,
    ContractItem,
    ContractParty,
    ContractRetention,
    ContractTrigger,
)
from models.financial import (
    FinancialBankAccount,
    FinancialCorrectionIndex,
    FinancialCounterparty,
    FinancialPaymentMethod,
)


class ContractService:
    TAB_REGISTRY = (
        {"key": "resumo", "label": "Resumo", "scope": "core", "description": "Dados centrais do contrato."},
        {"key": "cliente", "label": "Cliente", "scope": "core", "description": "Favorecido cliente vinculado ao contrato."},
        {"key": "itens", "label": "Itens do Contrato", "scope": "core", "description": "Escopo, serviços e itens negociados."},
        {"key": "faturamento", "label": "Itens de Faturamento", "scope": "core", "description": "Itens e regras de faturamento."},
        {"key": "periodicidade", "label": "Periodicidade", "scope": "core", "description": "Datas-base, competência, vencimento e gatilhos."},
        {"key": "fiscal", "label": "Fiscal", "scope": "core", "description": "Perfil fiscal e retenções."},
        {"key": "cobranca", "label": "Cobrança", "scope": "core", "description": "Condições financeiras e de cobrança."},
        {"key": "observacoes", "label": "Observações", "scope": "core", "description": "Contexto operacional e observações livres."},
        {"key": "revisao", "label": "Revisão", "scope": "core", "description": "Checklist de consistência do cadastro."},
        {"key": "validar", "label": "Validar / Editar Contrato", "scope": "capability", "description": "Aprovação operacional e ajustes finais."},
        {"key": "gerar_pdf", "label": "Gerar PDF", "scope": "capability", "description": "Upload/controle da versão em PDF."},
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
    def calculate_total_price(quantity: object, unit_price: object) -> Decimal:
        qty = ContractService._normalize_decimal(quantity)
        price = ContractService._normalize_decimal(unit_price)
        return (qty * price).quantize(Decimal("0.01"))

    @staticmethod
    def _next_code(model, company_id: int, prefix: str) -> str:
        last_number = 0
        rows = model.query.with_entities(model.code).filter(model.company_id == company_id).all()
        for (code,) in rows:
            match = re.search(r"(\d+)$", str(code or ""))
            if match:
                last_number = max(last_number, int(match.group(1)))
        return f"{prefix}-{last_number + 1:04d}"

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
        return (
            ContractParty.query.filter(ContractParty.company_id == company_id, ContractParty.deleted_at.is_(None))
            .order_by(ContractParty.name.asc())
            .all()
        )

    @staticmethod
    def list_customer_parties(company_id: int):
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
        return (
            Contract.query.filter(Contract.company_id == company_id, Contract.deleted_at.is_(None))
            .order_by(Contract.updated_at.desc())
            .all()
        )

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
            "correction_indexes": FinancialCorrectionIndex.query.filter(
                FinancialCorrectionIndex.company_id == company_id,
                FinancialCorrectionIndex.deleted_at.is_(None),
            ).order_by(FinancialCorrectionIndex.name.asc()).all(),
        }

    @staticmethod
    def get_party(company_id: int, party_id: int) -> Optional[ContractParty]:
        return ContractParty.query.filter(
            ContractParty.id == party_id,
            ContractParty.company_id == company_id,
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
    def create_party(*, company_id: int, payload: dict, user_id: Optional[int]):
        party = ContractParty(
            company_id=company_id,
            code=ContractService._next_code(ContractParty, company_id, "PART"),
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
        contract = Contract(
            company_id=company_id,
            code=ContractService._next_code(Contract, company_id, "CTR"),
            created_by_user_id=user_id,
            version=1,
        )
        ContractService.update_contract_general(contract=contract, payload=payload, user_id=user_id, is_new=True)
        db.session.add(contract)
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
            contract.status = ContractService._normalize_text(payload.get("status")) or contract.status or "draft"
        if "contract_type" in payload:
            contract.contract_type = ContractService._normalize_text(payload.get("contract_type")) or None
        if "currency_code" in payload:
            contract.currency_code = ContractService._normalize_text(payload.get("currency_code")) or "BRL"
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
        if "periodicity" in payload:
            contract.periodicity = ContractService._normalize_text(payload.get("periodicity")) or None
        if "competence_rule" in payload:
            contract.competence_rule = ContractService._normalize_text(payload.get("competence_rule")) or None
        if "due_rule" in payload:
            contract.due_rule = ContractService._normalize_text(payload.get("due_rule")) or None
        if "renewal_rule" in payload:
            contract.renewal_rule = ContractService._normalize_text(payload.get("renewal_rule")) or None
        if "notes" in payload:
            contract.notes = ContractService._normalize_text(payload.get("notes")) or None
        contract.updated_by_user_id = user_id
        if not is_new:
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
            "periodicity": payload.get("periodicity"),
            "competence_rule": payload.get("competence_rule"),
            "due_rule": payload.get("due_rule"),
            "renewal_rule": payload.get("renewal_rule"),
        }
        return ContractService.update_contract_general(contract=contract, payload=schedule_payload, user_id=user_id)

    @staticmethod
    def update_contract_notes(*, contract: Contract, payload: dict, user_id: Optional[int]):
        return ContractService.update_contract_general(
            contract=contract,
            payload={"notes": payload.get("notes")},
            user_id=user_id,
        )

    @staticmethod
    def update_contract_validation(*, contract: Contract, payload: dict, user_id: Optional[int]):
        metadata = dict(contract.metadata_json or {})
        metadata["validation_status"] = ContractService._normalize_text(payload.get("validation_status")) or "pending"
        metadata["validation_notes"] = ContractService._normalize_text(payload.get("validation_notes")) or None
        metadata["last_validation_user_id"] = user_id
        metadata["last_validation_at"] = datetime.utcnow().isoformat()
        contract.metadata_json = metadata
        contract.updated_by_user_id = user_id
        db.session.commit()
        return contract

    @staticmethod
    def add_contract_item(*, contract: Contract, payload: dict):
        item = ContractItem(
            company_id=contract.company_id,
            contract_id=contract.id,
            item_code=ContractService._normalize_text(payload.get("item_code")) or None,
            item_type=ContractService._normalize_text(payload.get("item_type")) or None,
            description=ContractService._normalize_text(payload.get("description")) or "Item contratual",
            quantity=ContractService._normalize_decimal(payload.get("quantity"), default="1"),
            unit_code=ContractService._normalize_text(payload.get("unit_code")) or None,
            unit_price=ContractService._normalize_decimal(payload.get("unit_price")),
            total_price=ContractService.calculate_total_price(payload.get("quantity"), payload.get("unit_price")),
            order_index=ContractService._normalize_int(payload.get("order_index")) or 0,
            notes=ContractService._normalize_text(payload.get("notes")) or None,
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
    def delete_billing_item(*, contract: Contract, item_id: int) -> bool:
        item = ContractBillingItem.query.filter_by(id=item_id, company_id=contract.company_id, contract_id=contract.id).first()
        if not item:
            return False
        db.session.delete(item)
        db.session.commit()
        return True

    @staticmethod
    def upsert_financial_terms(*, contract: Contract, payload: dict):
        record = ContractFinancialTerm.query.filter_by(contract_id=contract.id, company_id=contract.company_id).first()
        if not record:
            record = ContractFinancialTerm(company_id=contract.company_id, contract_id=contract.id)
            db.session.add(record)
        record.default_bank_account_id = ContractService._normalize_int(payload.get("default_bank_account_id"))
        record.default_payment_method_id = ContractService._normalize_int(payload.get("default_payment_method_id"))
        record.correction_index_id = ContractService._normalize_int(payload.get("correction_index_id"))
        record.payment_term_type = ContractService._normalize_text(payload.get("payment_term_type")) or None
        record.payment_term_days = ContractService._normalize_int(payload.get("payment_term_days"))
        record.billing_method = ContractService._normalize_text(payload.get("billing_method")) or None
        record.pricing_model = ContractService._normalize_text(payload.get("pricing_model")) or None
        record.adjustment_rule = ContractService._normalize_text(payload.get("adjustment_rule")) or None
        record.notes = ContractService._normalize_text(payload.get("notes")) or None
        db.session.commit()
        return record

    @staticmethod
    def upsert_fiscal_terms(*, contract: Contract, payload: dict):
        record = ContractFiscalTerm.query.filter_by(contract_id=contract.id, company_id=contract.company_id).first()
        if not record:
            record = ContractFiscalTerm(company_id=contract.company_id, contract_id=contract.id)
            db.session.add(record)
        record.fiscal_profile_code = ContractService._normalize_text(payload.get("fiscal_profile_code")) or None
        record.service_city = ContractService._normalize_text(payload.get("service_city")) or None
        record.tax_nature = ContractService._normalize_text(payload.get("tax_nature")) or None
        record.tax_observation = ContractService._normalize_text(payload.get("tax_observation")) or None
        record.notes = ContractService._normalize_text(payload.get("notes")) or None
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
