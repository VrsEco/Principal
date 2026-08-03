from __future__ import annotations

from datetime import datetime
import re
from typing import Any
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from models import Company, db, Process, ProcessBpmnDiagram


VALID_BPMN_STATUSES = {"draft", "published", "archived"}
SVG_NS = "http://www.w3.org/2000/svg"
ARTIFACT_VISUALS = {
    "pop": {"markers": ("[POP]",), "stroke": "#2563eb", "fill": "#eff6ff"},
    "form": {"markers": ("[FORM]",), "stroke": "#7c3aed", "fill": "#f5f3ff"},
    "check": {"markers": ("[CHECK]",), "stroke": "#059669", "fill": "#ecfdf5"},
    "ai": {"markers": ("[IA]",), "stroke": "#ea580c", "fill": "#fff7ed"},
    "data-in": {"markers": ("[DADOS IN]",), "stroke": "#0891b2", "fill": "#ecfeff"},
    "data-out": {"markers": ("[DADOS OUT]",), "stroke": "#e11d48", "fill": "#fff1f2"},
}


def sanitize_svg_snapshot(svg: str | None) -> str | None:
    """Remove conteúdo ativo antes de renderizar o snapshot SVG em telas HTML."""
    if not svg:
        return None

    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", "", str(svg), flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"\s+on[a-zA-Z]+\s*=\s*(['\"]).*?\1", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"javascript:", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def colorize_bpmn_artifact_svg(svg: str | None, bpmn_xml: str | None) -> str | None:
    """Aplica a identidade canônica dos artefatos a snapshots antigos e novos do Book."""
    cleaned = sanitize_svg_snapshot(svg)
    if not cleaned or not bpmn_xml:
        return cleaned

    try:
        root = ET.fromstring(str(bpmn_xml))
    except ET.ParseError:
        return cleaned

    artifact_by_element_id: dict[str, str] = {}
    for element in root.iter():
        if not str(element.tag).endswith("dataObjectReference"):
            continue
        element_id = str(element.attrib.get("id") or "").strip()
        name = str(element.attrib.get("name") or "").strip().upper()
        if not element_id or not name:
            continue
        for artifact_type, visual in ARTIFACT_VISUALS.items():
            if any(name.startswith(marker) for marker in visual["markers"]):
                artifact_by_element_id[element_id] = artifact_type
                break

    if not artifact_by_element_id:
        return cleaned

    def add_artifact_class(match: re.Match[str]) -> str:
        tag = match.group(0)
        id_match = re.search(r"\bdata-element-id=(['\"])(.*?)\1", tag, flags=re.IGNORECASE)
        if not id_match:
            return tag
        raw_id = id_match.group(2)
        base_id = raw_id[:-6] if raw_id.endswith("_label") else raw_id
        artifact_type = artifact_by_element_id.get(base_id)
        if not artifact_type:
            return tag
        class_name = f"app32-artifact-{artifact_type}"
        class_match = re.search(r"\bclass=(['\"])(.*?)\1", tag, flags=re.IGNORECASE)
        if class_match:
            classes = class_match.group(2).split()
            if class_name in classes:
                return tag
            replacement = f'class={class_match.group(1)}{class_match.group(2)} {class_name}{class_match.group(1)}'
            return tag[:class_match.start()] + replacement + tag[class_match.end():]
        return tag[:-1] + f' class="{class_name}">'

    colored = re.sub(r"<g\b[^>]*>", add_artifact_class, cleaned, flags=re.IGNORECASE)
    rules = []
    for artifact_type, visual in ARTIFACT_VISUALS.items():
        rules.append(
            f".app32-artifact-{artifact_type} .djs-visual>path"
            f"{{fill:{visual['fill']}!important;stroke:{visual['stroke']}!important}}"
        )
    style = f'<style id="app32-artifact-colors">{"".join(rules)}</style>'
    return re.sub(r"(<svg\b[^>]*>)", rf"\1{style}", colored, count=1, flags=re.IGNORECASE)


def _parse_svg_dimension(value: str | None, fallback: float) -> float:
    if value is None:
        return fallback

    match = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)", str(value))
    if not match:
        return fallback

    try:
        return float(match.group(1))
    except (TypeError, ValueError):
        return fallback


def _split_svg_viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    raw_viewbox = (root.get("viewBox") or "").strip()
    parts = raw_viewbox.replace(",", " ").split()
    if len(parts) == 4:
        try:
            return tuple(float(part) for part in parts)  # type: ignore[return-value]
        except ValueError:
            pass

    width = _parse_svg_dimension(root.get("width"), 1200.0)
    height = _parse_svg_dimension(root.get("height"), 800.0)
    return 0.0, 0.0, width, height


def build_bpmn_participant_metadata_label(
    *,
    company_name: str,
    process_code: str,
    process_name: str,
    version: int,
    published_at: datetime | None,
    status: str,
) -> str:
    date_label = ''
    if published_at:
        date_label = published_at.strftime('%d/%m/%Y')
    elif status == 'published':
        date_label = datetime.utcnow().strftime('%d/%m/%Y')

    label = (
        f"{(company_name.strip() or 'Empresa').upper()} | "
        f"{(process_code.strip() or 'Sem código')} - "
        f"{(process_name.strip() or 'Processo sem nome').upper()} | "
        f"V{int(version or 0):02d}"
    )
    if date_label:
        label = f"{label} - {date_label}"
    return label


def sync_bpmn_participant_metadata(
    bpmn_xml: str | None,
    *,
    company_name: str,
    process_code: str,
    process_name: str,
    version: int,
    published_at: datetime | None,
    status: str,
) -> str | None:
    if not bpmn_xml or ('<bpmn:definitions' not in str(bpmn_xml) and '<definitions' not in str(bpmn_xml)):
        return bpmn_xml

    namespaces = {
        'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
    }
    try:
        root = ET.fromstring(bpmn_xml)
    except ET.ParseError:
        return bpmn_xml

    participant_nodes = root.findall('.//bpmn:participant', namespaces)
    if not participant_nodes:
        participant_nodes = root.findall('.//participant')
    if not participant_nodes:
        return bpmn_xml

    label = build_bpmn_participant_metadata_label(
        company_name=company_name,
        process_code=process_code,
        process_name=process_name,
        version=version,
        published_at=published_at,
        status=status,
    )
    participant_nodes[0].set('name', label)
    return ET.tostring(root, encoding='unicode')


def decorate_bpmn_svg_snapshot(
    svg: str | None,
    *,
    company_name: str,
    process_code: str,
    process_name: str,
    version: int,
    published_at: datetime | None,
    status: str,
) -> str | None:
    return svg


def serialize_flow_snapshot(diagram: ProcessBpmnDiagram | None) -> dict[str, Any] | None:
    """Payload enxuto para exibição do BPMN publicado na área Fluxo do processo."""
    if not diagram or (not diagram.svg_snapshot and not diagram.bpmn_xml):
        return None

    return {
        "id": diagram.id,
        "status": diagram.status,
        "version": diagram.version,
        "name": diagram.name,
        "bpmn_xml": diagram.bpmn_xml,
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

    try:
        root = ET.fromstring(bpmn_xml)
    except ET.ParseError as exc:
        raise ValueError("O conteúdo informado não parece ser um XML BPMN 2.0 válido.") from exc

    root_tag = str(getattr(root, "tag", "") or "")
    root_local_name = root_tag.rsplit("}", 1)[-1] if "}" in root_tag else root_tag.split(":", 1)[-1]
    if root_local_name != "definitions":
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

    diagram.status = status
    diagram.name = str(payload.get("name") or process.name or "Diagrama BPMN").strip()
    diagram.bpmn_xml = bpmn_xml
    diagram.svg_snapshot = payload.get("svg_snapshot")
    diagram.png_snapshot = payload.get("png_snapshot")
    diagram.metadata_json = payload.get("metadata_json") if isinstance(payload.get("metadata_json"), dict) else {}
    diagram.updated_by_user_id = user_id
    diagram.updated_at = datetime.utcnow()

    if status == "published":
        # A nova linha precisa ter um ID antes do UPDATE em lote. Sem o flush,
        # o autoflush disparado pela query pode inserir o próprio diagrama e o
        # filtro `id != 0` acaba arquivando a versão recém-publicada.
        if diagram.id is None:
            db.session.flush()
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

    with db.session.no_autoflush:
        company_name = (
            db.session.query(Company.name)
            .filter(Company.id == process.company_id)
            .scalar()
            or "Empresa"
        )

    resolved_version = int(getattr(diagram, "version", 0) or 0)
    synced_bpmn_xml = sync_bpmn_participant_metadata(
        bpmn_xml,
        company_name=company_name,
        process_code=str(getattr(process, "code", "") or ""),
        process_name=str(getattr(process, "name", "") or ""),
        version=resolved_version,
        published_at=diagram.published_at,
        status=status,
    ) or bpmn_xml

    diagram.bpmn_xml = synced_bpmn_xml

    db.session.commit()
    return diagram
