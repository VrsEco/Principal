"""Geração do PDF executivo do planejamento Growth."""

from html import escape
from io import BytesIO
from typing import Any, Dict, Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#0B172A")
NAVY_LIGHT = colors.HexColor("#17375D")
BLUE = colors.HexColor("#2563EB")
GOLD = colors.HexColor("#C9A96E")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#E2E8F0")
SURFACE = colors.HexColor("#F8FAFC")
DANGER = colors.HexColor("#BE123C")
SUCCESS = colors.HexColor("#047857")


def _text(value: Any, fallback: str = "—") -> str:
    normalized = str(value or "").strip()
    return escape(normalized) if normalized else fallback


def _date_br(value: Any) -> str:
    normalized = str(value or "")
    if len(normalized) >= 10 and normalized[4:5] == "-":
        return f"{normalized[8:10]}/{normalized[5:7]}/{normalized[0:4]}"
    return _text(normalized)


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle(
            "GrowthCoverKicker", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=GOLD, spaceAfter=8,
        ),
        "cover_title": ParagraphStyle(
            "GrowthCoverTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=28, leading=32, textColor=colors.white, alignment=TA_LEFT,
            spaceAfter=12,
        ),
        "cover_company": ParagraphStyle(
            "GrowthCoverCompany", parent=base["Normal"], fontSize=13, leading=18,
            textColor=colors.HexColor("#CBD5E1"),
        ),
        "section": ParagraphStyle(
            "GrowthSection", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=17, leading=21, textColor=NAVY, spaceBefore=4, spaceAfter=12,
        ),
        "subsection": ParagraphStyle(
            "GrowthSubsection", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=11, leading=15, textColor=INK, spaceBefore=5, spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "GrowthBody", parent=base["BodyText"], fontSize=9.2, leading=14,
            textColor=colors.HexColor("#334155"), spaceAfter=8,
        ),
        "small": ParagraphStyle(
            "GrowthSmall", parent=base["Normal"], fontSize=7.5, leading=10,
            textColor=MUTED,
        ),
        "cell": ParagraphStyle(
            "GrowthCell", parent=base["Normal"], fontSize=7.5, leading=10,
            textColor=INK,
        ),
        "cell_bold": ParagraphStyle(
            "GrowthCellBold", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.5, leading=10, textColor=INK,
        ),
        "alert": ParagraphStyle(
            "GrowthAlert", parent=base["BodyText"], fontSize=8.5, leading=12,
            textColor=DANGER,
        ),
    }


