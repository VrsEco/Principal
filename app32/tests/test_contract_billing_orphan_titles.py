"""Dry-run e execução do reprocessamento de títulos órfãos de faturamentos cancelados."""

import json
from datetime import date
from decimal import Decimal

import pytest
from flask import Flask
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

from models import db
from models.contracts import Contract, ContractEvent, ContractNativeBilling, ContractParty
from models.financial import (
    FinancialBordero,
    FinancialBorderoItem,
    FinancialEntry,
    FinancialEntryAllocation,
    FinancialSchedule,
    FinancialSettlement,
)
from services.contract_billing_orphan_titles_service import (
    ACTION_BLOCKED,
    ACTION_CANCEL,
    ACTION_REVIEW,
    OrphanBillingTitlesService,
)

COMPANY_ID = 1


@compiles(JSONB, "sqlite")
def _jsonb_as_json_on_sqlite(element, compiler, **kw):
    return "JSON"


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                ContractParty.__table__,
                Contract.__table__,
                ContractEvent.__table__,
                ContractNativeBilling.__table__,
                FinancialSchedule.__table__,
                FinancialEntry.__table__,
                FinancialEntryAllocation.__table__,
                FinancialSettlement.__table__,
                FinancialBordero.__table__,
                FinancialBorderoItem.__table__,
            ],
        )
        db.session.add(ContractParty(id=27, company_id=COMPANY_ID, code="AL.F.023", name="Cliente Teste"))
        db.session.add(Contract(id=23, company_id=COMPANY_ID, party_id=27, code="AL.N.019", title="Contrato", status="active"))
        yield app
        db.session.remove()


def _billing(billing_id, code, *, status, main_schedule_id, retention="30.00"):
    db.session.add(
        ContractNativeBilling(
            id=billing_id,
            company_id=COMPANY_ID,
            contract_id=23,
            party_id=27,
            billing_code=code,
            status=status,
            competence_start=date(2026, 10, 1),
            competence_end=date(2026, 10, 31),
            issue_date=date(2026, 10, 1),
            gross_amount=Decimal("1000.00"),
            net_amount=Decimal("970.00"),
            idempotency_key=f"key-{billing_id}-{status}",
            metadata_json={
                "retention_amount": float(retention),
                "financial_integration": {
                    "main_schedule_id": main_schedule_id,
                    "satellite_schedule_ids": [main_schedule_id + 1],
                    **({"cancelled_schedule_ids": [main_schedule_id, main_schedule_id + 1]} if status == "cancelled" else {}),
                },
            },
        )
    )


def _group(billing_id, code, main_schedule_id, entry_id, *, status="cancelled", automatic="30.00", real=None, entry_status="partially_settled"):
    _billing(billing_id, code, status=status, main_schedule_id=main_schedule_id)
    for offset, (entry_type, nature, role, amount, st) in enumerate(
        [("receivable", "credit", "main", "1000.00", entry_status), ("payable", "debit", "satellite", "30.00", "settled")]
    ):
        schedule_id = main_schedule_id + offset
        db.session.add(
            FinancialSchedule(
                id=schedule_id,
                company_id=COMPANY_ID,
                schedule_code=f"AG-{schedule_id}",
                name=code,
                entry_type=entry_type,
                movement_nature=nature,
                origin_type="manual",
                status="cancelled" if status == "cancelled" else "active",
                frequency="one_time",
                start_date=date(2026, 10, 1),
                competence_date=date(2026, 10, 1),
                first_due_date=date(2026, 11, 10),
                next_due_date=date(2026, 11, 10),
                description=f"Faturamento contratual {code}",
                template_amount=Decimal(amount),
            )
        )
        db.session.add(
            FinancialEntry(
                id=entry_id + offset,
                company_id=COMPANY_ID,
                entry_code=f"AG-{schedule_id}-2026-11-10",
                entry_type=entry_type,
                movement_nature=nature,
                status=st,
                origin_type="manual",
                description=f"Faturamento contratual {code}",
                financial_schedule_id=schedule_id,
                external_reference=f"financial_schedule:{schedule_id}",
                competence_date=date(2026, 10, 1),
                due_date=date(2026, 11, 10),
                original_amount=Decimal(amount),
                metadata_json={"billing_code": code, "financial_role": role, "contract_native_billing_id": billing_id},
            )
        )
        if automatic:
            db.session.add(
                FinancialSettlement(
                    id=entry_id * 10 + offset,
                    company_id=COMPANY_ID,
                    financial_entry_id=entry_id + offset,
                    settlement_code=f"BX-{entry_id * 10 + offset}",
                    settlement_type="automatic_rule",
                    settlement_status="posted",
                    settlement_date=date(2026, 10, 1),
                    principal_amount=Decimal(automatic),
                    gross_amount=Decimal(automatic),
                    net_amount=Decimal(automatic),
                    metadata_json={"contract_satellite_engine_managed": True},
                )
            )
    if real:
        db.session.add(
            FinancialSettlement(
                id=entry_id * 10 + 5,
                company_id=COMPANY_ID,
                financial_entry_id=entry_id,
                settlement_code=f"REC-{entry_id}",
                settlement_type="manual",
                settlement_status="posted",
                settlement_date=date(2026, 10, 20),
                principal_amount=Decimal(real),
                gross_amount=Decimal(real),
                net_amount=Decimal(real),
                metadata_json={},
            )
        )


