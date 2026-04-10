from __future__ import annotations

import logging
import os
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func

from models import db
from src.intelligence.tools_support import (
    get_active_company_id,
    get_active_user,
    get_active_user_id,
    get_process_instance_in_active_company,
    get_project_task_in_active_company,
    sanitize_output,
)

logger = logging.getLogger(__name__)


def get_tasks_today(scope: str = "me"):
    """
    Lista as atividades (tarefas e instâncias de processo) do usuário que vencem hoje ou estão atrasadas.
    Ideal para o briefing matinal e cobranças proativas.
    :param scope: 'me' para o usuário logado, 'team' para a equipe, 'company' para toda a empresa.
    """
    
    from datetime import date
    from models.employee import Employee
    from models.process import Process, ProcessInstance, ProcessRoutine
    from models.project import Project, ProjectTask
    from sqlalchemy import func

    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Nenhuma empresa ativa identificada."

    today = date.today()
    today_str = today.isoformat()

    try:
        tasks = [
            dict(row._mapping)
            for row in (
                db.session.query(
                    ProjectTask.id,
                    ProjectTask.what.label("title"),
                    ProjectTask.due_date,
                    ProjectTask.status,
                    ProjectTask.who.label("responsible"),
                    Project.name.label("project_name"),
                )
                .join(Project, Project.id == ProjectTask.project_id)
                .filter(Project.company_id == company_id)
                .filter(ProjectTask.status.notin_(["completed", "cancelled"]))
                .filter(ProjectTask.due_date <= today)
                .order_by(ProjectTask.due_date.asc())
                .all()
            )
        ]

        responsible_employee_id = func.coalesce(
            ProcessInstance.responsible_id,
            ProcessInstance.executor_id,
            ProcessInstance.owner_employee_id,
        )
        process_title = func.coalesce(
            ProcessRoutine.name,
            Process.name,
            ProcessInstance.title,
        )

        procs = [
            dict(row._mapping)
            for row in (
                db.session.query(
                    ProcessInstance.id,
                    process_title.label("title"),
                    ProcessInstance.due_date,
                    ProcessInstance.status,
                    Employee.name.label("responsible"),
                )
                .outerjoin(ProcessRoutine, ProcessRoutine.id == ProcessInstance.routine_id)
                .outerjoin(Process, Process.id == ProcessInstance.process_id)
                .outerjoin(Employee, Employee.id == responsible_employee_id)
                .filter(ProcessInstance.company_id == company_id)
                .filter(ProcessInstance.status.notin_(["completed", "cancelled"]))
                .filter(ProcessInstance.due_date <= today)
                .order_by(ProcessInstance.due_date.asc())
                .all()
            )
        ]

        if not tasks and not procs:
            return f"🟢 Nenhuma tarefa vencendo hoje ({today_str}) ou atrasada. Ótimo!"

        result_lines = [f"📋 TAREFAS VENCENDO HOJE ({today_str}) E ATRASADAS:"]

        if tasks:
            result_lines.append("\n🗂️ Atividades de Projetos:")
            for t in tasks:
                emoji = "🔴" if str(t['due_date']) < today_str else "🟡"
                result_lines.append(
                    f"  {emoji} [{t['project_name']}] {t['title']} "
                    f"— Resp: {t['responsible'] or '?'} | Prazo: {t['due_date']}"
                )

        if procs:
            result_lines.append("\n⚙️ Instâncias de Processos:")
            for p in procs:
                emoji = "🔴" if str(p['due_date']) < today_str else "🟡"
                result_lines.append(
                    f"  {emoji} {p['title']} "
                    f"— Resp: {p['responsible'] or '?'} | Prazo: {p['due_date']}"
                )

        return sanitize_output("\n".join(result_lines))
    except Exception as e:
        return f"Erro ao buscar tarefas do dia: {str(e)}"

