from flask import current_app, request
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from models import db, ProjectTask, Project, Indicator, Process
from models.workflow_gap import WorkflowGapCandidate
from schemas.project import project_task_schema, project_tasks_schema
from utils.permissions import can_manage_project_tasks, has_company_full_access, has_permission, permission_required
from datetime import datetime
from services.project_task_due_date_change_service import (
    ProjectTaskDueDateChangeService,
)
from services.project_task_service import ProjectTaskService
from utils.error_handling import log_and_build_public_error_response

PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."


def _backlog_project_id() -> int | None:
    from services.agent_backlog_service import DEFAULT_AGENT_BACKLOG_PROJECT_CODE
    from services.project_task_service import ProjectTaskService

    return ProjectTaskService.extract_id_from_code(DEFAULT_AGENT_BACKLOG_PROJECT_CODE)


def _should_include_backlog_human_gate(project_id: int | None) -> bool:
    backlog_project_id = _backlog_project_id()
    return bool(backlog_project_id and int(project_id or 0) == int(backlog_project_id))


def _serialize_task(task, *, include_backlog_human_gate: bool = False, company_id: int | None = None):
    payload = project_task_schema.dump(task)
    payload.update(
        ProjectTaskDueDateChangeService.build_task_context(
            getattr(task, "id", 0),
            company_id=company_id,
        )
    )
    if not include_backlog_human_gate:
        return payload

    from services.backlog_human_gate_service import build_backlog_human_gate_context

    backlog_human_gate = build_backlog_human_gate_context(task)
    if backlog_human_gate:
        payload["backlog_human_gate"] = backlog_human_gate
    return payload


def _serialize_task_list(tasks, *, project_id: int | None = None, company_id: int | None = None):
    payload = project_tasks_schema.dump(tasks)
    due_date_change_context_map = ProjectTaskDueDateChangeService.build_task_context_map(
        [int(getattr(task, "id", 0) or 0) for task in tasks],
        company_id=company_id,
    )
    for item in payload:
        item.update(
            due_date_change_context_map.get(
                int(item.get("id", 0) or 0),
                ProjectTaskDueDateChangeService.empty_context(),
            )
        )
    if not _should_include_backlog_human_gate(project_id):
        return payload

    from services.backlog_human_gate_service import build_backlog_human_gate_context_map

    context_map = build_backlog_human_gate_context_map(
        [int(getattr(task, "id", 0) or 0) for task in tasks]
    )
    for item in payload:
        task_context = context_map.get(int(item.get("id", 0) or 0))
        if task_context:
            item["backlog_human_gate"] = task_context
    return payload


def _is_backlog_human_gate_task(task) -> bool:
    return bool(getattr(task, "agent_action_backlog_link", None))


def _build_backlog_human_gate_lock_response():
    return {
        "error": (
            "Este card operacional é espelhado a partir da fila HITL."
            " Use as ações do backlog para operar este item."
        )
    }, 409


def _detach_workflow_gap_candidates_for_task(*, task_id, project_id, company_id):
    if not task_id or not project_id:
        return

    query = WorkflowGapCandidate.query.filter(
        WorkflowGapCandidate.app_task_id == task_id,
        WorkflowGapCandidate.app_project_id == project_id,
    )
    if company_id is not None:
        query = query.filter(
            db.or_(
                WorkflowGapCandidate.company_id == company_id,
                WorkflowGapCandidate.company_id.is_(None),
            )
        )

    for candidate in query.all():
        candidate.app_task_id = None

def _sync_table_sequence(table_name: str, pk_column: str = 'id'):
    seq_row = db.session.execute(
        text("SELECT pg_get_serial_sequence(:table_name, :pk_column) AS seq"),
        {"table_name": table_name, "pk_column": pk_column}
    ).mappings().first()
    seq_name = seq_row['seq'] if seq_row else None
    if not seq_name:
        return False

    db.session.execute(
        text("SELECT setval(:seq_name, COALESCE((SELECT MAX(id) FROM project_tasks), 0) + 1, false)"),
        {"seq_name": seq_name}
    )
    db.session.commit()
    return True


