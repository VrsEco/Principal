from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional

from app import create_app
from models import db
from models.financial import FinancialEntry, FinancialSchedule, FinancialSettlement
from services.financial_schedule_service import FinancialScheduleService
from services.financial_service import FinancialService

COMPANY_ID = 1
MANIFEST_PATH = Path('tmp/save_water_import_manifest_v1.json')
REPORT_PATH = Path('tmp/save_water_canonical_reprocess_report_v1.json')
SOURCE_FILE = 'ContaAzul - Final.xlsx'
SCHEDULE_BATCH_ID = 'conta_azul_save_water_canonical_schedule_20260525_v1'
TRANSFER_BATCH_ID = 'conta_azul_save_water_canonical_transfer_20260525_v1'
AGENT_NAME = 'codex'
DEFAULT_COST_CENTER_ID = 23


def _norm(value: Any) -> str:
    value = '' if value is None else str(value).strip()
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii').lower()
    value = re.sub(r'\s+', ' ', value)
    return value.strip()


def _money(value: Any) -> Decimal:
    if value in (None, '', 'None'):
        return Decimal('0.00')
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _load_manifest() -> Dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))


def _resolve_counterparties() -> Dict[str, Any]:
    rows = db.session.execute(
        db.text("select id, name, document_number from financial_counterparties where company_id=:cid and deleted_at is null"),
        {'cid': COMPANY_ID},
    ).mappings().all()
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    by_doc: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        by_name.setdefault(_norm(item.get('name')), []).append(item)
        doc = _norm(item.get('document_number'))
        if doc:
            by_doc[doc] = item
    return {'by_name': by_name, 'by_doc': by_doc}


def _resolve_chart_accounts() -> Dict[str, Dict[str, Any]]:
    rows = db.session.execute(
        db.text("select id, code, name from financial_chart_accounts where company_id=:cid and deleted_at is null"),
        {'cid': COMPANY_ID},
    ).mappings().all()
    return {str(dict(r)['code']).strip(): dict(r) for r in rows}


def _resolve_counterparty_id(cache: Dict[str, Any], name: str, document: str) -> Optional[int]:
    doc = _norm(document)
    if doc and doc in cache['by_doc']:
        return int(cache['by_doc'][doc]['id'])
    nm = _norm(name)
    rows = cache['by_name'].get(nm) or []
    if rows:
        return int(rows[0]['id'])
    return None


def _rollback_schedule_batch(reason: str) -> Dict[str, Any]:
    schedules = FinancialSchedule.query.filter(
        FinancialSchedule.company_id == COMPANY_ID,
        FinancialSchedule.deleted_at.is_(None),
    ).order_by(FinancialSchedule.id.desc()).all()
    targets = [s for s in schedules if (s.metadata_json or {}).get('migration_schedule_batch_id') == SCHEDULE_BATCH_ID]
    deleted = 0
    errors = []
    for schedule in targets:
        _, err = FinancialScheduleService.delete_schedule(
            schedule_id=schedule.id,
            company_id=COMPANY_ID,
            allowed_company_ids=[COMPANY_ID],
        )
        if err:
            errors.append({'schedule_id': schedule.id, 'error': err})
        else:
            deleted += 1
    return {'deleted': deleted, 'errors': errors, 'reason': reason}


def _rollback_transfer_batch(reason: str) -> Dict[str, Any]:
    entries = FinancialEntry.query.filter(
        FinancialEntry.company_id == COMPANY_ID,
        FinancialEntry.deleted_at.is_(None),
    ).order_by(FinancialEntry.id.desc()).all()
    targets = [e for e in entries if (e.metadata_json or {}).get('migration_transfer_batch_id') == TRANSFER_BATCH_ID]
    settlement_deleted = 0
    entry_deleted = 0
    errors = []
    for entry in targets:
        settlements = FinancialSettlement.query.filter(
            FinancialSettlement.company_id == COMPANY_ID,
            FinancialSettlement.financial_entry_id == entry.id,
            FinancialSettlement.deleted_at.is_(None),
        ).order_by(FinancialSettlement.id.desc()).all()
        for settlement in settlements:
            _, err = FinancialService.delete_settlement(
                settlement_id=settlement.id,
                company_id=COMPANY_ID,
                allowed_company_ids=[COMPANY_ID],
            )
            if err:
                errors.append({'entry_id': entry.id, 'settlement_id': settlement.id, 'error': err})
            else:
                settlement_deleted += 1
        _, err = FinancialService.delete_entry(
            entry_id=entry.id,
            company_id=COMPANY_ID,
            allowed_company_ids=[COMPANY_ID],
        )
        if err:
            errors.append({'entry_id': entry.id, 'error': err})
        else:
            entry_deleted += 1
    return {'entries_deleted': entry_deleted, 'settlements_deleted': settlement_deleted, 'errors': errors, 'reason': reason}