def create_project_task(project_code: str, task_name: str, responsible_name: str = None, due_date: str = None, description: str = None, priority: str = "normal", notes: str = None):
    """
    Cria uma nova atividade em um projeto existente, respeitando o contexto multiempresa.
    :param project_code: Código do projeto no formato EMPRESA.J.ID. Ex: 'AB.J.17'
    :param task_name: Nome da atividade. Ex: 'Validar fluxo de WhatsApp'
    :param responsible_name: Opcional nome do responsável. Se omitido, usa o usuário atual.
    :param due_date: Opcional prazo no formato YYYY-MM-DD ou DD/MM/YYYY.
    :param description: Opcional descrição/como executar.
    :param priority: Prioridade da atividade. Ex: 'normal', 'high'
    :param notes: Observações adicionais.
    """
    from models.employee import Employee
    from models.user import User
    from services.project_task_service import ProjectTaskService

    user_id = get_active_user_id()
    if not user_id:
        return "Erro: Usuario nao autenticado."

    active_company_id = get_active_company_id()
    allowed_company_ids = [active_company_id] if active_company_id else []

    if not allowed_company_ids:
        user = User.query.get(user_id)
        if user and str(getattr(user, "role", "")).lower() == "admin":
            allowed_company_ids = None
        else:
            allowed_company_ids = [
                int(emp.company_id)
                for emp in Employee.query.filter(Employee.user_id == user_id).all()
                if getattr(emp, "company_id", None)
            ]
            if not allowed_company_ids:
                return "Erro: Nenhuma empresa vinculada ao usuario para criar a atividade."

    result, error = ProjectTaskService.create_project_task(
        project_code=project_code,
        task_name=task_name,
        user_id=user_id,
        allowed_company_ids=allowed_company_ids,
        responsible_name=responsible_name,
        due_date=due_date,
        description=description,
        priority=priority,
        notes=notes,
    )
    if error:
        return sanitize_output(error)
    if not result:
        return "Erro: Nao foi possivel criar a atividade de projeto."

    task = result["task"]
    project = result["project"]
    responsible = result.get("responsible_name") or "Nao informado"
    project_code_label = project.code if getattr(project, "code", None) else project_code
    activity_code = task.code if getattr(task, "code", None) else f"{project_code_label}.{task.id}"

    return sanitize_output(
        f"Atividade '{task.what}' cadastrada com sucesso no projeto '{project_code_label} - {project.name}'.\n"
        f"Codigo da Atividade: {activity_code}\n"
        f"Responsavel: {responsible}"
    )

def list_team_workload():
    """
    Analisa a carga de trabalho de todos os colaboradores da empresa.
    Identifica quem está sobrecarregado, ocioso ou em equilíbrio, com base nas horas
    disponíveis por semana versus tarefas abertas estimadas.
    Ideal para o supervisor identificar necessidade de redistribuição de tarefas.
    """
    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Nenhuma empresa ativa identificada."

    try:
        from sqlalchemy import text as sqltext

        with db.engine.connect() as conn:
            # Carga de tarefas abertas por colaborador (por nome no campo 'who')
            q = sqltext("""
                SELECT
                    e.name AS collaborator,
                    e.weekly_hours AS capacity_hours,
                    COUNT(pt.id) FILTER (WHERE pt.status NOT IN ('completed','cancelled')) AS open_tasks,
                    COUNT(pi.id) FILTER (WHERE pi.status NOT IN ('completed','cancelled')) AS open_instances
                FROM employees e
                LEFT JOIN project_tasks pt ON pt.who = e.name
                LEFT JOIN process_instances pi ON pi.employee_id = e.id
                WHERE e.company_id = :cid AND e.status = 'active'
                GROUP BY e.id, e.name, e.weekly_hours
                ORDER BY (open_tasks + open_instances) DESC
            """)
            rows = [dict(r._mapping) for r in conn.execute(q, {"cid": company_id})]

        if not rows:
            return "Nenhum colaborador ativo encontrado na empresa."

        lines = ["👥 ANÁLISE DE CARGA DA EQUIPE:", ""]
        for r in rows:
            cap = float(r['capacity_hours']) if r['capacity_hours'] else 40.0
            total_tasks = (r['open_tasks'] or 0) + (r['open_instances'] or 0)
            # Estimativa: cada tarefa = 2h médias
            estimated_hours = total_tasks * 2.0
            pct = (estimated_hours / cap * 100) if cap > 0 else 0

            if pct >= 100:
                emoji = "🔴 Sobrecarregado"
            elif pct >= 70:
                emoji = "🟡 Atenção"
            else:
                emoji = "🟢 OK"

            lines.append(
                f"  {emoji} | {r['collaborator']}: "
                f"{total_tasks} tarefas abertas (~{estimated_hours:.0f}h estimadas) "
                f"de {cap:.0f}h/semana disponíveis ({pct:.0f}%)"
            )

        return sanitize_output("\n".join(lines))
    except Exception as e:
        return f"Erro ao analisar carga da equipe: {str(e)}"

