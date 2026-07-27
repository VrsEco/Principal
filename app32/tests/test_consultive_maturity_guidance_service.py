from __future__ import annotations

from services.consultive_maturity_guidance_service import ConsultiveMaturityGuidanceService


def _context(engineering=True):
    return {
        "maturity": {"status": "partial", "score": 60},
        "internal_evidence": [{"label": "Missão", "finding": "Registrada."}],
        "gaps": [],
        "engineering_gaps": ([{"severity": "high", "description": "read model"}] if engineering else []),
    }


def _protocol(subphase="mission"):
    titles = {
        "mission": "Missão",
        "vision": "Visão",
        "values": "Valores",
        "positioning": "Posicionamento",
    }
    versions = {
        "mission": "mission-official-v1.0",
        "vision": "vision-official-v1.0",
        "values": "values-official-v1.0",
        "positioning": "positioning-official-v1.0",
    }
    journey_versions = {
        "mission": "mission-maturity-v1.2",
        "vision": "vision-maturity-v1.0",
        "values": "values-maturity-v1.0",
        "positioning": "positioning-maturity-v1.0",
    }
    questions = {
        "mission": "O que a empresa entrega?",
        "vision": "Onde a empresa quer estar?",
        "values": "Quais princípios são inegociáveis?",
        "positioning": "Quem é o cliente prioritário?",
    }
    return {
        "id": 1,
        "protocol_version": versions[subphase],
        "source": "global",
        "title": f"Protocolo da {titles[subphase]}",
        "depth_level": "simulation",
        "protocol": {
            "journey_version": journey_versions[subphase],
            "investigation_layers": (["gestor_intent", "external_benchmark"] if subphase == "mission" else [f"{subphase}_layer", "external_benchmark"]),
            "required_questions": [questions[subphase]],
        },
    }


def _analysis(*, validations=None, decision=None, status="received", subphase="mission"):
    return {
        "id": 77,
        "company_id": 9,
        "front_key": "identity",
        "status": status,
        "analysis_type": "methodological",
        "journey_eligible": True,
        "eligibility_reasons": [],
        "protocol_snapshot": {"subphase_key": subphase},
        "validations": validations or [],
        "latest_decision": decision,
    }


def _install(monkeypatch, analyses, *, engineering=True, subphase="mission"):
    calls = {}
    monkeypatch.setattr(
        "services.consultive_maturity_guidance_service.BusinessReviewReadModelService.get_structural_front_analysis",
        lambda **kwargs: calls.setdefault("context", kwargs) and _context(engineering),
    )
    monkeypatch.setattr(
        "services.consultive_maturity_guidance_service.ConsultiveProtocolService.resolve_protocol",
        lambda **kwargs: calls.setdefault("protocol", kwargs) and _protocol(subphase),
    )
    monkeypatch.setattr(
        "services.consultive_maturity_guidance_service.ConsultiveAssistedAnalysisService.list_analyses",
        lambda **kwargs: calls.setdefault("analyses", kwargs) and analyses,
    )
    return calls


def test_mission_without_analysis_returns_guided_diagnosis(monkeypatch):
    calls = _install(monkeypatch, [])

    result = ConsultiveMaturityGuidanceService.get_next_action(
        company_id=9, front_key="identity", subphase_key="mission"
    )

    assert result["company_id"] == 9
    assert result["journey_state"] == "collecting_evidence"
    assert result["next_action"]["key"] == "develop_mission_diagnosis"
    assert "O que a empresa entrega?" in result["next_action"]["required_inputs"]
    assert "consultive_register_assisted_analysis" in result["next_action"]["allowed_tools"]
    assert result["next_action"]["human_gate_required"] is True
    assert result["next_action"]["write_policy"] == {
        "write_tools": ["consultive_register_assisted_analysis"],
        "requires_explicit_human_confirmation": True,
        "canonical_write_allowed": False,
    }
    assert result["current_state"]["coverage"]["score"] == 60
    assert result["current_state"]["coverage"]["does_not_prove_methodological_maturity"] is True
    assert result["current_state"]["methodological_maturity"]["status"] == "in_development"
    assert result["current_state"]["methodological_maturity"]["is_mature"] is False
    assert result["current_state"]["methodological_maturity"]["score"] is None
    assert "assisted_analysis_missing" in result["current_state"]["methodological_maturity"]["open_reasons"]
    assert result["protocol"]["investigation_layers"] == ["gestor_intent", "external_benchmark"]
    assert calls["context"]["company_id"] == 9
    assert calls["analyses"]["company_id"] == 9