@pytest.fixture()
def seeded(app):
    _group(434, "AL.B.378", 2893, 4076)  # só ISS automático -> cancelar
    _group(433, "AL.B.377", 2891, 4074, real="500.00")  # recebimento real -> bloqueado
    _group(432, "AL.B.376", 2889, 4072, automatic="45.00")  # baixa difere da retenção -> revisar
    _group(273, "AL.B.273", 2800, 3900, status="generated")  # faturamento refeito/ativo -> intocado
    db.session.commit()


def _actions():
    groups = OrphanBillingTitlesService.scan(company_id=COMPANY_ID)
    return {group["billing"].billing_code: group["action"] for group in groups}


def test_dry_run_classifies_each_cancelled_billing_and_ignores_active_ones(seeded):
    assert _actions() == {
        "AL.B.378": ACTION_CANCEL,
        "AL.B.377": ACTION_BLOCKED,
        "AL.B.376": ACTION_REVIEW,
    }


def test_dry_run_rows_and_totals(seeded):
    rows = OrphanBillingTitlesService.build_rows(OrphanBillingTitlesService.scan(company_id=COMPANY_ID))
    principal = next(row for row in rows if row["billing_code"] == "AL.B.378" and row["papel"] == "principal")
    assert principal["contrato"] == "AL.N.019"
    assert principal["cliente"] == "Cliente Teste"
    assert principal["valor_original"] == 1000.0
    assert principal["valor_baixado"] == 30.0
    assert principal["saldo_aberto"] == 970.0
    assert principal["tipo_baixa"] == "retencao_automatica"
    assert principal["acao"] == ACTION_CANCEL
    blocked = next(row for row in rows if row["billing_code"] == "AL.B.377" and row["papel"] == "principal")
    assert blocked["tipo_baixa"] == "mista"
    assert "REC-4074" in blocked["motivo"]

    summary = OrphanBillingTitlesService.summarize(rows)
    assert summary["por_acao_receber"][ACTION_CANCEL] == {"titulos": 1, "valor_original": 1000.0, "valor_baixado": 30.0, "saldo_aberto": 970.0}
    assert summary["por_acao"][ACTION_CANCEL]["titulos"] == 2
    assert summary["por_acao"][ACTION_BLOCKED]["titulos"] == 2
    assert summary["por_acao"][ACTION_REVIEW]["titulos"] == 2


def test_dry_run_does_not_change_the_database(seeded):
    before = FinancialEntry.query.filter(FinancialEntry.deleted_at.is_(None)).count()
    OrphanBillingTitlesService.build_rows(OrphanBillingTitlesService.scan(company_id=COMPANY_ID))
    db.session.rollback()
    assert FinancialEntry.query.filter(FinancialEntry.deleted_at.is_(None)).count() == before
    assert FinancialSettlement.query.filter(FinancialSettlement.deleted_at.is_(None)).count() == 9