def complete_task(
    task_type: str,
    task_id: int,
    evidence_description: str = None,
    completion_date: str = None,
    notification_email: str = None,
    notification_whatsapp: str = None,
):
    """
    Marca uma tarefa de projeto ou instância de processo como CONCLUÍDA e opcionalmente notifica interessados.
    :param task_type: Tipo da tarefa: 'project_task' ou 'process_instance'
    :param task_id: ID da tarefa ou instância a ser concluída.
    :param evidence_description: Descrição do que foi feito como evidência/observação.
    :param completion_date: Opcional data da conclusão no formato YYYY-MM-DD. Se omitida, usa HOJE.
    :param notification_email: Opcional e-mail para notificar sobre a conclusão.
    :param notification_whatsapp: Opcional número de WhatsApp (com DDD) para notificar.
    """
    try:
        if completion_date:
            try:
                final_date = datetime.strptime(completion_date, "%Y-%m-%d").date()
            except ValueError:
                return f"Erro: Formato de data inválido '{completion_date}'. Use YYYY-MM-DD."
        else:
            tz_name = os.environ.get("APP_TIMEZONE") or "America/Bahia"
            final_date = datetime.now(ZoneInfo(tz_name)).date()

        if task_type == "project_task":
            task, error = get_project_task_in_active_company(task_id)
            if error:
                return error

            task.status = "completed"
            task.stage = "completed"
            task.completion_date = final_date

            if evidence_description:
                task.how = (task.how or "") + f"\n\n✅ EVIDÊNCIA DE CONCLUSÃO ({final_date}): {evidence_description}"

            if task.project:
                try:
                    task.project.update_progress()
                except Exception:
                    db.session.rollback()
                    return "Erro ao concluir tarefa: falha ao atualizar o progresso do projeto."

            db.session.commit()

            notif_msg = []
            if notification_email:
                from services.email_service import email_service

                body = (
                    f"A tarefa '{task.what}' do projeto '{task.project.name}' foi CONCLUÍDA.\n"
                    f"Evidência: {evidence_description or 'N/A'}"
                )
                email_service.send_email(
                    to_emails=[notification_email],
                    subject="Notificação de Conclusão - Gestão Versus",
                    body=body,
                )
                notif_msg.append(f"e-mail enviado para {notification_email}")

            if notification_whatsapp:
                from services.whatsapp_service import whatsapp_service

                wa_body = (
                    f"✅ *Conclusão de Tarefa*\n\nAtividade: {task.what}\nProjeto: {task.project.name}\n"
                    f"Status: CONCLUÍDA\nEvidência: {evidence_description or 'N/A'}"
                )
                whatsapp_service.send_message(notification_whatsapp, wa_body)
                notif_msg.append(f"WhatsApp enviado para {notification_whatsapp}")

            notif_status = f" | Notificações: {', '.join(notif_msg)}" if notif_msg else ""
            return (
                f"✅ Tarefa '{task.what}' (ID {task_id}) marcada como concluída!\n"
                f"   Data registrada: {final_date}\n"
                f"   Projeto ID: {task.project_id}\n"
                f"   Evidência registrada: {evidence_description or 'Não informada'}"
                f"{notif_status}"
            )

        if task_type == "process_instance":
            instance, error = get_process_instance_in_active_company(task_id)
            if error:
                return error

            instance.status = "completed"
            instance.completed_at = datetime.combine(final_date, datetime.min.time())
            instance.actual_end_date = final_date

            if evidence_description:
                instance.notes = (instance.notes or "") + f"\n\n✅ EVIDÊNCIA ({final_date}): {evidence_description}"

            db.session.commit()
            return (
                f"✅ Instância de processo ID {task_id} concluída!\n"
                f"   Data registrada: {final_date}\n"
                f"   Evidência registrada: {evidence_description or 'Não informada'}"
            )

        return "Tipo de tarefa inválido. Use 'project_task' ou 'process_instance'."
    except Exception as exc:
        db.session.rollback()
        return f"Erro ao concluir tarefa: {exc}"


