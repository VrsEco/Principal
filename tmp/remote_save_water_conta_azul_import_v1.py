from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from app import create_app
from models import db
from models.financial import FinancialEntry, FinancialEntryAllocation, FinancialSettlement, FinancialSettlementComponent
from services.financial_service import FinancialService

COMPANY_ID = 1
MANIFEST_PATH = Path('tmp/save_water_import_manifest_v1.json')
REPORT_PATH = Path('tmp/save_water_import_report_v1.json')
BATCH_ID = 'conta_azul_save_water_20260525_v1'
AGENT_NAME = 'codex'


def _norm(value: Any) -> str:
    value = '' if value is None else str(value).strip()
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii').lower()
    value = re.sub(r'\s+', ' ', value)
    return value.strip()


def _dec(value: Any) -> Decimal:
    if value in (None, '', 'None'):
        return Decimal('0.00')
    return Decimal(str(value)).quantize(Decimal('0.01'))


def _load_manifest() -> Dict[str, Any]:
    payload = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    if int(payload.get('company_id') or 0) != COMPANY_ID:
        raise RuntimeError(f'company_id divergente no manifesto: {payload.get("company_id")}')
    if str(payload.get('batch_id') or '') != BATCH_ID:
        raise RuntimeError(f'batch_id divergente no manifesto: {payload.get("batch_id")}')
    return payload


def _entry_batch_items() -> List[FinancialEntry]:
    items = FinancialEntry.query.filter(
        FinancialEntry.company_id == COMPANY_ID,
        FinancialEntry.deleted_at.is_(None),
    ).all()
    return [item for item in items if (item.metadata_json or {}).get('migration_batch_id') == BATCH_ID]


def _allocation_batch_items() -> List[FinancialEntryAllocation]:
    items = FinancialEntryAllocation.query.filter(
        FinancialEntryAllocation.company_id == COMPANY_ID,
        FinancialEntryAllocation.deleted_at.is_(None),
    ).all()
    return [item for item in items if (item.metadata_json or {}).get('migration_batch_id') == BATCH_ID]


def _settlement_batch_items() -> List[FinancialSettlement]:
    items = FinancialSettlement.query.filter(
        FinancialSettlement.company_id == COMPANY_ID,
        FinancialSettlement.deleted_at.is_(None),
    ).all()
    return [item for item in items if (item.metadata_json or {}).get('migration_batch_id') == BATCH_ID]


def _resolve_counterparties() -> Dict[str, Any]:
    items = db.session.execute(
        text(
            """
            select id, name, document_number
              from financial_counterparties
             where company_id = :cid
               and deleted_at is null
            """
        ),
        {'cid': COMPANY_ID},
    ).mappings().all()
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    by_doc: Dict[str, Dict[str, Any]] = {}
    for row in items:
        rowd = dict(row)
        by_name.setdefault(_norm(rowd.get('name')), []).append(rowd)
        doc = _norm(rowd.get('document_number'))
        if doc:
            by_doc[doc] = rowd
    return {'by_name': by_name, 'by_doc': by_doc}


def _resolve_chart_accounts() -> Dict[str, Dict[str, Any]]:
    items = db.session.execute(
        text(
            """
            select id, code, name
              from financial_chart_accounts
             where company_id = :cid
               and deleted_at is null
            """
        ),
        {'cid': COMPANY_ID},
    ).mappings().all()
    by_code: Dict[str, Dict[str, Any]] = {}
    for row in items:
        rowd = dict(row)
        by_code[str(rowd.get('code') or '').strip()] = rowd
    return by_code


def _resolve_counterparty_id(caches: Dict[str, Any], name: str, document: str) -> Optional[int]:
    doc_key = _norm(document)
    if doc_key and doc_key in caches['by_doc']:
        return int(caches['by_doc'][doc_key]['id'])
    name_key = _norm(name)
    if not name_key:
        return None
    matches = caches['by_name'].get(name_key) or []
    if len(matches) == 1:
        return int(matches[0]['id'])
    if matches:
        return int(matches[0]['id'])
    return None


