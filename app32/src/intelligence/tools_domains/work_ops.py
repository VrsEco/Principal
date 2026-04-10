from __future__ import annotations

import logging

from models import db
from src.intelligence.tools_support import _rank_companies_by_term, get_active_user_id, sanitize_output

logger = logging.getLogger(__name__)


def get_my_work(scope: str = 'me', company_ids: str = None, search_term: str = None):
    """
    Retorna a lista de atividades (Projetos e Processos) pendentes para o usuário logado.
    :param scope: 'me' para minhas atividades, 'team' para equipe, 'company' para toda a empresa.
    :param company_ids: Opcional, ids de empresas separados por virgula (ex: "31,32"). Se vazio, busca pendências em TODAS as empresas permitidas.
    :param search_term: Opcional, filtra atividades por título, descrição ou nome de empresa. Use para buscar tarefas de um colega específico (ex: "atividades de Caroline").
    """
    from sqlalchemy import or_
    from models.user import User
    from models.employee import Employee
    from models.company import Company
    from models.project import ProjectTask, Project
    from models.process import ProcessInstance

    user_id = get_active_user_id()
    logger.debug("get_my_work user_id=%s scope=%s", user_id, scope)

    if not user_id:
        return "Erro: Usuario nao autenticado."

    try:
        from datetime import datetime as dt

        user = db.session.get(User, user_id)
        if not user:
            return "Erro: Usuario nao encontrado."

        role = getattr(user, "role", "collaborator")
        scope = (scope or "me").strip().lower()
        if scope not in ("me", "team", "company"):
            scope = "me"

        # Vínculos do usuário
        user_emps = Employee.query.filter_by(user_id=user_id, status="active").all()
        if not user_emps:
            user_emps = Employee.query.filter_by(user_id=user_id).all()

        user_employee_ids = [e.id for e in user_emps]
        user_company_ids = sorted({e.company_id for e in user_emps if e.company_id})

        # Empresas acessíveis
        if role == "admin":
            accessible_companies = Company.query.filter_by(is_active=True).order_by(Company.id.asc()).all()
        else:
            if not user_company_ids:
                return "Nenhuma empresa acessivel encontrada para este usuario."
            accessible_companies = (
                Company.query.filter(Company.id.in_(user_company_ids))
                .order_by(Company.id.asc())
                .all()
            )

        accessible_company_ids = [c.id for c in accessible_companies]
        if not accessible_company_ids:
            return "Nenhuma empresa acessivel encontrada para este usuario."

        # Filtro explícito de company_ids
        if company_ids:
            requested_ids = [int(i.strip()) for i in company_ids.split(",") if i.strip().isdigit()]
            effective_company_ids = [cid for cid in requested_ids if cid in accessible_company_ids]
        else:
            effective_company_ids = list(accessible_company_ids)

        # Detecta empresa citada no texto livre e restringe o filtro por ela.
        matched_companies = []
        if search_term:
            text = search_term.strip()
            lower = text.lower()
            company_fragment = text
            for marker in ("na empresa", "da empresa", "empresa", "no cliente", "cliente"):
                idx = lower.find(marker)
                if idx >= 0:
                    company_fragment = text[idx + len(marker):].strip(" :-,.!?")
                    break

            matched_companies = _rank_companies_by_term(accessible_companies, company_fragment)
            if not matched_companies and company_fragment != text:
                matched_companies = _rank_companies_by_term(accessible_companies, text)

            if matched_companies:
                effective_company_ids = [c.id for c in matched_companies]

        if not effective_company_ids:
            return "Nenhuma empresa acessivel encontrada para o filtro informado."

        # Escopo (me/team) por colaboradores
        team_employee_ids = []
        if scope in ("me", "team"):
            team_rows = (
                Employee.query.filter(
                    Employee.company_id.in_(effective_company_ids),
                    Employee.status == "active",
                    Employee.id.isnot(None),
                )
                .order_by(Employee.id.asc())
                .all()
            )
            team_employee_ids = [e.id for e in team_rows]

        if scope == "me":
            target_employee_ids = set(user_employee_ids)
        elif scope == "team":
            target_employee_ids = set(team_employee_ids) - set(user_employee_ids)
        else:
            target_employee_ids = set()

        # Evita filtrar por texto quando a busca já virou filtro de empresa.
        apply_text_search = bool(search_term and not matched_companies)
        pattern = f"%{search_term.strip()}%" if apply_text_search else None

        # --- Projeto: project_tasks ---
        task_rows = (
            db.session.query(ProjectTask, Project, Company)
            .join(Project, Project.id == ProjectTask.project_id)
            .join(Company, Company.id == Project.company_id)
            .filter(Project.company_id.in_(effective_company_ids))
            .filter(ProjectTask.status.notin_(["completed", "done", "cancelled"]))
            .filter(ProjectTask.stage != "completed")
        )

        if scope == "me":
            if target_employee_ids:
                task_rows = task_rows.filter(ProjectTask.employee_id.in_(list(target_employee_ids)))
            elif user.name:
                task_rows = task_rows.filter(ProjectTask.who.ilike(f"%{user.name}%"))
        elif scope == "team":
            if target_employee_ids:
                task_rows = task_rows.filter(ProjectTask.employee_id.in_(list(target_employee_ids)))
            else:
                task_rows = task_rows.filter(ProjectTask.id == -1)

        if pattern:
            task_rows = task_rows.filter(
                or_(
                    ProjectTask.what.ilike(pattern),
                    ProjectTask.how.ilike(pattern),
                    ProjectTask.notes.ilike(pattern),
                    Project.name.ilike(pattern),
                    Company.name.ilike(pattern),
                    Company.client_code.ilike(pattern),
                )
            )

        task_rows = task_rows.order_by(ProjectTask.due_date.asc().nullslast(), ProjectTask.id.asc()).limit(300).all()

        # --- Processo: process_instances ---
        instance_rows = (
            db.session.query(ProcessInstance, Company)
            .join(Company, Company.id == ProcessInstance.company_id)
            .filter(ProcessInstance.company_id.in_(effective_company_ids))
            .filter(ProcessInstance.status.notin_(["completed", "done", "cancelled"]))
        )
        if pattern:
            instance_rows = instance_rows.filter(
                or_(
                    ProcessInstance.title.ilike(pattern),
                    ProcessInstance.description.ilike(pattern),
                    Company.name.ilike(pattern),
                    Company.client_code.ilike(pattern),
                )
            )

        instance_rows = instance_rows.order_by(
            ProcessInstance.due_date.asc().nullslast(), ProcessInstance.id.asc()
        ).limit(300).all()

        def _instance_belongs_to_scope(instance_obj, employee_ids):
            if not employee_ids:
                return False

            assigned_ids = {
                instance_obj.owner_employee_id,
                instance_obj.responsible_id,
                instance_obj.executor_id,
            }
            if any(aid in employee_ids for aid in assigned_ids if aid):
                return True

            collaborators = instance_obj.collaborators_json or []
            for c in collaborators:
                if not isinstance(c, dict):
                    continue
                cid = c.get("id") or c.get("employee_id")
                try:
                    if cid and int(cid) in employee_ids:
                        return True
                except Exception:
                    continue
            return False

        activities = []

        # Mapa de colaboradores para nomes (usado em instâncias de processo).
        employee_ids_in_instances = set()
        for instance, _company in instance_rows:
            for emp_id in (
                getattr(instance, "owner_employee_id", None),
                getattr(instance, "responsible_id", None),
                getattr(instance, "executor_id", None),
            ):
                if emp_id:
                    employee_ids_in_instances.add(emp_id)

        employee_name_map = {}
        if employee_ids_in_instances:
            rows = (
                Employee.query.filter(Employee.id.in_(list(employee_ids_in_instances)))
                .with_entities(Employee.id, Employee.name)
                .all()
            )
            employee_name_map = {row[0]: row[1] for row in rows}

        for task, project, company in task_rows:
            company_label = f"{company.client_code} - {company.name}" if company.client_code else company.name
            project_code = project.code if hasattr(project, "code") else f"{company.client_code or 'CP'}.J.{project.id}"
            task_suffix = f"{int(task.id):02d}" if str(task.id).isdigit() else str(task.id)
            activity_code = f"{project_code}.{task_suffix}"
            activities.append({
                "type": "projeto",
                "title": task.what,
                "project_name": project.name,
                "project_code": project_code,
                "activity_code": activity_code,
                "responsible_name": (task.employee_name or "Nao definido"),
                "company_name": company_label,
                "id": task.id,
                "deadline": task.due_date,
                "status": task.status or task.stage or "planned",
            })

        for instance, company in instance_rows:
            if scope in ("me", "team"):
                if not _instance_belongs_to_scope(instance, target_employee_ids):
                    continue
            company_label = f"{company.client_code} - {company.name}" if company.client_code else company.name
            process_code = (
                instance.instance_code
                or (instance.process_rel.code if getattr(instance, "process_rel", None) else None)
                or f"{company.client_code or 'CP'}.P.{instance.id}"
            )
            process_owner_name = (
                (getattr(instance, "process_rel", None) and getattr(instance.process_rel, "responsible", None))
                or employee_name_map.get(getattr(instance, "owner_employee_id", None))
                or employee_name_map.get(getattr(instance, "responsible_id", None))
                or "Nao definido"
            )
            activities.append({
                "type": "processo",
                "title": instance.title,
                "project_name": getattr(instance.process_rel, "name", None),
                "project_code": process_code,
                "activity_code": process_code,
                "process_owner_name": process_owner_name,
                "company_name": company_label,
                "id": instance.id,
                "deadline": instance.due_date,
                "status": instance.status or "pending",
            })

        def _deadline_sort_value(value):
            if value is None:
                return "9999-12-31"
            if isinstance(value, dt):
                return value.date().isoformat()
            if hasattr(value, "isoformat"):
                return value.isoformat()
            return str(value)

        activities.sort(
            key=lambda a: (
                a["deadline"] is None,
                _deadline_sort_value(a["deadline"]),
                a["id"],
            )
        )

        if not activities:
            if matched_companies:
                chosen = matched_companies[0]
                label = f"{chosen.client_code} - {chosen.name}" if chosen.client_code else chosen.name
                return f"Nenhuma atividade pendente encontrada para a empresa '{label}'."
            return f"Nenhuma atividade pendente encontrada no escopo '{scope}' para as empresas selecionadas."

        summary = []
        for item in activities:
            deadline_obj = item["deadline"]
            if isinstance(deadline_obj, dt):
                deadline = deadline_obj.date().isoformat()
            elif hasattr(deadline_obj, "isoformat"):
                deadline = deadline_obj.isoformat()
            else:
                deadline = deadline_obj or "Sem prazo"
            if item["type"] == "projeto":
                summary.append(
                    f"- [PROJETO] {item.get('project_code') or '-'} - {item.get('project_name') or '-'} "
                    f"| [ATIVIDADE] {item.get('activity_code') or '-'} - {item['title']} "
                    f"| Responsavel: {item.get('responsible_name') or 'Nao definido'} "
                    f"| Empresa: {item['company_name']} | ID: {item['id']} | Prazo: {deadline} | Status: {item['status']}"
                )
            else:
                summary.append(
                    f"- [PROCESSO] {item.get('project_code') or '-'} - {item['title']} "
                    f"| [ATIVIDADE] {item.get('activity_code') or '-'} - {item['title']} "
                    f"| Dono do Processo: {item.get('process_owner_name') or 'Nao definido'} "
                    f"| Empresa: {item['company_name']} | ID: {item['id']} | Prazo: {deadline} | Status: {item['status']}"
                )

        return "\n".join(summary)
    except Exception as e:
        return f"Erro ao buscar atividades via MCP: {str(e)}"
