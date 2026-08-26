import inspect

from api.routes.auth import _load_portal_project_tasks


def test_portal_project_tasks_excludes_soft_deleted_tasks_and_projects():
    source = inspect.getsource(_load_portal_project_tasks)

    assert "ProjectTask.is_deleted.is_(False)" in source
    assert "Project.is_deleted.is_(False)" in source
