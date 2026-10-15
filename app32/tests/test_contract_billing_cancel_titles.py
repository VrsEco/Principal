"""Cancelar faturamento nativo de contrato deve cancelar os títulos do ledger.

Cobre `ContractService.cancel_native_billing` + `ContractFinancialService.cancel_billing_titles`
com SQLite em memória e os modelos reais.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from flask import Flask
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

from models import db
from models.contracts import Contract, ContractEvent, ContractNativeBilling
from models.financial import (
    FinancialBordero,
    FinancialBorderoItem,
    FinancialEntry,
    FinancialEntryAllocation,
    FinancialSatelliteExecution,
    FinancialSchedule,
    FinancialScheduleLink,
    FinancialSettlement,
)
from services.contracts_service import ContractService

COMPANY_ID = 1
MAIN_SCHEDULE_ID = 2893
SATELLITE_SCHEDULE_ID = 2894


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
                Contract.__table__,
                ContractEvent.__table__,
                ContractNativeBilling.__table__,
                FinancialSchedule.__table__,
                FinancialScheduleLink.__table__,
                FinancialSatelliteExecution.__table__,
                FinancialEntry.__table__,
                FinancialEntryAllocation.__table__,
                FinancialSettlement.__table__,
                FinancialBordero.__table__,
                FinancialBorderoItem.__table__,
            ],
        )
        yield app
        db.session.remove()


def _schedule(schedule_id, code, entry_type="receivable", nature="credit", amount="1000.00"):
    schedule = FinancialSchedule(
        id=schedule_id,
        company_id=COMPANY_ID,
        schedule_code=code,
        name=code,
        entry_type=entry_type,
        movement_nature=nature,
        origin_type="manual",
        status="active",
        frequency="one_time",
        start_date=date(2026, 10, 1),
        competence_date=date(2026, 10, 1),
        first_due_date=date(2026, 11, 10),
        next_due_date=date(2026, 11, 10),
        description=f"Faturamento contratual {code}",
        template_amount=Decimal(amount),
    )
    db.session.add(schedule)
    return schedule


def _entry(entry_id, schedule_id, code, entry_type="receivable", nature="credit", amount="1000.00", status="partially_settled"):
    entry = FinancialEntry(
        id=entry_id,
        company_id=COMPANY_ID,
        entry_code=code,
        entry_type=entry_type,
        movement_nature=nature,
        status=status,
        origin_type="manual",
        description="Faturamento contratual AL.B.378",
        financial_schedule_id=schedule_id,
        external_reference=f"financial_schedule:{schedule_id}",
        competence_date=date(2026, 10, 1),
        due_date=date(2026, 11, 10),
        original_amount=Decimal(amount),
        metadata_json={"billing_code": "AL.B.378"},
    )
    db.session.add(entry)
    db.session.add(
        FinancialEntryAllocation(
            company_id=COMPANY_ID,
            financial_entry_id=entry_id,
            allocation_type="amount",
            allocated_amount=Decimal(amount),
        )
    )
    return entry


def _settlement(settlement_id, entry_id, code, *, automatic, amount="30.00", reconciliation_status="pending"):
    settlement = FinancialSettlement(
        id=settlement_id,
        company_id=COMPANY_ID,
        financial_entry_id=entry_id,
        settlement_code=code,
        settlement_type="automatic_rule" if automatic else "manual",
        settlement_status="posted",
        settlement_date=date(2026, 10, 1),
        principal_amount=Decimal(amount),
        gross_amount=Decimal(amount),
        net_amount=Decimal(amount),
        reconciliation_status=reconciliation_status,
        metadata_json={"contract_satellite_engine_managed": True} if automatic else {},
    )
    db.session.add(settlement)
    return settlement


def _billing(with_financial=True):
    contract = Contract(id=23, company_id=COMPANY_ID, party_id=27, code="AL.N.019", title="Contrato", status="active")
    integration = (
        {
            "main_schedule_id": MAIN_SCHEDULE_ID,
            "satellite_schedule_ids": [SATELLITE_SCHEDULE_ID],
        }
        if with_financial
        else {}
    )
    billing = ContractNativeBilling(
        id=434,
        company_id=COMPANY_ID,
        contract_id=contract.id,
        party_id=27,
        billing_code="AL.B.378",
        status="generated",
        competence_start=date(2026, 10, 1),
        competence_end=date(2026, 10, 31),
        issue_date=date(2026, 10, 1),
        due_date=date(2026, 11, 10),
        gross_amount=Decimal("1000.00"),
        net_amount=Decimal("970.00"),
        idempotency_key="contract:1:23:2026-10-01:2026-10-31",
        metadata_json={"financial_integration": integration} if integration else {},
    )
    db.session.add_all([contract, billing])
    return billing


def _seed_main_and_satellite(*, main_settlements=()):
    _schedule(MAIN_SCHEDULE_ID, "AG-002102")
    _schedule(SATELLITE_SCHEDULE_ID, "AG-002103", entry_type="payable", nature="debit", amount="30.00")
    _entry(4076, MAIN_SCHEDULE_ID, "AG-002102-2026-11-10")
    _entry(4077, SATELLITE_SCHEDULE_ID, "AG-002103-2026-11-10", entry_type="payable", nature="debit", amount="30.00", status="settled")
    _settlement(4224, 4076, "BX-003908", automatic=True)
    _settlement(4225, 4077, "BX-003909", automatic=True)
    for item in main_settlements:
        db.session.add(item)


def _cancel(reason="Refeito"):
    return ContractService.cancel_native_billing(
        company_id=COMPANY_ID, native_billing_id=434, user_id=14, reason=reason
    )


def test_cancel_billing_without_financial_titles_only_cancels_the_billing(app):
    _billing(with_financial=False)
    db.session.commit()

    result = _cancel()

    assert result.status == "cancelled"
    integration = result.metadata_json["financial_integration"]
    assert integration["cancelled_entry_ids"] == []
    assert integration["reversed_settlement_ids"] == []


def test_cancel_billing_cancels_open_title_and_satellite_without_settlement(app):
    _billing()
    _schedule(MAIN_SCHEDULE_ID, "AG-002102")
    _schedule(SATELLITE_SCHEDULE_ID, "AG-002103", entry_type="payable", nature="debit", amount="30.00")
    _entry(4076, MAIN_SCHEDULE_ID, "AG-002102-2026-11-10", status="posted")
    _entry(4077, SATELLITE_SCHEDULE_ID, "AG-002103-2026-11-10", entry_type="payable", nature="debit", amount="30.00", status="posted")
    db.session.commit()

    _cancel()

    entries = FinancialEntry.query.order_by(FinancialEntry.id).all()
    assert [entry.status for entry in entries] == ["cancelled", "cancelled"]
    assert all(entry.deleted_at is not None for entry in entries)
    assert FinancialEntry.query.filter(FinancialEntry.deleted_at.is_(None)).count() == 0
    assert FinancialEntryAllocation.query.filter(FinancialEntryAllocation.deleted_at.is_(None)).count() == 0


def test_cancel_billing_reverses_automatic_iss_settlements_and_records_audit(app):
    _billing()
    _seed_main_and_satellite()
    db.session.commit()

    result = _cancel(reason="Faturado em duplicidade")

    main = db.session.get(FinancialEntry, 4076)
    satellite = db.session.get(FinancialEntry, 4077)
    assert main.status == "cancelled" and main.deleted_at is not None
    assert satellite.status == "cancelled" and satellite.deleted_at is not None

    settlements = FinancialSettlement.query.order_by(FinancialSettlement.id).all()
    assert all(item.deleted_at is not None and item.settlement_status == "cancelled" for item in settlements)
    assert all(item.metadata_json["reversed_from_contract_billing"] is True for item in settlements)
    # nenhum saldo ativo sobra para os relatórios
    assert FinancialSettlement.query.filter(
        FinancialSettlement.deleted_at.is_(None), FinancialSettlement.settlement_status != "cancelled"
    ).count() == 0

    audit = main.metadata_json["billing_cancellation"]
    assert audit["cancelled_by_user_id"] == 14
    assert audit["reason"] == "Faturado em duplicidade"
    assert audit["billing_code"] == "AL.B.378"
    assert audit["previous_status"] == "partially_settled"
    assert audit["original_amount"] == 1000.0
    assert audit["reversed_settlement_ids"] == [4224]
    assert audit["reversed_settlement_amount"] == 30.0

    integration = result.metadata_json["financial_integration"]
    assert integration["cancelled_entry_ids"] == [4076, 4077]
    assert integration["reversed_settlement_ids"] == [4224, 4225]
    event = ContractEvent.query.filter_by(event_type="contract.billing_cancelled").one()
    assert event.event_payload["cancelled_entry_ids"] == [4076, 4077]


def test_cancel_billing_is_blocked_when_title_has_real_receipt(app):
    _billing()
    _seed_main_and_satellite(main_settlements=[_settlement(4300, 4076, "REC-000531", automatic=False, amount="500.00")])
    db.session.commit()

    with pytest.raises(ValueError) as excinfo:
        _cancel()

    assert "REC-000531" in str(excinfo.value)
    assert "AL.B.378" in str(excinfo.value)
    db.session.rollback()
    # nada foi alterado: faturamento, títulos e baixas continuam como estavam
    assert db.session.get(ContractNativeBilling, 434).status == "generated"
    assert db.session.get(FinancialSchedule, MAIN_SCHEDULE_ID).status == "active"
    assert db.session.get(FinancialSchedule, MAIN_SCHEDULE_ID).deleted_at is None
    assert FinancialEntry.query.filter(FinancialEntry.deleted_at.is_(None)).count() == 2
    assert FinancialSettlement.query.filter(FinancialSettlement.deleted_at.is_(None)).count() == 3


def test_cancel_billing_is_blocked_when_automatic_settlement_was_reconciled(app):
    _billing()
    _seed_main_and_satellite()
    db.session.get(FinancialSettlement, 4224).reconciliation_status = "reconciled"
    db.session.commit()

    with pytest.raises(ValueError) as excinfo:
        _cancel()

    assert "conciliada" in str(excinfo.value)


def test_cancel_billing_is_blocked_when_title_is_in_active_bordero(app):
    _billing()
    _seed_main_and_satellite()
    db.session.add(
        FinancialBordero(
            id=7,
            company_id=COMPANY_ID,
            bordero_code="BORD-007",
            name="Borderô de teste",
            bordero_type="receivable",
            status="open",
            description="Borderô de teste",
        )
    )
    db.session.add(
        FinancialBorderoItem(
            company_id=COMPANY_ID,
            bordero_id=7,
            financial_schedule_id=MAIN_SCHEDULE_ID,
            item_code="BORD-007-01",
            display_order=1,
        )
    )
    db.session.commit()

    with pytest.raises(ValueError) as excinfo:
        _cancel()

    assert "BORD-007" in str(excinfo.value)


def test_cancel_billing_does_not_touch_titles_of_other_billings(app):
    _billing()
    _seed_main_and_satellite()
    _schedule(3000, "AG-003000")
    _entry(5000, 3000, "AG-003000-2026-11-10", status="posted")
    db.session.commit()

    _cancel()

    other = db.session.get(FinancialEntry, 5000)
    assert other.status == "posted" and other.deleted_at is None
    assert "billing_cancellation" not in other.metadata_json


def test_cancel_billing_twice_is_idempotent(app):
    _billing()
    _seed_main_and_satellite()
    db.session.commit()

    first = _cancel()
    first_cancelled_at = db.session.get(FinancialEntry, 4076).deleted_at
    second = _cancel()

    assert first.id == second.id
    assert db.session.get(FinancialEntry, 4076).deleted_at == first_cancelled_at
