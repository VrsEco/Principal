import importlib.util
from pathlib import Path


def load(name: str):
    path = Path(__file__).resolve().parents[1] / "scripts" / "qa" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


budget = load("check_agent_context_budget")
handoff = load("generate_agent_handoff")


def write(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def valid_tree(root):
    for relative in budget.MANDATORY_FILES:
        write(root, relative, "# Único heading\nRegra curta.\n")
    write(root, budget.SPEC_PATH, "# SPEC\n")
    write(root, ".agent/skills/gestao_versus_core/SKILL.md", "# Único heading\nVeja docs/spec/politica_orcamento_contexto_v1.md.\n")
    for relative in budget.SQUAD_PROMPTS:
        write(root, relative, "# Prompt\nVeja docs/spec/politica_orcamento_contexto_v1.md.\n")


def test_context_budget_accepts_small_complete_governance_tree(tmp_path):
    valid_tree(tmp_path)
    result = budget.audit(tmp_path)
    assert result["ok"]
    assert result["mandatory_words"] > 0
    assert result["violations"] == []


def test_context_budget_rejects_excess_and_duplicate_heading(tmp_path):
    valid_tree(tmp_path)
    core = tmp_path / ".agent/skills/gestao_versus_core/SKILL.md"
    core.write_text("# Repetido\n# Repetido\n" + ("palavra " * 700), encoding="utf-8")
    result = budget.audit(tmp_path)
    rules = {row["rule"] for row in result["violations"]}
    assert not result["ok"]
    assert {"word_budget", "duplicate_heading", "spec_reference"} <= rules


def test_context_budget_requires_spec_reference_in_every_squad_prompt(tmp_path):
    valid_tree(tmp_path)
    prompt = tmp_path / budget.SQUAD_PROMPTS[1]
    prompt.write_text("# Prompt\nSem vínculo de política.\n", encoding="utf-8")
    result = budget.audit(tmp_path)
    assert any(
        item["file"] == budget.SQUAD_PROMPTS[1] and item["rule"] == "squad_spec_reference"
        for item in result["violations"]
    )


def test_handoff_is_compact_and_omits_empty_sections():
    content = handoff.render_handoff(
        objective="Corrigir autenticação tenant-safe",
        decisions=["Manter company_id obrigatório"],
        files=["app32/api/routes/auth.py"],
        tests=["pytest auth: 4 passaram"],
    )
    assert content.startswith("# Handoff compacto\n")
    assert "## Objetivo" in content
    assert "## Pendências" not in content
    assert "- Manter company_id obrigatório" in content


def test_handoff_requires_objective():
    try:
        handoff.render_handoff(objective="   ")
    except ValueError as error:
        assert "objective" in str(error)
    else:
        raise AssertionError("deveria rejeitar objetivo vazio")
