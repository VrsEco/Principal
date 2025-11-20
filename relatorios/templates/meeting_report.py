#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template Individual de Relatório de Reunião
Sistema Simplificado - Um botão = um relatório
"""

import sys
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Adiciona caminhos para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config_database import get_db


def generate_meeting_report_html(meeting_id: int) -> str:
    """
    Gera relatório HTML de uma reunião específica

    Args:
        meeting_id: ID da reunião

    Returns:
        str: HTML completo do relatório
    """

    # 1. Buscar dados da reunião
    db = get_db()
    meeting = db.get_meeting(meeting_id)

    if not meeting:
        return f"<html><body><h1>Reunião não encontrada (ID: {meeting_id})</h1></body></html>"

    # 2. Buscar dados da empresa
    company_id = meeting.get("company_id")
    company = db.get_company(company_id) if company_id else {}

    # 3. Buscar participantes
    guests = meeting.get("guests", [])
    if isinstance(guests, str):
        try:
            import json

            guests = json.loads(guests)
        except:
            guests = []

    # 4. Buscar pauta
    agenda = meeting.get("agenda", [])
    if isinstance(agenda, str):
        try:
            import json

            agenda = json.loads(agenda)
        except:
            agenda = []

    # 5. Buscar discussões
    discussions = meeting.get("discussions", [])
    if isinstance(discussions, str):
        try:
            import json

            discussions = json.loads(discussions)
        except:
            discussions = []

    # 6. Buscar atividades geradas
    activities = meeting.get("activities", [])
    if isinstance(activities, str):
        try:
            import json

            activities = json.loads(activities)
        except:
            activities = []

    # 7. Gerar HTML
    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Reunião - {meeting.get('title', 'Sem título')}</title>
    <style>
        {get_report_css()}
    </style>
</head>
<body>
    <div class="report-container">
        <!-- Cabeçalho -->
        <header class="report-header">
            <div class="company-info">
                <h1>{company.get('name', company.get('legal_name', 'Empresa'))}</h1>
                <p class="report-title">Relatório de Reuniões - {meeting.get('title', 'Sem título')} - Status: {get_status_label(meeting.get('status', 'draft'))} - Emitido em: {datetime.now().strftime('%d/%m/%Y - %H:%M')}</p>
            </div>
        </header>
        
                        <!-- Dados Preliminares e Convites -->
                        <section class="preliminary-data">
                            <h2>📋 Dados Preliminares e Convites</h2>
                            
                            <!-- Informações de Agendamento -->
                            <div class="scheduling-summary">
                                {generate_scheduling_summary(meeting)}
                            </div>
            
            <div class="subsection">
                <h3>Pauta</h3>
                {generate_agenda_section(agenda)}
            </div>
            
            <div class="subsection">
                <h3>Convidados</h3>
                {generate_participants_section(guests)}
            </div>
            
            <div class="subsection">
                <h3>Observações</h3>
                <div class="notes-content">
                    {meeting.get('invite_notes', 'Nenhuma observação foi adicionada.') if meeting.get('invite_notes') else 'Nenhuma observação foi adicionada.'}
                </div>
            </div>
        </section>
        
                        <!-- Execução da Reunião -->
                        <section class="meeting-execution">
                            <h2>🎯 Execução da Reunião</h2>
                            
                            <!-- Informações de Execução -->
                            <div class="execution-summary">
                                {generate_execution_summary(meeting)}
                            </div>
                            
                            <div class="subsection">
                                <h3>Participantes</h3>
                                {generate_participants_execution_section(meeting)}
                            </div>
            
            <div class="subsection">
                <h3>Discussões</h3>
                {generate_discussions_section(discussions)}
            </div>
            
            
            <div class="subsection">
                <h3>Notas Gerais</h3>
                <div class="notes-content">
                    {meeting.get('meeting_notes', 'Nenhuma nota foi registrada.') if meeting.get('meeting_notes') else 'Nenhuma nota foi registrada.'}
                </div>
            </div>
        </section>
        
        <!-- Projeto e Atividades Cadastradas -->
        <section class="project-activities">
            <h2>📊 Projeto e Atividades Cadastradas</h2>
            {generate_project_activities_section(meeting)}
        </section>
        
        <!-- Rodapé -->
        <footer class="report-footer">
            <p class="copyright">Versus Gestão Corporativa - Todos os direitos reservados</p>
        </footer>
        
    </div>
</body>
</html>
    """

    return html


