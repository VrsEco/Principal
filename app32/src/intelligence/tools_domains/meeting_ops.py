from __future__ import annotations

import os
import logging

from models import db
from src.intelligence.security.mcp_mutation_guard import (
    evaluate_mutation_limit,
    record_mutation_success,
)
from src.intelligence.security.runtime_identity import resolve_runtime_identity
from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy
from src.intelligence.tooling.capabilities import TOOL_CONTEXT_COMPANY, TOOL_CONTEXT_USER
from src.intelligence.tools_support import get_active_company_id, get_active_user_id

logger = logging.getLogger(__name__)


def _current_surface() -> str:
    return str(os.environ.get("APP32_MCP_SURFACE") or "user").strip().lower()


def _build_mcp_principal(company_id: int | None) -> dict[str, object]:
    user_id = get_active_user_id()
    runtime_identity = (
        resolve_runtime_identity(user_id=int(user_id), company_id=company_id)
        if user_id
        else {}
    )
    permissions = runtime_identity.get("permissions") or ()
    if isinstance(permissions, dict):
        permissions = tuple(str(key).strip().lower() for key in permissions.keys() if str(key).strip())
    elif isinstance(permissions, (list, tuple, set, frozenset)):
        permissions = tuple(str(item).strip().lower() for item in permissions if str(item).strip())
    elif permissions:
        permissions = (str(permissions).strip().lower(),)
    else:
        permissions = ()

    return {
        "user_id": user_id,
        "company_id": runtime_identity.get("company_id") or company_id,
        "employee_id": runtime_identity.get("employee_id"),
        "role": runtime_identity.get("role") or str(os.environ.get("APP32_MCP_FALLBACK_ROLE") or "colaborador").strip().lower(),
        "channel": str(os.environ.get("APP32_MCP_CHANNEL") or "claude_code").strip().lower(),
        "thread_id": os.environ.get("APP32_MCP_THREAD_ID"),
        "permissions": permissions,
        "accessible_company_ids": tuple(runtime_identity.get("accessible_company_ids") or ()),
    }


def _authorize_meeting_mcp(
    *,
    tool_name: str,
    action: str,
    company_id: int | None,
    risk: str,
    required_permissions: tuple[str, ...],
    confirmed_mutation: bool = False,
):
    principal = _build_mcp_principal(company_id)
    decision = evaluate_tool_policy(
        principal,
        ToolPolicyRequest(
            tool_name=tool_name,
            surface=_current_surface(),
            domain="meetings",
            action=action,
            risk=risk,
            requested_company_id=company_id,
            accessible_company_ids=tuple(principal.get("accessible_company_ids") or ()),
            required_permissions=required_permissions,
            confirmed_mutation=confirmed_mutation,
            required_context=(TOOL_CONTEXT_USER, TOOL_CONTEXT_COMPANY),
        ),
    )
    return principal, decision


def _resolve_requested_company_id(company_id: int | None) -> int | None:
    if company_id is None:
        active_company_id = get_active_company_id()
        return int(active_company_id) if active_company_id else None
    try:
        return int(company_id)
    except (TypeError, ValueError):
        return None


def _get_meeting_in_company_scope(meeting_id: int, company_id: int | None = None):
    from models.meeting import Meeting

    selected_company_id = _resolve_requested_company_id(company_id)
    if not selected_company_id:
        return None, "Erro: Nenhuma empresa ativa identificada."

    meeting = Meeting.query.filter_by(id=meeting_id, company_id=int(selected_company_id)).first()
    if not meeting:
        return None, f"Reunião ID {meeting_id} não encontrada na empresa selecionada."

    return meeting, None


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


