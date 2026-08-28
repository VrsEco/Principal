from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from pathlib import Path


TASK_TYPES = {
    "task", "userTask", "manualTask", "serviceTask", "sendTask",
    "receiveTask", "businessRuleTask", "scriptTask", "callActivity",
}
EVENT_TYPES = {"startEvent", "endEvent"}
GATEWAY_TYPES = {"exclusiveGateway", "parallelGateway", "inclusiveGateway", "eventBasedGateway"}
CODE_RE = re.compile(r"^[A-Z0-9]+(?:\.[A-Z0-9]+)+\.\d{2}\s+-\s+.+")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def validate_bpmn(xml_text: str, process_code: str | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return {"ok": False, "errors": [f"XML inválido: {exc}"], "warnings": [], "summary": {}}

    ids: dict[str, str] = {}
    nodes: dict[str, str] = {}
    names: dict[str, str] = {}
    starts: set[str] = set()
    ends: set[str] = set()
    tasks: set[str] = set()
    gateways: set[str] = set()
    flows: list[tuple[str, str, str]] = []
    lane_membership: defaultdict[str, list[str]] = defaultdict(list)
    lane_count = 0

    for element in root.iter():
        kind = _local(element.tag)
        element_id = element.attrib.get("id")
        if element_id:
            if element_id in ids:
                errors.append(f"Id duplicado: {element_id}.")
            ids[element_id] = kind
        if kind in TASK_TYPES | EVENT_TYPES | GATEWAY_TYPES and element_id:
            nodes[element_id] = kind
            names[element_id] = (element.attrib.get("name") or "").strip()
        if kind == "startEvent" and element_id:
            starts.add(element_id)
        elif kind == "endEvent" and element_id:
            ends.add(element_id)
        elif kind in TASK_TYPES and element_id:
            tasks.add(element_id)
        elif kind in GATEWAY_TYPES and element_id:
            gateways.add(element_id)
        elif kind == "sequenceFlow" and element_id:
            flows.append((element_id, element.attrib.get("sourceRef", ""), element.attrib.get("targetRef", "")))
        elif kind == "lane":
            lane_count += 1
            for child in element:
                if _local(child.tag) == "flowNodeRef" and child.text:
                    lane_membership[child.text.strip()].append(element_id or "lane-sem-id")

    if not starts:
        errors.append("O processo não possui evento de início.")
    if not ends:
        errors.append("O processo não possui evento de fim.")
    if not tasks:
        warnings.append("O processo não possui atividades executáveis.")

    outgoing: defaultdict[str, set[str]] = defaultdict(set)
    incoming: defaultdict[str, set[str]] = defaultdict(set)
    for flow_id, source, target in flows:
        if source not in nodes:
            errors.append(f"{flow_id}: sourceRef inexistente ou não executável ({source}).")
        if target not in nodes:
            errors.append(f"{flow_id}: targetRef inexistente ou não executável ({target}).")
        if source in nodes and target in nodes:
            outgoing[source].add(target)
            incoming[target].add(source)

    reachable: set[str] = set(starts)
    queue = deque(starts)
    while queue:
        current = queue.popleft()
        for target in outgoing[current]:
            if target not in reachable:
                reachable.add(target)
                queue.append(target)

    reverse_reachable: set[str] = set(ends)
    queue = deque(ends)
    while queue:
        current = queue.popleft()
        for source in incoming[current]:
            if source not in reverse_reachable:
                reverse_reachable.add(source)
                queue.append(source)

    for task_id in sorted(tasks):
        name = names.get(task_id, "")
        if task_id not in reachable:
            errors.append(f"Atividade não alcançável a partir do início: {task_id}.")
        if task_id not in reverse_reachable:
            errors.append(f"Atividade sem caminho até evento de fim: {task_id}.")
        if not CODE_RE.match(name):
            warnings.append(f"Atividade sem título canônico '<código> - <nome>': {task_id}.")
        if process_code and not name.startswith(f"{process_code}."):
            errors.append(f"Atividade fora da codificação do processo {process_code}: {name or task_id}.")
        memberships = lane_membership.get(task_id, [])
        if lane_count and len(memberships) != 1:
            errors.append(f"Atividade deve pertencer a exatamente uma lane: {task_id} ({len(memberships)} vínculos).")

    if not lane_count:
        warnings.append("O processo não possui lanes de times/papéis executores.")
    for gateway_id in sorted(gateways):
        if len(incoming[gateway_id]) <= 1 and len(outgoing[gateway_id]) == 1:
            warnings.append(f"Gateway com apenas uma saída: {gateway_id}.")
        if len(outgoing[gateway_id]) > 1 and not names.get(gateway_id):
            warnings.append(f"Gateway decisório sem pergunta/nome: {gateway_id}.")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "starts": len(starts), "ends": len(ends), "tasks": len(tasks),
            "gateways": len(gateways), "sequence_flows": len(flows), "lanes": lane_count,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida invariantes BPMN da Metodologia Versus.")
    parser.add_argument("bpmn_file", type=Path)
    parser.add_argument("--process-code")
    parser.add_argument("--strict", action="store_true", help="Trata warnings como falha.")
    args = parser.parse_args()
    result = validate_bpmn(args.bpmn_file.read_text(encoding="utf-8"), args.process_code)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if (not result["ok"] or (args.strict and result["warnings"])) else 0


if __name__ == "__main__":
    sys.exit(main())