def generate_participants_section(guests):
    """Gera seção de participantes"""
    if not guests:
        return """
        <div class="empty-state">
            <p>Nenhum participante foi convidado para esta reunião.</p>
        </div>
        """

    # Se guests é uma string, tentar converter para dict/lista
    if isinstance(guests, str):
        try:
            import json

            guests = json.loads(guests)
        except:
            guests = {}

    # Se guests é um dicionário com internal/external
    if isinstance(guests, dict):
        all_participants = []

        # Processar participantes internos
        internal_guests = guests.get("internal", [])
        for guest in internal_guests:
            if isinstance(guest, dict):
                all_participants.append(
                    {
                        "name": guest.get("name", "Nome não informado"),
                        "email": guest.get("email", ""),
                        "type": "Interno",
                    }
                )

        # Processar participantes externos
        external_guests = guests.get("external", [])
        for guest in external_guests:
            if isinstance(guest, dict):
                all_participants.append(
                    {
                        "name": guest.get("name", "Nome não informado"),
                        "email": guest.get("email", ""),
                        "type": "Externo",
                    }
                )

        guests = all_participants

    # Se guests é uma lista vazia
    if not guests:
        return """
        <div class="empty-state">
            <p>Nenhum participante foi convidado para esta reunião.</p>
        </div>
        """

    participants_html = '<div class="participants-grid">'
    for guest in guests:
        # Se guest é uma string, tratar como nome simples
        if isinstance(guest, str):
            name = guest
            email = ""
            role = ""
        else:
            # Se é dicionário, extrair campos
            name = (
                guest.get("name", "Nome não informado")
                if hasattr(guest, "get")
                else str(guest)
            )
            email = guest.get("email", "") if hasattr(guest, "get") else ""
            role = guest.get("type", "") if hasattr(guest, "get") else ""

        participants_html += f"""
        <div class="participant-card">
            <div class="participant-info">
                <h4>{name}</h4>
                {f'<p class="email">{email}</p>' if email else ''}
                {f'<p class="role">{role}</p>' if role else ''}
            </div>
        </div>
        """

    participants_html += "</div>"

    return f"""
    <div class="participants-content">
        <p class="items-count">({len(guests)} convidados)</p>
        {participants_html}
    </div>
    """


def generate_scheduling_summary(meeting):
    """Gera resumo de agendamento da reunião"""
    scheduled_date = meeting.get("scheduled_date", "")
    scheduled_time = meeting.get("scheduled_time", "")
    location = meeting.get("location", "")
    duration = meeting.get("duration", "")

    scheduling_info = []

    if scheduled_date:
        scheduling_info.append(f"Data: {scheduled_date}")
    if scheduled_time:
        scheduling_info.append(f"Horário: {scheduled_time}")
    if location:
        scheduling_info.append(f"Local: {location}")
    elif not location:
        # Fallback para local não definido
        scheduling_info.append("Local: Não definido")

    if scheduling_info:
        info_text = " | ".join(scheduling_info)
        return f"<p><strong>Agendamento:</strong> {info_text}</p>"
    else:
        return "<p><em>Reunião ainda não foi agendada.</em></p>"