def test_mission_advances_through_required_squad_validations(monkeypatch):
    client_validated = [{"squad": "client", "status": "validated"}]
    _install(monkeypatch, [_analysis(validations=client_validated)])
    result = ConsultiveMaturityGuidanceService.get_next_action(company_id=9, front_key="identity")
    assert result["journey_state"] == "awaiting_versus_validation"
    assert "consultive_register_squad_validation" in result["next_action"]["allowed_tools"]
    assert result["next_action"]["write_policy"]["requires_explicit_human_confirmation"] is True

    versus_validated = client_validated + [{"squad": "versus", "status": "validated"}]
    _install(monkeypatch, [_analysis(validations=versus_validated)])
    result = ConsultiveMaturityGuidanceService.get_next_action(company_id=9, front_key="identity")
    assert result["journey_state"] == "awaiting_engineering_validation"

    all_validated = versus_validated + [{"squad": "engineering", "status": "validated"}]
    _install(monkeypatch, [_analysis(validations=all_validated)])
    result = ConsultiveMaturityGuidanceService.get_next_action(company_id=9, front_key="identity")
    assert result["journey_state"] == "awaiting_consultant_decision"
    assert result["next_action"]["human_gate_required"] is True
    assert "consultive_register_consultant_decision" in result["next_action"]["allowed_tools"]


def test_rejected_validation_blocks_and_requests_revision(monkeypatch):
    _install(monkeypatch, [_analysis(validations=[{"squad": "client", "status": "needs_adjustment"}])])

    result = ConsultiveMaturityGuidanceService.get_next_action(company_id=9, front_key="identity")

    assert result["journey_state"] == "blocked"
    assert result["next_action"]["key"] == "revise_assisted_analysis"
    assert result["orchestration"]["blocked"] is True


def test_accepted_decision_authorizes_but_does_not_execute_persistence(monkeypatch):
    validations = [
        {"squad": "client", "status": "validated"},
        {"squad": "versus", "status": "validated"},
        {"squad": "engineering", "status": "validated"},
    ]
    _install(monkeypatch, [_analysis(validations=validations, decision={"decision": "accept"})])

    result = ConsultiveMaturityGuidanceService.get_next_action(company_id=9, front_key="identity")

    assert result["journey_state"] == "approved_for_execution"
    assert result["next_action"]["key"] == "persist_approved_mission"
    assert result["next_action"]["human_gate_required"] is True
    assert result["next_action"]["write_policy"]["canonical_write_allowed"] is True
    assert "persistir dado canônico sem autorização" in result["orchestration"]["must_not_execute"]


def test_engineering_validation_is_skipped_without_technical_gap(monkeypatch):
    validations = [
        {"squad": "client", "status": "validated"},
        {"squad": "versus", "status": "validated"},
    ]
    _install(monkeypatch, [_analysis(validations=validations)], engineering=False)

    result = ConsultiveMaturityGuidanceService.get_next_action(company_id=9, front_key="identity")

    assert result["journey_state"] == "awaiting_consultant_decision"
    assert result["current_state"]["engineering_validation_required"] is False


