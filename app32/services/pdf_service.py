import os
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.units import inch

class PDFGenerator:
    """Helper service to generate premium PDF reports using ReportLab."""
    
    @staticmethod
    def generate_my_work_report(user_name, activities, stats):
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=50, leftMargin=50,
            topMargin=50, bottomMargin=50
        )
        
        styles = getSampleStyleSheet()
        # Custom styles
        title_style = ParagraphStyle(
            'PremiumTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=12
        )
        subtitle_style = ParagraphStyle(
            'PremiumSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=20
        )
        
        elements = []
        
        # Header
        elements.append(Paragraph("Relatório de Atividades - Gestão Versus", title_style))
        elements.append(Paragraph(f"Colaborador: {user_name} | Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
        elements.append(Spacer(1, 10))
        
        # Stats Table
        stats_data = [
            ["Pendentes", "Em Andamento", "Atrasadas", "Concluídas"],
            [stats.get('pending', 0), stats.get('in_progress', 0), stats.get('overdue', 0), stats.get('completed', 0)]
        ]
        stats_table = Table(stats_data, colWidths=[1.2*inch]*4)
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#475569")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0"))
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 20))
        
        # Activities Table
        data = [["Tipo", "Descrição / Projeto", "Prazo", "Status"]]
        for act in activities:
            data.append([
                act.get('type', 'N/A').capitalize(),
                act.get('title', 'Sem título'),
                act.get('due_date') or act.get('deadline') or '--',
                act.get('status', 'N/A')
            ])
            
        table = Table(data, colWidths=[0.8*inch, 3.2*inch, 1.0*inch, 1.0*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