def generate_execution_summary(meeting):
    """Gera resumo de execução da reunião"""
    actual_date = meeting.get("actual_date", "")
    actual_time = meeting.get("actual_time", "")
    scheduled_date = meeting.get("scheduled_date", "")
    scheduled_time = meeting.get("scheduled_time", "")

    execution_info = []

    # Usar dados reais se disponíveis, senão usar dados agendados
    date_to_show = actual_date if actual_date else scheduled_date
    time_to_show = actual_time if actual_time else scheduled_time

    if date_to_show:
        execution_info.append(f"Data: {date_to_show}")
    if time_to_show:
        execution_info.append(f"Horário: {time_to_show}")

    # Adicionar status
    status = meeting.get("status", "draft")
    status_label = get_status_label(status)
    execution_info.append(f"Status: {status_label}")

    if execution_info:
        info_text = " | ".join(execution_info)
        return f"<p><strong>Execução:</strong> {info_text}</p>"
    else:
        return "<p><em>Reunião ainda não foi realizada.</em></p>"


def generate_participants_execution_section(meeting):
    """Gera seção de participantes da execução"""
    participants_json = meeting.get("participants_json")

    if not participants_json:
        return """
        <div class="empty-state">
            <p>Nenhum participante efetivo foi registrado para esta reunião.</p>
        </div>
        """

    # Se participants_json é uma string, tentar converter para dict/lista
    if isinstance(participants_json, str):
        try:
            import json

            participants_json = json.loads(participants_json)
        except:
            participants_json = {}

    # Se participants_json é um dicionário com internal/external
    if isinstance(participants_json, dict):
        all_participants = []

        # Processar participantes internos
        internal_participants = participants_json.get("internal", [])
        for participant in internal_participants:
            if isinstance(participant, dict):
                all_participants.append(
                    {
                        "name": participant.get("name", "Nome não informado"),
                        "email": participant.get("email", ""),
                        "type": "Interno",
                    }
                )

        # Processar participantes externos
        external_participants = participants_json.get("external", [])
        for participant in external_participants:
            if isinstance(participant, dict):
                all_participants.append(
                    {
                        "name": participant.get("name", "Nome não informado"),
                        "email": participant.get("email", ""),
                        "type": "Externo",
                    }
                )

        participants_json = all_participants

    # Se participants_json é uma lista vazia
    if not participants_json:
        return """
        <div class="empty-state">
            <p>Nenhum participante efetivo foi registrado para esta reunião.</p>
        </div>
        """

    participants_html = '<div class="participants-grid">'
    for participant in participants_json:
        # Se participant é uma string simples
        if isinstance(participant, str):
            name = participant
            email = ""
            participant_type = ""
        else:
            # Se participant é um dicionário, extrair campos
            name = (
                participant.get("name", "Nome não informado")
                if hasattr(participant, "get")
                else str(participant)
            )
            email = participant.get("email", "") if hasattr(participant, "get") else ""
            participant_type = (
                participant.get("type", "") if hasattr(participant, "get") else ""
            )

        participants_html += f"""
        <div class="participant-card">
            <div class="participant-info">
                <h4>{name}</h4>
                {f'<p class="email">{email}</p>' if email else ''}
                {f'<p class="role">{participant_type}</p>' if participant_type else ''}
            </div>
        </div>
        """

    participants_html += "</div>"

    return f"""
    <div class="participants-content">
        <p class="items-count">({len(participants_json)} participantes efetivos)</p>
        {participants_html}
    </div>
    """


def generate_project_activities_section(meeting):
    """Gera seção de projeto e atividades cadastradas no estilo planilha"""
    project_id = meeting.get("project_id")

    # Buscar dados do projeto se vinculado
    project_name = "Não vinculado"
    if project_id:
        try:
            db = get_db()
            project = db.get_project(project_id)
            if project:
                project_name = (
                    f"{project.get('code', 'N/A')} - {project.get('name', 'Sem nome')}"
                )
        except Exception as e:
            project_name = f"Erro ao carregar projeto: {str(e)}"

    # Dados para as colunas especificadas - usar dados disponíveis
    o_que = (
        meeting.get("what")
        or meeting.get("project_title")
        or meeting.get("title", "Não definido")
    )
    quem = meeting.get("who") or "Participantes da reunião"
    quando = meeting.get("when") or meeting.get("scheduled_date", "Não definido")
    como = meeting.get("how") or "Reunião presencial"

    # Gerar linha de dados
    table_row = f"""
    <tr>
        <td>{o_que}</td>
        <td>{quem}</td>
        <td>{quando}</td>
        <td>{como}</td>
        <td>{project_name}</td>
    </tr>
    """

    return f"""
    <table class="data-table">
        <thead>
            <tr>
                <th>O que</th>
                <th>Quem</th>
                <th>Quando</th>
                <th>Como</th>
                <th>Projeto Vinculado</th>
            </tr>
        </thead>
        <tbody>
            {table_row}
        </tbody>
    </table>
    """


