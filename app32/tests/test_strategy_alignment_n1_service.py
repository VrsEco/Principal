import pytest

from services.strategy_alignment_n1_service import StrategyAlignmentN1Service


def test_alignment_analysis_flags_core_gaps_from_structured_records():
    result = StrategyAlignmentN1Service.build_alignment_analysis_from_records(
        company_id=1,
        identity={
            "strategic_objectives": [
                {"key": "obj-crescer", "objective": "Crescer com eficiência"},
                {"key": "obj-esg", "objective": "Liderar ESG"},
            ],
            "pillars": [{"key": "pilar-eficiencia", "name": "Eficiência"}],
            "value_propositions": [{"key": "vp-industria", "segment": "Indústria"}],
            "differentials": [
                {"key": "dif-iot", "name": "IoT proprietário"},
                {"key": "dif-sem-processo", "name": "Consultoria regulatória"},
            ],
            "essential_competencies": [{"key": "comp-dados", "name": "Dados"}],
            "policies": [{"key": "pol-qualidade", "name": "Qualidade"}],
            "values": [{"key": "valor-sustentabilidade", "name": "Sustentabilidade"}],
        },
        processes=[
            {"id": 10, "name": "Monitorar consumo"},
            {"id": 20, "name": "Faturar cliente"},
        ],
        profiles=[
            {"process_id": 10, "objective": "Reduzir perdas de água", "maturity_level": "inicial"},
            {"process_id": 20, "objective": None, "strategic_criticality": "alta"},
        ],
        links=[
            {
                "id": 1,
                "process_id": 10,
                "link_type": "strategic_objective",
                "target_key": "obj-crescer",
            },
            {
                "id": 2,
                "process_id": 10,
                "link_type": "strategic_pillar",
                "target_key": "pilar-eficiencia",
            },
            {
                "id": 3,
                "process_id": 10,
                "link_type": "value_proposition",
                "target_key": "vp-industria",
            },
            {
                "id": 4,
                "process_id": 10,
                "link_type": "differential",
                "target_key": "dif-iot",
            },
        ],
        process_indicators=[
            {"id": 100, "name": "Lead time de instalação", "process_id": 10},
            {"id": 200, "name": "Acurácia de faturamento", "process_id": 20},
        ],
        corporate_indicators=[{"id": 900, "name": "Margem EBITDA"}],
        indicator_line_of_sight=[
            {"id": 1, "process_indicator_id": 100, "corporate_indicator_id": 900},
        ],
    )

    assert result["analysis_id"] == "strategic_alignment_n1"
    assert result["read_model"] == "strategic.alignment_n1"
    assert [item["key"] for item in result["gaps"]["objectives_without_process"]] == ["obj-esg"]
    assert [item["id"] for item in result["gaps"]["processes_without_objective"]] == [20]
    assert [item["id"] for item in result["gaps"]["processes_without_purpose"]] == [20]
    assert [item["key"] for item in result["gaps"]["differentials_without_process"]] == ["dif-sem-processo"]
    assert [item["key"] for item in result["gaps"]["values_without_policy"]] == ["valor-sustentabilidade"]
    assert [item["id"] for item in result["gaps"]["process_indicators_without_corporate"]] == [200]
    assert result["gaps"]["objectives_without_process"][0]["gap_status"] == "unmapped"
    assert result["summary"]["gap_counts"]["objectives_without_process"] == 1
    assert result["completeness"]["overall_pct"] is not None
    assert result["completeness"]["by_block"]["traceability"]["pct"] < 100
    assert result["completeness"]["gap_status_counts"]["objectives_without_process"]["unmapped"] == 1
    assert {signal["signal_type"] for signal in result["risk_signals"]} >= {
        "differential_low_maturity_process",
        "high_criticality_process_without_objective",
        "process_indicator_without_corporate_line_of_sight",
    }
    assert result["recommended_actions"][0]["priority"] == "P0"
    assert result["recommended_actions"][0]["target_label"]
    assert result["crossings"]["process_to_objectives"][0]["process"]["name"] == "Monitorar consumo"


def test_alignment_analysis_matches_okr_target_by_ref_id():
    result = StrategyAlignmentN1Service.build_alignment_analysis_from_records(
        company_id=1,
        identity={},
        processes=[{"id": 10, "name": "Processo core"}],
        profiles=[{"process_id": 10, "objective": "Executar OKR"}],
        links=[
            {
                "id": 1,
                "process_id": 10,
                "link_type": "strategic_objective",
                "target_ref_type": "okr_global",
                "target_ref_id": 77,
            }
        ],
        process_indicators=[],
        corporate_indicators=[],
        indicator_line_of_sight=[],
        okr_objectives=[
            {
                "key": "okr_global:77",
                "target_ref_type": "okr_global",
                "target_ref_id": 77,
                "objective": "Aumentar receita recorrente",
            }
        ],
    )

    assert result["gaps"]["objectives_without_process"] == []
    assert result["crossings"]["process_to_objectives"][0]["target"]["objective"] == "Aumentar receita recorrente"


def test_alignment_analysis_ignores_non_confirmed_structured_items():
    result = StrategyAlignmentN1Service.build_alignment_analysis_from_records(
        company_id=1,
        identity={
            "strategic_objectives": [
                {"key": "obj-confirmado", "objective": "Confirmado", "status": "confirmed"},
                {"key": "obj-pendente", "objective": "Pendente", "status": "pending"},
            ],
            "differentials": [
                {"key": "dif-draft", "name": "Draft", "status": "draft"},
            ],
        },
        processes=[{"id": 10, "name": "Processo core"}],
        profiles=[{"process_id": 10, "objective": "Executar", "status": "confirmed"}],
        links=[
            {
                "id": 1,
                "process_id": 10,
                "link_type": "strategic_objective",
                "target_key": "obj-confirmado",
            },
            {
                "id": 2,
                "process_id": 10,
                "link_type": "differential",
                "target_key": "dif-draft",
                "status": "pending",
            },
        ],
        process_indicators=[],
        corporate_indicators=[],
        indicator_line_of_sight=[],
    )

    assert result["summary"]["strategic_objectives"] == 1
    assert result["summary"]["differentials"] == 0
    assert result["gaps"]["objectives_without_process"] == []
    assert result["crossings"]["process_to_differentials"] == []


def test_maturation_summary_reports_open_backlog_and_block_maturity():
    summary = StrategyAlignmentN1Service._maturation_summary(
        [
            {"block_type": "identity", "status": "pending"},
            {"block_type": "identity", "status": "confirmed"},
            {"block_type": "alignment_link", "status": "draft"},
            {"block_type": "alignment_link", "status": "rejected"},
        ]
    )

    assert summary["backlog_open"] == 2
    assert summary["by_status"]["confirmed"] == 1
    assert summary["by_block"]["identity"]["canonical_confirmed"] == 1
    assert summary["by_block"]["identity"]["backlog_open"] == 1
    assert summary["by_block"]["identity"]["maturity_pct"] == 50


def test_alignment_service_blocks_company_outside_accessible_scope():
    with pytest.raises(PermissionError, match="escopo analítico"):
        StrategyAlignmentN1Service._ensure_access(99, accessible_company_ids=[1, 2])
