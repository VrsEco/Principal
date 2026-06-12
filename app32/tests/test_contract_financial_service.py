from decimal import Decimal
from types import SimpleNamespace

import pytest

from models.financial import FinancialSatelliteExecution, FinancialSatellitePolicy, FinancialScheduleLink
from services.contract_financial_service import ContractFinancialService


def test_satellite_policy_templates_include_iss_retido_default():
    templates = ContractFinancialService.get_satellite_policy_template_options()
    keys = {item["key"] for item in templates}

    assert "settle_iss_withheld_on_settlement" in keys
    assert "manual_contractual_retention_release" in keys


def test_satellite_models_to_dict_expose_core_fields():
    policy = FinancialSatellitePolicy(
        id=1,
        company_id=9,
        contract_id=100,
        policy_code="CTR-SAT-001",
        name="ISS retido por baixa",
        satellite_nature="iss_withheld",
        principal_effect_mode="partial_settlement_by_settlement",
        satellite_effect_mode="settle_by_settlement",
        trigger_event="on_partial_settlement",
        settlement_scope="full",
        auto_apply=True,
    )
    link = FinancialScheduleLink(
        id=2,
        company_id=9,
        parent_schedule_id=10,
        child_schedule_id=11,
        policy_id=1,
        link_type="satellite",
        title_nature="iss_withheld",
    )
    execution = FinancialSatelliteExecution(
        id=3,
        company_id=9,
        policy_id=1,
        parent_schedule_id=10,
        child_schedule_id=11,
        trigger_event="on_partial_settlement",
        executed_amount=Decimal("150.75"),
        execution_status="success",
    )

    assert policy.to_dict()["satellite_effect_mode"] == "settle_by_settlement"
    assert link.to_dict()["title_nature"] == "iss_withheld"
    assert execution.to_dict()["executed_amount"] == 150.75


def test_contract_billing_requires_chart_account_and_cost_center_before_financial_title():
    contract = SimpleNamespace(id=55, code="AA.B.008", company_id=9)

    with pytest.raises(ValueError) as excinfo:
        ContractFinancialService._ensure_billing_accounting_dimensions(
            contract=contract,
            chart_account_id=None,
            cost_center_id=None,
        )

    message = str(excinfo.value)
    assert "conta contábil" in message
    assert "centro de resultado" in message
    assert "AA.B.008" in message