def apply_task_employee_filter(query, company_id):
    from flask_login import current_user
    from models.employee import Employee
    from models.project import ProjectTask, ProjectActivityCollaborator
    from sqlalchemy import or_
    
    if not current_user.is_authenticated:
        return query

    # Perfis com acesso total na empresa veem todas as tarefas
    if company_id and has_company_full_access(company_id):
        return query

    # Colaborador: só tarefas onde é executor ou colaborador
    employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
    if employee:
        return query.filter(
            or_(
                ProjectTask.employee_id == employee.id,
                ProjectTask.collaborators.any(ProjectActivityCollaborator.employee_id == employee.id)
            )
        )
        
    return query


def _user_can_update_task(company_id, project_id, task_id):
    if can_manage_project_tasks(company_id):
        return True

    query = ProjectTask.query.filter_by(id=task_id, project_id=project_id, is_deleted=False)
    query = apply_task_employee_filter(query, company_id)
    return query.first() is not None


def _user_can_approve_due_date_change(company_id, project_id, task):
    project = Project.query.filter_by(id=project_id, company_id=company_id).first()
    if not project:
        return False
    return ProjectTaskDueDateChangeService.user_can_approve(project, company_id)


def _resolve_due_date_change_company_id(project_id, task_id):
    from .project import get_request_company_id

    company_id = get_request_company_id()
    if company_id:
        return company_id

    project = Project.query.filter_by(id=project_id).first()
    if not project:
        return None

    task = ProjectTask.query.filter_by(id=task_id, project_id=project_id, is_deleted=False).first()
    if not task:
        return None

    return project.company_id


def _validate_limited_task_update_payload(data):
    allowed_fields = {'stage', 'status', 'completion_date', 'logs'}
    extra_fields = set((data or {}).keys()) - allowed_fields
    if extra_fields:
        return False, extra_fields
    return True, set()


def _get_project_company_id(project_id):
    project = Project.query.filter_by(id=project_id).first()
    return int(project.company_id) if project and getattr(project, 'company_id', None) else None


def _user_can_create_task(company_id, project_id):
    if not company_id or not project_id:
        return False
    project = Project.query.filter_by(id=project_id, company_id=company_id).first()
    if not project:
        return False
    return can_manage_project_tasks(company_id)


def _validate_company_employee(company_id, employee_id, *, required=False):
    if employee_id in (None, ''):
        return None if not required else False

    from models.employee import Employee

    employee = Employee.query.filter_by(company_id=company_id, id=employee_id, status='active').first()
    return employee


def _normalize_task_assignment_payload(company_id, data):
    normalized = dict(data or {})
    employee_id = normalized.get('employee_id')
    employee = _validate_company_employee(company_id, employee_id) if employee_id else None
    if employee_id and not employee:
        raise ValidationError({'employee_id': ['Colaborador inválido para a empresa informada.']})
    if employee:
        normalized['employee_id'] = employee.id
        normalized['who'] = employee.name
    return normalized

class ProjectTaskListResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id):
        """List all tasks for a project with dependency status."""
        from flask import session
        from services.task_dependency_service import TaskDependencyService
        from models.project import ProjectTaskDependency

        from .project import get_request_company_id
        company_id = get_request_company_id()
            
        query = ProjectTask.query.filter_by(project_id=project_id, is_deleted=False).order_by(ProjectTask.id.asc())
        query = apply_task_employee_filter(query, company_id)
        tasks = query.all()
        dumped_tasks = _serialize_task_list(tasks, project_id=project_id, company_id=company_id)
        
        # Otimização: Busca todas as dependências do projeto de uma vez para evitar N+1 queries
        # Filtra por company_id para respeitar multi-tenancy no mapeamento de dependências
        all_deps = []
        if company_id:
            all_deps = ProjectTaskDependency.query.filter_by(
                project_id=project_id, 
                company_id=company_id
            ).all()
        
        # Mapa de bloqueio por sucessora
        # Uma tarefa está bloqueada se tiver alguma predecessora com stage != 'completed'
        blocked_map = {} # task_id -> list of blocking predecessors
        
        # Mapeamento rápido de ID para tarefa dumpada (para pegar o what/stage)
        tasks_by_id = {t['id']: t for t in dumped_tasks}
        
        for dep in all_deps:
            pred = tasks_by_id.get(dep.predecessor_task_id)
            if pred and pred.get('stage') != 'completed':
                if dep.successor_task_id not in blocked_map:
                    blocked_map[dep.successor_task_id] = []
                blocked_map[dep.successor_task_id].append({
                    "id": dep.id,
                    "predecessor_task_id": dep.predecessor_task_id,
                    "predecessor_what": pred.get('what'),
                    "predecessor_stage": pred.get('stage')
                })

        for task_data in dumped_tasks:
            # Se a tarefa está em 'todo' (legado ou externo), mapeamos para 'inbox' para visibilidade no Kanban
            # a menos que queiramos adicionar explicitamente a coluna 'todo' no frontend
            if task_data.get('stage') == 'todo':
                task_data['stage'] = 'inbox' 

            blocking = blocked_map.get(task_data['id'], [])
            task_data['is_blocked'] = len(blocking) > 0
            task_data['blocked_by'] = blocking
            
        return dumped_tasks, 200

    @permission_required('projects', 'view')
    def post(self, project_id):
        """Create a new task for a project."""
        from .project import get_request_company_id

        company_id = get_request_company_id() or _get_project_company_id(project_id)
        if not _user_can_create_task(company_id, project_id):
            return {"error": "Permission denied: create on projects"}, 403
        try:
            raw_data = request.get_json() or {}
            indicator_id = raw_data.pop('indicator_id', None)
            process_id = raw_data.pop('process_id', None)
            data = _normalize_task_assignment_payload(company_id, raw_data)
            data['project_id'] = project_id
            
            # Basic validation check
            if not data.get('what'):
                return {"error": "Description is required"}, 400

            if indicator_id:
                indicator = Indicator.query.filter_by(
                    id=indicator_id,
                    company_id=company_id,
                    is_active=True,
                ).first()
                if not indicator:
                    return {"error": "Indicador inválido para a empresa ativa."}, 400
            else:
                indicator = None

            if process_id:
                process = Process.query.filter_by(
                    id=process_id,
                    company_id=company_id,
                ).first()
                if not process:
                    return {"error": "Processo inválido para a empresa ativa."}, 400
            else:
                process = None

            if indicator or process:
                marker_lines = []
                if indicator:
                    marker_lines.append(f"APP32_INDICATOR_LINK: {indicator.id}")
                    marker_lines.append(f"Indicador vinculado: {indicator.name}")
                if process:
                    marker_lines.append(f"APP32_PROCESS_LINK: {process.id}")
                    marker_lines.append(f"Processo vinculado: {process.name}")
                marker_lines.append("Atividade corretiva criada a partir do Painel de Gestão Estratégica.")
                existing_notes = data.get('notes') or ''
                data['notes'] = (existing_notes + "\n\n" if existing_notes else "") + "\n".join(marker_lines)
            
            # Garantir sincronia status/stage na criação
            if data.get('stage') == 'completed':
                data['status'] = 'completed'
            elif data.get('stage') == 'inbox' or data.get('stage') == 'todo':
                data['status'] = 'planned'
                if data.get('stage') == 'todo': data['stage'] = 'inbox'

            def _build_task():
                task_obj = project_task_schema.load(data)
                db.session.add(task_obj)
                project = Project.query.get(project_id)
                if project:
                    project.update_progress()
                return task_obj

            try:
                task = _build_task()
                db.session.commit()
            except IntegrityError as exc:
                db.session.rollback()
                error_text = str(exc.orig) if getattr(exc, 'orig', None) else str(exc)
                if 'project_tasks_pkey' not in error_text and 'duplicate key value' not in error_text:
                    raise
                _sync_table_sequence('project_tasks')
                task = _build_task()
                db.session.commit()

            return _serialize_task(
                task,
                include_backlog_human_gate=_should_include_backlog_human_gate(project_id),
            ), 201
        except ValidationError as err:
            db.session.rollback()
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProjectTaskResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id, task_id):
        """Get a single task."""
        from .project import get_request_company_id
        company_id = get_request_company_id()
        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id, is_deleted=False)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()
        return _serialize_task(
            task,
            include_backlog_human_gate=_should_include_backlog_human_gate(project_id),
        ), 200

    @permission_required('projects', 'view')
    def put(self, project_id, task_id):
        """Update a task."""
        from .project import get_request_company_id
        company_id = get_request_company_id() or _get_project_company_id(project_id)
        if not _user_can_update_task(company_id, project_id, task_id):
            return {"error": "Permission denied: edit on projects"}, 403

        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id, is_deleted=False)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()
        try:
            data = request.get_json()
            if _is_backlog_human_gate_task(task):
                return _build_backlog_human_gate_lock_response()
            has_full_edit = can_manage_project_tasks(company_id)
            if not has_full_edit:
                is_valid_payload, extra_fields = _validate_limited_task_update_payload(data)
                if not is_valid_payload:
                    return {
                        "error": "Acesso negado: colaborador só pode atualizar status, conclusão e logs da própria atividade.",
                        "extra_fields": sorted(extra_fields),
                    }, 403
            
            # APP31 stage logic
            if 'stage' in data:
                if data['stage'] == 'completed':
                    task.status = 'completed'
                    if not data.get('completion_date') and not task.completion_date:
                        task.completion_date = datetime.now().date()
                elif data['stage'] == 'inbox':
                    task.status = 'planned'
                else:
                    task.status = 'in_progress'

            if 'logs' in data:
                task.logs = data['logs']
            
            task = project_task_schema.load(data, instance=task, partial=True)
            
            # Update project progress
            project = Project.query.get(project_id)
            if project:
                project.update_progress()
                
            # Garantir sincronia status/stage na edição
            if 'stage' in data:
                if data['stage'] == 'completed':
                    task.status = 'completed'
                    if not task.completion_date:
                        task.completion_date = datetime.now().date()
                elif data['stage'] == 'inbox' or data['stage'] == 'todo':
                    task.status = 'planned'
                    if data['stage'] == 'todo': task.stage = 'inbox'
                else:
                    task.status = 'in_progress'

            db.session.commit()
            return _serialize_task(
                task,
                include_backlog_human_gate=_should_include_backlog_human_gate(project_id),
            ), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

    @permission_required('projects', 'view')
    def patch(self, project_id, task_id):
        """Partial update (e.g. for stage moves)."""
        return self.put(project_id, task_id)

    @permission_required('projects', 'edit')
    def delete(self, project_id, task_id):
        """Delete a task."""
        from .project import get_request_company_id
        company_id = get_request_company_id()
        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id, is_deleted=False)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()
        if _is_backlog_human_gate_task(task):
            return _build_backlog_human_gate_lock_response()
        try:
            from flask_login import current_user

            _detach_workflow_gap_candidates_for_task(
                task_id=task.id,
                project_id=task.project_id,
                company_id=company_id,
            )
            task.is_deleted = True
            task.deleted_at = datetime.utcnow()
            task.deleted_by_user_id = getattr(current_user, "id", None) if getattr(current_user, "is_authenticated", False) else None
            task.delete_reason = "soft delete via API"
            
            # Update project progress
            with db.session.no_autoflush:
                project = Project.query.get(project_id)
                if project:
                    project.update_progress()
                
            db.session.commit()
            return {"message": "Task deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProjectTaskStageResource(Resource):
    @permission_required('projects', 'view')
    def patch(self, project_id, task_id):
        """Update task stage (Kanban drag & drop)."""
        from .project import get_request_company_id
        company_id = get_request_company_id()
        if not _user_can_update_task(company_id, project_id, task_id):
            return {"error": "Permission denied: edit on projects"}, 403

        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id, is_deleted=False)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()
        if _is_backlog_human_gate_task(task):
            return _build_backlog_human_gate_lock_response()
        try:
            data = request.get_json()
            stage = data.get('stage')
            if not stage:
                return {"error": "Stage is required"}, 400
            
            task.stage = stage
            
            # Handle logs and completion_date from payload (for Diary system)
            if 'logs' in data:
                task.logs = data['logs']
            
            if 'completion_date' in data:
                if data['completion_date']:
                    try:
                        task.completion_date = datetime.strptime(data['completion_date'], '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        task.completion_date = None
                else:
                    task.completion_date = None

            # Sync status with stage if applicable
            if stage == 'completed':
                task.status = 'completed'
                if not task.completion_date:
                    task.completion_date = datetime.now().date()
            elif stage == 'inbox':
                task.status = 'planned'
            else:
                task.status = 'in_progress'
                
            # Update project progress
            project = Project.query.get(project_id)
            if project:
                project.update_progress()
                
            db.session.commit()
            return _serialize_task(
                task,
                include_backlog_human_gate=_should_include_backlog_human_gate(project_id),
            ), 200
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProjectTaskDueDateChangeRequestListResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id, task_id):
        company_id = _resolve_due_date_change_company_id(project_id, task_id)
        if not company_id:
            return {"error": "Contexto da empresa não identificado para a atividade."}, 400
        _, project, project_error = ProjectTaskDueDateChangeService.get_task_or_error(
            company_id=company_id,
            project_id=project_id,
            task_id=task_id,
        )
        if project_error:
            return {"error": project_error}, 404

        can_request = _user_can_update_task(company_id, project_id, task_id)
        can_approve = ProjectTaskDueDateChangeService.user_can_approve(project, company_id)
        if not can_request and not can_approve:
            return {"error": "Permission denied: edit on projects"}, 403

        requests, project, error = ProjectTaskDueDateChangeService.list_requests(
            company_id=company_id,
            project_id=project_id,
            task_id=task_id,
        )
        if error:
            return {"error": error}, 404

        return {
            "requests": [item.to_dict() for item in requests],
            "permissions": {
                "can_request": can_request,
                "can_approve": can_approve,
            },
            "project_owner_name": getattr(project, "owner", None) if project else None,
        }, 200

    @permission_required('projects', 'view')
    def post(self, project_id, task_id):
        company_id = _resolve_due_date_change_company_id(project_id, task_id)
        if not company_id:
            return {"error": "Contexto da empresa não identificado para a atividade."}, 400
        if not _user_can_update_task(company_id, project_id, task_id):
            return {"error": "Permission denied: edit on projects"}, 403

        data = request.get_json() or {}
        request_obj, error = ProjectTaskDueDateChangeService.create_request(
            company_id=company_id,
            project_id=project_id,
            task_id=task_id,
            requested_due_date=data.get("requested_due_date"),
            reason=data.get("reason"),
        )
        if error:
            return {"error": error}, 400

        return {"request": request_obj.to_dict()}, 201