def list_meetings(
    company_id: int | None = None,
    status: str | None = None,
    limit: int = 20,
):
    """
    Lista reuniões da empresa ativa ou da empresa explicitamente informada.
    Use para leitura segura do domínio de reuniões sem executar mutação.
    """
    from models.meeting import Meeting

    selected_company_id = int(company_id) if company_id is not None else get_active_company_id()
    if not selected_company_id:
        return "Erro: Nenhuma empresa ativa identificada."

    try:
        normalized_limit = max(1, min(int(limit or 20), 100))
    except (TypeError, ValueError):
        normalized_limit = 20

    query = Meeting.query.filter_by(company_id=int(selected_company_id))
    normalized_status = str(status or "").strip().lower()
    if normalized_status:
        query = query.filter_by(status=normalized_status)

    meetings = (
        query.order_by(
            Meeting.scheduled_date.desc().nullslast(),
            Meeting.scheduled_time.desc().nullslast(),
            Meeting.created_at.desc(),
        )
        .limit(normalized_limit)
        .all()
    )

    if not meetings:
        return "Nenhuma reunião encontrada."

    lines = []
    for meeting in meetings:
        scheduled_date = meeting.scheduled_date.isoformat() if getattr(meeting, "scheduled_date", None) else "-"
        scheduled_time = getattr(meeting, "scheduled_time", None) or "-"
        project_title = getattr(getattr(meeting, "project", None), "name", None) or "Sem projeto vinculado"
        lines.append(
            f"ID: {meeting.id} | Título: {meeting.title} | Status: {meeting.status or '-'} | "
            f"Data: {scheduled_date} | Hora: {scheduled_time} | Projeto: {project_title}"
        )

    return "\n".join(lines)