def log_work_hours(task_type: str, task_id: int, hours: float, description: str, work_date: str = None):
    """
    Registra horas trabalhadas em uma tarefa de projeto ou instância de processo.
    """
    try:
        work_dt = datetime.strptime(work_date, "%Y-%m-%d").date() if work_date else date.today()
        if hours <= 0:
            return "Erro: informe uma quantidade de horas maior que zero."

        user_id = get_active_user_id()
        company_id = get_active_company_id()
        if not user_id:
            return "Erro: usuário não autenticado."

        if task_type == "project_task":
            from models.activity_work_log import ActivityWorkLog
            from models.employee import Employee
            from models.project import ProjectActivityCollaborator, ProjectTask, ProjectTaskHoursSummary

            task = db.session.get(ProjectTask, task_id)
            if not task:
                return f"Tarefa de projeto ID {task_id} não encontrada."
            if not task.project:
                return f"Erro: a tarefa {task_id} não possui projeto vinculado."
            if company_id and int(company_id) != int(task.project.company_id):
                return "Erro: a tarefa informada não pertence à empresa ativa do contexto."

            employee = (
                Employee.query.filter(
                    Employee.user_id == user_id,
                    Employee.company_id == task.project.company_id,
                    Employee.status == "active",
                )
                .order_by(Employee.id.asc())
                .first()
            )
            if not employee:
                return "Erro: não encontrei um colaborador ativo vinculado ao usuário na empresa desta tarefa."

            existing_collab = ProjectActivityCollaborator.query.filter_by(
                activity_id=task.id,
                employee_id=employee.id,
            ).first()
            if not existing_collab:
                existing_collab = ProjectActivityCollaborator(
                    company_id=task.project.company_id,
                    project_id=task.project_id,
                    activity_id=task.id,
                    employee_id=employee.id,
                    role="executor",
                    estimated_hours=Decimal("0"),
                    worked_hours=Decimal("0"),
                )
                db.session.add(existing_collab)
                db.session.flush()

            work_log = ActivityWorkLog(
                company_id=task.project.company_id,
                activity_type="project",
                activity_id=task.id,
                employee_id=employee.id,
                employee_name=employee.name,
                hours_worked=Decimal(str(hours)),
                description=description,
                work_date=work_dt,
                created_by=employee.id,
            )
            db.session.add(work_log)

            total_worked_hours = (
                db.session.query(func.coalesce(func.sum(ActivityWorkLog.hours_worked), 0))
                .filter(
                    ActivityWorkLog.activity_type == "project",
                    ActivityWorkLog.activity_id == task.id,
                )
                .scalar()
                or Decimal("0")
            )
            total_worked_hours = Decimal(str(total_worked_hours)) + Decimal(str(hours))

            existing_collab.worked_hours = (
                Decimal(str(existing_collab.worked_hours or 0)) + Decimal(str(hours))
            )
            task.worked_hours = total_worked_hours

            summary = ProjectTaskHoursSummary.query.filter_by(task_id=task.id).first()
            if not summary:
                summary = ProjectTaskHoursSummary(task_id=task.id)
                db.session.add(summary)
            summary.total_worked_hours = total_worked_hours

            db.session.commit()
            return (
                f"✅ {hours:.2f}h registradas na atividade '{task.what}' (ID {task_id}) em {work_dt}.\n"
                f"   Colaborador: {employee.name}\n"
                f"   Total acumulado: {float(total_worked_hours):.2f}h\n"
                f"   Descrição: {description}"
            )

        if task_type == "process_instance":
            from models.activity_work_log import ActivityWorkLog
            from models.employee import Employee
            from models.process import ProcessInstance

            instance = db.session.get(ProcessInstance, task_id)
            if not instance:
                return f"Instância de processo ID {task_id} não encontrada."
            if company_id and int(company_id) != int(instance.company_id):
                return "Erro: a instância informada não pertence à empresa ativa do contexto."

            employee = (
                Employee.query.filter(
                    Employee.user_id == user_id,
                    Employee.company_id == instance.company_id,
                    Employee.status == "active",
                )
                .order_by(Employee.id.asc())
                .first()
            )
            if not employee:
                return "Erro: não encontrei um colaborador ativo vinculado ao usuário na empresa desta instância."

            work_log = ActivityWorkLog(
                company_id=instance.company_id,
                activity_type="process",
                activity_id=instance.id,
                employee_id=employee.id,
                employee_name=employee.name,
                hours_worked=Decimal(str(hours)),
                description=description,
                work_date=work_dt,
                created_by=employee.id,
            )
            db.session.add(work_log)

            instance.worked_hours = Decimal(str(instance.worked_hours or 0)) + Decimal(str(hours))
            instance.actual_hours = Decimal(str(instance.actual_hours or 0)) + Decimal(str(hours))
            db.session.commit()
            return (
                f"✅ {hours:.2f}h registradas na instância '{instance.title}' (ID {task_id}) em {work_dt}.\n"
                f"   Colaborador: {employee.name}\n"
                f"   Total acumulado: {float(instance.worked_hours or 0):.2f}h\n"
                f"   Descrição: {description}"
            )

        return "Tipo de tarefa inválido. Use 'project_task' ou 'process_instance'."
    except Exception as exc:
        db.session.rollback()
        return f"Erro ao registrar horas: {exc}"