def generate_agenda_section(agenda):
    """Gera seção de pauta"""
    if not agenda:
        return """
        <div class="empty-state">
            <p>Nenhum item foi adicionado à pauta desta reunião.</p>
        </div>
        """

    # Se agenda é uma string, tentar converter para lista
    if isinstance(agenda, str):
        try:
            import json

            agenda = json.loads(agenda)
        except:
            agenda = []

    agenda_html = '<div class="agenda-list">'
    for i, item in enumerate(agenda, 1):
        # Se item é uma string, tratar como título simples
        if isinstance(item, str):
            title = item
            description = ""
            duration = ""
        else:
            # Se é dicionário, extrair campos
            title = (
                item.get("title", f"Item {i}") if hasattr(item, "get") else str(item)
            )
            description = item.get("description", "") if hasattr(item, "get") else ""
            duration = item.get("duration", "") if hasattr(item, "get") else ""

        agenda_html += f"""
        <div class="agenda-item">
            <div class="agenda-number">{i}</div>
            <div class="agenda-content">
                <h4>{title}</h4>
                {f'<p>{description}</p>' if description else ''}
                {f'<span class="duration">⏱️ {duration}</span>' if duration else ''}
            </div>
        </div>
        """

    agenda_html += "</div>"

    return f"""
    <div class="agenda-content">
        <p class="items-count">({len(agenda)} itens)</p>
        {agenda_html}
    </div>
    """


def generate_discussions_section(discussions):
    """Gera seção de discussões"""
    if not discussions:
        return """
        <div class="empty-state">
            <p>Nenhuma discussão foi registrada nesta reunião.</p>
        </div>
        """

    # Se discussions é uma string, tentar converter para lista
    if isinstance(discussions, str):
        try:
            import json

            discussions = json.loads(discussions)
        except:
            discussions = []

    discussions_html = '<div class="discussions-list">'
    for discussion in discussions:
        # Se discussion é uma string, tratar como tópico simples
        if isinstance(discussion, str):
            topic = discussion
            summary = ""
            participants = []
            decisions = []
        else:
            # Se é dicionário, extrair campos
            topic = (
                discussion.get("topic", "Tópico não informado")
                if hasattr(discussion, "get")
                else str(discussion)
            )
            summary = (
                discussion.get("summary", "") if hasattr(discussion, "get") else ""
            )
            participants = (
                discussion.get("participants", []) if hasattr(discussion, "get") else []
            )
            decisions = (
                discussion.get("decisions", []) if hasattr(discussion, "get") else []
            )

        discussions_html += f"""
        <div class="discussion-item">
            <h4>{topic}</h4>
            {f'<p class="summary">{summary}</p>' if summary else ''}
            {f'<div class="participants">Participantes: {", ".join(participants)}</div>' if participants else ''}
            {generate_decisions_list(decisions) if decisions else ''}
        </div>
        """

    discussions_html += "</div>"

    return f"""
    <div class="discussions-content">
        <p class="items-count">({len(discussions)} discussões)</p>
        {discussions_html}
    </div>
    """


def generate_decisions_list(decisions):
    """Gera lista de decisões"""
    if not decisions:
        return ""

    decisions_html = '<div class="decisions-list">'
    for decision in decisions:
        decisions_html += f'<div class="decision-item">• {decision}</div>'
    decisions_html += "</div>"

    return decisions_html


