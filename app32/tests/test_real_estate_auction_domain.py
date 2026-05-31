from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import configure_mappers

from models import (
    RealEstateAuctionAttachment,
    RealEstateAuctionDueDiligence,
    RealEstateAuctionEvent,
    RealEstateAuctionFinancialSheet,
    RealEstateAuctionImportJob,
    RealEstateAuctionImportJobItem,
    RealEstateAuctionProperty,
    RealEstateAuctionSource,
    RealEstateAuctionTenantSettings,
)


TENANT_SCOPED_MODELS = (
    RealEstateAuctionProperty,
    RealEstateAuctionEvent,
    RealEstateAuctionFinancialSheet,
    RealEstateAuctionDueDiligence,
    RealEstateAuctionAttachment,
    RealEstateAuctionSource,
    RealEstateAuctionImportJob,
    RealEstateAuctionImportJobItem,
    RealEstateAuctionTenantSettings,
)


def _constraint(model, name):
    return next(
        constraint
        for constraint in model.__table__.constraints
        if constraint.name == name
    )


def _constraint_columns(constraint):
    return [column.name for column in constraint.columns]


def test_real_estate_auction_models_are_tenant_scoped():
    for model in TENANT_SCOPED_MODELS:
        company_id = model.__table__.columns.get("company_id")

        assert company_id is not None, model.__tablename__
        assert company_id.nullable is False, model.__tablename__


def test_real_estate_auction_relationships_configure_with_composite_keys():
    configure_mappers()


def test_property_code_uniqueness_is_company_scoped():
    constraint = _constraint(
        RealEstateAuctionProperty,
        "uq_re_auction_properties_company_code",
    )

    assert isinstance(constraint, UniqueConstraint)
    assert _constraint_columns(constraint) == ["company_id", "code"]


def test_property_exposes_composite_company_id_constraint_for_child_fk():
    constraint = _constraint(
        RealEstateAuctionProperty,
        "uq_re_auction_properties_company_id",
    )

    assert isinstance(constraint, UniqueConstraint)
    assert _constraint_columns(constraint) == ["company_id", "id"]


def test_child_tables_use_composite_tenant_foreign_keys():
    expected_constraints = {
        RealEstateAuctionEvent: ("fk_re_auction_events_company_property", ["company_id", "property_id"]),
        RealEstateAuctionFinancialSheet: ("fk_re_auction_financial_sheets_company_property", ["company_id", "property_id"]),
        RealEstateAuctionDueDiligence: ("fk_re_auction_due_diligence_company_property", ["company_id", "property_id"]),
        RealEstateAuctionAttachment: ("fk_re_auction_attachments_company_property", ["company_id", "property_id"]),
        RealEstateAuctionImportJob: ("fk_re_auction_import_jobs_company_source", ["company_id", "source_id"]),
        RealEstateAuctionImportJobItem: ("fk_re_auction_import_items_company_job", ["company_id", "job_id"]),
    }

    for model, (constraint_name, columns) in expected_constraints.items():
        constraint = _constraint(model, constraint_name)

        assert isinstance(constraint, ForeignKeyConstraint)
        assert _constraint_columns(constraint) == columns


def test_import_job_item_fingerprint_uniqueness_is_tenant_scoped():
    constraint = _constraint(
        RealEstateAuctionImportJobItem,
        "uq_re_auction_import_items_company_job_fp",
    )

    assert isinstance(constraint, UniqueConstraint)
    assert _constraint_columns(constraint) == ["company_id", "job_id", "fingerprint"]


def test_tenant_settings_are_single_row_per_company():
    constraint = _constraint(
        RealEstateAuctionTenantSettings,
        "uq_re_auction_tenant_settings_company",
    )

    assert isinstance(constraint, UniqueConstraint)
    assert _constraint_columns(constraint) == ["company_id"]


def test_real_estate_auction_to_dict_preserves_company_and_financial_values():
    property_row = RealEstateAuctionProperty(
        id=10,
        company_id=7,
        code="GDI-001",
        address="Rua Exemplo, 100",
        city="Salvador",
        state="BA",
        occupied=True,
        status="in_analysis",
        triage_status="pending",
        appraisal_value=Decimal("450000.00"),
        metadata_json={"origin": "gandu_pilot"},
        auction_won_at=datetime(2026, 5, 31, 9, 0, 0),
    )
    sheet = RealEstateAuctionFinancialSheet(
        id=20,
        company_id=7,
        property_id=10,
        winning_bid=Decimal("300000.00"),
        projected_sale_value=Decimal("390000.00"),
        last_calculation_snapshot_json={"margin": "target"},
    )
    settings = RealEstateAuctionTenantSettings(
        id=30,
        company_id=7,
        module_enabled=True,
        display_name="Gandu Invest",
        code_prefix="GDI",
        settings_json={"default_bank": "Caixa"},
    )

    property_payload = property_row.to_dict()
    sheet_payload = sheet.to_dict()
    settings_payload = settings.to_dict()

    assert property_payload["company_id"] == 7
    assert property_payload["appraisal_value"] == 450000.00
    assert property_payload["auction_won_at"] == "2026-05-31T09:00:00"
    assert property_payload["metadata_json"] == {"origin": "gandu_pilot"}
    assert sheet_payload["company_id"] == 7
    assert sheet_payload["winning_bid"] == 300000.00
    assert sheet_payload["last_calculation_snapshot_json"] == {"margin": "target"}
    assert settings_payload["module_enabled"] is True
    assert settings_payload["settings_json"] == {"default_bank": "Caixa"}
