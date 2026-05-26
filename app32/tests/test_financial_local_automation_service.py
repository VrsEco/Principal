from services.financial_local_automation_service import FinancialLocalAutomationService


def test_financial_automation_templates_include_iss_retido():
    templates = FinancialLocalAutomationService.get_schedule_automation_template_options()
    keys = {item["key"] for item in templates}

    assert "settle_iss_withheld_on_settlement" in keys
    assert "manual_retention_release" in keys
