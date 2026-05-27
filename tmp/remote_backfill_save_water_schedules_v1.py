from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app import create_app
from models import db
from models.financial import FinancialEntry, FinancialSchedule, FinancialSettlement
from services.financial_schedule_service import FinancialScheduleService

COMPANY_ID = 1
SOURCE_BATCH_ID = 'conta_azul_save_water_20260525_v1'
SCHEDULE_BATCH_ID = 'conta_azul_save_water_schedule_backfill_20260525_v1'
MANIFEST_PATH = Path('tmp/save_water_import_manifest_v1.json')
REPORT_PATH = Path('tmp/save_water_schedule_backfill_report_v1.json')
AGENT_NAME = 'codex'


def _load_manifest() -> Dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))


def _rollback(reason: str) -> Dict[str, Any]:
    now = datetime.utcnow()
    schedules = FinancialSchedule.query.filter(
        FinancialSchedule.company_id == COMPANY_ID,
        FinancialSchedule.deleted_at.is_(None),
    ).all()
    schedules = [s for s in schedules if (s.metadata_json or {}).get('migration_schedule_batch_id') == SCHEDULE_BATCH_ID]
    schedule_ids = {int(s.id) for s in schedules}

    entries = FinancialEntry.query.filter(
        FinancialEntry.company_id == COMPANY_ID,
        FinancialEntry.deleted_at.is_(None),
    ).all()
    reverted_entries = 0
    for entry in entries:
        md = dict(entry.metadata_json or {})
        if md.get('migration_schedule_batch_id') != SCHEDULE_BATCH_ID:
            continue
        prev_ext = md.get('migration_schedule_backfill_previous_external_reference')
        prev_sched = md.get('migration_schedule_backfill_previous_financial_schedule_id')
        entry.external_reference = prev_ext
        entry.financial_schedule_id = prev_sched
        md['migration_schedule_backfill_rolled_back_at_utc'] = now.isoformat()
        md['migration_schedule_backfill_rollback_reason'] = reason
        entry.metadata_json = md
        reverted_entries += 1

    settlements = FinancialSettlement.query.filter(
        FinancialSettlement.company_id == COMPANY_ID,
        FinancialSettlement.deleted_at.is_(None),
    ).all()
    reverted_settlements = 0
    for settlement in settlements:
        md = dict(settlement.metadata_json or {})
        if md.get('migration_schedule_batch_id') != SCHEDULE_BATCH_ID:
            continue
        prev_ext = md.get('migration_schedule_backfill_previous_external_reference')
        settlement.external_reference = prev_ext
        md['migration_schedule_backfill_rolled_back_at_utc'] = now.isoformat()
        md['migration_schedule_backfill_rollback_reason'] = reason
        settlement.metadata_json = md
        reverted_settlements += 1

    deleted_schedules = 0
    for schedule in schedules:
        schedule.deleted_at = now
        schedule.metadata_json = {
            **dict(schedule.metadata_json or {}),
            'migration_schedule_backfill_rolled_back_at_utc': now.isoformat(),
            'migration_schedule_backfill_rollback_reason': reason,
        }
        deleted_schedules += 1

    db.session.commit()
    result = {
        'ok': True,
        'mode': 'rollback',
        'reason': reason,
        'schedule_batch_id': SCHEDULE_BATCH_ID,
        'counts': {
            'schedules_soft_deleted': deleted_schedules,
            'entries_relinked': reverted_entries,
            'settlements_relinked': reverted_settlements,
        },
    }
    REPORT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    return result


