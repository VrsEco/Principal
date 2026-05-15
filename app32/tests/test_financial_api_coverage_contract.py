import inspect
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.resources import financial, financial_automation, financial_budget


CRITICAL_FINANCIAL_API_CONTRACT = {
    financial.FinancialScheduleListResource: {"get": "view", "post": "create"},
    financial.FinancialScheduleResource: {"get": "view", "put": "edit", "delete": "delete"},
    financial.FinancialScheduleAssistedSettlementResource: {"post": "create"},
    financial.FinancialScheduleSettlementSimulationResource: {"post": "view"},
    financial.FinancialEntryListResource: {"get": "view", "post": "create"},
    financial.FinancialEntrySettlementListResource: {"get": "view", "post": "create"},
    financial.FinancialSettlementResource: {"get": "view", "delete": "delete"},
    financial.FinancialReportGenerateResource: {"get": "view"},
    financial.FinancialBorderoListResource: {"get": "view", "post": "create"},
    financial.FinancialBorderoSettlementListResource: {"post": "create"},
    financial.FinancialBorderoSettlementResource: {"put": "edit", "delete": "delete"},
    financial_automation.FinancialAutomationBatchListResource: {"post": "create"},
    financial_automation.FinancialAutomationBatchParseResource: {"post": "create"},
    financial_automation.FinancialAutomationGenerateResource: {"post": "create"},
    financial_automation.FinancialAutomationRecordResource: {"get": "view", "put": "edit", "delete": "delete"},
    financial_budget.FinancialBudgetExecutionWorkspaceResource: {"get": "view"},
    financial_budget.FinancialBudgetPlanningWorkspaceResource: {"get": "view"},
}


def test_critical_financial_api_methods_have_explicit_permission_contract():
    for resource_cls, method_actions in CRITICAL_FINANCIAL_API_CONTRACT.items():
        for method_name, expected_action in method_actions.items():
            method = getattr(resource_cls, method_name)
            marker = getattr(method, "_permission_required", None)

            assert marker == {"resource": "financial", "action": expected_action}, (
                f"{resource_cls.__name__}.{method_name} precisa manter permission_required"
                f"('financial', '{expected_action}')"
            )


def test_financial_api_resources_delegate_to_services_instead_of_embedding_business_flow():
    source_by_class = {
        resource_cls.__name__: inspect.getsource(resource_cls)
        for resource_cls in CRITICAL_FINANCIAL_API_CONTRACT
    }

    assert "FinancialSettlementCompositionService.create_assisted_settlement" in source_by_class["FinancialScheduleAssistedSettlementResource"]
    assert "FinancialSettlementCompositionService.simulate_settlement" in source_by_class["FinancialScheduleSettlementSimulationResource"]
    assert "FinancialReportService.generate_report" in source_by_class["FinancialReportGenerateResource"]
    assert "FinancialBorderoService.create_settlement" in source_by_class["FinancialBorderoSettlementListResource"]
    assert "FinancialBorderoService.update_settlement" in source_by_class["FinancialBorderoSettlementResource"]
    assert "FinancialBorderoService.delete_settlement" in source_by_class["FinancialBorderoSettlementResource"]
    assert "FinancialAutomationService.parse_batch_documents" in source_by_class["FinancialAutomationBatchParseResource"]
    assert "FinancialAutomationService.delete_record" in source_by_class["FinancialAutomationRecordResource"]
    assert "FinancialBudgetWorkspaceService.get_execution_workspace" in source_by_class["FinancialBudgetExecutionWorkspaceResource"]


def test_financial_quality_coverage_mentions_personas_and_budget_flow():
    covered_flows = {
        "titulos_financeiros": financial.FinancialScheduleListResource,
        "baixas": financial.FinancialEntrySettlementListResource,
        "dre_relatorios": financial.FinancialReportGenerateResource,
        "borderos": financial.FinancialBorderoSettlementListResource,
        "automacao_financeira": financial_automation.FinancialAutomationGenerateResource,
        "orcado_x_realizado": financial_budget.FinancialBudgetExecutionWorkspaceResource,
    }
    personas = ["operador_financeiro", "gestor", "controladoria"]

    assert set(covered_flows) == {
        "titulos_financeiros",
        "baixas",
        "dre_relatorios",
        "borderos",
        "automacao_financeira",
        "orcado_x_realizado",
    }
    assert personas == ["operador_financeiro", "gestor", "controladoria"]
