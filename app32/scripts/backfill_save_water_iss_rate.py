from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "0")
os.environ.setdefault("APP_BOOTSTRAP_DB_SCHEMA", "0")

from app import create_app  # noqa: E402
from models import db  # noqa: E402
from models.contracts import (  # noqa: E402
    Contract,
    ContractFiscalTerm,
    ContractItem,
    ContractNativeBilling,
    ContractNativeBillingItem,
    ContractingLegalEntity,
)
from models.financial import FinancialSchedule, FinancialScheduleLink  # noqa: E402
from services.contracts_service import ContractService  # noqa: E402


def _rule_payload(percent: Decimal, effective_from: date, effective_to: date | None = None) -> dict:
    return {
        "effective_from": ContractService._serialize_date(effective_from),
        "effective_to": ContractService._serialize_date(effective_to),
        "percent": ContractService._decimal_to_export_text(percent, places=4, strip_trailing=True),
    }


def _upsert_entity_iss_rule(entity: ContractingLegalEntity, percent: Decimal, effective_from: date, effective_to: date | None) -> bool:
    metadata = dict(entity.metadata_json or {})
    rules = ContractService._normalize_legal_entity_iss_rules(metadata.get("iss_rate_rules"))
    changed = False
    for rule in rules:
        if rule["effective_from"] == effective_from:
            if rule.get("effective_to") != effective_to or rule.get("percent") != percent:
                rule["effective_to"] = effective_to
                rule["percent"] = percent
                changed = True
            break
    else:
        rules.append({"effective_from": effective_from, "effective_to": effective_to, "percent": percent})
        changed = True
    rules.sort(key=lambda item: (item["effective_from"], item.get("effective_to") or date.max))
    metadata["iss_rate_rules"] = [_rule_payload(rule["percent"], rule["effective_from"], rule.get("effective_to")) for rule in rules]
    if entity.metadata_json != metadata:
        entity.metadata_json = metadata
        changed = True
    return changed


def _contract_uses_entity(contract: Contract, legal_entity_id: int) -> bool:
    if contract.contracting_legal_entity_id == legal_entity_id:
        return True
    fiscal_term = ContractFiscalTerm.query.filter_by(company_id=contract.company_id, contract_id=contract.id).first()
    return bool(fiscal_term and fiscal_term.contracting_legal_entity_id == legal_entity_id)


def _recalculate_retention_summary(metadata: dict) -> None:
    details = list(metadata.get("retention_details") or [])
    metadata["retention_summary"] = {
        "total_retention_amount": float(
            sum((ContractService._normalize_decimal(item.get("calculated_amount") or item.get("retention_amount")) for item in details), Decimal("0.00"))
        ),
        "retention_count": len(details),
    }


def _refresh_contract_item_iss(contract_item: ContractItem, reference_date: date) -> bool:
    metadata = ContractService._normalize_metadata_dict(contract_item.metadata_json)
    details = ContractService._normalize_metadata_dict_list(metadata.get("retention_details"))
    if not details:
        return False

    changed = False
    gross_amount = ContractService._normalize_decimal(contract_item.total_price)
    contract = contract_item.contract
    catalog_item = contract_item.contract_catalog_item
    for detail in details:
        if (
            (ContractService._normalize_text(detail.get("kind")) or "").lower() != "iss"
            or (ContractService._normalize_text(detail.get("retention_value_mode")) or "percent").lower() != "percent"
        ):
            continue
        effective_rate, rate_source, rate_rule = ContractService._resolve_effective_iss_rate_percent(
            contract=contract,
            catalog_item=catalog_item,
            reference_date=reference_date,
            fallback_rate=detail.get("retention_value"),
        )
        if effective_rate <= Decimal("0.00"):
            continue
        calculation_base, retention_amount = ContractService._calculate_retention_amount(
            gross_amount=gross_amount,
            deduction_mode=detail.get("base_deduction_mode"),
            deduction_value=detail.get("base_deduction_value"),
            value_mode="percent",
            value_amount=effective_rate,
        )
        new_values = {
            "retention_value": float(effective_rate),
            "rate_source": rate_source,
            "issuer_rate_rule": rate_rule,
            "calculation_base": float(calculation_base),
            "retention_amount": float(retention_amount),
            "calculated_amount": float(retention_amount),
        }
        for key, value in new_values.items():
            if detail.get(key) != value:
                detail[key] = value
                changed = True

    if changed:
        metadata["retention_details"] = details
        _recalculate_retention_summary(metadata)
        contract_item.metadata_json = metadata
    return changed