def _build_validation_snapshot(manifest: Dict[str, Any]) -> Dict[str, Any]:
    entry_items = _entry_batch_items()
    allocation_items = _allocation_batch_items()
    settlement_items = _settlement_batch_items()
    expected = dict(manifest.get('totals') or {})
    entry_type_counts: Dict[str, int] = {}
    for item in entry_items:
        entry_type_counts[item.entry_type] = entry_type_counts.get(item.entry_type, 0) + 1
    return {
        'batch_id': BATCH_ID,
        'company_id': COMPANY_ID,
        'expected': expected,
        'actual': {
            'entries': len(entry_items),
            'allocations': len(allocation_items),
            'settlements': len(settlement_items),
            'entry_type_counts': entry_type_counts,
            'entries_total_amount': float(sum((_dec(item.original_amount) for item in entry_items), Decimal('0.00'))),
            'settlements_total_amount': float(sum((_dec(item.principal_amount) for item in settlement_items), Decimal('0.00'))),
        },
        'ok': (
            len(entry_items) == int(expected.get('entries') or 0)
            and len(allocation_items) == int(expected.get('allocations') or 0)
            and len(settlement_items) == int(expected.get('settlements') or 0)
        ),
    }


def _rollback_internal(reason: str) -> Dict[str, Any]:
    now = datetime.utcnow()
    entry_items = _entry_batch_items()
    allocation_items = _allocation_batch_items()
    settlement_items = _settlement_batch_items()
    settlement_ids = [int(item.id) for item in settlement_items]

    component_deleted = 0
    if settlement_ids:
        component_deleted = db.session.query(FinancialSettlementComponent).filter(
            FinancialSettlementComponent.company_id == COMPANY_ID,
            FinancialSettlementComponent.financial_settlement_id.in_(settlement_ids),
        ).delete(synchronize_session=False) or 0

    for item in allocation_items:
        item.deleted_at = now
        item.metadata_json = {
            **dict(item.metadata_json or {}),
            'rollback_reason': reason,
            'rolled_back_at_utc': now.isoformat(),
        }

    for item in settlement_items:
        item.deleted_at = now
        item.metadata_json = {
            **dict(item.metadata_json or {}),
            'rollback_reason': reason,
            'rolled_back_at_utc': now.isoformat(),
        }

    for item in entry_items:
        item.deleted_at = now
        item.metadata_json = {
            **dict(item.metadata_json or {}),
            'rollback_reason': reason,
            'rolled_back_at_utc': now.isoformat(),
        }

    db.session.commit()
    result = {
        'ok': True,
        'rolled_back_at_utc': now.isoformat(),
        'reason': reason,
        'counts': {
            'entries_soft_deleted': len(entry_items),
            'allocations_soft_deleted': len(allocation_items),
            'settlements_soft_deleted': len(settlement_items),
            'components_hard_deleted': component_deleted,
        },
    }
    REPORT_PATH.write_text(json.dumps({'mode': 'rollback', **result}, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return result


def run_import() -> Dict[str, Any]:
    manifest = _load_manifest()
    existing_entries = _entry_batch_items()
    if existing_entries:
        raise RuntimeError(f'Já existem {len(existing_entries)} lançamentos ativos para o lote {BATCH_ID}.')

    before_counts = {
        'entries_active_company': FinancialEntry.query.filter(FinancialEntry.company_id == COMPANY_ID, FinancialEntry.deleted_at.is_(None)).count(),
        'allocations_active_company': FinancialEntryAllocation.query.filter(FinancialEntryAllocation.company_id == COMPANY_ID, FinancialEntryAllocation.deleted_at.is_(None)).count(),
        'settlements_active_company': FinancialSettlement.query.filter(FinancialSettlement.company_id == COMPANY_ID, FinancialSettlement.deleted_at.is_(None)).count(),
    }

    counterparty_cache = _resolve_counterparties()
    chart_accounts = _resolve_chart_accounts()

    created_entry_codes: List[str] = []
    issues: List[Dict[str, Any]] = []

    try:
        for entry_manifest in manifest['entries']:
            counterparty_id = _resolve_counterparty_id(
                counterparty_cache,
                entry_manifest.get('counterparty_name') or '',
                entry_manifest.get('counterparty_document') or '',
            )
            if entry_manifest.get('counterparty_name') and not counterparty_id:
                raise RuntimeError(
                    f"Favorecido não encontrado para {entry_manifest['title_key']}: {entry_manifest.get('counterparty_name')}"
                )

            primary_chart_id = None
            primary_chart_code = entry_manifest.get('primary_chart_account_code')
            if primary_chart_code:
                chart = chart_accounts.get(primary_chart_code)
                if not chart:
                    raise RuntimeError(f"Plano de contas não encontrado: {primary_chart_code} em {entry_manifest['title_key']}")
                primary_chart_id = int(chart['id'])

            has_allocations = bool(entry_manifest.get('allocations'))
            review_status = 'approved' if has_allocations or entry_manifest['entry_type'] == 'transfer' else 'pending_review'

            entry_payload = {
                'company_id': COMPANY_ID,
                'entry_code': entry_manifest['entry_code'],
                'entry_type': entry_manifest['entry_type'],
                'movement_nature': entry_manifest['movement_nature'],
                'origin_type': 'migration',
                'status': 'posted',
                'review_status': review_status,
                'description': entry_manifest['description'],
                'document_number': str(entry_manifest['excel_row']),
                'external_reference': entry_manifest['title_key'],
                'origin_reference': 'conta_azul_final_xlsx',
                'issue_date': entry_manifest['issue_date'] or None,
                'competence_date': entry_manifest['competence_date'],
                'due_date': entry_manifest['due_date'] or None,
                'occurred_on': entry_manifest['issue_date'] or entry_manifest['competence_date'],
                'original_amount': entry_manifest['original_amount'],
                'currency_code': 'BRL',
                'counterparty_id': counterparty_id,
                'chart_account_id': primary_chart_id,
                'cost_center_id': int(entry_manifest['cost_center_id']),
                'created_by_agent': AGENT_NAME,
                'notes': f"[Migração Conta Azul][{BATCH_ID}] {entry_manifest.get('notes') or ''}".strip(),
                'metadata_json': {
                    'migration_batch_id': BATCH_ID,
                    'source_system': 'conta_azul',
                    'source_file': manifest.get('source_file'),
                    'source_excel_row': entry_manifest['excel_row'],
                    'source_title_key': entry_manifest['title_key'],
                    'source_status': entry_manifest.get('status_original'),
                    'source_origin_type': entry_manifest.get('origin_source_type'),
                    'scenario': entry_manifest.get('scenario'),
                    'payment_method_name': entry_manifest.get('payment_method_name'),
                    'cost_center_code': entry_manifest.get('cost_center_code'),
                    'classification_pending': (not has_allocations and entry_manifest['entry_type'] != 'transfer'),
                    'imported_at_utc': datetime.utcnow().isoformat(),
                },
            }
            entry, error = FinancialService.create_entry(payload=entry_payload, allowed_company_ids=[COMPANY_ID])
            if error:
                raise RuntimeError(f"Erro ao criar lançamento {entry_manifest['entry_code']}: {error}")
            created_entry_codes.append(entry.entry_code)

            if has_allocations:
                allocations_payload = []
                for allocation in entry_manifest['allocations']:
                    chart_code = allocation['chart_account_code']
                    chart = chart_accounts.get(chart_code)
                    if not chart:
                        raise RuntimeError(f"Plano de contas não encontrado no rateio: {chart_code} em {entry_manifest['title_key']}")
                    allocations_payload.append({
                        'company_id': COMPANY_ID,
                        'financial_entry_id': entry.id,
                        'chart_account_id': int(chart['id']),
                        'cost_center_id': int(entry_manifest['cost_center_id']),
                        'allocation_type': 'amount',
                        'allocated_amount': allocation['amount'],
                        'notes': allocation.get('note') or None,
                        'metadata_json': {
                            'migration_batch_id': BATCH_ID,
                            'source_excel_row': entry_manifest['excel_row'],
                            'source_title_key': entry_manifest['title_key'],
                            'source_note': allocation.get('note'),
                        },
                    })
                _, alloc_error = FinancialService.replace_allocations(
                    payload={
                        'company_id': COMPANY_ID,
                        'financial_entry_id': entry.id,
                        'allocations': allocations_payload,
                    },
                    allowed_company_ids=[COMPANY_ID],
                )
                if alloc_error:
                    raise RuntimeError(f"Erro ao criar rateios de {entry_manifest['entry_code']}: {alloc_error}")
            else:
                issues.append({
                    'title_key': entry_manifest['title_key'],
                    'entry_code': entry_manifest['entry_code'],
                    'issue': 'missing_allocation',
                })

            for index, settlement_manifest in enumerate(entry_manifest.get('settlements') or [], start=1):
                if not settlement_manifest.get('settlement_date'):
                    continue
                settlement_code = f"{entry_manifest['entry_code']}-S{index:02d}"
                settlement_payload = {
                    'company_id': COMPANY_ID,
                    'financial_entry_id': entry.id,
                    'settlement_code': settlement_code,
                    'settlement_type': 'manual',
                    'settlement_status': 'posted',
                    'settlement_date': settlement_manifest['settlement_date'],
                    'bank_account_id': settlement_manifest.get('bank_account_id'),
                    'principal_amount': settlement_manifest['amount'],
                    'gross_amount': settlement_manifest['amount'],
                    'net_amount': settlement_manifest['amount'],
                    'reconciliation_status': 'pending',
                    'notes': f"[Migração Conta Azul][{BATCH_ID}] {settlement_manifest.get('notes') or ''}".strip(),
                    'created_by_agent': AGENT_NAME,
                    'metadata_json': {
                        'migration_batch_id': BATCH_ID,
                        'source_excel_row': entry_manifest['excel_row'],
                        'source_title_key': entry_manifest['title_key'],
                        'source_component': settlement_manifest.get('component'),
                        'source_status': entry_manifest.get('status_original'),
                        'bank_account_name': settlement_manifest.get('bank_account_name'),
                        'imported_at_utc': datetime.utcnow().isoformat(),
                    },
                }
                _, settlement_error = FinancialService.create_settlement(
                    payload=settlement_payload,
                    allowed_company_ids=[COMPANY_ID],
                )
                if settlement_error:
                    raise RuntimeError(f"Erro ao criar baixa {settlement_code}: {settlement_error}")

        validation = _build_validation_snapshot(manifest)
        result = {
            'ok': validation['ok'],
            'mode': 'import',
            'batch_id': BATCH_ID,
            'company_id': COMPANY_ID,
            'before_counts': before_counts,
            'validation': validation,
            'created_entry_codes_sample': created_entry_codes[:20],
            'issues': issues,
            'imported_at_utc': datetime.utcnow().isoformat(),
        }
        REPORT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        if not validation['ok']:
            rollback_result = _rollback_internal('Validação pós-carga divergente do manifesto.')
            result['rollback'] = rollback_result
            result['ok'] = False
        return result
    except Exception as exc:
        db.session.rollback()
        rollback_result = _rollback_internal(f'Rollback automático por falha: {exc}')
        result = {
            'ok': False,
            'mode': 'import',
            'batch_id': BATCH_ID,
            'company_id': COMPANY_ID,
            'error': str(exc),
            'created_entry_codes_sample': created_entry_codes[:20],
            'issues': issues,
            'rollback': rollback_result,
            'failed_at_utc': datetime.utcnow().isoformat(),
        }
        REPORT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        return result


def run_validate() -> Dict[str, Any]:
    manifest = _load_manifest()
    result = {'mode': 'validate', **_build_validation_snapshot(manifest)}
    REPORT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return result


def main() -> None:
    mode = (sys.argv[1] if len(sys.argv) > 1 else 'validate').strip().lower()
    app = create_app('production')
    with app.app_context():
        if mode == 'import':
            payload = run_import()
        elif mode == 'rollback':
            payload = _rollback_internal('Rollback manual solicitado pelo operador.')
        elif mode == 'validate':
            payload = run_validate()
        else:
            raise SystemExit(f'Modo inválido: {mode}')
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
