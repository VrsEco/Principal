import ast
import os


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MIGRATION_PATH = os.path.join(
    ROOT,
    "migrations",
    "versions",
    "20260721_2130_seed_official_vision_values_protocols.py",
)


def _source():
    with open(MIGRATION_PATH, "r", encoding="utf-8") as handle:
        return handle.read()


def test_mvv_protocol_migration_is_valid_and_tenant_safe():
    source = _source()

    ast.parse(source)
    assert 'revision = "20260721_2130"' in source
    assert 'down_revision = "20260721_0900"' in source
    assert '"version": "vision-official-v1.0"' in source
    assert '"version": "values-official-v1.0"' in source
    assert "client_code = 'AA'" in source
    assert "company_id IS NOT DISTINCT FROM CAST(:company_id AS INTEGER)" in source
    assert "company_id=9" not in source.replace(" ", "")
    assert "consultive_assisted_analyses" not in source


def test_vision_protocol_has_complete_methodological_contract():
    source = _source()

    questions = [
        "Onde os gestores querem que a empresa esteja em 3 a 5 anos",
        "Quais evidências mensuráveis permitirão reconhecer que a Visão foi alcançada?",
        "Quais tendências, cenários e premissas externas sustentam ou ameaçam a Visão?",
        "Como a Visão se conecta à Missão, aos Valores, ao Posicionamento e ao Planejamento Estratégico",
    ]
    for question in questions:
        assert question in source

    assert '"vision-maturity-v1.0"' not in source  # versão é construída de forma determinística.
    assert '"future_state_simulation"' in source
    assert "cenários favorável, base e adverso" in source
    assert "Não transforme a Visão em meta" in source


def test_values_protocol_tests_behaviors_and_decisions():
    source = _source()

    questions = [
        "Quais princípios a empresa não negocia",
        "Qual comportamento observável demonstra cada valor no cotidiano?",
        "Quais anticomportamentos violam explicitamente cada valor?",
        "Como processos, políticas, controles e incentivos reforçam ou contradizem cada valor?",
        "Como líderes e equipes devem agir diante de uma violação de valor?",
    ]
    for question in questions:
        assert question in source

    assert '"dilemma_simulation"' in source
    assert "sem copiar listas de valores" in source
    assert '"final_mvv_coherence_review_required": True' in source


def test_paper_spec_and_harness_reference_official_mvv_protocols():
    paths = [
        os.path.join(ROOT, "docs", "papers", "paper_metodo_versus_estruturacao_evolutiva_v1.md"),
        os.path.join(ROOT, "docs", "spec", "contrato_tecnico_analise_assistida_mcp_v1.md"),
        os.path.join(ROOT, "docs", "harnesses", "squad_cliente", "harness_coordenador_cliente_v1.md"),
    ]
    for path in paths:
        body = open(path, "r", encoding="utf-8").read()
        assert "vision-official-v1.0" in body
        assert "values-official-v1.0" in body

    spec = open(paths[1], "r", encoding="utf-8").read()
    assert "Coerência final do MVV" in spec
    harness = open(paths[2], "r", encoding="utf-8").read()
    assert "uma análise de Missão nunca pode avançar Visão ou Valores" in harness