def test_executed_state_only_declares_maturity_without_open_gaps(monkeypatch):
    validations = [
        {"squad": "client", "status": "validated"},
        {"squad": "versus", "status": "validated"},
    ]
    _install(
        monkeypatch,
        [_analysis(validations=validations, decision={"decision": "accept"}, status="converted")],
        engineering=False,
    )

    result = ConsultiveMaturityGuidanceService.get_next_action(company_id=9, front_key="identity")

    maturity = result["current_state"]["methodological_maturity"]
    assert result["journey_state"] == "executed_verified"
    assert maturity["status"] == "mature"
    assert maturity["is_mature"] is True
    assert maturity["open_reasons"] == []


def test_technical_test_is_auditable_but_does_not_advance_journey(monkeypatch):
    technical = _analysis()
    technical.update(
        analysis_type="technical_test",
        journey_eligible=False,
        eligibility_reasons=["technical_test_not_methodological"],
    )
    _install(monkeypatch, [technical], engineering=False)

    result = ConsultiveMaturityGuidanceService.get_next_action(
        company_id=9, front_key="identity", subphase_key="mission"
    )

    state = result["current_state"]
    assert result["journey_version"] == "mission-maturity-v1.2"
    assert result["journey_state"] == "collecting_evidence"
    assert state["latest_analysis_id"] is None
    assert state["latest_received_analysis_id"] == 77
    assert state["latest_received_analysis_type"] == "technical_test"
    assert state["latest_received_journey_eligible"] is False
    assert state["latest_received_eligibility_reasons"] == ["technical_test_not_methodological"]
    assert "latest_analysis_ineligible" in state["methodological_maturity"]["open_reasons"]
    assert result["next_action"]["key"] == "develop_mission_diagnosis"


def test_ineligible_methodological_analysis_does_not_advance_journey(monkeypatch):
    incomplete = _analysis()
    incomplete.update(
        journey_eligible=False,
        eligibility_reasons=["human_evidence_missing", "internal_evidence_missing"],
    )
    _install(monkeypatch, [incomplete], engineering=False)

    result = ConsultiveMaturityGuidanceService.get_next_action(company_id=9, front_key="identity")

    assert result["journey_state"] == "collecting_evidence"
    assert result["current_state"]["latest_received_analysis_id"] == 77
    assert result["current_state"]["latest_analysis_id"] is None


def test_vision_without_analysis_uses_its_own_official_journey(monkeypatch):
    _install(monkeypatch, [], engineering=False, subphase="vision")

    result = ConsultiveMaturityGuidanceService.get_next_action(
        company_id=10, front_key="identity", subphase_key="vision"
    )

    assert result["journey_version"] == "vision-maturity-v1.0"
    assert result["pilot_scope"] is True
    assert result["journey_state"] == "collecting_evidence"
    assert result["next_action"]["key"] == "develop_vision_diagnosis"
    assert result["next_action"]["label"] == "Diagnosticar e amadurecer a Visão"
    assert "Onde a empresa quer estar?" in result["next_action"]["required_inputs"]
    assert result["protocol"]["version"] == "vision-official-v1.0"


def test_values_without_analysis_uses_behavioral_journey(monkeypatch):
    _install(monkeypatch, [], engineering=False, subphase="values")

    result = ConsultiveMaturityGuidanceService.get_next_action(
        company_id=10, front_key="identity", subphase_key="values"
    )

    assert result["journey_version"] == "values-maturity-v1.0"
    assert result["journey_state"] == "collecting_evidence"
    assert result["next_action"]["key"] == "develop_values_diagnosis"
    assert result["next_action"]["label"] == "Diagnosticar e amadurecer os Valores"
    assert "Quais princípios são inegociáveis?" in result["next_action"]["required_inputs"]


