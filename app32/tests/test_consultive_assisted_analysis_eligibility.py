from __future__ import annotations

from services.consultive_assisted_analysis_service import ConsultiveAssistedAnalysisService


def test_technical_test_is_never_journey_eligible():
    eligible, reasons = ConsultiveAssistedAnalysisService.evaluate_eligibility(
        analysis_type="technical_test",
        payload={"diagnosis": "Smoke de escrita"},
        protocol_snapshot={"subphase_key": "mission"},
    )
    assert eligible is False
    assert reasons == ["technical_test_not_methodological"]


def test_methodological_mission_requires_human_internal_and_benchmark_evidence():
    eligible, reasons = ConsultiveAssistedAnalysisService.evaluate_eligibility(
        analysis_type="methodological",
        payload={"diagnosis": "Diagnóstico"},
        protocol_snapshot={"subphase_key": "mission"},
    )
    assert eligible is False
    assert set(reasons) == {
        "human_evidence_missing",
        "internal_evidence_missing",
        "risks_missing",
        "recommendations_missing",
        "benchmark_or_justification_missing",
    }


def test_methodological_mission_becomes_eligible_with_minimum_evidence():
    eligible, reasons = ConsultiveAssistedAnalysisService.evaluate_eligibility(
        analysis_type="methodological",
        payload={
            "human_evidence": ["Gestor confirmou público prioritário"],
            "internal_evidence": ["Processo de entrega mapeado"],
            "risks": ["Promessa ampla"],
            "recommendations": ["Reduzir escopo da missão"],
            "benchmark_not_applicable_reason": "Piloto interno aprovado sem pesquisa externa nesta rodada",
        },
        protocol_snapshot={"subphase_key": "mission"},
    )
    assert eligible is True
    assert reasons == []


def test_ineligible_analysis_is_rejected_by_downstream_gates():
    from types import SimpleNamespace
    from services.urgent_business_review_common import UrgentBusinessReviewError

    analysis = SimpleNamespace(analysis_type="technical_test", journey_eligible=False)
    try:
        ConsultiveAssistedAnalysisService._require_journey_eligible(analysis)
    except UrgentBusinessReviewError as exc:
        assert "inelegível" in str(exc)
    else:
        raise AssertionError("Análise técnica não pode passar pelo gate metodológico")


def test_analysis_and_validation_serializers_keep_their_own_contracts():
    from models.consultive_assisted_analysis import AssistedAnalysis, AssistedAnalysisValidation

    analysis = AssistedAnalysis(
        id=7,
        company_id=9,
        front_key="identity",
        status="received",
        analysis_type="technical_test",
        journey_eligible=False,
        eligibility_reasons_json=["technical_test_not_methodological"],
        diagnosis="Smoke",
    )
    validation = AssistedAnalysisValidation(
        id=1, company_id=9, analysis_id=7, squad="client", status="pending"
    )

    assert analysis.to_dict()["analysis_type"] == "technical_test"
    assert analysis.to_dict()["journey_eligible"] is False
    assert validation.to_dict()["status"] == "pending"
    assert "analysis_type" not in validation.to_dict()
