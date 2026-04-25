from __future__ import annotations

from datetime import datetime
import re
from typing import Any
from xml.sax.saxutils import escape

from models import db, Process, ProcessBpmnDiagram


VALID_BPMN_STATUSES = {"draft", "published", "archived"}


def sanitize_svg_snapshot(svg: str | None) -> str | None:
    """Remove conteúdo ativo antes de renderizar o snapshot SVG em telas HTML."""
    if not svg:
        return None

    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", "", str(svg), flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"\s+on[a-zA-Z]+\s*=\s*(['\"]).*?\1", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"javascript:", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def serialize_flow_snapshot(diagram: ProcessBpmnDiagram | None) -> dict[str, Any] | None:
    """Payload enxuto para exibição do BPMN publicado na área Fluxo do processo."""
    if not diagram or not diagram.svg_snapshot:
        return None

    return {
        "id": diagram.id,
        "status": diagram.status,
        "version": diagram.version,
        "name": diagram.name,
        "svg_snapshot": sanitize_svg_snapshot(diagram.svg_snapshot),
        "published_at": diagram.published_at.isoformat() if diagram.published_at else None,
        "updated_at": diagram.updated_at.isoformat() if diagram.updated_at else None,
    }


def build_empty_bpmn_xml(process: Process) -> str:
    """Create a minimal BPMN 2.0 document for a process.

    The XML is intentionally generic and tool-neutral so it can be opened by
    bpmn-js and other BPMN 2.0 compliant modelers.
    """

    process_code = escape(str(getattr(process, "code", "") or f"process_{process.id}"))
    process_name = escape(str(getattr(process, "name", "") or "Novo processo"))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                  id="Definitions_{process.id}"
                  targetNamespace="https://app32.gestaoversus.com.br/bpmn">
  <bpmn:process id="Process_{process.id}" name="{process_code} - {process_name}" isExecutable="false">
    <bpmn:startEvent id="StartEvent_1" name="Início" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_{process.id}">
      <bpmndi:BPMNShape id="StartEvent_1_di" bpmnElement="StartEvent_1">
        <dc:Bounds x="180" y="120" width="36" height="36" />
      </bpmndi:BPMNShape>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""


def serialize_diagram(diagram: ProcessBpmnDiagram | None, process: Process | None = None) -> dict[str, Any]:
    if not diagram:
        if not process:
            return {}
        return {
            "id": None,
            "company_id": process.company_id,
            "process_id": process.id,
            "version": 0,
            "status": "unsaved",
            "name": getattr(process, "name", None),
            "bpmn_xml": build_empty_bpmn_xml(process),
            "svg_snapshot": None,
            "png_snapshot": None,
            "metadata_json": {},
            "created_by_user_id": None,
            "updated_by_user_id": None,
            "published_at": None,
            "created_at": None,
            "updated_at": None,
        }

    return {
        "id": diagram.id,
        "company_id": diagram.company_id,
        "process_id": diagram.process_id,
        "version": diagram.version,
        "status": diagram.status,
        "name": diagram.name,
        "bpmn_xml": diagram.bpmn_xml,
        "svg_snapshot": diagram.svg_snapshot,
        "png_snapshot": diagram.png_snapshot,
        "metadata_json": diagram.metadata_json or {},
        "created_by_user_id": diagram.created_by_user_id,
        "updated_by_user_id": diagram.updated_by_user_id,
        "published_at": diagram.published_at.isoformat() if diagram.published_at else None,
        "created_at": diagram.created_at.isoformat() if diagram.created_at else None,
        "updated_at": diagram.updated_at.isoformat() if diagram.updated_at else None,
    }


def get_latest_diagram(*, process_id: int, company_id: int, status: str | None = None) -> ProcessBpmnDiagram | None:
    query = ProcessBpmnDiagram.query.filter_by(process_id=process_id, company_id=company_id)
    if status:
        query = query.filter_by(status=status)
    else:
        query = query.filter(ProcessBpmnDiagram.status.in_(["draft", "published"]))
    return query.order_by(ProcessBpmnDiagram.updated_at.desc(), ProcessBpmnDiagram.id.desc()).first()


def _next_version(process_id: int, company_id: int) -> int:
    latest = (
        ProcessBpmnDiagram.query.filter_by(process_id=process_id, company_id=company_id)
        .order_by(ProcessBpmnDiagram.version.desc(), ProcessBpmnDiagram.id.desc())
        .first()
    )
    return int(getattr(latest, "version", 0) or 0) + 1


def upsert_process_bpmn_diagram(
    *,
    process: Process,
    payload: dict[str, Any],
    user_id: int | None,
) -> ProcessBpmnDiagram:
    if not isinstance(payload, dict):
        raise ValueError("Payload inválido.")

    status = str(payload.get("status") or "draft").strip().lower()
    if status not in VALID_BPMN_STATUSES:
        raise ValueError("Status BPMN inválido.")

    bpmn_xml = payload.get("bpmn_xml")
    if not isinstance(bpmn_xml, str) or not bpmn_xml.strip():
        raise ValueError("bpmn_xml é obrigatório.")

    if "<bpmn:definitions" not in bpmn_xml and "<definitions" not in bpmn_xml:
        raise ValueError("O conteúdo informado não parece ser um XML BPMN 2.0 válido.")

    diagram_id = payload.get("id")
    diagram = None
    if diagram_id:
        diagram = ProcessBpmnDiagram.query.filter_by(
            id=int(diagram_id),
            process_id=process.id,
            company_id=process.company_id,
        ).first()
        if not diagram:
            raise ValueError("Diagrama BPMN não encontrado para o processo e empresa ativa.")

    if not diagram and status == "draft":
        diagram = ProcessBpmnDiagram.query.filter_by(
            process_id=process.id,
            company_id=process.company_id,
            status="draft",
        ).order_by(ProcessBpmnDiagram.updated_at.desc(), ProcessBpmnDiagram.id.desc()).first()

    if not diagram:
        diagram = ProcessBpmnDiagram(
            company_id=process.company_id,
            process_id=process.id,
            version=_next_version(process.id, process.company_id),
            created_by_user_id=user_id,
        )
        db.session.add(diagram)

    if status == "published":
        (
            ProcessBpmnDiagram.query.filter_by(
                process_id=process.id,
                company_id=process.company_id,
                status="published",
            )
            .filter(ProcessBpmnDiagram.id != (diagram.id or 0))
            .update({"status": "archived"}, synchronize_session=False)
        )
        diagram.published_at = datetime.utcnow()

    diagram.status = status
    diagram.name = str(payload.get("name") or process.name or "Diagrama BPMN").strip()
    diagram.bpmn_xml = bpmn_xml
    diagram.svg_snapshot = payload.get("svg_snapshot")
    diagram.png_snapshot = payload.get("png_snapshot")
    diagram.metadata_json = payload.get("metadata_json") if isinstance(payload.get("metadata_json"), dict) else {}
    diagram.updated_by_user_id = user_id
    diagram.updated_at = datetime.utcnow()

    db.session.commit()
    return diagram
