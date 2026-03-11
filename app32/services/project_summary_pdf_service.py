from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Indenter, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from flask_login import current_user

from models import Company, Portfolio, Project, ProjectTask
from services.project_summary_pdf_support import (
    aggregate_portfolio_hours,
    aggregate_project_hours,
    build_header_rows_portfolio,
    build_header_rows_project,
    calculate_portfolio_score,
    calculate_project_score,
    calculate_task_score,
    format_date_br,
    format_incident_score,
    normalize_text,
    portfolio_occurrence_summary,
    project_occurrence_summary,
    task_collaborators,
    task_completion_percent,
    task_diary_rows,
    task_occurrence_summary,
    task_occurrences,
    to_float,
)

PALETTE = {
    'primary': colors.HexColor('#2563eb'),
    'primary_dark': colors.HexColor('#1d4ed8'),
    'accent': colors.HexColor('#0f766e'),
    'text': colors.HexColor('#0f172a'),
    'muted': colors.HexColor('#475569'),
    'border': colors.HexColor('#cbd5e1'),
    'surface': colors.HexColor('#f8fafc'),
}


def _get_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('GVTitle', parent=base['Title'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=PALETTE['primary_dark'], alignment=TA_LEFT, spaceAfter=10),
        'subtitle': ParagraphStyle('GVSubtitle', parent=base['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=PALETTE['accent'], spaceBefore=8, spaceAfter=6),
        'block_title': ParagraphStyle('GVBlockTitle', parent=base['BodyText'], fontName='Helvetica-Bold', fontSize=9.4, leading=12, textColor=PALETTE['primary_dark'], spaceAfter=4),
        'body': ParagraphStyle('GVBody', parent=base['BodyText'], fontName='Helvetica', fontSize=8.5, leading=11, textColor=PALETTE['text'], spaceAfter=4, wordWrap='CJK'),
        'muted': ParagraphStyle('GVMuted', parent=base['BodyText'], fontName='Helvetica', fontSize=8, leading=11, textColor=PALETTE['muted'], spaceAfter=3),
        'table_header': ParagraphStyle('GVTableHeader', parent=base['BodyText'], fontName='Helvetica-Bold', fontSize=8.2, leading=10, textColor=colors.white, wordWrap='CJK'),
        'table_cell': ParagraphStyle('GVTableCell', parent=base['BodyText'], fontName='Helvetica', fontSize=8.1, leading=9.8, textColor=PALETTE['text'], wordWrap='CJK'),
        'table_cell_small': ParagraphStyle('GVTableCellSmall', parent=base['BodyText'], fontName='Helvetica', fontSize=7.4, leading=8.8, textColor=PALETTE['text'], wordWrap='CJK'),
    }


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    safe = escape(str(text or '-')).replace('\n', '<br/>')
    return Paragraph(safe, style)


def _p_markup(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text or '-', style)


def _logged_user_name() -> str:
    try:
        if getattr(current_user, 'is_authenticated', False):
            return (
                getattr(current_user, 'name', None)
                or getattr(current_user, 'full_name', None)
                or getattr(current_user, 'username', None)
                or getattr(current_user, 'email', None)
                or 'Usuário autenticado'
            )
    except Exception:
        pass
    return 'Sistema'


def _format_datetime_br(value: datetime) -> str:
    return value.strftime('%d/%m/%Y às %H:%M hs')


def _pdf_doc(buffer: BytesIO, title: str, company_name: str):
    emitted_at = datetime.now()
    logged_user = _logged_user_name()
    subtitle = f'Empresa: {company_name} | Usuário Logado: {logged_user}'

    def _decorate(canvas, doc):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(PALETTE['primary'])
        canvas.rect(0, height - 24 * mm, width, 24 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 12)
        canvas.drawString(14 * mm, height - 10 * mm, title)
        canvas.setFont('Helvetica', 8.2)
        canvas.drawString(14 * mm, height - 16 * mm, subtitle[:120])

        canvas.setFillColor(PALETTE['muted'])
        canvas.setFont('Helvetica', 7.5)
        canvas.drawString(14 * mm, 9 * mm, 'Versus Gestão Corporativa - www.gestaoversus.com.br - Todos os direitos reservados')
        canvas.drawRightString(width - 14 * mm, 9 * mm, f'Emitido em {_format_datetime_br(emitted_at)}')
        canvas.restoreState()

    return (
        SimpleDocTemplate(buffer, pagesize=A4, topMargin=31 * mm, bottomMargin=16 * mm, leftMargin=14 * mm, rightMargin=14 * mm, title=title),
        _decorate,
    )


def _section_table(rows: list[list[Any]], col_widths: list[float], *, left_padding: int = 8, compact: bool = False, shaded: bool = False) -> Table:
    styles = _get_styles()
    header_style = styles['table_header']
    cell_style = styles['table_cell_small'] if compact else styles['table_cell']
    formatted = []
    for row_idx, row in enumerate(rows):
        style = header_style if row_idx == 0 else cell_style
        formatted.append([cell if isinstance(cell, Paragraph) else _p(cell, style) for cell in row])
    table = Table(formatted, colWidths=col_widths, repeatRows=1)
    commands = [
        ('BACKGROUND', (0, 0), (-1, 0), PALETTE['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.35, PALETTE['border']),
        ('LEFTPADDING', (0, 0), (-1, -1), left_padding),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 4 if compact else 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4 if compact else 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]
    if shaded:
        commands.append(('BACKGROUND', (0, 1), (-1, -1), PALETTE['surface']))
    table.setStyle(TableStyle(commands))
    return table


def _info_table(rows: list[tuple[str, str]], *, left_padding: int = 8) -> Table:
    styles = _get_styles()
    data = [[_p(label, styles['table_cell']), _p(value, styles['table_cell'])] for label, value in rows]
    table = Table(data, colWidths=[48 * mm, 124 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PALETTE['surface']),
        ('GRID', (0, 0), (-1, -1), 0.35, PALETTE['border']),
        ('LEFTPADDING', (0, 0), (-1, -1), left_padding),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    return table


def _compact_info_table(rows: list[tuple[str, str]], *, pairs_per_row: int = 2, left_padding: int = 8, wide_fields: set[str] | None = None) -> Table:
    styles = _get_styles()
    wide_fields = {item.lower() for item in (wide_fields or set())}
    total_cols = pairs_per_row
    data = []

    card_style = ParagraphStyle(
        'GVCompactCard',
        parent=styles['table_cell'],
        fontName='Helvetica',
        fontSize=8.1,
        leading=10.5,
        textColor=PALETTE['text'],
        wordWrap='CJK',
    )

    def card(label: str, value: str) -> Paragraph:
        markup = (
            f'<font color="#0f766e"><b>{escape(label or "-")}</b></font><br/>'
            f'<font color="#0f172a">{escape(value or "-")}</font>'
        )
        return Paragraph(markup, card_style)

    line_items: list[tuple[str, str]] = []
    for label, value in rows:
        if label and label.lower() in wide_fields:
            if line_items:
                while len(line_items) < pairs_per_row:
                    line_items.append(('', ''))
                data.append([card(item_label, item_value) if item_label else '' for item_label, item_value in line_items])
                line_items = []
            wide_row = [card(label, value)] + [''] * (total_cols - 1)
            data.append(wide_row)
            continue

        line_items.append((label, value))
        if len(line_items) == pairs_per_row:
            data.append([card(item_label, item_value) for item_label, item_value in line_items])
            line_items = []

    if line_items:
        while len(line_items) < pairs_per_row:
            line_items.append(('', ''))
        data.append([card(item_label, item_value) if item_label else '' for item_label, item_value in line_items])

    col_widths = [57 * mm] * 3 if pairs_per_row == 3 else [86 * mm] * 2
    table = Table(data, colWidths=col_widths)
    style_commands = [
        ('BACKGROUND', (0, 0), (-1, -1), PALETTE['surface']),
        ('GRID', (0, 0), (-1, -1), 0.35, PALETTE['border']),
        ('LEFTPADDING', (0, 0), (-1, -1), left_padding),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]

    for row_index, row in enumerate(data):
        if row[0] != '' and row[1:] == [''] * (total_cols - 1):
            style_commands.append(('SPAN', (0, row_index), (-1, row_index)))

    table.setStyle(TableStyle(style_commands))
    return table


def _build_project_task_row(task: ProjectTask) -> list[Any]:
    styles = _get_styles()
    return [
        _p_markup(f'<b>{escape(task.code or f"J.{task.project_id}.{task.id}")}</b><br/>{escape(normalize_text(task.what))}', styles['table_cell_small']),
        normalize_text(task.employee_name),
        format_date_br(task.due_date),
        normalize_text(task.stage or task.status),
        f'{to_float(task.estimated_hours):.1f}h',
        f'{to_float(task.worked_hours):.1f}h',
        f'{task_completion_percent(task)}%',
        f'{calculate_task_score(task):.1f}',
    ]


def _task_header_table(task: ProjectTask, occurrence_summary: dict[str, Any]) -> Table:
    styles = _get_styles()
    card_style = ParagraphStyle(
        'GVTaskCard',
        parent=styles['table_cell'],
        fontName='Helvetica',
        fontSize=8.2,
        leading=11,
        textColor=PALETTE['text'],
        wordWrap='CJK',
    )

    def card(label: str, value: str) -> Paragraph:
        markup = (
            f'<font color="#0f766e"><b>{escape(label)}</b></font><br/>'
            f'<font color="#0f172a">{escape(value or "-")}</font>'
        )
        return Paragraph(markup, card_style)

    rows = [
        [
            card('Quem', normalize_text(task.employee_name)),
            card('Quando', format_date_br(task.due_date)),
            card('Onde', f'{task.project.code} - {task.project.name}' if task.project else 'Projeto não identificado'),
        ],
        [
            card('Horas previstas', f'{to_float(task.estimated_hours):.1f}h'),
            card('Peso', f'{to_float(task.score_weight, 1.0):.2f}'),
            card('Pontuação', f'{calculate_task_score(task):.1f} pts'),
        ],
        [
            card('Ocorrências positivas', f"{occurrence_summary['positive']['count']} | {format_incident_score(int(occurrence_summary['positive']['score']))}"),
            card('Ocorrências negativas', f"{occurrence_summary['negative']['count']} | {format_incident_score(int(occurrence_summary['negative']['score']))}"),
            card('Resultado ocorrências', format_incident_score(int(occurrence_summary['total_score']))),
        ],
        [card('Como', normalize_text(task.how)), '', ''],
        [card('Observações', normalize_text(task.notes)), '', ''],
    ]

    table = Table(rows, colWidths=[58 * mm, 58 * mm, 58 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PALETTE['surface']),
        ('GRID', (0, 0), (-1, -1), 0.35, PALETTE['border']),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (0, 3), (2, 3)),
        ('SPAN', (0, 4), (2, 4)),
    ]))
    return table


def generate_task_summary_pdf_bytes(task: ProjectTask) -> bytes:
    styles = _get_styles()
    buffer = BytesIO()
    company = Company.query.get(task.project.company_id) if task.project else None
    company_name = company.name if company else 'Empresa'
    doc, decorator = _pdf_doc(buffer, 'Relatório de Atividade de Projeto', company_name)
    story: list[Any] = []
    occurrence_summary = task_occurrence_summary(task)

    story.append(Paragraph(f'{escape(task.code or f"J.{task.id}")} - {escape(normalize_text(task.what))}', styles['title']))
    story.append(Paragraph(f'{escape(company_name)} | Gerado em {format_date_br(datetime.now())}', styles['muted']))
    story.append(Spacer(1, 4))
    story.append(Paragraph('Cabeçalho geral', styles['subtitle']))
    story.append(_task_header_table(task, occurrence_summary))
    story.append(Spacer(1, 8))

    story.append(Paragraph('Ocorrências detalhadas', styles['subtitle']))
    occurrences = task_occurrences(task)
    if occurrences:
        occurrence_rows = [['Data', 'Tipo', 'Título', 'Descrição', 'Pontuação']]
        for occurrence in occurrences:
            occurrence_rows.append([
                format_date_br(occurrence.created_at),
                normalize_text(occurrence.type),
                normalize_text(occurrence.title),
                normalize_text(occurrence.description, '-'),
                format_incident_score(int(occurrence.score or 0)),
            ])
        story.append(_section_table(occurrence_rows, [20 * mm, 20 * mm, 38 * mm, 84 * mm, 18 * mm], compact=True, shaded=True))
    else:
        story.append(Paragraph('Nenhuma ocorrência registrada para o contexto desta atividade.', styles['body']))
    story.append(Spacer(1, 8))

    story.append(Paragraph('Diário de bordo', styles['subtitle']))
    diary_rows = task_diary_rows(task)
    if diary_rows:
        story.append(_section_table([['Data', 'Registro']] + [[date_label, text] for date_label, text in diary_rows], [34 * mm, 142 * mm], shaded=True))
    else:
        story.append(Paragraph('Nenhum registro no diário de bordo.', styles['body']))
    story.append(Spacer(1, 8))

    story.append(Paragraph('Colaboradores e horas realizadas', styles['subtitle']))
    collaborator_rows = [['Colaborador', 'Previstas', 'Realizadas', 'Observações']]
    for collab in task_collaborators(task):
        collaborator_rows.append([
            normalize_text(collab['employee_name']),
            f"{to_float(collab['estimated_hours']):.1f}h",
            f"{to_float(collab['worked_hours']):.1f}h",
            normalize_text(collab['notes'], '-'),
        ])
    story.append(_section_table(collaborator_rows, [56 * mm, 24 * mm, 24 * mm, 72 * mm], shaded=True))

    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    return buffer.getvalue()


def generate_project_summary_pdf_bytes(project: Project) -> bytes:
    styles = _get_styles()
    buffer = BytesIO()
    company = Company.query.get(project.company_id) if project.company_id else None
    company_name = company.name if company else 'Empresa'
    doc, decorator = _pdf_doc(buffer, 'Relatório de Projeto', company_name)
    story: list[Any] = []
    collaborator_rows, estimated_total, worked_total = aggregate_project_hours(project)
    tasks = project.tasks.order_by(ProjectTask.due_date.asc().nullslast(), ProjectTask.id.asc()).all()
    occurrence = project_occurrence_summary(project)

    story.append(Paragraph(f'{escape(project.code)} - {escape(project.name)}', styles['title']))
    story.append(Paragraph(f'{escape(company_name)} | Gerado em {format_date_br(datetime.now())}', styles['muted']))
    story.append(Spacer(1, 4))
    story.append(Paragraph('Cabeçalho geral', styles['subtitle']))
    story.append(_compact_info_table(build_header_rows_project(project, estimated_total, worked_total), pairs_per_row=2, wide_fields={'Observações'}))
    story.append(Spacer(1, 8))

    story.append(Paragraph('Horas por colaborador', styles['subtitle']))
    hour_rows = [['Colaborador', 'Horas previstas', 'Horas realizadas']]
    for row in collaborator_rows or [{'employee_name': 'Sem lançamentos', 'estimated_hours': 0, 'worked_hours': 0}]:
        hour_rows.append([row['employee_name'], f"{to_float(row['estimated_hours']):.1f}h", f"{to_float(row['worked_hours']):.1f}h"])
    story.append(_section_table(hour_rows, [90 * mm, 42 * mm, 42 * mm], shaded=True))
    story.append(Spacer(1, 8))

    story.append(Paragraph('Indicadores de ocorrências', styles['subtitle']))
    story.append(_section_table([
        ['Ocorrências positivas', 'Ocorrências negativas', 'Resultado', 'Pontuação'],
        [
            f"{occurrence['positive']['count']} | {format_incident_score(int(occurrence['positive']['score']))}",
            f"{occurrence['negative']['count']} | {format_incident_score(int(occurrence['negative']['score']))}",
            format_incident_score(int(occurrence['total_score'])),
            f'{calculate_project_score(project)} pts',
        ],
    ], [44 * mm, 44 * mm, 42 * mm, 40 * mm], shaded=True))
    story.append(Spacer(1, 8))

    story.append(Paragraph('Atividades do projeto', styles['subtitle']))
    if not tasks:
        story.append(Paragraph('Nenhuma atividade cadastrada.', styles['body']))
    else:
        task_rows = [['Atividade', 'Quem', 'Quando', 'Etapa', 'Prev.', 'Real.', '%']]
        for task in tasks:
            task_rows.append(_build_project_task_row(task)[:-1])
        story.append(_section_table(task_rows, [72 * mm, 30 * mm, 18 * mm, 16 * mm, 14 * mm, 14 * mm, 12 * mm], left_padding=7, compact=True, shaded=True))

    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    return buffer.getvalue()


def generate_portfolio_summary_pdf_bytes(portfolio: Portfolio) -> bytes:
    styles = _get_styles()
    buffer = BytesIO()
    company = Company.query.get(portfolio.company_id) if portfolio.company_id else None
    company_name = company.name if company else 'Empresa'
    doc, decorator = _pdf_doc(buffer, 'Relatório de Portfólio de Projetos', company_name)
    story: list[Any] = []
    projects = Project.query.filter_by(company_id=portfolio.company_id, portfolio_id=portfolio.id).order_by(Project.deadline.asc().nullslast(), Project.id.asc()).all()
    collaborator_rows, estimated_total, worked_total, avg_progress = aggregate_portfolio_hours(portfolio)
    occurrence = portfolio_occurrence_summary(portfolio)

    story.append(Paragraph(f'{escape(portfolio.code)} - {escape(portfolio.name)}', styles['title']))
    story.append(Paragraph(f'{escape(company_name)} | Gerado em {format_date_br(datetime.now())}', styles['muted']))
    story.append(Spacer(1, 4))
    story.append(Paragraph('Cabeçalho geral', styles['subtitle']))
    story.append(_compact_info_table(build_header_rows_portfolio(portfolio, estimated_total, worked_total, avg_progress), pairs_per_row=2, wide_fields={'Observações'}))
    story.append(Spacer(1, 8))

    story.append(Paragraph('Horas por colaborador', styles['subtitle']))
    hour_rows = [['Colaborador', 'Horas previstas', 'Horas realizadas']]
    for row in collaborator_rows or [{'employee_name': 'Sem lançamentos', 'estimated_hours': 0, 'worked_hours': 0}]:
        hour_rows.append([row['employee_name'], f"{to_float(row['estimated_hours']):.1f}h", f"{to_float(row['worked_hours']):.1f}h"])
    story.append(_section_table(hour_rows, [90 * mm, 42 * mm, 42 * mm], shaded=True))
    story.append(Spacer(1, 8))

    story.append(Paragraph('Indicadores de ocorrências', styles['subtitle']))
    story.append(_section_table([
        ['Ocorrências positivas', 'Ocorrências negativas', 'Resultado', 'Pontuação'],
        [
            f"{occurrence['positive']['count']} | {format_incident_score(int(occurrence['positive']['score']))}",
            f"{occurrence['negative']['count']} | {format_incident_score(int(occurrence['negative']['score']))}",
            format_incident_score(int(occurrence['total_score'])),
            f'{calculate_portfolio_score(portfolio)} pts',
        ],
    ], [44 * mm, 44 * mm, 42 * mm, 40 * mm], shaded=True))
    story.append(Spacer(1, 8))

    story.append(Paragraph('Projetos e atividades', styles['subtitle']))
    if not projects:
        story.append(Paragraph('Nenhum projeto vinculado a este portfólio.', styles['body']))
    else:
        for project in projects:
            _, project_estimated, project_worked = aggregate_project_hours(project)
            project_occurrence = project_occurrence_summary(project)
            story.append(Indenter(left=8 * mm))
            story.append(Paragraph(f'{escape(project.code)} - {escape(project.name)}', styles['block_title']))
            story.append(_section_table([
                ['Responsável', 'Prazo', '% conclusão', 'Previstas', 'Realizadas'],
                [
                    normalize_text(project.owner, 'Não definido'),
                    format_date_br(project.deadline),
                    f"{int(project.task_stats.get('progress', 0))}%",
                    f'{project_estimated:.1f}h',
                    f'{project_worked:.1f}h',
                ],
            ], [54 * mm, 28 * mm, 26 * mm, 26 * mm, 36 * mm], left_padding=10, shaded=True))
            story.append(Spacer(1, 4))
            story.append(_section_table([
                ['Ocorrências positivas', 'Ocorrências negativas', 'Resultado', 'Pontuação'],
                [
                    f"{project_occurrence['positive']['count']} | {format_incident_score(int(project_occurrence['positive']['score']))}",
                    f"{project_occurrence['negative']['count']} | {format_incident_score(int(project_occurrence['negative']['score']))}",
                    format_incident_score(int(project_occurrence['total_score'])),
                    f'{calculate_project_score(project)} pts',
                ],
            ], [44 * mm, 44 * mm, 42 * mm, 40 * mm], left_padding=10, shaded=True))
            story.append(Spacer(1, 4))
            project_tasks = project.tasks.order_by(ProjectTask.due_date.asc().nullslast(), ProjectTask.id.asc()).all()
            if project_tasks:
                story.append(Indenter(left=6 * mm))
                task_rows = [['Atividade', 'Quem', 'Quando', 'Etapa', 'Prev.', 'Real.', '%']]
                for task in project_tasks:
                    task_rows.append(_build_project_task_row(task)[:-1])
                story.append(_section_table(task_rows, [66 * mm, 28 * mm, 18 * mm, 14 * mm, 13 * mm, 13 * mm, 10 * mm], left_padding=8, compact=True, shaded=True))
                story.append(Indenter(left=-6 * mm))
            else:
                story.append(Paragraph('Nenhuma atividade cadastrada neste projeto.', styles['body']))
            story.append(Indenter(left=-8 * mm))
            story.append(Spacer(1, 6))

    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    return buffer.getvalue()
