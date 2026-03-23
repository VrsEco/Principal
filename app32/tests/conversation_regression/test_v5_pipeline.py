import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from services.conversation_regression_service import ConversationRegressionService


def test_v5_build_augmented_catalog_mescla_catalogo_base_com_gaps_reais():
    base_catalog = {
        "a_consultar": [
            {"id": "base_1", "type": "routing", "failure_class": "routing", "input": "Base"}
        ]
    }
    candidates = [
        {
            "id": 901,
            "app_task_code": "AA.J.31.901",
            "channel": "whatsapp",
            "resolution_type": "parser_failed",
            "user_request_text": "Quais as atividades em aberto para Caroline Marques?",
        }
    ]

    catalog = ConversationRegressionService.build_augmented_catalog(
        base_catalog=base_catalog,
        workflow_gap_candidates=candidates,
    )

    assert "a_consultar" in catalog
    assert len(catalog["a_consultar"]) == 2
    assert any(case["id"] == "aa_j_31_901" for case in catalog["a_consultar"])


def test_v5_build_snapshot_gera_catalogo_relatorio_e_payload():
    candidates = [
        {
            "id": 902,
            "app_task_code": "AA.J.31.902",
            "channel": "whatsapp",
            "resolution_type": "entity_resolution_failed",
            "user_request_text": "Analise as atividades sem responsável de todas as empresas.",
        }
    ]

    snapshot = ConversationRegressionService.build_snapshot(
        workflow_gap_candidates=candidates,
        base_catalog={"d_analisar": []},
    )

    assert snapshot["catalog"]["d_analisar"][0]["id"] == "aa_j_31_902"
    assert snapshot["real_cases"]["d_analisar"][0]["resolved_in_catalog"] is False
    assert snapshot["report"]["summary"]["total_chapters"] >= 1
    assert snapshot["backlog_sync"]["project_code"] == "AA.J.31"


def test_v5_build_snapshot_marca_caso_real_ja_coberto_no_catalogo():
    candidate = {
        "id": 903,
        "app_task_code": "AA.J.31.903",
        "channel": "whatsapp",
        "resolution_type": "parser_failed",
        "user_request_text": "Quais as atividades em aberto para Caroline Marques?",
    }

    snapshot = ConversationRegressionService.build_snapshot(
        workflow_gap_candidates=[candidate],
        base_catalog={
            "a_consultar": [
                {
                    "id": "base_case",
                    "type": "routing",
                    "failure_class": "routing",
                    "input": "Quais as atividades em aberto para Caroline Marques?",
                }
            ]
        },
    )

    item = snapshot["real_cases"]["a_consultar"][0]
    assert item["resolved_in_catalog"] is True
    assert snapshot["backlog_sync"]["items"][0]["status"] == "completed"


def test_v5_persist_snapshot_grava_artefatos(tmp_path):
    snapshot = ConversationRegressionService.build_snapshot(
        workflow_gap_candidates=[],
        base_catalog={"a_consultar": []},
    )

    paths = ConversationRegressionService.persist_snapshot(
        snapshot,
        output_dir=str(tmp_path),
        stem="qa_conversation",
    )

    assert os.path.exists(paths["catalog_json"])
    assert os.path.exists(paths["report_json"])
    assert os.path.exists(paths["report_html"])
    assert os.path.exists(paths["backlog_sync_json"])
    assert os.path.exists(paths["metadata_json"])
