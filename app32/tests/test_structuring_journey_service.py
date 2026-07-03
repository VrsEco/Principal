from services.structuring_journey_service import StructuringJourneyService


def _subblock(journey, block_key, subblock_key):
    block = next(item for item in journey["blocks"] if item["key"] == block_key)
    return next(item for item in block["subblocks"] if item["key"] == subblock_key)


def _block(journey, block_key):
    return next(item for item in journey["blocks"] if item["key"] == block_key)


def test_structuring_journey_allows_parallel_identity_subblocks_and_soft_gate():
    journey = StructuringJourneyService.build_structuring_journey_from_records(
        company_id=9,
        identity={
            "mission": "Economizar água",
            "values": [{"key": "sustentabilidade", "name": "Sustentabilidade"}],
        },
        process_areas=[],
        macro_processes=[],
        processes=[],
        profiles=[],
        bpmn_diagrams=[],
        routines=[],
        process_steps=[],
        execution_contracts=[],
        maturation_items=[
            {
                "block_type": "identity",
                "status": "pending",
                "payload": {"identity_field": "vision", "name": "Ser referência"},
            }
        ],
    )

    assert _subblock(journey, "identity", "mission")["status"] == "confirmed"
    assert _subblock(journey, "identity", "values")["status"] == "confirmed"
    assert _subblock(journey, "identity", "vision")["status"] == "pending"
    assert journey["blocks"][0]["gate"]["ready"] is False
    assert journey["blocks"][1]["unlocked"] is False
    assert journey["blocks"][1]["write_blocked"] is False
    assert journey["gate_policy"] == "soft"


def test_structuring_journey_gates_blocks_and_rolls_up_modeling_by_process():
    journey = StructuringJourneyService.build_structuring_journey_from_records(
        company_id=9,
        identity={
            "mission": "Economizar água",
            "vision": "Ser referência",
            "values": [{"key": "sustentabilidade"}],
            "positioning": "Solução de eficiência hídrica para indústrias intensivas em água.",
            "org_chart": {"status": "defined"},
        },
        process_areas=[{"id": 1, "name": "Operações"}],
        macro_processes=[{"id": 10, "area_id": 1, "name": "Atendimento"}],
        processes=[{"id": 100, "macro_id": 10, "name": "Instalar sensores", "responsible": "Ana"}],
        profiles=[{"process_id": 100, "objective": "Instalar com qualidade"}],
        bpmn_diagrams=[
            {
                "id": 5,
                "process_id": 100,
                "bpmn_xml": "<bpmn:process><bpmn:laneSet><bpmn:lane id='l1'/></bpmn:laneSet><bpmn:exclusiveGateway id='g1'/></bpmn:process>",
            }
        ],
        routines=[{"id": 77, "process_id": 100, "name": "Instalar"}],
        process_steps=[{"id": 88, "routine_id": 77, "name": "Separar kit"}],
        execution_contracts=[{"id": 99, "process_id": 100, "is_active": True}],
        indicators=[{"id": 7, "process_id": 100, "source_scope": "process"}],
        indicator_data=[{"id": 70, "indicator_id": 7}],
        maturation_items=[
            {
                "block_type": "processes",
                "status": "confirmed",
                "payload": {"audit": True},
            }
        ],
    )

    assert journey["blocks"][0]["gate"]["ready"] is True
    assert journey["blocks"][1]["gate"]["ready"] is True
    assert journey["blocks"][2]["unlocked"] is True
    assert _subblock(journey, "processes", "architecture")["maturity_pct"] == 100
    assert _subblock(journey, "processes", "modeling")["status"] == "confirmed"
    assert _subblock(journey, "processes", "implementation")["status"] == "confirmed"
    assert _subblock(journey, "processes", "stabilization")["status"] == "confirmed"
    assert _subblock(journey, "processes", "audit")["status"] == "confirmed"
    assert journey["summary"]["blocks_ready"] == 2


def test_structuring_journey_uses_four_canonical_structuring_fronts():
    journey = StructuringJourneyService.build_structuring_journey_from_records(
        company_id=9,
        identity={},
        process_areas=[],
        macro_processes=[],
        processes=[],
        profiles=[],
        bpmn_diagrams=[],
        routines=[],
        process_steps=[],
        execution_contracts=[],
        maturation_items=[],
    )

    assert [block["key"] for block in journey["blocks"]] == [
        "identity",
        "processes",
        "growth_plan",
        "strategic_management",
    ]
    assert [item["key"] for item in _block(journey, "processes")["subblocks"]] == [
        "architecture",
        "modeling",
        "implementation",
        "stabilization",
        "audit",
    ]
    assert [item["key"] for item in _block(journey, "growth_plan")["subblocks"]] == [
        "structured",
        "connected",
        "deployed",
        "linked_to_management",
    ]
    assert [item["key"] for item in _block(journey, "strategic_management")["subblocks"]] == [
        "indicators",
        "cycles",
        "incentives",
        "connection_web",
    ]