class ProjectTaskDueDateChangeRequestDecisionResource(Resource):
    @permission_required('projects', 'view')
    def post(self, project_id, task_id, request_id, action):
        company_id = _resolve_due_date_change_company_id(project_id, task_id)
        if not company_id:
            return {"error": "Contexto da empresa não identificado para a atividade."}, 400
        task, _, error = ProjectTaskDueDateChangeService.get_task_or_error(
            company_id=company_id,
            project_id=project_id,
            task_id=task_id,
        )
        if error or not task:
            return {"error": error or "Atividade não encontrada."}, 404

        if not _user_can_approve_due_date_change(company_id, project_id, task):
            return {
                "error": "Somente o responsável do projeto pode aprovar ou rejeitar adiamentos."
            }, 403

        data = request.get_json() or {}
        request_obj, error = ProjectTaskDueDateChangeService.decide_request(
            company_id=company_id,
            project_id=project_id,
            task_id=task_id,
            request_id=request_id,
            action=action,
            approved_due_date=data.get("approved_due_date"),
            approval_note=data.get("approval_note"),
        )
        if error:
            return {"error": error}, 400

        refreshed_task = ProjectTask.query.filter_by(
            id=task_id, project_id=project_id, is_deleted=False
        ).first()
        return {
            "request": request_obj.to_dict(),
            "task": _serialize_task(
                refreshed_task or task,
                include_backlog_human_gate=_should_include_backlog_human_gate(project_id),
                company_id=company_id,
            ),
        }, 200

class ProjectTaskCollaboratorListResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id, task_id):
        """List collaborators and their hours for a task."""
        from models.project import ProjectActivityCollaborator
        collaborators = ProjectActivityCollaborator.query.filter_by(activity_id=task_id, is_deleted=False).all()
        return [c.to_dict() for c in collaborators], 200

    @permission_required('projects', 'view')
    def post(self, project_id, task_id):
        """Add or update a collaborator/hours for a task."""
        from models.project import ProjectActivityCollaborator
        from .project import get_request_company_id

        company_id = get_request_company_id() or _get_project_company_id(project_id)
        if not _user_can_create_task(company_id, project_id):
            return {"error": "Permission denied: edit on projects"}, 403
        try:
            data = request.get_json()
            employee_id = data.get('employee_id')
            role = data.get('role', 'executor')
            hours = float(data.get('hours', 0))
            notes = data.get('notes', '')

            if not employee_id:
                return {"error": "Employee ID is required"}, 400

            employee = _validate_company_employee(company_id, employee_id, required=True)
            if not employee:
                return {"error": "Colaborador inválido para a empresa informada."}, 400

            # Check if already exists for this role? Or just add a new entry (log style)
            # APP31 seems to treat this as a log of work.
            collaborator = ProjectActivityCollaborator(
                activity_id=task_id,
                employee_id=employee.id,
                role=role,
                worked_hours=hours,
                notes=notes
            )
            db.session.add(collaborator)
            
            # Update total worked_hours in ProjectTask
            task = ProjectTask.query.get(task_id)
            if task:
                total_worked = db.session.query(db.func.sum(ProjectActivityCollaborator.worked_hours)).filter_by(activity_id=task_id, is_deleted=False).scalar() or 0
                task.worked_hours = total_worked
            
            db.session.commit()
            return collaborator.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProjectTaskCollaboratorResource(Resource):
    @permission_required('projects', 'view')
    def delete(self, project_id, task_id, collaborator_id):
        """Delete a specific work log entry for a task."""
        from models.project import ProjectActivityCollaborator
        from .project import get_request_company_id

        company_id = get_request_company_id() or _get_project_company_id(project_id)
        if not _user_can_create_task(company_id, project_id):
            return {"error": "Permission denied: edit on projects"}, 403
        try:
            collab = ProjectActivityCollaborator.query.filter_by(
                id=collaborator_id, activity_id=task_id
            ).first_or_404()
            collab.is_deleted = True
            # Recalculate total hours
            task = ProjectTask.query.get(task_id)
            if task:
                from models import db as _db
                total_worked = _db.session.query(_db.func.sum(ProjectActivityCollaborator.worked_hours)).filter_by(
                    activity_id=task_id, is_deleted=False).scalar() or 0
                task.worked_hours = total_worked
            db.session.commit()
            return {"message": "Work log deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": PUBLIC_ERROR_MESSAGE}, 500

