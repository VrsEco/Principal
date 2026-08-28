from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".agent" / "skills" / "versus-modelagem-processos-bpmn" / "scripts" / "validar_bpmn_versus.py"
SPEC = importlib.util.spec_from_file_location("validar_bpmn_versus", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


VALID = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs">
  <process id="Process_1" isExecutable="false">
    <laneSet id="LaneSet_1"><lane id="Lane_1" name="Comercial"><flowNodeRef>Task_1</flowNodeRef></lane></laneSet>
    <startEvent id="Start_1" />
    <userTask id="Task_1" name="AA.C.2.1.1.01 - Qualificar oportunidade" />
    <endEvent id="End_1" />
    <sequenceFlow id="F1" sourceRef="Start_1" targetRef="Task_1" />
    <sequenceFlow id="F2" sourceRef="Task_1" targetRef="End_1" />
  </process>
</definitions>"""


def test_accepts_connected_flow_with_canonical_code() -> None:
    result = MODULE.validate_bpmn(VALID, "AA.C.2.1.1")
    assert result["ok"] is True
    assert result["summary"]["tasks"] == 1


def test_rejects_activity_from_another_process_code() -> None:
    result = MODULE.validate_bpmn(VALID.replace("AA.C.2.1.1.01", "AA.C.9.9.9.01"), "AA.C.2.1.1")
    assert result["ok"] is False
    assert any("fora da codificação" in item for item in result["errors"])


def test_rejects_orphan_activity() -> None:
    orphan = VALID.replace(
        '<endEvent id="End_1" />',
        '<userTask id="Task_2" name="AA.C.2.1.1.02 - Registrar oportunidade" /><endEvent id="End_1" />',
    ).replace('</lane>', '<flowNodeRef>Task_2</flowNodeRef></lane>')
    result = MODULE.validate_bpmn(orphan, "AA.C.2.1.1")
    assert result["ok"] is False
    assert any("não alcançável" in item for item in result["errors"])


def test_accepts_converging_gateway_with_single_outgoing_flow() -> None:
    converging = """<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" id="Defs">
  <process id="Process_1" isExecutable="false">
    <laneSet id="LaneSet_1"><lane id="Lane_1" name="Comercial">
      <flowNodeRef>Task_1</flowNodeRef><flowNodeRef>Task_2</flowNodeRef><flowNodeRef>Task_3</flowNodeRef>
    </lane></laneSet>
    <startEvent id="Start_1" />
    <exclusiveGateway id="Split_1" name="Qual caminho?" />
    <userTask id="Task_1" name="AA.C.2.1.1.01 - Analisar caminho A" />
    <userTask id="Task_2" name="AA.C.2.1.1.02 - Analisar caminho B" />
    <exclusiveGateway id="Merge_1" />
    <userTask id="Task_3" name="AA.C.2.1.1.03 - Consolidar resultado" />
    <endEvent id="End_1" />
    <sequenceFlow id="F1" sourceRef="Start_1" targetRef="Split_1" />
    <sequenceFlow id="F2" sourceRef="Split_1" targetRef="Task_1" />
    <sequenceFlow id="F3" sourceRef="Split_1" targetRef="Task_2" />
    <sequenceFlow id="F4" sourceRef="Task_1" targetRef="Merge_1" />
    <sequenceFlow id="F5" sourceRef="Task_2" targetRef="Merge_1" />
    <sequenceFlow id="F6" sourceRef="Merge_1" targetRef="Task_3" />
    <sequenceFlow id="F7" sourceRef="Task_3" targetRef="End_1" />
  </process>
</definitions>"""
    result = MODULE.validate_bpmn(converging, "AA.C.2.1.1")
    assert result["ok"] is True
    assert not any("Merge_1" in item and "apenas uma saída" in item for item in result["warnings"])
