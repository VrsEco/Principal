from __future__ import annotations

from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


STATUS_LABELS = {
    "accepted": "Conforme",
    "rejected": "Não conforme",
    "na": "Não aplicável",
}


def _text(value: Any) -> str:
    if value in (None, ""):
        return "—"
    if isinstance(value, bool):
        return "Sim" if value else "Não"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "—"
    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or value)
    return str(value)


def generate_process_artifact_pdf_bytes(artifact_execution, *, instance=None) -> bytes:
    """Emite a versão auditável de um formulário/checklist já materializado."""
    snapshot = artifact_execution.definition_snapshot_json or {}
    config = snapshot.get("configuration_json") or {}
    output = artifact_execution.output_json or {}
    answers = output.get("answers") or {}
    evidence = artifact_execution.evidence_json or {}

    buffer = BytesIO()
    styles = getSampleStyleSheet()
    body = ParagraphStyle("ArtifactBody", parent=styles["BodyText"], fontSize=9, leading=12)
    muted = ParagraphStyle("ArtifactMuted", parent=body, textColor=colors.HexColor("#64748b"))
    title = ParagraphStyle("ArtifactTitle", parent=styles["Title"], fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"))
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=snapshot.get("name") or "Registro operacional",
    )
    story = [
        Paragraph(escape(snapshot.get("name") or "Registro operacional"), title),
        Paragraph(
            escape(
                f"{('Formulário' if artifact_execution.artifact_type == 'form' else 'Checklist')} "
                f"· versão {artifact_execution.artifact_version or 1} · registro #{artifact_execution.id}"
            ),
            muted,
        ),
        Spacer(1, 6 * mm),
    ]

    activity = getattr(artifact_execution, "activity_execution", None)
    metadata = [
        ["Empresa", str(artifact_execution.company_id)],
        ["Instância", getattr(instance, "instance_code", None) or getattr(instance, "id", None) or artifact_execution.process_instance_id],
        ["Atividade", getattr(activity, "bpmn_element_name", None) or getattr(activity, "bpmn_element_id", None) or "—"],
        ["Concluído em", artifact_execution.completed_at.strftime("%d/%m/%Y %H:%M") if artifact_execution.completed_at else "Em andamento"],
    ]
    meta_table = Table(metadata, colWidths=[34 * mm, 140 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#334155")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([meta_table, Spacer(1, 6 * mm)])

    rows = [[Paragraph("<b>Campo / critério</b>", body), Paragraph("<b>Resposta</b>", body), Paragraph("<b>Observação / evidência</b>", body)]]
    if artifact_execution.artifact_type == "form":
        for section in config.get("sections") or []:
            for field in section.get("fields") or []:
                rows.append([
                    Paragraph(escape(field.get("label") or field.get("id") or "Campo"), body),
                    Paragraph(escape(_text(answers.get(field.get("id")))), body),
                    Paragraph(escape(section.get("title") or "—"), muted),
                ])
    else:
        for item in config.get("items") or []:
            answer = answers.get(item.get("id")) or {}
            evidence_value = evidence.get(item.get("id"))
            observation = " · ".join(part for part in [
                _text(answer.get("comment")) if answer.get("comment") else None,
                f"Evidência: {_text(evidence_value)}" if evidence_value else None,
            ] if part) or "—"
            rows.append([
                Paragraph(escape(item.get("label") or item.get("id") or "Critério"), body),
                Paragraph(escape(STATUS_LABELS.get(answer.get("status"), _text(answer.get("status")))), body),
                Paragraph(escape(observation), body),
            ])

    if len(rows) == 1:
        rows.append([Paragraph("Sem campos configurados", muted), Paragraph("—", body), Paragraph("—", body)])
    table = Table(rows, colWidths=[62 * mm, 42 * mm, 70 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(table)
    document.build(story)
    return buffer.getvalue()
