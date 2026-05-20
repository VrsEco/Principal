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
    assert normalized["__schema_version__"] == 2


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
