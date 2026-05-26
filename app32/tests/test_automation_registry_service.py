from services.automation_registry_service import AutomationRegistryService


def test_automation_registry_service_normalizes_filters():
    filters = AutomationRegistryService.normalize_filters(
        {
            "module_key": " Contracts ",
            "origin_type": " Native ",
            "status": " Active ",
            "search": " faturamento ",
            "only_error": "sim",
            "only_approval": "0",
        }
    )

    assert filters["module_key"] == "contracts"
    assert filters["origin_type"] == "native"
    assert filters["status"] == "active"
    assert filters["search"] == "faturamento"
    assert filters["only_error"] is True
    assert filters["only_approval"] is False
