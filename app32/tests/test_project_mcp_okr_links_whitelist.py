from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_project_mcp_service_whitelists_and_validates_okr_links():
    text = _read("services", "project_mcp_service.py")

    assert '"okr_links",' in text
    assert "def _normalize_okr_links(" in text
    assert "OKRGlobal.query.filter(" in text
    assert "OKRArea.query.filter(" in text
    assert "project.okr_links = ProjectMCPService._normalize_okr_links(" in text
    assert "okr_links=normalized_okr_links" in text


def test_create_project_tool_exposes_okr_links_parameter():
    tools_text = _read("src", "intelligence", "tools.py")
    ops_text = _read("src", "intelligence", "tools_domains", "project_ops.py")

    assert "def create_project(company_id: int, name: str, description: str = None, responsible_name: str = None, start_date: str = None, due_date: str = None, okr_links: list[int] = None):" in tools_text
    assert "okr_links: list[int] | None = None," in ops_text
    assert "okr_links=okr_links," in ops_text
