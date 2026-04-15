
from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PALETTE = {
    "primary": colors.HexColor("#2563eb"),
    "primary_dark": colors.HexColor("#1d4ed8"),
    "accent": colors.HexColor("#0f766e"),
    "text": colors.HexColor("#0f172a"),
    "muted": colors.HexColor("#475569"),
    "border": colors.HexColor("#cbd5e1"),
    "surface": colors.HexColor("#f8fafc"),
}

SOURCE_LABELS = {
    "human_review": "Revisao humana",
    "sapiens_workflow": "Sapiens / workflow",
    "agent_action": "Acao de agente",
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("AIMonitoringTitle", parent=base["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=PALETTE["primary_dark"], spaceAfter=10),
        "subtitle": ParagraphStyle("AIMonitoringSubtitle", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=PALETTE["accent"], spaceBefore=8, spaceAfter=6),
        "body": ParagraphStyle("AIMonitoringBody", parent=base["BodyText"], fontName="Helvetica", fontSize=8.3, leading=10.8, textColor=PALETTE["text"], spaceAfter=4),
        "muted": ParagraphStyle("AIMonitoringMuted", parent=base["BodyText"], fontName="Helvetica", fontSize=7.7, leading=10, textColor=PALETTE["muted"], spaceAfter=3),
        "table_header": ParagraphStyle("AIMonitoringTableHeader", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8.0, leading=9.8, textColor=colors.white),
        "table_cell": ParagraphStyle("AIMonitoringTableCell", parent=base["BodyText"], fontName="Helvetica", fontSize=7.8, leading=9.6, textColor=PALETTE["text"]),
    }


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    safe = escape(str(text or "-")).replace("\n", "<br/>")
    return Paragraph(safe, style)


def _doc(buffer: BytesIO, title: str, company_name: str, generated_by: str):
    emitted_at = datetime.now()
    subtitle = f"Empresa: {company_name} | Usuario logado: {generated_by}"

    def _decorate(canvas, doc):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(PALETTE["primary"])
        canvas.rect(0, height - 24 * mm, width, 24 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(14 * mm, height - 10 * mm, title)
        canvas.setFont("Helvetica", 8.2)
        canvas.drawString(14 * mm, height - 16 * mm, subtitle[:120])
        canvas.setFillColor(PALETTE["muted"])
        canvas.setFont("Helvetica", 7.4)
        canvas.drawString(14 * mm, 9 * mm, "Versus Gestao Corporativa - www.gestaoversus.com.br - Todos os direitos reservados")
        canvas.drawRightString(width - 14 * mm, 9 * mm, f"Emitido em {emitted_at.strftime('%d/%m/%Y as %H:%M hs')}")
        canvas.restoreState()

    return (
        SimpleDocTemplate(buffer, pagesize=A4, topMargin=31 * mm, bottomMargin=16 * mm, leftMargin=14 * mm, rightMargin=14 * mm, title=title),
        _decorate,
    )


def _table(rows: list[list[Any]], col_widths: list[float], *, header: bool = True, shaded: bool = True) -> Table:
    styles = _styles()
    formatted: list[list[Any]] = []
    for row_index, row in enumerate(rows):
        row_style = styles["table_header"] if header and row_index == 0 else styles["table_cell"]
        formatted.append([item if isinstance(item, Paragraph) else _paragraph(item, row_style) for item in row])
    table = Table(formatted, colWidths=col_widths, repeatRows=1 if header else 0)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, PALETTE["border"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), PALETTE["primary"]),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ])
        if shaded and len(rows) > 1:
            commands.append(("BACKGROUND", (0, 1), (-1, -1), PALETTE["surface"]))
    elif shaded:
        commands.append(("BACKGROUND", (0, 0), (-1, -1), PALETTE["surface"]))
    table.setStyle(TableStyle(commands))
    return table


def generate_ai_monitoring_report_pdf(*, panel: dict[str, Any], company_name: str, generated_by: str) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc, decorator = _doc(buffer, "Relatorio de Monitoramento e Auditoria", company_name, generated_by)
    story: list[Any] = []

    summary = panel.get("summary") or {}
    filters = panel.get("filters") or {}
    events = list(panel.get("events") or [])
    by_source = summary.get("by_source") or {}
    by_status = summary.get("by_status") or {}

    story.append(Paragraph("Monitoramento e Auditoria da IA Corporativa", styles["title"]))
    story.append(Paragraph(f"Empresa: {escape(company_name)} | Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["muted"]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Resumo executivo", styles["subtitle"]))
    story.append(_table([
        ["Indicador", "Valor"],
        ["Total de eventos", summary.get("total", 0)],
        ["Revisoes humanas", by_source.get("human_review", 0)],
        ["Sapiens / workflows", by_source.get("sapiens_workflow", 0)],
        ["Acoes de agentes", by_source.get("agent_action", 0)],
    ], [95 * mm, 81 * mm]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Filtros aplicados", styles["subtitle"]))
    story.append(_table([
        ["Campo", "Valor"],
        ["Fonte", SOURCE_LABELS.get(filters.get("source") or "", "Todas")],
        ["Limite", filters.get("limit", 50)],
        ["Company ID", panel.get("company_id") or "-"],
    ], [55 * mm, 121 * mm]))
    story.append(Spacer(1, 8))

    if by_status:
        story.append(Paragraph("Distribuicao por status", styles["subtitle"]))
        status_rows = [["Status", "Quantidade"]]
        for key, value in sorted(by_status.items(), key=lambda item: str(item[0])):
            status_rows.append([key or "-", value])
        story.append(_table(status_rows, [95 * mm, 81 * mm]))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Linha do tempo recente", styles["subtitle"]))
    if not events:
        story.append(Paragraph("Nenhum evento encontrado para os filtros selecionados.", styles["body"]))
    else:
        event_rows = [["Data/Hora", "Fonte", "Titulo", "Ator / Canal", "Status"]]
        for event in events[:18]:
            actor_channel = " / ".join(
                item for item in [str(event.get("actor") or "-").strip(), str(event.get("channel") or "-").strip()] if item
            )
            event_rows.append([
                event.get("created_at") or "-",
                SOURCE_LABELS.get(event.get("source") or "", event.get("source") or "-"),
                event.get("title") or "Evento operacional",
                actor_channel or "-",
                event.get("status") or "-",
            ])
        story.append(_table(event_rows, [28 * mm, 28 * mm, 56 * mm, 42 * mm, 22 * mm], shaded=True))

        story.append(Spacer(1, 8))
        story.append(Paragraph("Detalhamento dos eventos", styles["subtitle"]))
        for index, event in enumerate(events[:12], start=1):
            story.append(_table([
                ["Campo", "Valor"],
                [f"Evento {index}", event.get("title") or "Evento operacional"],
                ["Data/Hora", event.get("created_at") or "-"],
                ["Fonte", SOURCE_LABELS.get(event.get("source") or "", event.get("source") or "-")],
                ["Ator", event.get("actor") or "-"],
                ["Canal", event.get("channel") or "-"],
                ["Status", event.get("status") or "-"],
                ["Descricao", event.get("description") or "Sem descricao operacional."],
            ], [42 * mm, 134 * mm]))
            story.append(Spacer(1, 5))

    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    return buffer.getvalue()
