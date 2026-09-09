from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_DIR = APP_DIR.parent


def _read(relative_path: str) -> str:
    return (REPOSITORY_DIR / relative_path).read_text(encoding="utf-8")


def test_date_utils_parse_date_only_as_a_local_calendar_day():
    source = _read("static/js/date_utils.js")

    assert "new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))" in source
    assert "function todayIso(date = new Date())" in source
    assert "window.App32DateUtils" in source


def test_base_layouts_load_calendar_date_utils_before_page_content():
    for relative_path, content_marker in (
        ("app32/templates/base.html", "{% block content %}"),
        ("app32/templates/layouts/base.html", "{% block layout %}"),
    ):
        source = _read(relative_path)
        assert "js/date_utils.js" in source
        assert source.index("js/date_utils.js") < source.index(content_marker)


def test_date_inputs_do_not_default_to_utc_calendar_day():
    forbidden_patterns = (
        "new Date().toISOString().split('T')[0]",
        "new Date().toISOString().slice(0, 10)",
    )
    source_files = [
        *APP_DIR.joinpath("templates").rglob("*.html"),
        *REPOSITORY_DIR.joinpath("static/js").rglob("*.js"),
    ]

    for source_file in source_files:
        source = source_file.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            assert pattern not in source, f"UTC date-only default in {source_file}"


def test_calendar_date_sensitive_screens_use_shared_local_contract():
    expected_references = {
        "static/js/projects.js": "window.App32DateUtils.parseCalendarDate",
        "static/js/sapiens_knowledge.js": "window.App32DateUtils.formatCalendarDatePtBr",
        "app32/templates/modules/projects/project_analysis.html": "window.App32DateUtils.todayIso()",
        "app32/templates/modules/indicators/indicator_details_v2.html": "window.App32DateUtils.startOfLocalDay",
        "app32/templates/legacy/grv_projects_analysis.html": "window.App32DateUtils.parseCalendarDate",
    }

    for relative_path, expected_reference in expected_references.items():
        assert expected_reference in _read(relative_path)