class ProjectTaskHoursSummaryResource(Resource):

    @permission_required('projects', 'view')
    def get(self, project_id, task_id):
        """Get summary of hours for a task."""
        from models.project import ProjectActivityCollaborator
        from .project import get_request_company_id
        company_id = get_request_company_id()
        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id, is_deleted=False)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()
        
        collaborators = ProjectActivityCollaborator.query.filter_by(activity_id=task_id, is_deleted=False).all()
        total_worked = sum(float(c.worked_hours) for c in collaborators)
        
        return {
            "success": True,
            "data": {
                "estimated_hours": float(task.estimated_hours) if task.estimated_hours else 0,
                "worked_hours": total_worked,
                "progress_percent": (total_worked / float(task.estimated_hours) * 100) if task.estimated_hours and float(task.estimated_hours) > 0 else 0,
                "collaborators": [c.to_dict() for c in collaborators]
            }
        }, 200

class ProjectAllTasksResource(Resource):
    @permission_required('projects', 'view')
    def get(self):
        """List all tasks for all projects in the active company."""
        from .project import get_request_company_id
        try:
            company_id = get_request_company_id()
            show_inactive = request.args.get('show_inactive', 'false').lower() == 'true'
            
            if not company_id:
                return [], 200
                
            # Efficiently fetch tasks for projects of the current company
            from models import Project
            query = ProjectTask.query.join(Project, ProjectTask.project_id == Project.id)\
                                     .filter(Project.company_id == company_id)
            
            if not show_inactive:
                query = query.filter(Project.status.not_in(['completed', 'cancelled', 'archived']))
                
            query = apply_task_employee_filter(query, company_id)
            tasks = query.order_by(ProjectTask.id.asc()).all()
            
            payload = project_tasks_schema.dump(tasks)
            backlog_project_id = _backlog_project_id()
            if backlog_project_id:
                from services.backlog_human_gate_service import build_backlog_human_gate_context_map

                backlog_task_ids = [
                    int(getattr(task, "id", 0) or 0)
                    for task in tasks
                    if int(getattr(task, "project_id", 0) or 0) == int(backlog_project_id)
                ]
                if backlog_task_ids:
                    context_map = build_backlog_human_gate_context_map(backlog_task_ids)
                    for item in payload:
                        task_context = context_map.get(int(item.get("id", 0) or 0))
                        if task_context:
                            item["backlog_human_gate"] = task_context

            return payload, 200
        except Exception as e:
            current_app.logger.exception("Erro ao listar todas as tarefas da empresa company_id=%s", company_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500
class ProjectTaskTransferResource(Resource):
    @permission_required('projects', 'edit')
    def post(self, project_id, task_id):
        """Transfer a task to another project."""
        from .project import get_request_company_id
        from flask_login import current_user

        company_id = get_request_company_id()
        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id, is_deleted=False)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()
        if _is_backlog_human_gate_task(task):
            return _build_backlog_human_gate_lock_response()
        try:
            data = request.get_json(force=True, silent=True) or {}
            target_project_id = data.get('target_project_id')
            note = data.get('note', '')

            if not target_project_id:
                return {"error": "Target project ID is required"}, 400

            result, error = ProjectTaskService.transfer_task(
                company_id=int(company_id),
                source_project_id=int(project_id),
                task_id=int(task_id),
                target_project_id=int(target_project_id),
                note=note,
                user_name=getattr(current_user, 'name', None),
            )
            if error:
                lowered_error = error.lower()
                if "não encontrada" in lowered_error or "não encontrado" in lowered_error:
                    return {"error": error}, 404
                if "empresa ativa" in lowered_error:
                    return {"error": error}, 403
                if "diferente" in lowered_error:
                    return {"error": error}, 400
                return {"error": error}, 400

            return {
                "success": True,
                "message": "Atividade transferida com sucesso",
                "new_code": result["new_code"],
            }, 200
        except Exception as exc:
            return log_and_build_public_error_response(
                current_app.logger,
                exc,
                context=(
                    "Erro ao transferir atividade "
                    f"task_id={task_id} projeto_origem={project_id} company_id={company_id}"
                ),
            )