def _build_schedule_allocations(source: Dict[str, Any], chart_accounts: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    allocs = list(source.get('allocations') or [])
    if not allocs:
        return []
    if len(allocs) == 1:
        chart = chart_accounts.get(allocs[0]['chart_account_code'])
        if not chart:
            raise RuntimeError(f"Plano de contas não encontrado: {allocs[0]['chart_account_code']} em {source['entry_code']}")
        return [{
            'chart_account_id': int(chart['id']),
            'cost_center_id': DEFAULT_COST_CENTER_ID,
            'allocation_type': 'percentage',
            'percentage': '100',
            'notes': allocs[0].get('note') or None,
            'metadata_json': {
                'migration_schedule_batch_id': SCHEDULE_BATCH_ID,
                'source_entry_code': source['entry_code'],
            },
        }]

    built: List[Dict[str, Any]] = []
    for alloc in allocs:
        chart = chart_accounts.get(alloc['chart_account_code'])
        if not chart:
            raise RuntimeError(f"Plano de contas não encontrado: {alloc['chart_account_code']} em {source['entry_code']}")
        built.append({
            'chart_account_id': int(chart['id']),
            'cost_center_id': DEFAULT_COST_CENTER_ID,
            'allocation_type': 'amount',
            'allocated_amount': str(alloc['amount']),
            'notes': alloc.get('note') or None,
            'metadata_json': {
                'migration_schedule_batch_id': SCHEDULE_BATCH_ID,
                'source_entry_code': source['entry_code'],
            },
        })
    return built


def _schedule_status(source: Dict[str, Any]) -> str:
    return 'completed' if _money(source.get('open_balance_amount')) == Decimal('0.00') else 'active'


def run() -> Dict[str, Any]:
    manifest = _load_manifest()
    cp_cache = _resolve_counterparties()
    chart_accounts = _resolve_chart_accounts()

    created_schedules = []
    created_transfer_entries = []
    skipped = []

    try:
        for source in manifest['entries']:
            entry_type = source['entry_type']
            title_key = source['title_key']
            counterparty_id = _resolve_counterparty_id(cp_cache, source.get('counterparty_name') or '', source.get('counterparty_document') or '')

            if entry_type == 'transfer':
                # reimportar como lançamento transacional direto
                entry_payload = {
                    'company_id': COMPANY_ID,
                    'entry_code': f"{source['entry_code']}-CAN",
                    'entry_type': 'transfer',
                    'movement_nature': source['movement_nature'],
                    'origin_type': 'migration',
                    'status': 'settled' if source.get('settlements') else 'posted',
                    'review_status': 'approved',
                    'description': source['description'],
                    'document_number': str(source['excel_row']),
                    'external_reference': title_key,
                    'origin_reference': 'conta_azul_final_xlsx',
                    'issue_date': source['issue_date'] or None,
                    'competence_date': source['competence_date'],
                    'due_date': source['due_date'] or None,
                    'occurred_on': source['issue_date'] or source['competence_date'],
                    'original_amount': source['original_amount'],
                    'currency_code': 'BRL',
                    'bank_account_id': (source.get('settlements') or [{}])[0].get('bank_account_id'),
                    'counterparty_id': counterparty_id,
                    'cost_center_id': DEFAULT_COST_CENTER_ID,
                    'created_by_agent': AGENT_NAME,
                    'notes': f"[Migração Canônica Transfer][{TRANSFER_BATCH_ID}] {source.get('notes') or ''}".strip(),
                    'metadata_json': {
                        'migration_transfer_batch_id': TRANSFER_BATCH_ID,
                        'source_excel_row': source['excel_row'],
                        'source_title_key': title_key,
                        'source_file': SOURCE_FILE,
                    },
                }
                entry, error = FinancialService.create_entry(payload=entry_payload, allowed_company_ids=[COMPANY_ID])
                if error:
                    raise RuntimeError(f"Erro ao criar transferência {source['entry_code']}: {error}")
                for idx, settlement in enumerate(source.get('settlements') or [], start=1):
                    _, serr = FinancialService.create_settlement(
                        payload={
                            'company_id': COMPANY_ID,
                            'financial_entry_id': entry.id,
                            'settlement_code': f"{source['entry_code']}-CAN-TR-{idx:02d}",
                            'settlement_type': 'manual',
                            'settlement_status': 'posted',
                            'settlement_date': settlement['settlement_date'],
                            'bank_account_id': settlement.get('bank_account_id'),
                            'principal_amount': settlement['amount'],
                            'gross_amount': settlement['amount'],
                            'net_amount': settlement['amount'],
                            'reconciliation_status': 'pending',
                            'created_by_agent': AGENT_NAME,
                            'notes': f"[Migração Canônica Transfer][{TRANSFER_BATCH_ID}] {settlement.get('notes') or ''}".strip(),
                            'metadata_json': {
                                'migration_transfer_batch_id': TRANSFER_BATCH_ID,
                                'source_excel_row': source['excel_row'],
                                'source_title_key': title_key,
                                'source_component': settlement.get('component'),
                            },
                        },
                        allowed_company_ids=[COMPANY_ID],
                    )
                    if serr:
                        raise RuntimeError(f"Erro ao criar baixa da transferência {source['entry_code']}: {serr}")
                created_transfer_entries.append(source['entry_code'])
                continue

            allocations = _build_schedule_allocations(source, chart_accounts)
            if not allocations:
                skipped.append({'entry_code': f"{source['entry_code']}-CAN", 'reason': 'missing_allocation'})
                continue

            first_chart_id = int(allocations[0]['chart_account_id'])
            comp_date = source['competence_date']
            due_date = source['due_date'] or source['competence_date']
            normalized_comp_date = comp_date if comp_date <= due_date else due_date
            schedule_payload = {
                'company_id': COMPANY_ID,
                'name': (source['description'] or source['entry_code'])[:120],
                'entry_type': entry_type,
                'movement_nature': source['movement_nature'],
                'origin_type': 'migration',
                'status': _schedule_status(source),
                'frequency': 'one_time',
                'interval_value': 1,
                'start_date': normalized_comp_date,
                'competence_date': normalized_comp_date,
                'end_date': due_date,
                'first_due_date': due_date,
                'next_due_date': due_date,
                'description': (source['description'] or source['entry_code'])[:255],
                'document_number_prefix': str(source['excel_row']),
                'template_amount': source['original_amount'],
                'currency_code': 'BRL',
                'counterparty_id': counterparty_id,
                'chart_account_id': first_chart_id,
                'cost_center_id': DEFAULT_COST_CENTER_ID,
                'created_by_agent': AGENT_NAME,
                'notes': f"[Migração Canônica Título][{SCHEDULE_BATCH_ID}] {source.get('notes') or ''}".strip(),
                'metadata_json': {
                    'migration_schedule_batch_id': SCHEDULE_BATCH_ID,
                    'source_file': SOURCE_FILE,
                    'source_excel_row': source['excel_row'],
                    'source_title_key': title_key,
                    'source_entry_code': source['entry_code'],
                    'source_status': source.get('status_original'),
                    'counterparty_name': source.get('counterparty_name'),
                    'direct_entry': True,
                    'source_competence_date_original': source['competence_date'],
                    'source_due_date_original': due_date,
                },
                'allocations': allocations,
            }
            schedule, error = FinancialScheduleService.create_schedule(payload=schedule_payload, allowed_company_ids=[COMPANY_ID])
            if error:
                raise RuntimeError(f"Erro ao criar título canônico {source['entry_code']}: {error}")
            schedule_id = int(schedule['id'])
            created_schedules.append(schedule_id)

            if source.get('settlements'):
                for settlement in source['settlements']:
                    _, serr = FinancialScheduleService.create_settlement_from_schedule(
                        schedule_id=schedule_id,
                        company_id=COMPANY_ID,
                        payload={
                            'settlement_type': 'manual',
                            'settlement_status': 'posted',
                            'settlement_date': settlement['settlement_date'],
                            'bank_account_id': settlement.get('bank_account_id'),
                            'principal_amount': settlement['amount'],
                            'gross_amount': settlement['amount'],
                            'net_amount': settlement['amount'],
                            'reconciliation_status': 'pending',
                            'created_by_agent': AGENT_NAME,
                            'notes': f"[Migração Canônica Baixa][{SCHEDULE_BATCH_ID}] {settlement.get('notes') or ''}".strip(),
                            'metadata_json': {
                                'migration_schedule_batch_id': SCHEDULE_BATCH_ID,
                                'source_excel_row': source['excel_row'],
                                'source_title_key': title_key,
                                'source_component': settlement.get('component'),
                            },
                        },
                        allowed_company_ids=[COMPANY_ID],
                    )
                    if serr:
                        raise RuntimeError(f"Erro ao criar baixa canônica de {source['entry_code']}: {serr}")
            else:
                _, eerr = FinancialScheduleService.create_entry_from_schedule(
                    schedule_id=schedule_id,
                    company_id=COMPANY_ID,
                    allowed_company_ids=[COMPANY_ID],
                    ignore_bordero_lock=True,
                )
                if eerr:
                    raise RuntimeError(f"Erro ao criar lançamento do título aberto {source['entry_code']}: {eerr}")

        result = {
            'ok': True,
            'schedule_batch_id': SCHEDULE_BATCH_ID,
            'transfer_batch_id': TRANSFER_BATCH_ID,
            'created_schedule_count': len(created_schedules),
            'created_transfer_entry_count': len(created_transfer_entries),
            'skipped': skipped,
            'processed_at_utc': datetime.utcnow().isoformat(),
        }
        REPORT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        return result
    except Exception as exc:
        schedule_rb = _rollback_schedule_batch(f'rollback automático: {exc}')
        transfer_rb = _rollback_transfer_batch(f'rollback automático: {exc}')
        result = {
            'ok': False,
            'error': str(exc),
            'schedule_rollback': schedule_rb,
            'transfer_rollback': transfer_rb,
        }
        REPORT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        return result


if __name__ == '__main__':
    app = create_app('production')
    with app.app_context():
        print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
