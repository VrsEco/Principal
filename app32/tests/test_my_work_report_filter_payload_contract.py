from pathlib import Path


def test_my_work_report_payload_preserves_empty_project_process_selection():
    repo_root = Path(__file__).resolve().parents[2]
    source = (repo_root / "static" / "js" / "my-work.js").read_text(encoding="utf-8")

    assert "projectsDirectoryCount > 0 && state.selectedProjectIds.length === 0" in source
    assert "filters.project_selection = SELECTION_MODE_NONE" in source
    assert "processesDirectoryCount > 0 && state.selectedProcessIds.length === 0" in source
    assert "filters.process_selection = SELECTION_MODE_NONE" in source


def test_my_work_template_busts_report_filter_asset_cache():
    repo_root = Path(__file__).resolve().parents[2]
    template = (
        repo_root
        / "app32"
        / "templates"
        / "modules"
        / "my_work"
        / "my_work_v2.html"
    ).read_text(encoding="utf-8")

    assert "20260703-mywork-report-filter-selection" in template
