from __future__ import annotations

import logging

from models import db
from src.intelligence.tools_support import get_active_company_id, get_meeting_in_active_company

logger = logging.getLogger(__name__)


def _get_meeting_project(meeting):
    if not getattr(meeting, "project_id", None):
        return None, None

    from models.project import Project

    project = Project.query.filter_by(
        id=meeting.project_id,
        company_id=meeting.company_id,
    ).first()
    if not project:
        return None, "Erro: projeto vinculado à reunião não pertence à empresa ativa."
    return project, None


def schedule_meeting(title: str, date: str, time: str, guests: str, agenda_items: str = None, notes: str = None):
    """
    Cria e agenda uma nova reunião no sistema enviando convite para os participantes.
    :param title: Título/Assunto da reunião. Ex: 'Revisão de Metas Q1'
    :param date: Data da reunião no formato YYYY-MM-DD. Ex: '2026-03-01'
    :param time: Horário no formato HH:MM. Ex: '14:30'
    :param guests: Lista de e-mails ou nomes dos convidados, separados por vírgula. Ex: 'ana@empresa.com, pedro@empresa.com'
    :param agenda_items: Pautas separadas por ponto-e-vírgula. Ex: 'Revisão de metas; Status dos projetos; Próximos passos'
    :param notes: Observações ou pauta livre para o convite.
    """
    from models.meeting import Meeting
    from models.user import User
    from services.email_service import email_service
    from services.whatsapp_service import whatsapp_service
    import json

    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Nenhuma empresa ativa identificada."

    try:
        # Monta estrutura de convidados
        guest_list = [g.strip() for g in guests.split(',') if g.strip()]
        guest_dict = {g: g for g in guest_list}  # {email/nome: email/nome}

        # Monta pauta
        agenda = []
        if agenda_items:
            agenda = [{"title": item.strip()} for item in agenda_items.split(';') if item.strip()]

        meeting = Meeting(
            company_id=int(company_id),
            title=title,
            scheduled_date=date,
            scheduled_time=time,
            invite_notes=notes or "",
            guests_json=json.dumps(guest_dict),
            agenda_json=json.dumps(agenda),
            status='draft'
        )
        db.session.add(meeting)
        db.session.commit()

        # Envia convite por e-mail para quem for e-mail válido
        email_guests = [g for g in guest_list if '@' in g]
        if email_guests:
            pauta_texto = "\n".join([f"  • {a['title']}" for a in agenda]) if agenda else "A definir na reunião."
            email_body = (
                f"Prezado(a),\n\n"
                f"Você foi convidado(a) para a reunião:\n\n"
                f"📅 {title}\n"
                f"🗓️  Data: {date} às {time}\n"
                f"📋 Pautas:\n{pauta_texto}\n\n"
                f"{notes or ''}\n\n"
                f"Atenciosamente,\nGestão Versus"
            )
            email_service.send_email(
                to_emails=email_guests,
                subject=f"Convite de Reunião: {title}",
                body=email_body
            )

        return (
            f"✅ Reunião '{title}' criada com sucesso!\n"
            f"   ID: {meeting.id} | Data: {date} às {time}\n"
            f"   Convidados: {', '.join(guest_list)}\n"
            f"   Convite enviado por e-mail para: {', '.join(email_guests) if email_guests else 'Nenhum e-mail válido informado.'}\n"
            f"   Para iniciar a reunião quando chegar a hora, diga: 'Sapiens, inicie a reunião {meeting.id}'."
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao agendar reunião: {str(e)}"

def start_meeting(meeting_id: int):
    """
    Inicia uma reunião agendada. Marca o horário real de início e vincula/cria um projeto automático.
    :param meeting_id: ID da reunião a ser iniciada (obtido ao criar a reunião).
    """
    from models.project import Project
    from datetime import datetime

    try:
        meeting, error_message = get_meeting_in_active_company(meeting_id)
        if error_message:
            return error_message

        now = datetime.now()
        meeting.actual_date = now.date()
        meeting.actual_time = now.strftime("%H:%M")
        meeting.status = 'in_progress'

        # Cria projeto vinculado se não existir
        if not meeting.project_id:
            proj = Project(
                company_id=meeting.company_id,
                name=f"Reunião - {meeting.title} ({now.strftime('%d/%m/%Y')})",
                status="in_progress",
                priority="medium",
                owner="Sapiens",
                deadline=now.date(),
                notes=f"Projeto gerado automaticamente para a reunião ID {meeting.id}: {meeting.title}"
            )
            db.session.add(proj)
            db.session.flush()
            meeting.project_id = proj.id

        db.session.commit()
        return (
            f"🟢 Reunião '{meeting.title}' INICIADA!\n"
            f"   Horário de início: {now.strftime('%d/%m/%Y às %H:%M')}\n"
            f"   Projeto vinculado: ID {meeting.project_id}\n"
            f"   Agora registre os pontos discutidos: 'Sapiens, registre o ponto: [tópico] — decisão: [decisão] — responsável: [nome] — prazo: [data]'"
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao iniciar reunião: {str(e)}"

def log_meeting_discussion(meeting_id: int, topic: str, decision: str = None, responsible: str = None, deadline: str = None):
    """
    Registra um ponto discutido, decisão tomada ou atividade criada durante a reunião.
    Use repetidamente para cada ponto discutido durante a reunião.
    :param meeting_id: ID da reunião em andamento.
    :param topic: Assunto/Tópico discutido. Ex: 'Revisão das metas de vendas'
    :param decision: Decisão tomada. Ex: 'Aumentar meta em 15% para Q2'
    :param responsible: Nome do responsável pela ação. Ex: 'Carlos'
    :param deadline: Prazo para conclusão no formato YYYY-MM-DD. Ex: '2026-03-31'
    """
    from models.project import ProjectTask
    import json

    try:
        meeting, error_message = get_meeting_in_active_company(meeting_id)
        if error_message:
            return error_message

        # Adiciona à lista de discussões
        discussions = json.loads(meeting.discussions_json or "[]")
        entry = {
            "title": topic,
            "decision": decision or "",
            "responsible": responsible or "",
            "deadline": deadline or "",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        discussions.append(entry)
        meeting.discussions_json = json.dumps(discussions)

        # Se houver responsável e prazo, cria atividade na lista de atividades da reunião
        if responsible and deadline:
            activities = json.loads(meeting.activities_json or "[]")
            activities.append({
                "title": decision or topic,
                "responsible": responsible,
                "deadline": deadline,
                "how": f"Originado da discussão: {topic}"
            })
            meeting.activities_json = json.dumps(activities)

            # Se já existe projeto vinculado, cria a task diretamente, com defesa cross-tenant.
            if meeting.project_id:
                project, project_error = _get_meeting_project(meeting)
                if project_error:
                    return project_error
                from models.project import ProjectTask
                from datetime import datetime as dt
                try:
                    due = dt.strptime(deadline, '%Y-%m-%d').date()
                except:
                    due = None
                task = ProjectTask(
                    project_id=meeting.project_id,
                    what=decision or topic,
                    how=f"Decisão de reunião: {topic}",
                    who=responsible,
                    due_date=due,
                    status='not_started',
                    priority='medium'
                )
                db.session.add(task)

        db.session.commit()

        resp = f"📝 Ponto registrado na reunião '{meeting.title}':\n   Tópico: {topic}"
        if decision:
            resp += f"\n   Decisão: {decision}"
        if responsible:
            resp += f"\n   Responsável: {responsible}"
        if deadline:
            resp += f"\n   Prazo: {deadline}"
        if responsible and deadline and meeting.project_id:
            resp += f"\n   ✅ Atividade criada automaticamente no projeto ID {meeting.project_id}."
        return resp
    except Exception as e:
        db.session.rollback()
        return f"Erro ao registrar ponto da reunião: {str(e)}"

def finish_meeting(meeting_id: int):
    """
    Encerra uma reunião em andamento e gera a Ata de Reunião (ATA) completa.
    Após encerrar, use 'send_meeting_minutes' para enviar a ATA aos participantes.
    :param meeting_id: ID da reunião a ser encerrada.
    """
    import json
    from datetime import datetime

    try:
        meeting, error_message = get_meeting_in_active_company(meeting_id)
        if error_message:
            return error_message

        meeting.status = 'completed'
        db.session.commit()

        # Monta a ATA
        discussions = json.loads(meeting.discussions_json or "[]")
        activities = json.loads(meeting.activities_json or "[]")
        guests = json.loads(meeting.guests_json or "{}")

        ata_lines = [
            f"ATA DE REUNIÃO",
            f"={'='*50}",
            f"Título: {meeting.title}",
            f"Data: {meeting.actual_date or meeting.scheduled_date}",
            f"Horário: {meeting.actual_time or meeting.scheduled_time}",
            f"Participantes: {', '.join(guests.keys()) if guests else 'Não registrado'}",
            f"",
            f"PONTOS DISCUTIDOS:",
        ]
        for i, d in enumerate(discussions, 1):
            ata_lines.append(f"  {i}. {d.get('title', '')}")
            if d.get('decision'):
                ata_lines.append(f"     Decisão: {d['decision']}")
            if d.get('responsible'):
                ata_lines.append(f"     Responsável: {d['responsible']} | Prazo: {d.get('deadline', 'N/A')}")

        if activities:
            ata_lines += ["", "ATIVIDADES CRIADAS:"]
            for a in activities:
                ata_lines.append(f"  • [{a.get('responsible','?')}] {a.get('title','?')} — Prazo: {a.get('deadline','N/A')}")

        ata_text = "\n".join(ata_lines)
        meeting.meeting_notes = ata_text

        # ✅ ALINHAMENTO COM API OFICIAL (MeetingFinishResource):
        # Cria tarefa-resumo no projeto vinculado — idêntico ao comportamento da interface.
        if meeting.project_id:
            try:
                from models.project import ProjectTask
                task_desc = f"Atas da reunião (ID: {meeting.id})\n\n"
                if discussions:
                    task_desc += "Principais Deliberações:\n"
                    for d in discussions:
                        task_desc += f"- {d.get('title', 'Tópico')}: {d.get('decision', '')}\n"

                summary_task = ProjectTask(
                    project_id=meeting.project_id,
                    what=f"Resumo da Reunião: {meeting.title}",
                    how=task_desc,
                    status="completed",
                    due_date=datetime.utcnow().date(),
                    priority="low"
                )
                db.session.add(summary_task)
            except Exception:
                pass  # Não bloqueia o encerramento se houver erro na task-resumo

        db.session.commit()

        return (
            f"🏁 Reunião '{meeting.title}' ENCERRADA!\n\n"
            f"{ata_text}\n\n"
            f"Para enviar a ATA por e-mail/WhatsApp, diga:\n"
            f"'Sapiens, envie a ATA da reunião {meeting_id}'"
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao encerrar reunião: {str(e)}"

def send_meeting_minutes(meeting_id: int, channel: str = "email"):
    """
    Envia a ATA (Ata de Reunião) para todos os participantes após o encerramento.
    :param meeting_id: ID da reunião já encerrada.
    :param channel: Canal de envio: 'email', 'whatsapp' ou 'ambos'. Padrão: 'email'
    """
    channel = (channel or "email").strip().lower()
    if channel not in {"email", "whatsapp", "ambos"}:
        return "Erro: canal inválido. Use 'email', 'whatsapp' ou 'ambos'."

    from services.email_service import email_service
    from services.whatsapp_service import whatsapp_service
    import json

    try:
        meeting, error_message = get_meeting_in_active_company(meeting_id)
        if error_message:
            return error_message

        guests = json.loads(meeting.guests_json or "{}")
        ata = meeting.meeting_notes or "ATA não gerada. Encerre a reunião primeiro."

        email_guests = [g for g in guests.keys() if '@' in g]
        wa_guests = [v for v in guests.values() if v and '@' not in v]

        sent_email = sent_wa = 0

        if channel in ('email', 'ambos') and email_guests:
            ok = email_service.send_email(
                to_emails=email_guests,
                subject=f"ATA da Reunião: {meeting.title}",
                body=ata
            )
            if ok:
                sent_email = len(email_guests)

        if channel in ('whatsapp', 'ambos') and wa_guests:
            for phone in wa_guests:
                ok = whatsapp_service.send_message(phone, f"📋 *ATA DA REUNIÃO: {meeting.title}*\n\n{ata}")
                if ok:
                    sent_wa += 1

        return (
            f"📤 ATA da reunião '{meeting.title}' enviada!\n"
            f"   E-mails enviados: {sent_email}\n"
            f"   WhatsApps enviados: {sent_wa}"
        )
    except Exception as e:
        return f"Erro ao enviar ATA: {str(e)}"