def _metric_table(report: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> Table:
    stats = report.get("stats", {})
    items = [
        (stats.get("drivers", 0), "Direcionadores"),
        (stats.get("global_okrs", 0), "OKRs globais"),
        (stats.get("key_results", 0), "Resultados-chave"),
        (stats.get("area_okrs", 0), "OKRs de área"),
        (stats.get("projects", 0), "Projetos"),
    ]
    cells = [
        Paragraph(f"<b><font size='16'>{value}</font></b><br/><font color='#64748B'>{label}</font>", styles["cell"])
        for value, label in items
    ]
    table = Table([cells], colWidths=[34.2 * mm] * 5, rowHeights=[20 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SURFACE),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _section_title(number: str, title: str, styles: Dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(f"<font color='#2563EB'>{number}</font>&nbsp;&nbsp;{escape(title)}", styles["section"])


def _rows_or_empty(rows: Iterable[Any], empty_message: str, styles: Dict[str, ParagraphStyle]):
    rows = list(rows)
    if rows:
        return rows
    return [Paragraph(escape(empty_message), styles["small"])]


def generate_growth_report_pdf(
    *, plan: Any, company: Any, report: Dict[str, Any]
) -> bytes:
    """Gera arquivo PDF A4 determinístico a partir do read model tenant-safe."""
    buffer = BytesIO()
    styles = _styles()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=16 * mm,
        title=f"Relatório Executivo - {plan.title}",
        author="Gestão Versus",
        subject="Planejamento estratégico Growth",
    )

    story = [Spacer(1, 44 * mm)]
    story.extend([
        Paragraph("PLANEJAMENTO ESTRATÉGICO · GROWTH", styles["cover_kicker"]),
        Paragraph(_text(plan.title), styles["cover_title"]),
        Paragraph(_text(company.name), styles["cover_company"]),
        Spacer(1, 42 * mm),
    ])
    cover_meta = Table([
        ["STATUS", "AVANÇO DO PLANO", "ATUALIZADO EM", "EMITIDO EM"],
        [
            _text(report.get("status_label")),
            f"{int(report.get('progress', 0) or 0)}%",
            _text(report.get("plan_updated_on")),
            _text(report.get("generated_on")),
        ],
    ], colWidths=[42.75 * mm] * 4)
    cover_meta.setStyle(TableStyle([
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#9FB1C7")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 6.5),
        ("FONTSIZE", (0, 1), (-1, 1), 9),
        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#4A607A")),
        ("TOPPADDING", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ("TOPPADDING", (0, 1), (-1, 1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.extend([cover_meta, PageBreak()])

    story.extend([
        _section_title("01", "Resumo executivo", styles),
        Paragraph(
            _text(report.get("description"), f"Consolidado estratégico de {company.name}."),
            styles["body"],
        ),
        Spacer(1, 3 * mm),
        _metric_table(report, styles),
        Spacer(1, 7 * mm),
    ])
    governance = report.get("governance", {})
    attention = Table([
        ["Riscos críticos", "Prazos vencidos", "Sem responsável"],
        [
            str(governance.get("high_risk_count", 0)),
            str(governance.get("overdue_count", 0)),
            str(governance.get("missing_owner_count", 0)),
        ],
    ], colWidths=[57 * mm] * 3)
    attention.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#A9B9CC")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.white),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("FONTSIZE", (0, 1), (-1, 1), 16),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.5, NAVY_LIGHT),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, NAVY_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([attention, Spacer(1, 8 * mm)])

    story.append(_section_title("02", "Direcionadores estratégicos", styles))
    driver_blocks = []
    for driver in report.get("drivers", []):
        driver_blocks.append(KeepTogether([
            Paragraph(
                f"<font color='#2563EB'><b>{_text(driver.get('type_label'))}</b></font>"
                f" &nbsp;·&nbsp; Prioridade {_text(driver.get('priority_label')).lower()}",
                styles["small"],
            ),
            Paragraph(_text(driver.get("description")), styles["body"]),
            Spacer(1, 2 * mm),
        ]))
    story.extend(_rows_or_empty(driver_blocks, "Direcionadores ainda não registrados.", styles))
    story.append(Spacer(1, 5 * mm))

    story.append(_section_title("03", "Objetivos e resultados-chave", styles))
    okr_blocks = []
    for index, okr in enumerate(report.get("global_okrs", []), start=1):
        block = [
            Paragraph(f"O{index:02d} · {_text(okr.get('type_label'))}", styles["small"]),
            Paragraph(_text(okr.get("objective")), styles["subsection"]),
            Paragraph(
                f"Responsável: {_text(okr.get('owner'), 'Não definido')} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"Prazo: {_date_br(okr.get('deadline'))}",
                styles["small"],
            ),
        ]
        key_results = okr.get("key_results", [])
        if key_results:
            kr_rows = [["KR", "Resultado-chave", "Métrica / Meta"]]
            for kr_index, kr in enumerate(key_results, start=1):
                kr_rows.append([
                    f"KR{kr_index}",
                    Paragraph(_text(kr.get("label")), styles["cell"]),
                    Paragraph(
                        f"{_text(kr.get('metric'), 'Métrica não informada')} / {_text(kr.get('target'), 'Meta não informada')}",
                        styles["cell"],
                    ),
                ])
            kr_table = Table(kr_rows, colWidths=[14 * mm, 96 * mm, 61 * mm], repeatRows=1)
            kr_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), SURFACE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7),
                ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            block.extend([Spacer(1, 3 * mm), kr_table])
        else:
            block.append(Paragraph("Nenhum resultado-chave vinculado.", styles["small"]))
        block.append(Spacer(1, 5 * mm))
        okr_blocks.append(KeepTogether(block))
    story.extend(_rows_or_empty(okr_blocks, "OKRs globais ainda não definidos.", styles))

    story.extend([PageBreak(), _section_title("04", "Compromissos por área", styles)])
    area_rows = [["Área", "Objetivo", "Responsável", "KRs"]]
    for okr in report.get("area_okrs", []):
        area_rows.append([
            Paragraph(_text(okr.get("department")), styles["cell_bold"]),
            Paragraph(_text(okr.get("objective")), styles["cell"]),
            Paragraph(_text(okr.get("owner"), "Não definido"), styles["cell"]),
            str(okr.get("key_results_count", 0)),
        ])
    if len(area_rows) > 1:
        area_table = Table(area_rows, colWidths=[34 * mm, 78 * mm, 44 * mm, 15 * mm], repeatRows=1)
        area_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([area_table, Spacer(1, 9 * mm)])
    else:
        story.extend([Paragraph("OKRs por área ainda não registrados.", styles["small"]), Spacer(1, 9 * mm)])

    story.append(_section_title("05", "Projetos estratégicos", styles))
    project_rows = [["Projeto", "Responsável", "Status", "Progresso", "Prazo"]]
    for project in report.get("projects", []):
        project_rows.append([
            Paragraph(f"<b>{_text(project.get('code'))}</b><br/>{_text(project.get('name'))}", styles["cell"]),
            Paragraph(_text(project.get("owner"), "Não definido"), styles["cell"]),
            _text(project.get("status_label")),
            f"{int(project.get('progress', 0) or 0)}%",
            _date_br(project.get("deadline")),
        ])
    if len(project_rows) > 1:
        project_table = Table(project_rows, colWidths=[62 * mm, 38 * mm, 29 * mm, 21 * mm, 24 * mm], repeatRows=1)
        project_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("FONTSIZE", (2, 1), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([project_table, Spacer(1, 9 * mm)])
    else:
        story.extend([Paragraph("Nenhum projeto vinculado ao plano.", styles["small"]), Spacer(1, 9 * mm)])

    story.append(_section_title("06", "Prontidão para execução", styles))
    story.append(Paragraph(
        f"O plano registra <b>{int(report.get('progress', 0) or 0)}%</b> de avanço. "
        f"Há <b>{governance.get('active_projects', 0)}</b> projetos em andamento e "
        f"<b>{governance.get('completed_projects', 0)}</b> concluídos.",
        styles["body"],
    ))
    high_risks = governance.get("high_risks", [])
    if high_risks:
        story.append(Paragraph("Riscos críticos para deliberação", styles["subsection"]))
        for risk in high_risks:
            story.append(Paragraph(f"• {_text(risk.get('description'))}", styles["alert"]))

    def draw_page(canvas, document):
        canvas.saveState()
        page = canvas.getPageNumber()
        if page == 1:
            canvas.setFillColor(NAVY)
            canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
            canvas.setStrokeColor(colors.HexColor("#314967"))
            canvas.circle(A4[0] + 20 * mm, A4[1] - 42 * mm, 58 * mm, stroke=1, fill=0)
            canvas.circle(A4[0] - 5 * mm, A4[1] - 42 * mm, 38 * mm, stroke=1, fill=0)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 12)
            canvas.drawString(18 * mm, A4[1] - 20 * mm, "VERSUS")
            canvas.setFillColor(GOLD)
            canvas.rect(18 * mm, A4[1] - 24 * mm, 20 * mm, 0.8 * mm, fill=1, stroke=0)
        else:
            canvas.setStrokeColor(BORDER)
            canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
            canvas.setFillColor(MUTED)
            canvas.setFont("Helvetica", 7)
            canvas.drawString(18 * mm, 8 * mm, f"Gestão Versus · {_text(company.name)}")
            canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"Página {page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return buffer.getvalue()