def request_deadline_extension(task_type: str, task_id: int, new_deadline: str, reason: str):
    """
    Solicita ao superior hierárquico o adiamento do prazo de uma tarefa.
    """
    from models.agent_action import AgentAction
    from services.email_service import email_service
    from services.whatsapp_service import whatsapp_service

    company_id = get_active_company_id()

    try:
        task_name = f"Tarefa ID {task_id}"
        current_deadline = "N/A"

        user = get_active_user()
        requester_name = user.name if user else "Usuário"

        if task_type == "project_task":
            task, error = get_project_task_in_active_company(task_id)
            if error:
                return error
            task_name = task.what
            current_deadline = str(task.due_date) if task.due_date else "Sem prazo"
        elif task_type == "process_instance":
            inst, error = get_process_instance_in_active_company(task_id)
            if error:
                return error
            current_deadline = str(inst.due_date) if inst.due_date else "Sem prazo"

        action = AgentAction(
            type="approval_request",
            status="pending",
            requesting_agent="sapiens",
            handling_agent="operations",
            title=f"Solicitação de Adiamento: {task_name}",
            description=(
                f"Solicitante: {requester_name}\n"
                f"Tarefa: {task_name} (ID {task_id}, tipo: {task_type})\n"
                f"Prazo Atual: {current_deadline}\n"
                f"Novo Prazo Solicitado: {new_deadline}\n"
                f"Motivo: {reason}"
            ),
            payload={
                "task_type": task_type,
                "task_id": task_id,
                "new_deadline": new_deadline,
                "reason": reason,
                "requester": requester_name,
            },
            company_id=int(company_id) if company_id else None,
            user_id=get_active_user_id(),
        )
        db.session.add(action)
        db.session.commit()
        try:
            from services.agent_action_backlog_service import ensure_backlog_task_for_action

            ensure_backlog_task_for_action(action, autocommit=True)
        except Exception:
            logger.exception("Falha ao espelhar approval_request #%s no backlog AA.J.31", action.id)

        from models.employee import Employee
        from models.user import User

        managers = (
            db.session.query(User)
            .join(Employee, Employee.user_id == User.id)
            .filter(Employee.company_id == int(company_id), User.role.in_(["admin", "client"]))
            .all()
        ) if company_id else []

        wa_sent = 0
        for mgr in managers:
            if mgr.whatsapp:
                msg = (
                    f"⚠️ *Solicitação de Adiamento de Prazo* (Ticket #{action.id})\n\n"
                    f"📋 Tarefa: *{task_name}*\n"
                    f"👤 Solicitante: {requester_name}\n"
                    f"📅 Prazo Atual: {current_deadline}\n"
                    f"📅 Novo Prazo Pedido: *{new_deadline}*\n"
                    f"💬 Motivo: {reason}\n\n"
                    f"Responda 'APROVAR {action.id}' ou 'RECUSAR {action.id}' para o Sapiens processar."
                )
                whatsapp_service.send_message(mgr.whatsapp, msg)
                wa_sent += 1
            if mgr.email:
                email_service.send_email(
                    to_emails=[mgr.email],
                    subject=f"[Ação Necessária] Adiamento de Prazo: {task_name}",
                    body=(
                        f"Solicitante: {requester_name}\n"
                        f"Tarefa: {task_name}\n"
                        f"Prazo atual: {current_deadline} → Novo prazo: {new_deadline}\n"
                        f"Motivo: {reason}\n\n"
                        f"Acesse o sistema para aprovar ou recusar. Ticket #{action.id}"
                    ),
                )

        return (
            f"🕐 Solicitação de adiamento enviada ao seu superior! (Ticket #{action.id})\n"
            f"   Tarefa: {task_name}\n"
            f"   Prazo atual: {current_deadline} → Solicitado: {new_deadline}\n"
            f"   Motivo: {reason}\n"
            f"   {wa_sent} gestor(es) notificado(s) via WhatsApp.\n"
            f"   Aguarde a resposta. Assim que aprovado, o prazo será alterado automaticamente no sistema."
        )
    except Exception as exc:
        db.session.rollback()
        return f"Erro ao solicitar adiamento: {exc}"

