from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def test_sidebar_has_system_tests_subgroup_separate_from_ai():
    sidebar = (BASE_DIR / "templates" / "partials" / "sidebar_standard.html").read_text(encoding="utf-8")

    assert "Testes" in sidebar
    assert 'href="/qa/robot-tests"' in sidebar
    assert "Robô de Testes" in sidebar
    assert 'href="/qa/e2e"' not in sidebar
    assert "Central E2E Técnica" not in sidebar

    ai_block_start = sidebar.index("IA Corporativa")
    ai_block_end = sidebar.index("Testes", ai_block_start)
    ai_block = sidebar[ai_block_start:ai_block_end]

    assert "/qa/robot-tests" not in ai_block
    assert "/qa/e2e" not in ai_block
