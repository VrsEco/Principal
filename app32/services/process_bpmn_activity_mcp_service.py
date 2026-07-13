from __future__ import annotations

from uuid import uuid4
from xml.etree import ElementTree as ET

from models import Process
from services.process_bpmn_service import build_empty_bpmn_xml, get_latest_diagram, upsert_process_bpmn_diagram

NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
ET.register_namespace("bpmn", NS)

def create_bpmn_activity(*, company_id: int, process_id: int, name: str, lane_id: str | None = None, lane_name: str | None = None, source_element_id: str | None = None, target_element_id: str | None = None, order_index: int | None = None, data_object_name: str | None = None, data_object_direction: str = "input_output", data_object_id: str | None = None) -> dict:
    process = Process.query.filter_by(id=process_id, company_id=company_id).first()
    if not process: raise ValueError("Processo não encontrado para a empresa informada.")
    if not str(name or "").strip(): raise ValueError("name é obrigatório.")
    if data_object_direction not in {"input", "output", "input_output"}: raise ValueError("data_object_direction inválido.")
    diagram = get_latest_diagram(process_id=process_id, company_id=company_id, status="draft")
    xml = diagram.bpmn_xml if diagram else build_empty_bpmn_xml(process)
    root = ET.fromstring(xml); proc = root.find(f"{{{NS}}}process")
    if proc is None: raise ValueError("Processo BPMN inválido.")
    task_id = f"Task_{uuid4().hex[:12]}"; task = ET.SubElement(proc, f"{{{NS}}}task", id=task_id, name=str(name).strip())
    _bind_lane(proc, task_id, lane_id, lane_name)
    data_ref = _data_object(proc, data_object_id, data_object_name)
    if data_ref:
        assoc = ET.SubElement(proc, f"{{{NS}}}association", id=f"Association_{uuid4().hex[:10]}")
        assoc.set("sourceRef", data_ref if data_object_direction == "input" else task_id)
        assoc.set("targetRef", task_id if data_object_direction == "input" else data_ref)
    source = source_element_id or _by_order(proc, order_index)
    if source: ET.SubElement(proc, f"{{{NS}}}sequenceFlow", id=f"Flow_{uuid4().hex[:10]}", sourceRef=source, targetRef=task_id)
    if target_element_id: ET.SubElement(proc, f"{{{NS}}}sequenceFlow", id=f"Flow_{uuid4().hex[:10]}", sourceRef=task_id, targetRef=target_element_id)
    saved = upsert_process_bpmn_diagram(process=process, payload={"id": diagram.id if diagram else None, "status":"draft", "name": process.name, "bpmn_xml": ET.tostring(root, encoding="unicode"), "metadata_json": (diagram.metadata_json if diagram else {}) or {}}, user_id=None)
    return {"activity": {"id": task_id, "name": name, "lane_id": lane_id, "lane_name": lane_name}, "data_object_reference": data_ref, "diagram_id": saved.id, "status": saved.status}

def _bind_lane(proc, task_id, lane_id, lane_name):
    lanes = proc.find(f"{{{NS}}}laneSet")
    if lanes is None: return
    for lane in lanes.findall(f"{{{NS}}}lane"):
        if (lane_id and lane.get("id") == lane_id) or (lane_name and lane.get("name") == lane_name):
            ET.SubElement(lane, f"{{{NS}}}flowNodeRef").text = task_id; return
    if lane_id or lane_name:
        lane = ET.SubElement(lanes, f"{{{NS}}}lane", id=lane_id or f"Lane_{uuid4().hex[:10]}", name=lane_name or lane_id)
        ET.SubElement(lane, f"{{{NS}}}flowNodeRef").text = task_id

def _data_object(proc, requested_id, name):
    if requested_id:
        if proc.find(f".//{{{NS}}}dataObjectReference[@id='{requested_id}']") is None: raise ValueError("Data Object Reference não encontrado no processo.")
        return requested_id
    if not name: return None
    for ref in proc.findall(f"{{{NS}}}dataObjectReference"):
        if ref.get("name") == name: return ref.get("id")
    obj_id=f"DataObject_{uuid4().hex[:10]}"; ref_id=f"DataObjectReference_{uuid4().hex[:10]}"
    ET.SubElement(proc, f"{{{NS}}}dataObject", id=obj_id, name=name)
    ET.SubElement(proc, f"{{{NS}}}dataObjectReference", id=ref_id, name=name, dataObjectRef=obj_id)
    return ref_id

def _by_order(proc, order_index):
    if order_index is None: return None
    nodes=[n for n in list(proc) if n.tag.rsplit('}',1)[-1] in {'startEvent','task','endEvent'}]
    return nodes[max(0, min(int(order_index)-1, len(nodes)-1))].get('id') if nodes else None
