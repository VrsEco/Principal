import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from .real_case_catalog import build_real_case_export, workflow_gap_to_case_stub
from .runner import load_catalog
from .smoke_assisted import build_smoke_assisted_plan
from .taxonomy import classify_result_bucket, infer_failure_class


def test_v3_taxonomia_classifica_falhas_por_classe():
    assert infer_failure_class({"type": "parsing"}) == "parsing"
    assert infer_failure_class({"type": "routing"}) == "routing"
    assert infer_failure_class({"type": "multiturn"}) == "multi_turn"
    assert classify_result_bucket(case={"type": "routing"}, passed=False) == "routing"
    assert classify_result_bucket(case={"type": "routing"}, passed=True) == "passed"


def test_v3_exporta_workflow_gap_para_catalogo_de_caso_real():
    candidate = {
        "id": 702,
        "app_task_code": "AA.J.31.702",
        "channel": "whatsapp",
        "resolution_type": "parser_failed",
        "user_request_text": "Quais as atividades em aberto para Caroline Marques?",
    }

    stub = workflow_gap_to_case_stub(
        candidate,
        chapter="a_consultar",
        case_type="multiturn",
        failure_class="multi_turn",
        expected={"expected_action_key": "my_work.open"},
    )

    assert stub["id"] == "aa_j_31_702"
    assert stub["source"] == "workflow_gap:whatsapp"
    assert stub["expected"]["expected_action_key"] == "my_work.open"


def test_v3_agrupa_exportacao_de_casos_reais():
    export = build_real_case_export(
        [
            {
                "id": 703,
                "app_task_code": "AA.J.31.703",
                "channel": "whatsapp",
                "resolution_type": "routing",
                "user_request_text": "Pode dar como concluida as atividades de IDs: 24 e 323",
            }
        ],
        chapter="c_encerrar",
        case_type="routing",
        failure_class="routing",
    )

    assert "c_encerrar" in export
    assert export["c_encerrar"][0]["id"] == "aa_j_31_703"


def test_v3_gera_plano_de_smoke_assistido_priorizando_casos_reais():
    plan = build_smoke_assisted_plan(load_catalog())

    assert plan["total_cases"] >= 13
    assert plan["chapters"]["a_consultar"]["prioritized_smokes"]
    assert plan["chapters"]["c_encerrar"]["prioritized_smokes"]