def generate_activities_section(activities):
    """Gera seção de atividades"""
    if not activities:
        return """
        <div class="empty-state">
            <p>Nenhuma atividade foi gerada a partir desta reunião.</p>
        </div>
        """

    # Se activities é uma string, tentar converter para lista
    if isinstance(activities, str):
        try:
            import json

            activities = json.loads(activities)
        except:
            activities = []

    activities_html = '<div class="activities-list">'
    for activity in activities:
        # Se activity é uma string, tratar como título simples
        if isinstance(activity, str):
            title = activity
            description = ""
            responsible = ""
            deadline = ""
            status = "pending"
        else:
            # Se é dicionário, extrair campos
            title = (
                activity.get("title", "Atividade sem título")
                if hasattr(activity, "get")
                else str(activity)
            )
            description = (
                activity.get("description", "") if hasattr(activity, "get") else ""
            )
            responsible = (
                activity.get("responsible", "") if hasattr(activity, "get") else ""
            )
            deadline = activity.get("deadline", "") if hasattr(activity, "get") else ""
            status = (
                activity.get("status", "pending")
                if hasattr(activity, "get")
                else "pending"
            )

        activities_html += f"""
        <div class="activity-item">
            <h4>{title}</h4>
            {f'<p>{description}</p>' if description else ''}
            <div class="activity-meta">
                {f'<span class="responsible">👤 {responsible}</span>' if responsible else ''}
                {f'<span class="deadline">📅 {deadline}</span>' if deadline else ''}
                <span class="status-badge status-{status}">{get_activity_status_label(status)}</span>
            </div>
        </div>
        """

    activities_html += "</div>"

    return f"""
    <div class="activities-content">
        <p class="items-count">({len(activities)} atividades)</p>
        {activities_html}
    </div>
    """


def get_status_label(status):
    """Retorna label do status da reunião"""
    labels = {
        "draft": "Rascunho",
        "scheduled": "Agendada",
        "in_progress": "Em Andamento",
        "completed": "Concluída",
        "cancelled": "Cancelada",
    }
    return labels.get(status, status.title())


def get_activity_status_label(status):
    """Retorna label do status da atividade"""
    labels = {
        "pending": "Pendente",
        "in_progress": "Em Andamento",
        "completed": "Concluída",
        "cancelled": "Cancelada",
    }
    return labels.get(status, status.title())


