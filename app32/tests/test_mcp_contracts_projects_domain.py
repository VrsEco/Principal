from src.intelligence.mcp_contracts import APP32_CRUD_CONTRACTS_MANIFEST


def test_projects_contract_marks_project_crud_and_task_delete_as_implemented():
    projects = APP32_CRUD_CONTRACTS_MANIFEST.get_domain("projects")

    assert projects is not None
    implemented = {(op.action, op.entity, op.implementation_status) for op in projects.operations}

    assert ("create", "project", "implemented") in implemented
    assert ("list", "project", "implemented") in implemented
    assert ("read", "project", "implemented") in implemented
    assert ("update", "project", "implemented") in implemented
    assert ("delete", "project", "implemented") in implemented
    assert ("delete", "project_task", "implemented") in implemented