def test_values_accepted_decision_authorizes_only_values_persistence(monkeypatch):
    validations = [
        {"squad": "client", "status": "validated"},
        {"squad": "versus", "status": "validated"},
    ]
    analysis = _analysis(
        validations=validations,
        decision={"decision": "accept"},
        subphase="values",
    )
    _install(monkeypatch, [analysis], engineering=False, subphase="values")

    result = ConsultiveMaturityGuidanceService.get_next_action(
        company_id=10, front_key="identity", subphase_key="values"
    )

    assert result["journey_state"] == "approved_for_execution"
    assert result["next_action"]["key"] == "persist_approved_values"
    assert result["next_action"]["label"] == "Persistir e verificar os Valores aprovados"
    assert result["next_action"]["write_policy"]["canonical_write_allowed"] is True


def test_vision_does_not_consume_mission_analysis(monkeypatch):
    _install(
        monkeypatch,
        [_analysis(validations=[{"squad": "client", "status": "validated"}], subphase="mission")],
        engineering=False,
        subphase="vision",
    )

    result = ConsultiveMaturityGuidanceService.get_next_action(
        company_id=10, front_key="identity", subphase_key="vision"
    )

    assert result["journey_state"] == "collecting_evidence"
    assert result["current_state"]["latest_analysis_id"] is None
    assert result["next_action"]["key"] == "develop_vision_diagnosis"


def test_vision_does_not_consume_legacy_analysis_without_subphase(monkeypatch):
    legacy = _analysis(subphase="mission")
    legacy["protocol_snapshot"] = {"subphase_key": None}
    _install(monkeypatch, [legacy], engineering=False, subphase="vision")

    result = ConsultiveMaturityGuidanceService.get_next_action(
        company_id=10, front_key="identity", subphase_key="vision"
    )

    assert result["journey_state"] == "collecting_evidence"
    assert result["current_state"]["latest_analysis_id"] is None


def test_positioning_without_analysis_uses_market_fit_journey(monkeypatch):
    _install(monkeypatch, [], engineering=False, subphase="positioning")

    result = ConsultiveMaturityGuidanceService.get_next_action(
        company_id=10, front_key="identity", subphase_key="positioning"
    )

    assert result["journey_version"] == "positioning-maturity-v1.0"
    assert result["pilot_scope"] is True
    assert result["journey_state"] == "collecting_evidence"
    assert result["next_action"]["key"] == "develop_positioning_diagnosis"
    assert result["next_action"]["label"] == "Diagnosticar e amadurecer o Posicionamento"
    assert "Quem é o cliente prioritário?" in result["next_action"]["required_inputs"]
    assert result["protocol"]["version"] == "positioning-official-v1.0"


def test_positioning_accepted_decision_authorizes_only_positioning_persistence(monkeypatch):
    validations = [
        {"squad": "client", "status": "validated"},
        {"squad": "versus", "status": "validated"},
    ]
    analysis = _analysis(
        validations=validations,
        decision={"decision": "accept"},
        subphase="positioning",
    )
    _install(monkeypatch, [analysis], engineering=False, subphase="positioning")

    result = ConsultiveMaturityGuidanceService.get_next_action(
        company_id=10, front_key="identity", subphase_key="positioning"
    )

    assert result["journey_state"] == "approved_for_execution"
    assert result["next_action"]["key"] == "persist_approved_positioning"
    assert result["next_action"]["label"] == "Persistir e verificar o Posicionamento aprovado"
    assert result["next_action"]["write_policy"]["canonical_write_allowed"] is True


def test_positioning_does_not_consume_values_or_legacy_analysis(monkeypatch):
    legacy = _analysis(subphase="mission")
    legacy["id"] = 78
    legacy["protocol_snapshot"] = {"subphase_key": None}
    _install(
        monkeypatch,
        [
            _analysis(
                validations=[{"squad": "client", "status": "validated"}],
                subphase="values",
            ),
            legacy,
        ],
        engineering=False,
        subphase="positioning",
    )

    result = ConsultiveMaturityGuidanceService.get_next_action(
        company_id=10, front_key="identity", subphase_key="positioning"
    )

    assert result["journey_state"] == "collecting_evidence"
    assert result["current_state"]["latest_analysis_id"] is None
    assert result["current_state"]["latest_received_analysis_id"] is None
