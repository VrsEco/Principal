from app32.services.rbac_permission_catalog_service import RbacPermissionCatalogService


def test_normalize_payload_preserves_legacy_and_nested_keys():
    payload = {
        "projects": ["view", "edit", "invalid"],
        "projects.tasks": ["view", "assign"],
        "financial": "view",
        "__schema_version__": 1,
    }

    normalized = RbacPermissionCatalogService.normalize_payload(payload)

    assert normalized["projects"] == ["view", "edit"]
    assert normalized["projects.tasks"] == ["view", "assign"]
    assert normalized["financial"] == ["view"]
    assert normalized["__schema_version__"] == 3


def test_tree_for_payload_marks_selected_actions():
    payload = {
        "projects": ["view", "edit"],
        "projects.tasks.board": ["view", "change_status"],
    }

    tree = RbacPermissionCatalogService.tree_for_payload(payload)
    projects = next(item for item in tree if item["key"] == "projects")
    tasks = next(item for item in projects["children"] if item["key"] == "projects.tasks")
    board = next(item for item in tasks["children"] if item["key"] == "projects.tasks.board")

    assert projects["selected_actions"] == ["view", "edit"]
    assert board["selected_actions"] == ["view", "change_status"]
    assert projects["granted_count"] >= 4


def test_has_permission_uses_flat_map_compatibility():
    payload = {
        "projects": ["view", "edit"],
        "projects.hours": ["approve"],
    }

    assert RbacPermissionCatalogService.has_permission(payload, "projects", "view") is True
    assert RbacPermissionCatalogService.has_permission(payload, "projects.hours", "approve") is True
    assert RbacPermissionCatalogService.has_permission(payload, "projects", "delete") is False


def test_catalog_covers_systemic_modules_screens_apis_and_tools():
    catalog = RbacPermissionCatalogService.get_catalog()
    node_map = RbacPermissionCatalogService.node_map()

    assert catalog["schema_version"] == 3
    assert "configure" in {item["key"] for item in catalog["actions"]}
    assert "execute" in {item["key"] for item in catalog["actions"]}
    assert len(catalog["roots"]) >= 10
    assert len(node_map) >= 110

    assert "companies.structure.roles" in node_map
    assert "financial.screens.budget" in node_map
    assert "operations.screens.ai_mcp_console" in node_map
    assert "agents.api.chat" in node_map
    assert "mcp.catalog.permission_matrix" in node_map
    assert "integrations.webhooks.telegram" in node_map

    preset_keys = {preset["key"] for preset in catalog["presets"]}
    assert "admin_unidade" in preset_keys
    assert "financeiro" in preset_keys
    assert "auditor_leitura" in preset_keys
