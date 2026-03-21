from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (BASE_DIR / relative_path).read_text(encoding="utf-8")


def test_project_manage_board_loads_backlog_human_gate_assets_and_slot():
    content = _read("templates/modules/projects/project_manage.html")

    assert "css/backlog-human-gate.css" in content
    assert "js/backlog-human-gate.js" in content
    assert 'id="backlogHumanGateSection"' in content
    assert 'id="backlogHumanGateBoardSection"' in content
    assert "BacklogHumanGate?.configure" in content
    assert "mountBoardSection" in content


def test_project_analysis_board_loads_backlog_human_gate_assets_and_slot():
    content = _read("templates/modules/projects/project_analysis.html")

    assert "css/backlog-human-gate.css" in content
    assert "js/backlog-human-gate.js" in content
    assert 'id="backlogHumanGateSection"' in content
    assert 'id="backlogHumanGateBoardSection"' in content
    assert "BacklogHumanGate?.configure" in content
    assert "mountBoardSection" in content