def run_backfill() -> Dict[str, Any]:
    manifest = _load_manifest()
    active_existing = FinancialSchedule.query.filter(
        FinancialSchedule.company_id == COMPANY_ID,
        FinancialSchedule.deleted_at.is_(None),
    ).all()
    if any((s.metadata_json or {}).get('migration_schedule_batch_id') == SCHEDULE_BATCH_ID for s in active_existing):
        raise RuntimeError(f'Já existem schedules ativos do lote {SCHEDULE_BATCH_ID}.')

    manifest_by_code = {item['entry_code']: item for item in manifest['entries']}
    entries = FinancialEntry.query.filter(
        FinancialEntry.company_id == COMPANY_ID,
        FinancialEntry.deleted_at.is_(None),
    ).order_by(FinancialEntry.id.asc()).all()
    target_entries = [e for e in entries if (e.metadata_json or {}).get('migration_batch_id') == SOURCE_BATCH_ID]

    created = []
    skipped = []

    try:
        for entry in target_entries:
            if entry.entry_type == 'transfer':
                skipped.append({'entry_code': entry.entry_code, 'reason': 'transfer_not_supported_on_schedule_screen'})
                continue

            source = manifest_by_code.get(entry.entry_code)
            if not source:
                skipped.append({'entry_code': entry.entry_code, 'reason': 'manifest_missing'})
                continue

            allocations = list(source.get('allocations') or [])
            if not allocations:
                skipped.append({'entry_code': entry.entry_code, 'reason': 'missing_allocation'})
                continue

            if entry.financial_schedule_id:
                skipped.append({'entry_code': entry.entry_code, 'reason': 'already_linked', 'schedule_id': entry.financial_schedule_id})
                continue

            schedule_allocations = []
            fallback_chart_account_id = entry.chart_account_id
            fallback_cost_center_id = entry.cost_center_id or 23
            for alloc in allocations:
                chart_code = alloc.get('chart_account_code')
                if not chart_code:
                    raise RuntimeError(f'Rateio sem chart_account_code em {entry.entry_code}')
                chart = db.session.execute(
                    db.text("select id from financial_chart_accounts where company_id=:cid and deleted_at is null and code=:code"),
                    {'cid': COMPANY_ID, 'code': chart_code},
                ).scalar()
                if not chart:
                    raise RuntimeError(f'Plano de contas não encontrado ({chart_code}) em {entry.entry_code}')
                if fallback_chart_account_id is None:
                    fallback_chart_account_id = int(chart)
                schedule_allocations.append({
                    'chart_account_id': int(chart),
                    'cost_center_id': int(fallback_cost_center_id),
                    'allocation_type': 'amount',
                    'allocated_amount': str(alloc.get('amount')),
                    'notes': alloc.get('note') or None,
                    'metadata_json': {
                        'migration_schedule_batch_id': SCHEDULE_BATCH_ID,
                        'source_entry_code': entry.entry_code,
                        'source_batch_id': SOURCE_BATCH_ID,
                    },
                })

            due_date = entry.due_date or entry.competence_date or entry.occurred_on
            competence_date = entry.competence_date or due_date or entry.occurred_on
            if due_date is None or competence_date is None:
                raise RuntimeError(f'Datas insuficientes para schedule de {entry.entry_code}')
            normalized_competence_date = competence_date if competence_date <= due_date else due_date

            schedule_payload = {
                'company_id': COMPANY_ID,                'name': (entry.description or entry.entry_code)[:120],
                'entry_type': entry.entry_type,
                'movement_nature': entry.movement_nature,
                'origin_type': 'migration',
                'status': 'completed' if entry.status == 'settled' else 'active',
                'frequency': 'one_time',
                'interval_value': 1,
                'start_date': normalized_competence_date,
                'competence_date': normalized_competence_date,
                'end_date': due_date,
                'first_due_date': due_date,
                'next_due_date': due_date,
                'description': (entry.description or entry.entry_code)[:255],
                'template_amount': entry.original_amount,
                'currency_code': entry.currency_code or 'BRL',
                'counterparty_id': entry.counterparty_id,
                'chart_account_id': fallback_chart_account_id,
                'cost_center_id': fallback_cost_center_id,
                'created_by_agent': AGENT_NAME,
                'notes': f'[Backfill Schedule][{SCHEDULE_BATCH_ID}] {entry.notes or ""}'.strip(),
                'metadata_json': {
                    'migration_schedule_batch_id': SCHEDULE_BATCH_ID,
                    'migration_source_batch_id': SOURCE_BATCH_ID,
                    'source_entry_code': entry.entry_code,
                    'source_title_key': (entry.metadata_json or {}).get('source_title_key'),
                    'source_excel_row': (entry.metadata_json or {}).get('source_excel_row'),
                    'source_status': (entry.metadata_json or {}).get('source_status'),
                    'source_competence_date_original': str(competence_date),
                    'source_due_date_original': str(due_date),
                    'counterparty_name': source.get('counterparty_name'),
                    'direct_entry': True,
                },
                'allocations': schedule_allocations,
            }

            schedule_data, error = FinancialScheduleService.create_schedule(
                payload=schedule_payload,
                allowed_company_ids=[COMPANY_ID],
                auto_commit=False,
            )
            if error:
                raise RuntimeError(f'Erro ao criar schedule de {entry.entry_code}: {error}')

            schedule_id = int(schedule_data['id'])
            entry_md = dict(entry.metadata_json or {})
            entry_md['migration_schedule_batch_id'] = SCHEDULE_BATCH_ID
            entry_md['migration_schedule_backfill_previous_external_reference'] = entry.external_reference
            entry_md['migration_schedule_backfill_previous_financial_schedule_id'] = entry.financial_schedule_id
            entry_md['migration_schedule_linked_at_utc'] = datetime.utcnow().isoformat()
            entry.external_reference = f'financial_schedule:{schedule_id}'
            entry.financial_schedule_id = schedule_id
            entry.metadata_json = entry_md

            linked_settlements = FinancialSettlement.query.filter(
                FinancialSettlement.company_id == COMPANY_ID,
                FinancialSettlement.financial_entry_id == entry.id,
                FinancialSettlement.deleted_at.is_(None),
            ).all()
            for settlement in linked_settlements:
                settlement_md = dict(settlement.metadata_json or {})
                settlement_md['migration_schedule_batch_id'] = SCHEDULE_BATCH_ID
                settlement_md['migration_schedule_backfill_previous_external_reference'] = settlement.external_reference
                settlement_md['migration_schedule_linked_at_utc'] = datetime.utcnow().isoformat()
                settlement.external_reference = f'financial_schedule:{schedule_id}'
                settlement.metadata_json = settlement_md

            db.session.commit()
            created.append({'entry_code': entry.entry_code, 'schedule_id': schedule_id, 'schedule_code': schedule_data['schedule_code']})

        visible_count = FinancialSchedule.query.filter(
            FinancialSchedule.company_id == COMPANY_ID,
            FinancialSchedule.deleted_at.is_(None),
        ).count()
        result = {
            'ok': True,
            'mode': 'backfill',
            'schedule_batch_id': SCHEDULE_BATCH_ID,
            'source_batch_id': SOURCE_BATCH_ID,
            'created_count': len(created),
            'skipped_count': len(skipped),
            'created_preview': created[:20],
            'skipped': skipped,
            'visible_schedule_count_after': visible_count,
            'processed_at_utc': datetime.utcnow().isoformat(),
        }
        REPORT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        return result
    except Exception as exc:
        db.session.rollback()
        rollback = _rollback(f'Falha no backfill de schedules: {exc}')
        return {
            'ok': False,
            'mode': 'backfill',
            'error': str(exc),
            'rollback': rollback,
        }


def main() -> None:
    import sys
    mode = (sys.argv[1] if len(sys.argv) > 1 else 'backfill').strip().lower()
    app = create_app('production')
    with app.app_context():
        if mode == 'rollback':
            payload = _rollback('Rollback manual do backfill de schedules solicitado pelo operador.')
        else:
            payload = run_backfill()
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

if __name__ == '__main__':
    main()