def _refresh_financial_satellites(native_billing: ContractNativeBilling, iss_amount: Decimal) -> int:
    metadata = dict(native_billing.metadata_json or {})
    integration = dict(metadata.get("financial_integration") or {})
    schedule_ids = ContractService._normalize_id_list(integration.get("satellite_schedule_ids"))
    if not schedule_ids:
        return 0

    updated = 0
    schedules = FinancialSchedule.query.filter(
        FinancialSchedule.company_id == native_billing.company_id,
        FinancialSchedule.id.in_(schedule_ids),
        FinancialSchedule.deleted_at.is_(None),
    ).all()
    for schedule in schedules:
        schedule_metadata = dict(schedule.metadata_json or {})
        if (ContractService._normalize_text(schedule_metadata.get("retention_kind")) or "").lower() != "iss":
            continue
        schedule.template_amount = iss_amount
        retention_detail = dict(schedule_metadata.get("retention_detail") or {})
        retention_detail["retention_value"] = float(
            ContractService._normalize_decimal(retention_detail.get("retention_value"))
        )
        retention_detail["calculated_amount"] = float(iss_amount)
        retention_detail["retention_amount"] = float(iss_amount)
        schedule_metadata["retention_detail"] = retention_detail
        schedule_metadata["backfilled_issuer_iss_rate_at"] = datetime.utcnow().isoformat()
        schedule.metadata_json = schedule_metadata
        updated += 1

    links = FinancialScheduleLink.query.filter(
        FinancialScheduleLink.company_id == native_billing.company_id,
        FinancialScheduleLink.child_schedule_id.in_(schedule_ids),
        FinancialScheduleLink.deleted_at.is_(None),
    ).all()
    for link in links:
        link_metadata = dict(link.metadata_json or {})
        if (ContractService._normalize_text(link_metadata.get("retention_kind")) or "").lower() != "iss":
            continue
        retention_detail = dict(link_metadata.get("retention_detail") or {})
        retention_detail["calculated_amount"] = float(iss_amount)
        retention_detail["retention_amount"] = float(iss_amount)
        link_metadata["retention_detail"] = retention_detail
        link_metadata["backfilled_issuer_iss_rate_at"] = datetime.utcnow().isoformat()
        link.metadata_json = link_metadata
    return updated


def _refresh_native_billing(native_billing: ContractNativeBilling) -> tuple[bool, int]:
    contract = native_billing.contract
    if not contract:
        return False, 0

    gross_total = Decimal("0.00")
    net_total = Decimal("0.00")
    retention_summary: dict[str, float] = {}
    changed = False
    iss_amount_total = Decimal("0.00")

    for billing_item in native_billing.items.order_by(ContractNativeBillingItem.id.asc()).all():
        contract_item = ContractItem.query.filter(
            ContractItem.company_id == native_billing.company_id,
            ContractItem.id == billing_item.contract_item_id,
            ContractItem.contract_id == contract.id,
        ).first()
        if not contract_item:
            continue
        snapshot = ContractService._build_native_billing_item_snapshot(contract_item, reference_date=native_billing.issue_date)
        metadata = {**dict(billing_item.metadata_json or {}), **snapshot}
        billing_item.metadata_json = metadata
        billing_item.amount = ContractService._normalize_decimal(snapshot.get("gross_amount"))
        gross_total += ContractService._normalize_decimal(snapshot.get("gross_amount"))
        net_total += ContractService._normalize_decimal(snapshot.get("net_amount"))
        for detail in snapshot.get("retention_details") or []:
            kind = (ContractService._normalize_text(detail.get("kind")) or "").lower()
            amount = ContractService._normalize_decimal(detail.get("calculated_amount") or detail.get("retention_amount"))
            retention_summary[kind] = round(float(retention_summary.get(kind) or 0) + float(amount), 2)
            if kind == "iss":
                iss_amount_total += amount
        changed = True

    if not changed:
        return False, 0

    fiscal_snapshot = ContractService.build_contract_fiscal_snapshot(contract, reference_date=native_billing.issue_date)
    metadata = dict(native_billing.metadata_json or {})
    metadata["retention_summary"] = retention_summary
    metadata["retention_amount"] = float(sum((Decimal(str(value)) for value in retention_summary.values()), Decimal("0.00")))
    metadata["fiscal_snapshot"] = fiscal_snapshot
    fiscal_invoice = dict(metadata.get("fiscal_invoice") or {})
    if fiscal_invoice:
        fiscal_data = dict(fiscal_invoice.get("fiscal_data") or {})
        fiscal_data["issuer_iss_rate"] = fiscal_snapshot.get("issuer_iss_rate")
        fiscal_data["issuer_iss_rate_effective_from"] = fiscal_snapshot.get("issuer_iss_rate_effective_from")
        fiscal_data["issuer_iss_rate_effective_to"] = fiscal_snapshot.get("issuer_iss_rate_effective_to")
        fiscal_invoice["fiscal_data"] = fiscal_data
        metadata["fiscal_invoice"] = fiscal_invoice
    native_billing.gross_amount = gross_total.quantize(Decimal("0.01"))
    native_billing.net_amount = net_total.quantize(Decimal("0.01"))
    native_billing.metadata_json = metadata
    updated_schedules = _refresh_financial_satellites(native_billing, iss_amount_total.quantize(Decimal("0.01")))
    return True, updated_schedules