def schedule_meeting(
    title: str,
    date: str,
    time: str,
    guests: str,
    agenda_items: str = None,
    notes: str = None,
    company_id: int | None = None,
):
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
    from services.email_service import email_service
    import json

    requested_company_id = _resolve_requested_company_id(company_id)
    principal, decision = _authorize_meeting_mcp(
        tool_name="schedule_meeting",
        action="create",
        company_id=requested_company_id,
        risk="medium",
        required_permissions=("meeting.schedule",),
    )
    if not decision.allowed:
        return f"Erro: {decision.reason}"

    limit_decision = evaluate_mutation_limit(
        action="create",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return f"Erro: {limit_decision.reason}"

    try:
        # Monta estrutura de convidados
        guest_list = [g.strip() for g in guests.split(',') if g.strip()]
        guest_dict = {g: g for g in guest_list}  # {email/nome: email/nome}

        # Monta pauta
        agenda = []
        if agenda_items:
            agenda = [{"title": item.strip()} for item in agenda_items.split(';') if item.strip()]

        meeting = Meeting(
            company_id=int(decision.resolved_company_id),
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

        persisted = Meeting.query.filter_by(
            id=meeting.id,
            company_id=int(decision.resolved_company_id),
        ).first()
        if not persisted:
            return "Erro: falha na validação pós-escrita da reunião na empresa selecionada."

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

        if principal.get("user_id"):
            record_mutation_success(
                action="create",
                company_id=int(decision.resolved_company_id),
                user_id=int(principal["user_id"]),
                tool_name="schedule_meeting",
                domain="meetings",
                metadata={"meeting_id": int(meeting.id)},
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

def start_meeting(meeting_id: int, company_id: int | None = None):
    """
    Inicia uma reunião agendada. Marca o horário real de início e vincula/cria um projeto automático.
    :param meeting_id: ID da reunião a ser iniciada (obtido ao criar a reunião).
    """
    from models.project import Project
    from datetime import datetime

    requested_company_id = _resolve_requested_company_id(company_id)
    principal, decision = _authorize_meeting_mcp(
        tool_name="start_meeting",
        action="update",
        company_id=requested_company_id,
        risk="medium",
        required_permissions=("meeting.start",),
    )
    if not decision.allowed:
        return f"Erro: {decision.reason}"

    limit_decision = evaluate_mutation_limit(
        action="update",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return f"Erro: {limit_decision.reason}"

    try:
        meeting, error_message = _get_meeting_in_company_scope(
            meeting_id,
            company_id=decision.resolved_company_id,
        )
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
        if principal.get("user_id"):
            record_mutation_success(
                action="update",
                company_id=int(decision.resolved_company_id),
                user_id=int(principal["user_id"]),
                tool_name="start_meeting",
                domain="meetings",
                metadata={"meeting_id": int(meeting_id)},
            )
        return (
            f"🟢 Reunião '{meeting.title}' INICIADA!\n"
            f"   Horário de início: {now.strftime('%d/%m/%Y às %H:%M')}\n"
            f"   Projeto vinculado: ID {meeting.project_id}\n"
            f"   Agora registre os pontos discutidos: 'Sapiens, registre o ponto: [tópico] — decisão: [decisão] — responsável: [nome] — prazo: [data]'"
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao iniciar reunião: {str(e)}"

def log_meeting_discussion(
    meeting_id: int,
    topic: str,
    decision: str = None,
    responsible: str = None,
    deadline: str = None,
    company_id: int | None = None,
):
    """
    Registra um ponto discutido, decisão tomada ou atividade criada durante a reunião.
    Use repetidamente para cada ponto discutido durante a reunião.
    :param meeting_id: ID da reunião em andamento.
    :param topic: Assunto/Tópico discutido. Ex: 'Revisão das metas de vendas'
    :param decision: Decisão tomada. Ex: 'Aumentar meta em 15% para Q2'
    :param responsible: Nome do responsável pela ação. Ex: 'Carlos'
    :param deadline: Prazo para conclusão no formato YYYY-MM-DD. Ex: '2026-03-31'
    """
    import json

    requested_company_id = _resolve_requested_company_id(company_id)
    principal, policy_decision = _authorize_meeting_mcp(
        tool_name="log_meeting_discussion",
        action="update",
        company_id=requested_company_id,
        risk="low",
        required_permissions=("meeting.notes.write",),
    )
    if not policy_decision.allowed:
        return f"Erro: {policy_decision.reason}"

    limit_decision = evaluate_mutation_limit(
        action="update",
        company_id=policy_decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return f"Erro: {limit_decision.reason}"

    try:
        meeting, error_message = _get_meeting_in_company_scope(
            meeting_id,
            company_id=policy_decision.resolved_company_id,
        )
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
        if principal.get("user_id"):
            record_mutation_success(
                action="update",
                company_id=int(policy_decision.resolved_company_id),
                user_id=int(principal["user_id"]),
                tool_name="log_meeting_discussion",
                domain="meetings",
                metadata={"meeting_id": int(meeting_id)},
            )

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

def finish_meeting(meeting_id: int, company_id: int | None = None):
    """
    Encerra uma reunião em andamento e gera a Ata de Reunião (ATA) completa.
    Após encerrar, use 'send_meeting_minutes' para enviar a ATA aos participantes.
    :param meeting_id: ID da reunião a ser encerrada.
    """
    import json
    from datetime import datetime

    requested_company_id = _resolve_requested_company_id(company_id)
    principal, decision = _authorize_meeting_mcp(
        tool_name="finish_meeting",
        action="update",
        company_id=requested_company_id,
        risk="medium",
        required_permissions=("meeting.finish",),
    )
    if not decision.allowed:
        return f"Erro: {decision.reason}"

    limit_decision = evaluate_mutation_limit(
        action="update",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return f"Erro: {limit_decision.reason}"

    try:
        meeting, error_message = _get_meeting_in_company_scope(
            meeting_id,
            company_id=decision.resolved_company_id,
        )
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
        if principal.get("user_id"):
            record_mutation_success(
                action="update",
                company_id=int(decision.resolved_company_id),
                user_id=int(principal["user_id"]),
                tool_name="finish_meeting",
                domain="meetings",
                metadata={"meeting_id": int(meeting_id)},
            )

        return (
            f"🏁 Reunião '{meeting.title}' ENCERRADA!\n\n"
            f"{ata_text}\n\n"
            f"Para enviar a ATA por e-mail/WhatsApp, diga:\n"
            f"'Sapiens, envie a ATA da reunião {meeting_id}'"
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao encerrar reunião: {str(e)}"

def send_meeting_minutes(meeting_id: int, channel: str = "email", company_id: int | None = None):
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

    requested_company_id = _resolve_requested_company_id(company_id)
    principal, decision = _authorize_meeting_mcp(
        tool_name="send_meeting_minutes",
        action="update",
        company_id=requested_company_id,
        risk="medium",
        required_permissions=("meeting.minutes.send",),
    )
    if not decision.allowed:
        return f"Erro: {decision.reason}"

    limit_decision = evaluate_mutation_limit(
        action="update",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return f"Erro: {limit_decision.reason}"

    try:
        meeting, error_message = _get_meeting_in_company_scope(
            meeting_id,
            company_id=decision.resolved_company_id,
        )
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

        if principal.get("user_id"):
            record_mutation_success(
                action="update",
                company_id=int(decision.resolved_company_id),
                user_id=int(principal["user_id"]),
                tool_name="send_meeting_minutes",
                domain="meetings",
                metadata={"meeting_id": int(meeting_id), "channel": channel},
            )

        return (
            f"📤 ATA da reunião '{meeting.title}' enviada!\n"
            f"   E-mails enviados: {sent_email}\n"
            f"   WhatsApps enviados: {sent_wa}"
        )
    except Exception as e:
        return f"Erro ao enviar ATA: {str(e)}"


def _meeting_service_mutation(
    *,
    tool_name: str,
    company_id: int | None,
    service_method,
    metadata: dict | None = None,
    **service_kwargs,
):
    requested_company_id = _resolve_requested_company_id(company_id)
    principal, decision = _authorize_meeting_mcp(
        tool_name=tool_name,
        action="create" if tool_name in {"create_meeting", "create_meeting_topic", "create_meeting_decision", "create_meeting_activity"} else "update",
        company_id=requested_company_id,
        risk="medium",
        required_permissions=("meeting.write",),
    )
    if not decision.allowed:
        return {"success": False, "error": decision.reason, "policy": decision.to_audit_event()}

    limit_decision = evaluate_mutation_limit(
        action="create" if tool_name.startswith("create_") else "update",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return {"success": False, "error": limit_decision.reason, "limits": limit_decision.to_dict()}

    try:
        payload, error = service_method(
            company_id=int(decision.resolved_company_id),
            **service_kwargs,
        )
        if error:
            return {"success": False, "error": error}
        if principal.get("user_id"):
            record_mutation_success(
                action="create" if tool_name.startswith("create_") else "update",
                company_id=int(decision.resolved_company_id),
                user_id=int(principal["user_id"]),
                tool_name=tool_name,
                domain="meetings",
                metadata=dict(metadata or {}),
            )
        return {"success": True, **(payload or {})}
    except Exception as exc:
        db.session.rollback()
        logger.exception("Falha na tool %s", tool_name)
        return {"success": False, "error": f"Erro ao operar reunião: {exc}"}


def create_meeting(
    title: str,
    company_id: int | None = None,
    project_id: int | None = None,
    participants: list | dict | None = None,
    meeting_notes: str | None = None,
):
    """Cria uma reunião de trabalho sem exigir agendamento."""
    from services.meeting_mcp_service import MeetingMCPService

    return _meeting_service_mutation(
        tool_name="create_meeting",
        company_id=company_id,
        service_method=MeetingMCPService.create_meeting,
        metadata={"project_id": project_id},
        title=title,
        project_id=project_id,
        participants=participants,
        meeting_notes=meeting_notes,
    )


def get_meeting(meeting_id: int, company_id: int | None = None):
    """Lê a reunião completa, incluindo temas, decisões e atividades."""
    from services.meeting_mcp_service import MeetingMCPService

    requested_company_id = _resolve_requested_company_id(company_id)
    _, decision = _authorize_meeting_mcp(
        tool_name="get_meeting",
        action="read",
        company_id=requested_company_id,
        risk="low",
        required_permissions=("meeting.read",),
    )
    if not decision.allowed:
        return {"success": False, "error": decision.reason, "policy": decision.to_audit_event()}
    meeting, error = MeetingMCPService.get_meeting(
        company_id=int(decision.resolved_company_id), meeting_id=int(meeting_id)
    )
    if error or meeting is None:
        return {"success": False, "error": error}
    return {"success": True, "meeting": meeting.to_dict()}


def update_meeting(meeting_id: int, changes: dict, company_id: int | None = None):
    """Atualiza campos whitelisted da reunião sem depender de agendamento."""
    from services.meeting_mcp_service import MeetingMCPService

    return _meeting_service_mutation(
        tool_name="update_meeting", company_id=company_id,
        service_method=MeetingMCPService.update_meeting,
        metadata={"meeting_id": int(meeting_id)}, meeting_id=int(meeting_id), changes=changes,
    )


def create_meeting_topic(
    meeting_id: int, title: str, notes: str | None = None,
    discussion: str | None = None, company_id: int | None = None,
):
    from services.meeting_mcp_service import MeetingMCPService
    return _meeting_service_mutation(
        tool_name="create_meeting_topic", company_id=company_id,
        service_method=MeetingMCPService.create_topic,
        metadata={"meeting_id": int(meeting_id)}, meeting_id=int(meeting_id),
        title=title, notes=notes, discussion=discussion,
    )


def update_meeting_topic(meeting_id: int, topic_id: str, changes: dict, company_id: int | None = None):
    from services.meeting_mcp_service import MeetingMCPService
    return _meeting_service_mutation(
        tool_name="update_meeting_topic", company_id=company_id,
        service_method=MeetingMCPService.update_topic,
        metadata={"meeting_id": int(meeting_id), "topic_id": topic_id},
        meeting_id=int(meeting_id), topic_id=topic_id, changes=changes,
    )


def delete_meeting_topic(meeting_id: int, topic_id: str, company_id: int | None = None):
    from services.meeting_mcp_service import MeetingMCPService
    return _meeting_service_mutation(
        tool_name="delete_meeting_topic", company_id=company_id,
        service_method=MeetingMCPService.delete_topic,
        metadata={"meeting_id": int(meeting_id), "topic_id": topic_id},
        meeting_id=int(meeting_id), topic_id=topic_id,
    )


def create_meeting_decision(meeting_id: int, topic_id: str, text: str, rationale: str | None = None, owner: str | None = None, company_id: int | None = None):
    from services.meeting_mcp_service import MeetingMCPService
    return _meeting_service_mutation(
        tool_name="create_meeting_decision", company_id=company_id,
        service_method=MeetingMCPService.create_decision,
        metadata={"meeting_id": int(meeting_id), "topic_id": topic_id},
        meeting_id=int(meeting_id), topic_id=topic_id, text=text, rationale=rationale, owner=owner,
    )


def update_meeting_decision(meeting_id: int, topic_id: str, decision_id: str, changes: dict, company_id: int | None = None):
    from services.meeting_mcp_service import MeetingMCPService
    return _meeting_service_mutation(
        tool_name="update_meeting_decision", company_id=company_id,
        service_method=MeetingMCPService.update_decision,
        metadata={"meeting_id": int(meeting_id), "topic_id": topic_id, "decision_id": decision_id},
        meeting_id=int(meeting_id), topic_id=topic_id, decision_id=decision_id, changes=changes,
    )


def delete_meeting_decision(meeting_id: int, topic_id: str, decision_id: str, company_id: int | None = None):
    from services.meeting_mcp_service import MeetingMCPService
    return _meeting_service_mutation(
        tool_name="delete_meeting_decision", company_id=company_id,
        service_method=MeetingMCPService.delete_decision,
        metadata={"meeting_id": int(meeting_id), "topic_id": topic_id, "decision_id": decision_id},
        meeting_id=int(meeting_id), topic_id=topic_id, decision_id=decision_id,
    )


def create_meeting_activity(
    meeting_id: int, title: str, company_id: int | None = None, responsible: str | None = None,
    deadline: str | None = None, budget: str | None = None, estimated_hours: float | None = None,
    priority: str = "normal", how: str | None = None, employee_id: int | None = None,
    project_id: int | None = None,
):
    from services.meeting_mcp_service import MeetingMCPService
    return _meeting_service_mutation(
        tool_name="create_meeting_activity", company_id=company_id,
        service_method=MeetingMCPService.create_activity,
        metadata={"meeting_id": int(meeting_id), "project_id": project_id},
        meeting_id=int(meeting_id), title=title, responsible=responsible, deadline=deadline,
        budget=budget, estimated_hours=estimated_hours, priority=priority, how=how,
        employee_id=employee_id, project_id=project_id,
    )


def update_meeting_activity(meeting_id: int, activity_id: str, changes: dict, company_id: int | None = None):
    from services.meeting_mcp_service import MeetingMCPService
    return _meeting_service_mutation(
        tool_name="update_meeting_activity", company_id=company_id,
        service_method=MeetingMCPService.update_activity,
        metadata={"meeting_id": int(meeting_id), "activity_id": activity_id},
        meeting_id=int(meeting_id), activity_id=activity_id, changes=changes,
    )


def delete_meeting_activity(meeting_id: int, activity_id: str, company_id: int | None = None):
    from services.meeting_mcp_service import MeetingMCPService
    return _meeting_service_mutation(
        tool_name="delete_meeting_activity", company_id=company_id,
        service_method=MeetingMCPService.delete_activity,
        metadata={"meeting_id": int(meeting_id), "activity_id": activity_id},
        meeting_id=int(meeting_id), activity_id=activity_id,
    )


def sync_meeting_activities_to_project(meeting_id: int, activity_ids: list[str] | None = None, company_id: int | None = None):
    """Cria ou atualiza ProjectTask a partir das atividades da reunião."""
    from services.meeting_mcp_service import MeetingMCPService
    return _meeting_service_mutation(
        tool_name="sync_meeting_activities_to_project", company_id=company_id,
        service_method=MeetingMCPService.sync_activities,
        metadata={"meeting_id": int(meeting_id), "activity_ids": activity_ids or []},
        meeting_id=int(meeting_id), activity_ids=activity_ids,
    )


def delete_meeting_secure(
    meeting_id: int,
    reason: str,
    confirm: bool = False,
    company_id: int | None = None,
):
    """
    Exclui uma reunião de forma administrativa, tenant-safe e auditável.
    Use apenas em surface admin e com confirmação explícita.
    """
    from models import WorkJourneyItem

    requested_company_id = _resolve_requested_company_id(company_id)
    principal, decision = _authorize_meeting_mcp(
        tool_name="delete_meeting_secure",
        action="delete",
        company_id=requested_company_id,
        risk="high",
        required_permissions=("meeting.delete",),
        confirmed_mutation=bool(confirm),
    )
    if not decision.allowed:
        return {"success": False, "error": decision.reason, "policy": decision.to_audit_event()}

    limit_decision = evaluate_mutation_limit(
        action="delete",
        company_id=decision.resolved_company_id,
        user_id=principal.get("user_id"),
    )
    if not limit_decision.allowed:
        return {"success": False, "error": limit_decision.reason, "limits": limit_decision.to_dict()}

    meeting, error_message = _get_meeting_in_company_scope(
        meeting_id,
        company_id=decision.resolved_company_id,
    )
    if error_message:
        return {"success": False, "error": error_message}

    linked_project_id = getattr(meeting, "project_id", None)
    meeting_title = getattr(meeting, "title", None)
    work_journey_items = (
        WorkJourneyItem.query.filter_by(
            company_id=int(decision.resolved_company_id),
            item_type="meeting",
            source_id=int(meeting_id),
        ).all()
    )

    try:
        removed_work_journey_items = len(work_journey_items)
        for item in work_journey_items:
            db.session.delete(item)

        db.session.delete(meeting)
        db.session.commit()

        if principal.get("user_id"):
            record_mutation_success(
                action="delete",
                company_id=int(decision.resolved_company_id),
                user_id=int(principal["user_id"]),
                tool_name="delete_meeting_secure",
                domain="meetings",
                metadata={
                    "meeting_id": int(meeting_id),
                    "meeting_title": meeting_title,
                    "reason": str(reason or "").strip(),
                    "linked_project_id": int(linked_project_id) if linked_project_id else None,
                    "removed_work_journey_items": removed_work_journey_items,
                },
            )

        return {
            "success": True,
            "meeting_id": int(meeting_id),
            "company_id": int(decision.resolved_company_id),
            "title": meeting_title,
            "linked_project_id": int(linked_project_id) if linked_project_id else None,
            "removed_work_journey_items": removed_work_journey_items,
            "reason": str(reason or "").strip(),
            "message": "Reunião excluída com sucesso.",
        }
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "error": f"Erro ao excluir reunião: {exc}"}

