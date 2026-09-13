import inspect

from services.my_work import discovery_service, process_service, project_service


def test_discovery_passes_valid_due_date_window_to_query_services():
    source = inspect.getsource(discovery_service.get_user_activities_v2)

    assert "due_date_start = parse_due_date_filter" in source
    assert "due_date_start=due_date_start" in source
    assert "due_date_end=due_date_end" in source


def test_normalized_sources_apply_window_before_materializing_rows():
    project_source = inspect.getsource(project_service.fetch_normalized_project_rows)
    process_source = inspect.getsource(process_service.fetch_normalized_process_rows)

    assert "ProjectTask.due_date >= due_date_start" in project_source
    assert "ProjectTask.due_date <= due_date_end" in project_source
    assert "ProcessInstance.due_date >= due_date_start" in process_source
    assert "ProcessInstance.due_date <= due_date_end" in process_source