def squad_create_intervention(title: str, due_date: str, how: str, notes: str = "", assignee_name: str = "Agente Squad"):
    """
    SQUAD DE ENGENHARIA: cria uma intervenção no projeto AA.J.31.
    """
    from models.employee import Employee
    from models.project import Project, ProjectTask
    from models.user import User
    from services.whatsapp_service import whatsapp_service

    try:
        due_dt = datetime.strptime(due_date, "%Y-%m-%d").date()
    except ValueError:
        return f"Erro: formato de data inválido '{due_date}'. Use YYYY-MM-DD."

    project = Project.query.get(31)
    if not project:
        return "Erro: projeto AA.J.31 não encontrado."

    existing = (
        ProjectTask.query.filter(
            ProjectTask.project_id == project.id,
            ProjectTask.what.ilike(title.strip()),
            ProjectTask.status.notin_(["completed", "cancelled"]),
        )
        .order_by(ProjectTask.id.desc())
        .first()
    )
    if existing:
        return f"Já existe intervenção aberta semelhante: '{existing.what}' (ID: {existing.id}). Nenhuma duplicata gerada."

    emp = Employee.query.filter(
        Employee.company_id == project.company_id,
        Employee.name.ilike(f"%{assignee_name}%"),
    ).first()
    emp_id = emp.id if emp else None

    fabiano = Employee.query.join(User, User.id == Employee.user_id).filter(
        Employee.company_id == project.company_id,
        User.name.ilike("%Fabiano%"),
    ).first()

    task = ProjectTask(
        project_id=project.id,
        what=title,
        who=emp.name if emp else assignee_name,
        employee_id=emp_id,
        due_date=due_dt,
        how=how,
        notes=notes,
        status="planned",
        stage="inbox",
        priority="normal",
        score_weight=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.session.add(task)
    db.session.commit()

    if fabiano and hasattr(fabiano, "user") and getattr(fabiano.user, "whatsapp", None):
        msg = (
            f"🛠️ *Squad de Engenharia - Nova Intervenção!*\n\n"
            f"📌 *O Quê:* {title}\n"
            f"👤 *Quem:* {assignee_name}\n"
            f"📅 *Prazo:* {due_date}\n"
            f"📋 *Como:* {how}\n"
            f"📝 *Obs:* {notes}\n"
        )
        whatsapp_service.send_message(fabiano.user.whatsapp, msg)

    return f"Atividade '{title}' criada com sucesso no projeto AA.J.31. ID criado da tarefa: {task.id}"


def squad_update_intervention(task_id: int, stage: str, log_history: str, hours_worked: float = 0.0):
    """
    SQUAD DE ENGENHARIA: atualiza o andamento de uma intervenção.
    """
    from models.activity_work_log import ActivityWorkLog
    from models.employee import Employee
    from models.project import ProjectActivityCollaborator, ProjectTaskHoursSummary
    from models.user import User
    from services.whatsapp_service import whatsapp_service

    task, error = get_project_task_in_active_company(task_id)
    if error:
        return error

    task.stage = stage
    if stage == "completed":
        task.status = "completed"
    elif stage in ("executing", "pending", "waiting"):
        task.status = "in_progress"

    logs = list(task.logs) if task.logs else []
    logs.append(
        {
            "date": datetime.utcnow().isoformat(),
            "author": "Squad Bot",
            "text": log_history,
        }
    )
    task.logs = logs

    fabiano = None
    if task.project:
        fabiano = Employee.query.join(User, User.id == Employee.user_id).filter(
            Employee.company_id == task.project.company_id,
            User.name.ilike("%Fabiano%"),
        ).first()

    if float(hours_worked) > 0 and fabiano:
        log = ActivityWorkLog(
            activity_type="project",
            activity_id=task_id,
            employee_id=fabiano.id,
            employee_name=fabiano.name,
            hours_worked=Decimal(str(hours_worked)),
            description=log_history[:250],
            work_date=datetime.utcnow().date(),
            created_at=datetime.utcnow(),
        )
        db.session.add(log)

        collab = ProjectActivityCollaborator.query.filter_by(activity_id=task_id, employee_id=fabiano.id).first()
        if not collab:
            collab = ProjectActivityCollaborator(activity_id=task_id, employee_id=fabiano.id, role="executor")
            db.session.add(collab)
        collab.worked_hours = Decimal(str(collab.worked_hours or 0)) + Decimal(str(hours_worked))
        db.session.flush()

        task.worked_hours = (task.worked_hours or 0) + Decimal(str(hours_worked))

        sum_row = ProjectTaskHoursSummary.query.filter_by(task_id=task_id).first()
        if not sum_row:
            sum_row = ProjectTaskHoursSummary(task_id=task_id)
            db.session.add(sum_row)
        sum_row.total_worked_hours = Decimal(str(sum_row.total_worked_hours or 0)) + Decimal(str(hours_worked))

    db.session.commit()

    if stage in ("executing", "in_progress") and fabiano and hasattr(fabiano, "user") and getattr(fabiano.user, "whatsapp", None):
        msg = (
            f"⚙️ *Squad de Engenharia - Intervenção em Andamento*\n\n"
            f"📌 *Atividade:* {task.what}\n"
            f"🔄 *Fase atual:* {stage}\n"
            f"⏱️ *Tempo investido (agora):* {hours_worked}h\n"
            f"📝 *Histórico:* {log_history}"
        )
        whatsapp_service.send_message(fabiano.user.whatsapp, msg)

    return f"Status da intervenção {task_id} atualizado para '{stage}'. {hours_worked}h lançadas com sucesso."


def squad_finish_intervention(task_id: int, remark: str, hours_worked: float = 0.0):
    """
    SQUAD DE ENGENHARIA: conclui a intervenção e notifica o responsável.
    """
    from models.employee import Employee
    from models.user import User
    from services.whatsapp_service import whatsapp_service

    task, error = get_project_task_in_active_company(task_id)
    if error:
        return error

    comp_resp = squad_update_intervention(
        task_id=task_id,
        stage="completed",
        log_history=remark,
        hours_worked=hours_worked,
    )

    task.completion_date = datetime.utcnow().date()
    db.session.commit()

    if task.project:
        fabiano = Employee.query.join(User, User.id == Employee.user_id).filter(
            Employee.company_id == task.project.company_id,
            User.name.ilike("%Fabiano%"),
        ).first()
        if fabiano and hasattr(fabiano, "user") and getattr(fabiano.user, "whatsapp", None):
            msg = (
                f"✅ *Squad de Engenharia - Intervenção Concluída!*\n\n"
                f"📌 *Atividade:* {task.what}\n"
                f"💰 *Tempo investido final:* {hours_worked}h\n"
                f"🏁 *Resultado/Observação:* {remark}"
            )
            whatsapp_service.send_message(fabiano.user.whatsapp, msg)

    return f"Atividade {task_id} concluída com sucesso! Detalhes: {comp_resp}"
