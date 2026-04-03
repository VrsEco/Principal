from __future__ import annotations

from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from services.work_journey_agenda_service import get_work_journey_agenda


def generate_work_journey_agenda_pdf(company_id: int, employee_id: int, anchor: date, scope: str) -> bytes:
    payload = get_work_journey_agenda(company_id, employee_id, anchor, scope, False)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    margin_x = 12 * mm
    y = height - 15 * mm

    pdf.setTitle(f"agenda-jornada-{payload['employee']['name']}-{payload['anchor_date']}")
    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(margin_x, y, 'Agenda da Jornada do Colaborador')
    y -= 8 * mm
    pdf.setFont('Helvetica', 10)
    pdf.drawString(margin_x, y, f"Colaborador: {payload['employee']['name']} · Escopo: {payload['scope_label']} · Status: {payload['status_label']}")
    y -= 6 * mm
    pdf.drawString(margin_x, y, f"Período: {payload['period_start']} até {payload['period_end']}")
    y -= 10 * mm

    for day in payload['days']:
        if y < 35 * mm:
            pdf.showPage()
            y = height - 15 * mm
        pdf.setFont('Helvetica-Bold', 12)
        pdf.setFillColor(colors.HexColor('#1e3a8a'))
        pdf.drawString(margin_x, y, f"{day.get('subtitle') or day.get('weekday_label') or day['label']} - {day['label']}")
        pdf.setFillColor(colors.black)
        y -= 6 * mm
        for block in day['blocks']:
            if y < 25 * mm:
                pdf.showPage()
                y = height - 15 * mm
            pdf.setFont('Helvetica-Bold', 10)
            title = f"{block['name']} ({block['start_time']} - {block['end_time']})"
            if block['overload_minutes'] > 0:
                title += f" · Sobrecarga {block['overload_label']}"
            pdf.drawString(margin_x + 4 * mm, y, title)
            y -= 5 * mm
            pdf.setFont('Helvetica', 9)
            items = block['items'] or []
            if not items:
                pdf.drawString(margin_x + 8 * mm, y, 'Sem tarefas alocadas.')
                y -= 5 * mm
                continue
            for item in items:
                if y < 18 * mm:
                    pdf.showPage()
                    y = height - 15 * mm
                line = f"• {item['display_title']} · {item['allocated_label']}"
                if item.get('planned_window_label'):
                    line += f" · {item['planned_window_label']}"
                if item.get('is_over_capacity'):
                    line += ' · Extrapolado'
                pdf.drawString(margin_x + 8 * mm, y, line[:150])
                y -= 4.5 * mm
            y -= 1 * mm
        y -= 3 * mm

    if payload['unassigned_items']:
        if y < 35 * mm:
            pdf.showPage()
            y = height - 15 * mm
        pdf.setFont('Helvetica-Bold', 12)
        pdf.drawString(margin_x, y, 'Fila de não alocadas')
        y -= 6 * mm
        pdf.setFont('Helvetica', 9)
        for item in payload['unassigned_items']:
            if y < 18 * mm:
                pdf.showPage()
                y = height - 15 * mm
            line = f"• {item['display_title']} · {item['planned_date']} · {item['allocated_label']}"
            pdf.drawString(margin_x + 6 * mm, y, line[:150])
            y -= 4.5 * mm

    pdf.save()
    return buffer.getvalue()