def get_report_css():
    """Retorna CSS do relatório"""
    return """
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        line-height: 1.6;
        color: #333;
        background: #f8fafc;
    }
    
    .report-container {
        max-width: 800px;
        margin: 0 auto;
        background: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        min-height: 100vh;
    }
    
    .report-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .company-info h1 {
        font-size: 24px;
        margin-bottom: 5px;
        color: #2d3748;
    }
    
    .report-title {
        font-size: 16px;
        color: #4a5568;
        font-weight: 500;
        line-height: 1.3;
        margin: 0;
    }
    
    .report-meta {
        text-align: right;
        font-size: 14px;
        opacity: 0.9;
    }
    
    section {
        padding: 20px;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 15px;
    }
    
    section:last-of-type {
        border-bottom: none;
    }
    
    h2 {
        color: #2d3748;
        margin-bottom: 12px;
        font-size: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    h3 {
        color: #4a5568;
        margin-bottom: 8px;
        font-size: 14px;
        font-weight: 600;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 4px;
    }
    
    .subsection {
        margin-bottom: 15px;
        padding: 12px;
        background: #f8fafc;
        border-radius: 6px;
        border-left: 3px solid #667eea;
    }
    
    .items-count {
        color: #718096;
        font-size: 12px;
        font-style: italic;
        margin-bottom: 8px;
    }
    
    .notes-content {
        background: white;
        padding: 10px;
        border-radius: 4px;
        border: 1px solid #e2e8f0;
        color: #4a5568;
        line-height: 1.4;
        font-size: 13px;
    }
    
    .scheduling-summary {
        background: #f0f8ff;
        padding: 10px;
        border-radius: 4px;
        border-left: 3px solid #007bff;
        color: #004085;
        margin-bottom: 15px;
    }
    
    .scheduling-summary p {
        margin: 0;
        font-size: 14px;
    }
    
    .execution-summary {
        background: #e6fffa;
        padding: 10px;
        border-radius: 4px;
        border-left: 3px solid #38b2ac;
        color: #234e52;
        margin-bottom: 15px;
    }
    
    .execution-summary p {
        margin: 0;
        font-size: 14px;
    }
    
    .participants-execution-list {
        margin-top: 15px;
        padding: 10px;
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        border-radius: 4px;
    }
    
    .participants-execution-list h4 {
        margin: 0 0 10px 0;
        font-size: 14px;
        font-weight: 600;
        color: #495057;
    }
    
    .participants-execution-list ul {
        margin: 0;
        padding-left: 20px;
    }
    
    .participants-execution-list li {
        margin: 5px 0;
        font-size: 13px;
        color: #6c757d;
    }
    
    .project-info {
        background: white;
        padding: 10px;
        border-radius: 4px;
        border: 1px solid #e2e8f0;
    }
    
    .project-info h4 {
        color: #2d3748;
        margin-bottom: 6px;
        font-size: 14px;
    }
    
    .project-details p {
        margin-bottom: 4px;
        color: #4a5568;
        font-size: 13px;
    }
    
    .data-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        font-size: 12px;
    }
    
    .data-table th,
    .data-table td {
        border: 1px solid #e2e8f0;
        padding: 8px;
        text-align: left;
        vertical-align: top;
    }
    
    .data-table th {
        background-color: #f7fafc;
        font-weight: 600;
        color: #2d3748;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .data-table td {
        color: #4a5568;
        background-color: white;
    }
    
    .data-table tr:nth-child(even) td {
        background-color: #f8fafc;
    }
    
    /* Larguras específicas para as colunas */
    .data-table th:nth-child(1),
    .data-table td:nth-child(1) {
        width: 25%; /* O que */
    }
    
    .data-table th:nth-child(2),
    .data-table td:nth-child(2) {
        width: 20%; /* Quem */
    }
    
    .data-table th:nth-child(3),
    .data-table td:nth-child(3) {
        width: 15%; /* Quando */
    }
    
    .data-table th:nth-child(4),
    .data-table td:nth-child(4) {
        width: 15%; /* Como */
    }
    
    .data-table th:nth-child(5),
    .data-table td:nth-child(5) {
        width: 25%; /* Projeto Vinculado */
    }
    
    .report-footer {
        margin-top: 40px;
        padding: 20px;
        text-align: center;
        border-top: 1px solid #e2e8f0;
        background-color: #f8fafc;
    }
    
    .copyright {
        color: #718096;
        font-size: 12px;
        margin: 0;
        opacity: 0.8;
    }
    
    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 8px;
        margin-bottom: 12px;
    }
    
    .info-item {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 8px;
        padding: 6px 0;
    }
    
    .info-item label {
        font-weight: 600;
        color: #4a5568;
        font-size: 13px;
        min-width: 80px;
        flex-shrink: 0;
    }
    
    .info-item span {
        color: #2d3748;
        font-size: 13px;
        flex: 1;
    }
    
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .status-draft { background: #e2e8f0; color: #4a5568; }
    .status-scheduled { background: #bee3f8; color: #2c5282; }
    .status-in_progress { background: #fef5e7; color: #c05621; }
    .status-completed { background: #c6f6d5; color: #22543d; }
    .status-cancelled { background: #fed7d7; color: #c53030; }
    .status-pending { background: #e2e8f0; color: #4a5568; }
    
    .participants-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
    }
    
    .participant-card {
        background: #f7fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 6px;
    }
    
    .participant-info h4 {
        color: #2d3748;
        margin-bottom: 3px;
        font-size: 13px;
    }
    
    .participant-info .email {
        color: #667eea;
        font-size: 12px;
    }
    
    .participant-info .role {
        color: #718096;
        font-size: 12px;
        font-style: italic;
    }
    
    .agenda-list {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
    }
    
    @media (max-width: 768px) {
        .agenda-list {
            grid-template-columns: 1fr;
        }
    }
    
    .agenda-item {
        display: flex;
        gap: 10px;
        padding: 8px 12px;
        background: #f7fafc;
        border-left: 3px solid #667eea;
        border-radius: 6px;
    }
    
    .agenda-number {
        background: #667eea;
        color: white;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 12px;
        flex-shrink: 0;
    }
    
    .agenda-content h4 {
        color: #2d3748;
        margin-bottom: 3px;
        font-size: 13px;
    }
    
    .agenda-content p {
        color: #4a5568;
        margin-bottom: 3px;
        font-size: 12px;
    }
    
    .duration {
        color: #667eea;
        font-size: 12px;
        font-weight: 500;
    }
    
    .discussions-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    
    .discussion-item {
        padding: 10px 12px;
        background: #f7fafc;
        border-radius: 6px;
        border-left: 3px solid #48bb78;
    }
    
    .discussion-item h4 {
        color: #2d3748;
        margin-bottom: 6px;
        font-size: 13px;
    }
    
    .discussion-item .summary {
        color: #4a5568;
        margin-bottom: 6px;
        font-size: 12px;
    }
    
    .discussion-item .participants {
        color: #667eea;
        font-size: 12px;
        margin-bottom: 6px;
    }
    
    .decisions-list {
        background: #e6fffa;
        padding: 8px 12px;
        border-radius: 4px;
        border-left: 3px solid #38b2ac;
    }
    
    .decision-item {
        color: #234e52;
        margin-bottom: 3px;
        font-size: 12px;
    }
    
    .activities-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .activity-item {
        padding: 8px 12px;
        background: #f7fafc;
        border-radius: 6px;
        border-left: 3px solid #ed8936;
    }
    
    .activity-item h4 {
        color: #2d3748;
        margin-bottom: 6px;
        font-size: 13px;
    }
    
    .activity-item p {
        color: #4a5568;
        margin-bottom: 6px;
        font-size: 12px;
    }
    
    .activity-meta {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }
    
    .activity-meta span {
        font-size: 12px;
    }
    
    .responsible {
        color: #667eea;
    }
    
    .deadline {
        color: #ed8936;
    }
    
    .empty-state {
        text-align: center;
        padding: 40px;
        color: #718096;
        font-style: italic;
    }
    
    .report-footer {
        background: #f7fafc;
        padding: 20px 30px;
        border-top: 1px solid #e2e8f0;
    }
    
    .footer-content {
        text-align: center;
        color: #718096;
        font-size: 14px;
    }
    
    .footer-content p {
        margin-bottom: 5px;
    }
    
    @media print {
        body {
            background: white;
        }
        
        .report-container {
            box-shadow: none;
            max-width: none;
        }
        
        section {
            page-break-inside: avoid;
        }
    }
    """


# Função de conveniência para uso direto
def generate_meeting_report(meeting_id: int, save_path: str = None) -> str:
    """
    Gera relatório de reunião e opcionalmente salva em arquivo

    Args:
        meeting_id: ID da reunião
        save_path: Caminho para salvar o arquivo (opcional)

    Returns:
        str: HTML do relatório
    """
    html = generate_meeting_report_html(meeting_id)

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(html)

    return html


# Teste quando executado diretamente
if __name__ == "__main__":
    # Teste com uma reunião existente
    test_meeting_id = 1
    html = generate_meeting_report(
        test_meeting_id, f"relatorio_reuniao_{test_meeting_id}.html"
    )
    print(f"Relatório gerado com sucesso! ({len(html)} caracteres)")
