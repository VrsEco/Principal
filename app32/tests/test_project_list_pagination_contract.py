from flask import Flask
from pathlib import Path

from api.resources.project import PROJECT_LIST_MAX_PER_PAGE, _project_list_pagination_args


def _app():
    return Flask(__name__)


def test_project_list_pagination_is_opt_in_for_legacy_clients():
    with _app().test_request_context('/api/projects'):
        assert _project_list_pagination_args() == (False, 1, PROJECT_LIST_MAX_PER_PAGE)


def test_project_list_pagination_normalizes_page_and_caps_page_size():
    with _app().test_request_context('/api/projects?paginated=true&page=-3&per_page=999'):
        assert _project_list_pagination_args() == (True, 1, PROJECT_LIST_MAX_PER_PAGE)


def test_project_list_pagination_rejects_zero_page_size_by_normalizing_it():
    with _app().test_request_context('/api/projects?paginated=true&page=2&per_page=0'):
        assert _project_list_pagination_args() == (True, 2, 1)


def test_project_list_pagination_keeps_tenant_scope_and_has_database_index():
    root = Path(__file__).resolve().parents[1]
    resource = (root / 'api' / 'resources' / 'project.py').read_text(encoding='utf-8')
    model = (root / 'models' / 'project.py').read_text(encoding='utf-8')
    migration = (
        root / 'migrations' / 'versions' / '20260913_1200_add_project_list_pagination_index.py'
    ).read_text(encoding='utf-8')

    assert 'Project.query.filter_by(company_id=company_id)' in resource
    assert 'query.offset((page - 1) * per_page).limit(per_page).all()' in resource
    assert '"has_more": page * per_page < int(total or 0)' in resource
    assert 'ix_projects_company_id' in model
    assert 'ix_projects_company_id' in migration
    assert 'down_revision = "20260913_1100"' in migration
