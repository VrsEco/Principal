from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import configure_mappers

from models import (
    IndicatorLineOfSight,
    OrganizationalIdentity,
    ProcessStrategicAlignmentLink,
    ProcessStrategyProfile,
)


TENANT_SCOPED_MODELS = (
    OrganizationalIdentity,
    ProcessStrategyProfile,
    ProcessStrategicAlignmentLink,
    IndicatorLineOfSight,
)


def _constraint(model, name):
    return next(
        constraint
        for constraint in model.__table__.constraints
        if constraint.name == name
    )


def _constraint_columns(constraint):
    return [column.name for column in constraint.columns]


def test_strategy_alignment_models_are_tenant_scoped():
    for model in TENANT_SCOPED_MODELS:
        company_id = model.__table__.columns.get("company_id")

        assert company_id is not None, model.__tablename__
        assert company_id.nullable is False, model.__tablename__


def test_strategy_alignment_relationships_configure_with_composite_keys():
    configure_mappers()


def test_organizational_identity_is_single_row_per_company():
    constraint = _constraint(
        OrganizationalIdentity,
        "uq_organizational_identities_company",
    )

    assert isinstance(constraint, UniqueConstraint)
    assert _constraint_columns(constraint) == ["company_id"]


def test_process_profile_uses_composite_tenant_fk():
    constraint = _constraint(
        ProcessStrategyProfile,
        "fk_process_strategy_profiles_company_process",
    )

    assert isinstance(constraint, ForeignKeyConstraint)
    assert _constraint_columns(constraint) == ["company_id", "process_id"]


def test_alignment_link_type_is_constrained():
    constraint = _constraint(
        ProcessStrategicAlignmentLink,
        "ck_process_alignment_links_type",
    )

    assert isinstance(constraint, CheckConstraint)
    assert "strategic_objective" in str(constraint.sqltext)
    assert "policy" in str(constraint.sqltext)


def test_indicator_line_of_sight_is_unique_by_company_pair():
    constraint = _constraint(
        IndicatorLineOfSight,
        "uq_indicator_line_of_sight_company_pair",
    )

    assert isinstance(constraint, UniqueConstraint)
    assert _constraint_columns(constraint) == [
        "company_id",
        "process_indicator_id",
        "corporate_indicator_id",
    ]


def test_strategy_alignment_to_dict_preserves_structured_payloads():
    identity = OrganizationalIdentity(
        id=1,
        company_id=7,
        mission="Economizar água",
        values_json=[{"name": "Sustentabilidade"}],
        swot_json={"strengths": ["marca"]},
    )
    link = ProcessStrategicAlignmentLink(
        id=2,
        company_id=7,
        process_id=10,
        link_type="strategic_objective",
        target_ref_type="okr_global",
        target_ref_id=99,
        target_key="okr_global:99",
        contribution_weight=Decimal("0.7500"),
    )

    assert identity.to_dict()["values"] == [{"name": "Sustentabilidade"}]
    assert identity.to_dict()["structured"] is True
    assert link.to_dict()["contribution_weight"] == 0.75