def run(*, company_id: int, legal_entity_id: int, iss_rate_percent: Decimal, effective_from: date, effective_to: date | None, dry_run: bool) -> dict:
    entity = ContractingLegalEntity.query.filter_by(company_id=company_id, id=legal_entity_id).first()
    if not entity:
        raise SystemExit(f"PJ emissora {legal_entity_id} não localizada na company_id={company_id}.")

    changed_entity = _upsert_entity_iss_rule(entity, iss_rate_percent, effective_from, effective_to)
    contracts = [
        contract
        for contract in Contract.query.filter(Contract.company_id == company_id, Contract.deleted_at.is_(None)).order_by(Contract.id.asc()).all()
        if _contract_uses_entity(contract, legal_entity_id)
    ]

    changed_items = 0
    changed_billings = 0
    changed_schedules = 0
    for contract in contracts:
        reference_date = contract.billing_start_at or contract.service_start_at or effective_from
        for contract_item in contract.items.order_by(ContractItem.id.asc()).all():
            if _refresh_contract_item_iss(contract_item, reference_date):
                changed_items += 1
        for native_billing in ContractNativeBilling.query.filter(
            ContractNativeBilling.company_id == company_id,
            ContractNativeBilling.contract_id == contract.id,
            ContractNativeBilling.status != "cancelled",
        ).order_by(ContractNativeBilling.id.asc()).all():
            changed, schedules = _refresh_native_billing(native_billing)
            if changed:
                changed_billings += 1
                changed_schedules += schedules

    payload = {
        "company_id": company_id,
        "legal_entity_id": legal_entity_id,
        "legal_entity": entity.legal_name,
        "iss_rate_percent": ContractService._decimal_to_export_text(iss_rate_percent, places=4, strip_trailing=True),
        "effective_from": ContractService._serialize_date(effective_from),
        "effective_to": ContractService._serialize_date(effective_to),
        "changed_entity": changed_entity,
        "contracts_scanned": len(contracts),
        "changed_contract_items": changed_items,
        "changed_native_billings": changed_billings,
        "changed_financial_schedules": changed_schedules,
        "dry_run": dry_run,
    }
    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill controlado da alíquota ISS da PJ emissora em contratos/faturamentos.")
    parser.add_argument("--company-id", type=int, required=True)
    parser.add_argument("--legal-entity-id", type=int, required=True)
    parser.add_argument("--iss-rate-percent", required=True)
    parser.add_argument("--effective-from", required=True)
    parser.add_argument("--effective-to")
    parser.add_argument("--apply", action="store_true", help="Sem esta flag, executa dry-run e faz rollback.")
    parser.add_argument("--config", default="production")
    args = parser.parse_args()

    app = create_app(args.config)
    with app.app_context():
        payload = run(
            company_id=args.company_id,
            legal_entity_id=args.legal_entity_id,
            iss_rate_percent=ContractService._normalize_decimal(args.iss_rate_percent).quantize(Decimal("0.0001")),
            effective_from=ContractService._normalize_date(args.effective_from),
            effective_to=ContractService._normalize_date(args.effective_to),
            dry_run=not args.apply,
        )
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
