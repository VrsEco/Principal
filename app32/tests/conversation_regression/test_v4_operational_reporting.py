import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from .operational_report import (
    build_operational_report,
    render_operational_report_html,
    render_operational_report_json,
)
from .real_case_catalog import (
    build_real_case_backlog_sync_payload,
    build_real_case_export,
    infer_case_type_from_gap_candidate,
    infer_chapter_from_gap_candidate,
    infer_failure_class_from_gap_candidate,
)
from .runner import load_catalog


def test_v4_infere_capitulo_tipo_e_falha_a_partir_do_gap():
    candidate = {
        "id": 801,
        "channel": "whatsapp",
        "resolution_type": "entity_resolution_failed",
        "user_request_text": "Analise as atividades sem responsável de todas as empresas.",
    }

    assert infer_chapter_from_gap_candidate(candidate) == "d_analisar"
    assert infer_case_type_from_gap_candidate(candidate) == "multiturn"
    assert infer_failure_class_from_gap_candidate(candidate) == "multi_turn"


def test_v4_exportacao_automatica_agrupa_gaps_por_capitulo():
    candidates = [
        {
            "id": 802,
            "app_task_code": "AA.J.31.802",
            "channel": "whatsapp",
            "resolution_type": "parser_failed",
            "user_request_text": "Quais as atividades em aberto para Caroline Marques?",
        },
        {
            "id": 803,
            "app_task_code": "AA.J.31.803",
            "channel": "whatsapp",
            "resolution_type": "entity_resolution_failed",
            "user_request_text": "Analise as atividades sem responsável de todas as empresas.",
        },
    ]

    export = build_real_case_export(candidates)

    assert "a_consultar" in export
    assert "d_analisar" in export
    assert export["a_consultar"][0]["failure_class"] == "parsing"
    assert export["d_analisar"][0]["type"] == "multiturn"


def test_v4_monta_payload_de_sync_para_backlog_aa_j_31():
    export = {
        "a_consultar": [
            {
                "id": "aa_j_31_804",
                "failure_class": "routing",
                "source_ref": {
                    "workflow_gap_id": 804,
                    "app_task_code": "AA.J.31.804",
                },
            }
        ]
    }

    payload = build_real_case_backlog_sync_payload(export)

    assert payload["project_code"] == "AA.J.31"
    assert payload["integration"] == "conversation_regression_v4"
    assert payload["items"][0]["app_task_code"] == "AA.J.31.804"
    assert payload["items"][0]["stage"] == "inbox"


def test_v4_gera_relatorio_operacional_json_e_html():
    report = build_operational_report(load_catalog())
    json_report = render_operational_report_json(report)
    html_report = render_operational_report_html(report)

    assert '"total_chapters": 4' in json_report
    assert "Conversation Regression V4" in html_report
    assert "a_consultar" in html_report
    assert "Smoke a_consultar" in html_report