class ProjectTaskDependencyListResource(Resource):
    """Gerencia dependências de uma atividade: predecessoras e sucessoras."""

    @permission_required('projects', 'view')
    def get(self, project_id, task_id):
        """Lista todas as dependências (predecessoras e sucessoras) de uma atividade."""
        from services.task_dependency_service import TaskDependencyService
        from .project import get_request_company_id

        company_id = get_request_company_id()
        if not company_id:
            return {"error": "Empresa ativa não identificada. Por favor, selecione uma empresa no portal."}, 401

        # Valida que a tarefa pertence ao projeto e empresa
        task = ProjectTask.query.filter_by(
            id=task_id, project_id=project_id, is_deleted=False
        ).first()
        if not task:
            return {"error": "Atividade não encontrada neste projeto."}, 404

        result = TaskDependencyService.get_task_dependencies(
            company_id=company_id,
            task_id=task_id,
        )
        return result, 200

    @permission_required('projects', 'edit')
    def post(self, project_id, task_id):
        """Adiciona uma dependência finish_to_start: predecessor_task_id → task_id (successor)."""
        from flask_login import current_user
        from services.task_dependency_service import TaskDependencyService
        from models.employee import Employee
        from .project import get_request_company_id

        company_id = get_request_company_id()
        if not company_id:
            return {"error": "Empresa ativa não identificada. Por favor, selecione uma empresa no portal."}, 401

        try:
            data = request.get_json(force=True, silent=True) or {}
            predecessor_task_id = data.get('predecessor_task_id')

            if not predecessor_task_id:
                return {"error": "O campo 'predecessor_task_id' é obrigatório."}, 400

            # Resolve o employee do usuário logado para auditoria
            employee = Employee.query.filter_by(
                user_id=current_user.id,
                company_id=company_id,
            ).first()
            employee_id = employee.id if employee else None

            # Conversão segura para int (suporta string floats "123.0")
            p_id = int(float(predecessor_task_id))
            s_id = int(float(task_id))

            result, error = TaskDependencyService.add_dependency(
                company_id=company_id,
                project_id=int(float(project_id)),
                predecessor_task_id=p_id,
                successor_task_id=s_id,
                created_by_employee_id=employee_id,
            )

            if error:
                return {"error": error}, 400

            return result, 201
        except Exception as e:
            current_app.logger.exception("Erro ao transferir tarefa task_id=%s projeto_origem=%s", task_id, project_id)
            return {"error": PUBLIC_ERROR_MESSAGE}, 500


class ProjectTaskDependencyResource(Resource):
    """Remove uma dependência específica."""

    @permission_required('projects', 'edit')
    def delete(self, project_id, task_id, dep_id):
        """Remove uma dependência de atividade."""
        from services.task_dependency_service import TaskDependencyService
        from .project import get_request_company_id

        company_id = get_request_company_id()
        if not company_id:
            return {"error": "Empresa ativa não identificada. Por favor, selecione uma empresa no portal."}, 401

        success, error = TaskDependencyService.remove_dependency(
            company_id=company_id,
            dep_id=int(float(dep_id)),
        )

        if not success:
            return {"error": error}, 404

        return {"message": "Dependência removida com sucesso."}, 200

