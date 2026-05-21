from __future__ import annotations

from collections import defaultdict
from typing import Any
from xml.etree import ElementTree as ET


_IGNORED_TAGS = {
    "definitions",
    "process",
    "lane",
    "laneSet",
    "participant",
    "collaboration",
    "BPMNDiagram",
    "BPMNPlane",
    "BPMNShape",
    "BPMNEdge",
    "Bounds",
    "waypoint",
}

_EXECUTABLE_ACTIVITY_TAGS = {
    "task",
    "userTask",
    "manualTask",
    "serviceTask",
    "businessRuleTask",
    "scriptTask",
    "sendTask",
    "receiveTask",
    "callActivity",
    "subProcess",
}

_GATEWAY_TAGS = {
    "exclusiveGateway",
    "parallelGateway",
    "inclusiveGateway",
    "eventBasedGateway",
    "complexGateway",
}


def parse_bpmn_graph(bpmn_xml: str | None) -> dict[str, Any]:
    if not bpmn_xml:
        return _empty_graph()

    try:
        root = ET.fromstring(bpmn_xml)
    except ET.ParseError:
        return _empty_graph(error="invalid_bpmn_xml")

    lanes = _extract_lanes(root)
    lane_by_node: dict[str, dict[str, Any]] = {}
    for lane in lanes:
        for node_id in lane.get("flow_node_refs", []):
            lane_by_node[str(node_id)] = lane

    nodes: list[dict[str, Any]] = []
    node_index: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    incoming_map: dict[str, list[str]] = defaultdict(list)
    outgoing_map: dict[str, list[str]] = defaultdict(list)

    for element in root.iter():
        tag_name = _strip_namespace(element.tag)
        element_id = str(element.attrib.get("id") or "").strip()
        if not element_id:
            continue

        if tag_name == "sequenceFlow":
            source_ref = str(element.attrib.get("sourceRef") or "").strip()
            target_ref = str(element.attrib.get("targetRef") or "").strip()
            if not source_ref or not target_ref:
                continue
            edge = {
                "id": element_id,
                "name": str(element.attrib.get("name") or "").strip() or None,
                "source_ref": source_ref,
                "target_ref": target_ref,
                "condition": _extract_condition_expression(element),
                "is_default_flow": False,
            }
            edges.append(edge)
            incoming_map[target_ref].append(source_ref)
            outgoing_map[source_ref].append(target_ref)
            continue

        if tag_name in _IGNORED_TAGS:
            continue

        lane = lane_by_node.get(element_id)
        node = {
            "id": element_id,
            "name": str(element.attrib.get("name") or "").strip() or None,
            "type": tag_name,
            "lane_id": lane.get("id") if lane else None,
            "lane_name": lane.get("name") if lane else None,
        }
        nodes.append(node)
        node_index[element_id] = node

    _mark_default_flows(root, edges)

    for node in nodes:
        node_id = node["id"]
        node["incoming_ids"] = list(incoming_map.get(node_id, []))
        node["outgoing_ids"] = list(outgoing_map.get(node_id, []))
        node["incoming_count"] = len(node["incoming_ids"])
        node["outgoing_count"] = len(node["outgoing_ids"])
        node["is_executable_activity"] = _is_executable_activity(node["type"])
        node["is_gateway"] = node["type"] in _GATEWAY_TAGS
        node["is_event"] = node["type"].endswith("Event")
        node["outgoing_edges"] = [
            edge
            for edge in edges
            if edge["source_ref"] == node_id
        ]

    return {
        "nodes": nodes,
        "edges": edges,
        "lanes": lanes,
        "activities": [node for node in nodes if node["is_executable_activity"]],
        "gateways": [node for node in nodes if node["is_gateway"]],
        "events": [node for node in nodes if node["is_event"]],
        "node_index": node_index,
        "metrics": {
            "nodes": len(nodes),
            "edges": len(edges),
            "activities": sum(1 for node in nodes if node["is_executable_activity"]),
            "gateways": sum(1 for node in nodes if node["is_gateway"]),
            "events": sum(1 for node in nodes if node["is_event"]),
            "lanes": len(lanes),
        },
    }


def _extract_lanes(root: ET.Element) -> list[dict[str, Any]]:
    lanes: list[dict[str, Any]] = []
    for element in root.iter():
        tag_name = _strip_namespace(element.tag)
        if tag_name != "lane":
            continue
        flow_node_refs = [
            (child.text or "").strip()
            for child in element
            if _strip_namespace(child.tag) == "flowNodeRef" and (child.text or "").strip()
        ]
        lanes.append(
            {
                "id": str(element.attrib.get("id") or "").strip(),
                "name": str(element.attrib.get("name") or "").strip() or None,
                "flow_node_refs": flow_node_refs,
            }
        )
    return lanes


def _mark_default_flows(root: ET.Element, edges: list[dict[str, Any]]) -> None:
    edge_index = {edge["id"]: edge for edge in edges}
    for element in root.iter():
        default_flow_id = str(element.attrib.get("default") or "").strip()
        if not default_flow_id:
            continue
        edge = edge_index.get(default_flow_id)
        if edge is not None:
            edge["is_default_flow"] = True


def _extract_condition_expression(element: ET.Element) -> str | None:
    for child in element:
        if _strip_namespace(child.tag) != "conditionExpression":
            continue
        text = "".join(child.itertext()).strip()
        return text or None
    return None


def _is_executable_activity(tag_name: str) -> bool:
    if tag_name in _EXECUTABLE_ACTIVITY_TAGS:
        return True
    return tag_name.endswith("Task")


def _strip_namespace(tag_name: str) -> str:
    if "}" in tag_name:
        return tag_name.split("}", 1)[1]
    if ":" in tag_name:
        return tag_name.split(":", 1)[1]
    return tag_name


def _empty_graph(*, error: str | None = None) -> dict[str, Any]:
    return {
        "nodes": [],
        "edges": [],
        "lanes": [],
        "activities": [],
        "gateways": [],
        "events": [],
        "node_index": {},
        "metrics": {
            "nodes": 0,
            "edges": 0,
            "activities": 0,
            "gateways": 0,
            "events": 0,
            "lanes": 0,
        },
        "error": error,
    }
