from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from typing import Any

from flask_login import current_user
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models import Employee, User
from services.notification_hub import notification_hub
from services.proactive_service import _build_summary_attempt_order

PALETTE = {
    'primary': colors.HexColor('#2563eb'),
    'primary_dark': colors.HexColor('#1d4ed8'),
    'accent': colors.HexColor('#0f766e'),
    'text': colors.HexColor('#0f172a'),
    'muted': colors.HexColor('#475569'),
    'border': colors.HexColor('#cbd5e1'),
    'surface': colors.HexColor('#f8fafc'),
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('RoutineSummaryTitle', parent=base['Title'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=PALETTE['primary_dark'], alignment=TA_LEFT, spaceAfter=10),
        'subtitle': ParagraphStyle('RoutineSummarySubtitle', parent=base['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=PALETTE['accent'], spaceBefore=8, spaceAfter=6),
        'body': ParagraphStyle('RoutineSummaryBody', parent=base['BodyText'], fontName='Helvetica', fontSize=8.6, leading=11, textColor=PALETTE['text'], spaceAfter=4, wordWrap='CJK'),
        'muted': ParagraphStyle('RoutineSummaryMuted', parent=base['BodyText'], fontName='Helvetica', fontSize=8, leading=10, textColor=PALETTE['muted'], spaceAfter=3),
        'table_header': ParagraphStyle('RoutineSummaryTableHeader', parent=base['BodyText'], fontName='Helvetica-Bold', fontSize=8.1, leading=10, textColor=colors.white, wordWrap='CJK'),
        'table_cell': ParagraphStyle('RoutineSummaryTableCell', parent=base['BodyText'], fontName='Helvetica', fontSize=8, leading=9.6, textColor=PALETTE['text'], wordWrap='CJK'),
    }


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


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    safe = escape(str(text or '-')).replace('\n', '<br/>')
    return Paragraph(safe, style)


def _summary_table(rows: list[list[Any]], col_widths: list[float]) -> Table:
    styles = _styles()
    formatted = []
    for idx, row in enumerate(rows):
        row_style = styles['table_header'] if idx == 0 else styles['table_cell']
        formatted.append([cell if isinstance(cell, Paragraph) else _paragraph(cell, row_style) for cell in row])

    table = Table(formatted, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PALETTE['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), PALETTE['surface']),
        ('GRID', (0, 0), (-1, -1), 0.35, PALETTE['border']),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return table


def _resolve_user_from_employee(employee: Employee | None) -> User | None:
    if not employee or not getattr(employee, 'user_id', None):
        return None
    user = User.query.get(employee.user_id)
    if not user or not getattr(user, 'is_active', False):
        return None
    return user


def get_routine_analysis_target_user(company_id: int, employee_id: int | None) -> User | None:
    if not employee_id:
        return None
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id, status='active').first()
    return _resolve_user_from_employee(employee)


def build_summary_hint(user: User | None) -> str | None:
    if not user:
        return 'Colaborador sem usuário ativo vinculado para envio digital.'
    available = []
    if getattr(user, 'email', None):
        available.append('E-mail')
    if getattr(user, 'whatsapp', None):
        available.append('WhatsApp')
    if available:
        return None
    return 'Colaborador sem E-mail ou WhatsApp configurados no perfil. PDF permanece disponível.'


def build_summary_options(user: User | None, pdf_url: str, send_url: str) -> list[dict[str, str]]:
    options = [{'channel': 'pdf', 'label': 'PDF', 'kind': 'download', 'url': pdf_url}]
    if user and getattr(user, 'email', None):
        options.append({'channel': 'email', 'label': 'E-mail', 'kind': 'send', 'url': send_url})
    if user and getattr(user, 'whatsapp', None):
        options.append({'channel': 'whatsapp', 'label': 'WhatsApp', 'kind': 'send', 'url': send_url})
    return options


def _normalize_text(value: Any, fallback: str = 'Não informado') -> str:
    normalized = str(value or '').strip()
    return normalized or fallback


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except Exception:
        return default


def ensure_routine_analysis_drilldown(company_id: int, employee_id: int, analysis: dict[str, Any]) -> dict[str, Any]:
    if analysis.get('drilldown'):
        return analysis

    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).first()
    if not employee:
        return analysis

    analysis['drilldown'] = {
        'employee': {
            'id': employee.id,
            'name': getattr(employee, 'name', None) or f'Colaborador {employee.id}',
            'department': getattr(employee, 'department', None) or 'Não informado',
            'email': getattr(employee, 'email', None) or '',
        },
        'summary': {
            'routine_count': 0,
            'routine_total_hours': 0.0,
            'process_count': 0,
            'process_total_hours': 0.0,
            'project_count': 0,
            'project_total_hours': 0.0,
            'meeting_count': 0,
            'meeting_total_hours': 0.0,
        },
        'routine_groups': [],
        'routines': [],
        'projects': [],
        'processes': [],
        'meetings': [],
    }
    return analysis


def build_routine_analysis_summary_payload(analysis: dict[str, Any]) -> dict[str, str | None]:
    drilldown = analysis.get('drilldown') or {}
    employee = drilldown.get('employee') or {}
    employee_name = _normalize_text(employee.get('name'), 'Colaborador')
    summary = analysis.get('summary') or {}
    drill_summary = drilldown.get('summary') or {}
    top_routines = drilldown.get('routines') or []
    top_processes = drilldown.get('processes') or []
    top_projects = drilldown.get('projects') or []
    top_meetings = drilldown.get('meetings') or []

    routine_lines = '\n'.join(
        f"  • {item.get('name')} — {_to_float(item.get('weekly_equivalent_hours')):.1f}h/sem"
        for item in top_routines[:5]
    ) or '  • Sem rotinas vinculadas no recorte.'
    process_lines = '\n'.join(
        f"  • {item.get('instance_title')} — {_to_float(item.get('estimated_hours')):.1f}h"
        for item in top_processes[:5]
    ) or '  • Sem instâncias realizadas no recorte.'
    project_lines = '\n'.join(
        f"  • {item.get('task_name')} — {_to_float(item.get('estimated_hours')):.1f}h"
        for item in top_projects[:5]
    ) or '  • Sem carga de projetos no recorte.'
    meeting_lines = '\n'.join(
        f"  • {item.get('title')} — {_to_float(item.get('estimated_hours')):.1f}h"
        for item in top_meetings[:5]
    ) or '  • Sem reuniões no recorte.'

    return {
        'subject': f'Resumo da Rotina - {employee_name}',
        'body': (
            f'Olá, {employee_name}!\n\n'
            'Segue o resumo da sua análise de rotina:\n\n'
            f'- Escopo: {_normalize_text(summary.get("scope_label"))}\n'
            f'- Departamento: {_normalize_text(employee.get("department"))}\n'
            f'- Capacidade semanal: {_to_float(summary.get("total_capacity_weekly_hours")):.1f}h\n'
            f'- Rotina prevista: {_to_float(summary.get("total_fixed_weekly_hours")):.1f}h/sem\n'
            f'- Projetos no escopo: {_to_float(summary.get("scoped_project_hours")):.1f}h\n'
            f'- Processos realizados no escopo: {_to_float(summary.get("scoped_process_hours")):.1f}h\n'
            f'- Reuniões no escopo: {_to_float(summary.get("scoped_meeting_hours")):.1f}h\n'
            f'- Comprometimento total: {_to_float(summary.get("scoped_total_commitment_hours")):.1f}h\n'
            f'- Utilização total: {_to_float(summary.get("scoped_total_utilization_percent")):.1f}%\n\n'
            f'ROTINA PREVISTA ({int(drill_summary.get("routine_count", 0))} itens)\n'
            f'{routine_lines}\n\n'
            f'PROCESSOS REALIZADOS ({int(drill_summary.get("process_count", 0))} itens)\n'
            f'{process_lines}\n\n'
            f'PROJETOS ({int(drill_summary.get("project_count", 0))} itens)\n'
            f'{project_lines}\n\n'
            f'REUNIÕES ({int(drill_summary.get("meeting_count", 0))} itens)\n'
            f'{meeting_lines}\n'
        ),
        'html_body': None,
    }


def _build_pdf_doc(buffer: BytesIO, title: str, company_name: str):
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


def generate_routine_analysis_summary_pdf_bytes(company_name: str, analysis: dict[str, Any]) -> bytes:
    styles = _styles()
    drilldown = analysis.get('drilldown') or {}
    employee = drilldown.get('employee') or {}
    summary = analysis.get('summary') or {}
    drill_summary = drilldown.get('summary') or {}

    employee_name = _normalize_text(employee.get('name'), 'Colaborador')
    title = f'Resumo da Rotina - {employee_name}'
    buffer = BytesIO()
    doc, decorator = _build_pdf_doc(buffer, title, company_name)
    story = [
        Paragraph(title, styles['title']),
        Paragraph(
            f'Escopo atual: {_normalize_text(summary.get("scope_label"))} · Departamento: {_normalize_text(employee.get("department"))}',
            styles['muted'],
        ),
        Spacer(1, 4),
        _summary_table(
            [
                ['Indicador', 'Valor'],
                ['Capacidade semanal', f'{_to_float(summary.get("total_capacity_weekly_hours")):.1f}h'],
                ['Rotina prevista', f'{_to_float(summary.get("total_fixed_weekly_hours")):.1f}h/sem'],
                ['Projetos', f'{_to_float(summary.get("scoped_project_hours")):.1f}h'],
                ['Processos realizados', f'{_to_float(summary.get("scoped_process_hours")):.1f}h'],
                ['Reuniões', f'{_to_float(summary.get("scoped_meeting_hours")):.1f}h'],
                ['Comprometimento total', f'{_to_float(summary.get("scoped_total_commitment_hours")):.1f}h'],
                ['Utilização total', f'{_to_float(summary.get("scoped_total_utilization_percent")):.1f}%'],
            ],
            [70 * mm, 100 * mm],
        ),
        Spacer(1, 8),
        Paragraph('Rotina prevista x realizado', styles['subtitle']),
        _summary_table(
            [
                ['Bloco', 'Qtde.', 'Horas'],
                ['Rotinas cadastradas (previsto)', str(int(drill_summary.get('routine_count', 0))), f'{_to_float(drill_summary.get("routine_total_hours")):.1f}h/sem'],
                ['Instâncias de processo (realizado)', str(int(drill_summary.get('process_count', 0))), f'{_to_float(drill_summary.get("process_total_hours")):.1f}h'],
                ['Projetos', str(int(drill_summary.get('project_count', 0))), f'{_to_float(drill_summary.get("project_total_hours")):.1f}h'],
                ['Reuniões', str(int(drill_summary.get('meeting_count', 0))), f'{_to_float(drill_summary.get("meeting_total_hours")):.1f}h'],
            ],
            [88 * mm, 35 * mm, 47 * mm],
        ),
        Spacer(1, 8),
    ]

    def append_list(title_text: str, rows: list[list[Any]], widths: list[float], empty_text: str):
        story.append(Paragraph(title_text, styles['subtitle']))
        if len(rows) == 1:
            story.append(Paragraph(empty_text, styles['muted']))
        else:
            story.append(_summary_table(rows, widths))
        story.append(Spacer(1, 7))

    routine_rows = [['Rotina', 'Processo', 'Horas/sem']]
    for item in (drilldown.get('routines') or [])[:8]:
        routine_rows.append([
            item.get('name') or 'Rotina',
            item.get('process_name') or 'Sem processo',
            f'{_to_float(item.get("weekly_equivalent_hours")):.1f}h',
        ])
    append_list('Rotinas cadastradas (previsto)', routine_rows, [70 * mm, 85 * mm, 15 * mm], 'Sem rotinas vinculadas no recorte.')

    process_rows = [['Instância', 'Processo', 'Horas']]
    for item in (drilldown.get('processes') or [])[:8]:
        process_rows.append([
            item.get('instance_title') or 'Instância',
            item.get('process_name') or 'Processo',
            f'{_to_float(item.get("estimated_hours")):.1f}h',
        ])
    append_list('Instâncias de processo (realizado)', process_rows, [70 * mm, 85 * mm, 15 * mm], 'Sem instâncias realizadas no recorte.')

    project_rows = [['Atividade', 'Projeto', 'Horas']]
    for item in (drilldown.get('projects') or [])[:8]:
        project_rows.append([
            item.get('task_name') or 'Atividade',
            item.get('project_name') or 'Projeto',
            f'{_to_float(item.get("estimated_hours")):.1f}h',
        ])
    append_list('Projetos', project_rows, [70 * mm, 85 * mm, 15 * mm], 'Sem carga de projetos no recorte.')

    meeting_rows = [['Reunião', 'Contexto', 'Horas']]
    for item in (drilldown.get('meetings') or [])[:8]:
        meeting_rows.append([
            item.get('title') or 'Reunião',
            item.get('project_name') or 'Sem projeto',
            f'{_to_float(item.get("estimated_hours")):.1f}h',
        ])
    append_list('Reuniões', meeting_rows, [70 * mm, 85 * mm, 15 * mm], 'Sem reuniões no recorte.')

    doc.build(story, onFirstPage=decorator, onLaterPages=decorator)
    return buffer.getvalue()


def send_routine_analysis_summary_to_employee(company_id: int, analysis: dict[str, Any], preferred_channel: str | None = None) -> dict[str, Any]:
    drilldown = analysis.get('drilldown') or {}
    employee = drilldown.get('employee') or {}
    user = get_routine_analysis_target_user(company_id, employee.get('id'))
    if not user:
        return {'success': False, 'error': 'Colaborador sem usuário ativo vinculado'}

    payload = build_routine_analysis_summary_payload(analysis)
    attempt_order = [preferred_channel] if preferred_channel else _build_summary_attempt_order(user)
    if not attempt_order:
        return {'success': False, 'error': 'Usuário sem canais configurados para envio'}

    for channel in attempt_order:
        normalized = (channel or '').strip().lower()
        if normalized == 'email':
            result = notification_hub.send_email(user.email, payload['subject'], payload['body'], html_body=payload.get('html_body'))
        else:
            result = notification_hub.send_to_user(user, normalized, payload['body'], subject=payload['subject'], html_body=payload.get('html_body'), parse_mode='HTML')
        if result.get('success'):
            result['delivery_channel'] = normalized
            result['subject'] = payload['subject']
            result['target_user_id'] = user.id
            return result

    return {'success': False, 'error': 'Falha ao enviar resumo em todos os canais configurados', 'attempted_channels': attempt_order}