def test_report_files_are_written_with_all_columns(seeded, tmp_path):
    rows = OrphanBillingTitlesService.build_rows(OrphanBillingTitlesService.scan(company_id=COMPANY_ID))
    files = OrphanBillingTitlesService.write_report(
        rows=rows, summary=OrphanBillingTitlesService.summarize(rows), directory=tmp_path, stem="dry", meta={"company_id": COMPANY_ID}
    )
    header = open(files["csv"], encoding="utf-8-sig").readline().strip().split(";")
    assert header[:3] == ["entry_id", "entry_code", "papel"]
    assert "acao" in header and "tipo_baixa" in header and "valor_baixado" in header
    assert len(json.load(open(files["json"], encoding="utf-8"))["titulos"]) == len(rows) == 6


def test_execute_cancels_only_approved_eligible_groups_and_keeps_the_rest(seeded):
    metrics_before = OrphanBillingTitlesService.ledger_metrics(company_id=COMPANY_ID)
    rows = OrphanBillingTitlesService.build_rows(OrphanBillingTitlesService.scan(company_id=COMPANY_ID))
    approved = {row["entry_id"] for row in rows}  # aprova tudo; só 'cancelar' pode ser executado

    results = OrphanBillingTitlesService.execute(company_id=COMPANY_ID, user_id=14, approved_entry_ids=approved, log=lambda *_: None)

    outcome = {item["billing_code"]: item["resultado"] for item in results}
    assert outcome == {"AL.B.378": "cancelado", "AL.B.377": "ignorado_bloqueado", "AL.B.376": "ignorado_revisar"}
    for entry_id in (4076, 4077):
        entry = db.session.get(FinancialEntry, entry_id)
        assert entry.status == "cancelled" and entry.deleted_at is not None
        assert entry.metadata_json["billing_cancellation"]["cancelled_by_user_id"] == 14
    for entry_id in (4074, 4075, 4072, 4073, 3900, 3901):
        entry = db.session.get(FinancialEntry, entry_id)
        assert entry.deleted_at is None and "billing_cancellation" not in entry.metadata_json
    billing = db.session.get(ContractNativeBilling, 434)
    assert billing.metadata_json["financial_integration"]["cancelled_entry_ids"] == [4076, 4077]

    metrics_after = OrphanBillingTitlesService.ledger_metrics(company_id=COMPANY_ID)
    assert metrics_before["receber_aberto"]["titulos"] - metrics_after["receber_aberto"]["titulos"] == 1
    assert metrics_before["receber_aberto"]["saldo_aberto"] - metrics_after["receber_aberto"]["saldo_aberto"] == 970.0
    assert metrics_before["faturamentos_ativos"] == metrics_after["faturamentos_ativos"]


def test_execute_is_idempotent(seeded):
    approved = {row["entry_id"] for row in OrphanBillingTitlesService.build_rows(OrphanBillingTitlesService.scan(company_id=COMPANY_ID))}
    OrphanBillingTitlesService.execute(company_id=COMPANY_ID, user_id=14, approved_entry_ids=approved, log=lambda *_: None)
    second = OrphanBillingTitlesService.execute(company_id=COMPANY_ID, user_id=14, approved_entry_ids=approved, log=lambda *_: None)

    assert [item for item in second if item["resultado"] == "cancelado"] == []
    assert "AL.B.378" not in _actions()


def test_execute_ignores_titles_not_in_the_approved_dry_run(seeded):
    results = OrphanBillingTitlesService.execute(company_id=COMPANY_ID, user_id=14, approved_entry_ids={999999}, log=lambda *_: None)

    assert results == []
    assert db.session.get(FinancialEntry, 4076).deleted_at is None


def test_execute_cancels_reviewed_billing_only_when_explicitly_accepted(seeded):
    approved = {row["entry_id"] for row in OrphanBillingTitlesService.build_rows(OrphanBillingTitlesService.scan(company_id=COMPANY_ID))}

    results = OrphanBillingTitlesService.execute(
        company_id=COMPANY_ID,
        user_id=14,
        approved_entry_ids=approved,
        accepted_review_billing_codes={"AL.B.376", "AL.B.377"},  # 377 está bloqueado: aceite não libera
        log=lambda *_: None,
    )

    outcome = {item["billing_code"]: item["resultado"] for item in results}
    assert outcome == {"AL.B.378": "cancelado", "AL.B.377": "ignorado_bloqueado", "AL.B.376": "cancelado"}
    assert db.session.get(FinancialEntry, 4072).deleted_at is not None
    assert db.session.get(FinancialEntry, 4074).deleted_at is None
