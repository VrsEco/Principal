from flask import request, jsonify
from flask_restful import Resource
from models import db, Project, Company
from models.workflow_gap import WorkflowGapCandidate
from schemas.project import project_schema, projects_schema
from utils.permissions import get_default_company_id, has_company_full_access, has_permission, is_platform_admin, permission_required


def _get_current_company_employee(company_id):
    from flask_login import current_user
    from models.employee import Employee

    if not current_user.is_authenticated or not company_id:
        return None
    return Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()


def _task_is_visible_to_employee(task, employee_id):
    if not task or not employee_id:
        return False
    if task.employee_id == employee_id:
        return True
    for collaborator in getattr(task, 'collaborators', []) or []:
        if getattr(collaborator, 'is_deleted', False):
            continue
        if collaborator.employee_id == employee_id:
            return True
    return False


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


def _get_project_with_access(project_id, action='view'):
    company_id = get_request_company_id()
    if not company_id:
        return None, None

    query = Project.query.filter_by(id=project_id, company_id=company_id)
    query = apply_project_employee_filter(query, company_id)
    return query.first_or_404(), company_id


def _get_task_with_access(project_id, task_id, action='view'):
    from models.project import ProjectTask

    project, company_id = _get_project_with_access(project_id, action='view')
    if not project:
        return None, None, None

    task = ProjectTask.query.filter_by(project_id=project.id, id=task_id).first_or_404()

    if has_company_full_access(company_id):
        return task, project, company_id

    employee = _get_current_company_employee(company_id)
    if not employee or not _task_is_visible_to_employee(task, employee.id):
        return None, project, company_id

    return task, project, company_id

def get_request_company_id():
    from flask import session
    from flask_login import current_user
    
    # 1. Try Query Arg
    val = request.args.get('company_id')
    if val:
        try:
            return int(float(val))
        except Exception:
            pass
            
    # 2. Try session
    cid = session.get('active_company_id')
    if cid:
        return int(cid)
        
    # 3. Try current_user
    if current_user.is_authenticated:
        default_company_id = get_default_company_id()
        if default_company_id:
            return default_company_id
            
    return None

def apply_project_employee_filter(query, company_id):
    from flask_login import current_user
    from models.employee import Employee
    from models.project import Project, ProjectTask, ProjectActivityCollaborator
    from sqlalchemy import or_
    
    if not current_user.is_authenticated:
        return query

    if has_company_full_access(company_id):
        return query

    # Colaborador: só projetos onde tem atividades atribuídas
    employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
    if employee:
        return query.filter(
            Project.tasks.any(
                or_(
                    ProjectTask.employee_id == employee.id,
                    ProjectTask.collaborators.any(ProjectActivityCollaborator.employee_id == employee.id)
                )
            )
        )
        
    return query

class ProjectListResource(Resource):
    @permission_required('projects', 'view')
    def get(self):
        """List all projects, optionally filtered by company_id, plan_id, and inactive status."""
        company_id = get_request_company_id()
        plan_id = request.args.get('plan_id', type=int)
        show_inactive = request.args.get('show_inactive', 'false').lower() == 'true'
        
        if not company_id:
            return [], 200
            
        query = Project.query.filter_by(company_id=company_id).order_by(Project.id.asc())
        query = apply_project_employee_filter(query, company_id)
        
        if not show_inactive:
            query = query.filter(Project.status.not_in(['completed', 'cancelled', 'archived']))
            
        if plan_id:
            query = query.filter_by(plan_id=plan_id)
            
        projects = query.all()
        return projects_schema.dump(projects), 200

    @permission_required('projects', 'create')
    def post(self):
        """Create a new project."""
        company_id = get_request_company_id()
        if not has_company_full_access(company_id):
            return {"message": "Acesso negado: colaboradores não podem criar projetos."}, 403
        data = request.get_json()
        new_project = Project(
            company_id=company_id,
            name=data['name'],
            plan_id=data.get('plan_id'),
            owner=data.get('owner'),
            status=data.get('status', 'planned'),
            deadline=data.get('deadline'),
            budget=data.get('budget'),
            notes=data.get('notes'),
            priority=data.get('priority', 'medium'),
            portfolio_id=data.get('portfolio_id')
        )
        db.session.add(new_project)
        db.session.commit()
        return project_schema.dump(new_project), 201

class ProjectResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id):
        """Get a specific project by ID."""
        project, company_id = _get_project_with_access(project_id, action='view')
        if not company_id:
            return {"message": "Active company context required"}, 400
        return project_schema.dump(project), 200

    @permission_required('projects', 'edit')
    def put(self, project_id):
        """Update an existing project."""
        project, company_id = _get_project_with_access(project_id, action='edit')
        if not company_id:
            return {"message": "Active company context required"}, 400
        if not has_company_full_access(company_id):
            return {"message": "Acesso negado: colaboradores não podem editar projetos."}, 403
        data = request.get_json()
        
        project.name = data.get('name', project.name)
        project.plan_id = data.get('plan_id', project.plan_id)
        project.owner = data.get('owner', project.owner)
        project.status = data.get('status', project.status)
        project.deadline = data.get('deadline', project.deadline)
        project.budget = data.get('budget', project.budget)
        project.notes = data.get('notes', project.notes)
        project.priority = data.get('priority', project.priority)
        project.portfolio_id = data.get('portfolio_id', project.portfolio_id)
        
        db.session.commit()
        return project_schema.dump(project), 200

    @permission_required('projects', 'delete')
    def delete(self, project_id):
        """Delete a project."""
        project, company_id = _get_project_with_access(project_id, action='delete')
        if not company_id:
            return {"message": "Active company context required"}, 400
        if not has_company_full_access(company_id):
            return {"message": "Acesso negado: colaboradores não podem excluir projetos."}, 403
        db.session.delete(project)
        db.session.commit()
        return '', 204

class ProjectTaskListResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id):
        """List all tasks for a project."""
        from flask_login import current_user
        from models.employee import Employee
        from models.project import ProjectTask, ProjectActivityCollaborator
        from schemas.project import project_tasks_schema
        from sqlalchemy import or_
        company_id = get_request_company_id()
        if not company_id:
            return [], 200

        project_query = Project.query.filter_by(id=project_id, company_id=company_id)
        project_query = apply_project_employee_filter(project_query, company_id)
        project = project_query.first_or_404()

        tasks_query = ProjectTask.query.filter_by(project_id=project.id)

        if not has_company_full_access(company_id):
            employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
            if not employee:
                return [], 200
            tasks_query = tasks_query.filter(
                or_(
                    ProjectTask.employee_id == employee.id,
                    ProjectTask.collaborators.any(ProjectActivityCollaborator.employee_id == employee.id)
                )
            )

        tasks = tasks_query.all()
        return project_tasks_schema.dump(tasks), 200

    @permission_required('projects', 'edit')
    def post(self, project_id):
        """Add a new task to a project."""
        from models.project import ProjectTask
        from schemas.project import project_task_schema
        project, company_id = _get_project_with_access(project_id, action='edit')
        if not project:
            return {"message": "Projeto não encontrado no contexto ativo."}, 404
        if not has_company_full_access(company_id):
            return {"message": "Acesso negado: colaboradores não podem criar atividades."}, 403
        data = request.get_json()
        new_task = ProjectTask(
            project_id=project.id,
            what=data['what'],
            who=data.get('who'),
            employee_id=data.get('employee_id'),
            due_date=data.get('due_date'),
            how=data.get('how'),
            amount=data.get('amount'),
            status=data.get('status', 'planned'),
            stage=data.get('stage', 'inbox'),
            priority=data.get('priority', 'normal'),
            notes=data.get('notes')
        )
        db.session.add(new_task)
        db.session.commit()
        return project_task_schema.dump(new_task), 201

class ProjectTaskResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id, task_id):
        """Get a specific project task."""
        from schemas.project import project_task_schema
        task, _, _ = _get_task_with_access(project_id, task_id, action='view')
        if not task:
            return {"message": "Acesso negado à atividade."}, 403
        return project_task_schema.dump(task), 200

    @permission_required('projects', 'edit')
    def put(self, project_id, task_id):
        """Update a project task."""
        from schemas.project import project_task_schema
        task, _, _ = _get_task_with_access(project_id, task_id, action='edit')
        if not task:
            return {"message": "Acesso negado à atividade."}, 403
        data = request.get_json()
        
        task.what = data.get('what', task.what)
        task.who = data.get('who', task.who)
        task.employee_id = data.get('employee_id', task.employee_id)
        task.due_date = data.get('due_date', task.due_date)
        task.how = data.get('how', task.how)
        task.amount = data.get('amount', task.amount)
        task.status = data.get('status', task.status)
        task.stage = data.get('stage', task.stage)
        task.priority = data.get('priority', task.priority)
        task.notes = data.get('notes', task.notes)
        
        # Update completion date if stage becomes 'completed'
        if task.stage == 'completed' and not task.completion_date:
            from datetime import datetime
            task.completion_date = datetime.now().date()
        
        # Log entry if provided
        if 'new_log' in data:
            if not task.logs: task.logs = []
            from datetime import datetime
            task.logs.append({
                "date": datetime.now().isoformat(),
                "text": data['new_log']
            })
            
        db.session.commit()
        return project_task_schema.dump(task), 200

    @permission_required('projects', 'edit')
    def delete(self, project_id, task_id):
        """Delete a project task."""
        task, _, company_id = _get_task_with_access(project_id, task_id, action='delete')
        if not task:
            return {"message": "Acesso negado à atividade."}, 403
        if not has_company_full_access(company_id):
            return {"message": "Acesso negado: colaboradores não podem excluir atividades."}, 403
        _detach_workflow_gap_candidates_for_task(
            task_id=task.id,
            project_id=task.project_id,
            company_id=company_id,
        )
        db.session.delete(task)
        db.session.commit()
        return '', 204

class ProjectTaskStageResource(Resource):
    @permission_required('projects', 'edit')
    def patch(self, project_id, task_id):
        """Update only the stage of a task."""
        from schemas.project import project_task_schema
        task, _, company_id = _get_task_with_access(project_id, task_id, action='edit')
        if not task:
            return {"message": "Acesso negado à atividade."}, 403
        if not has_company_full_access(company_id):
            return {"message": "Acesso negado: colaboradores não podem editar atividades completas."}, 403
        data = request.get_json()
        
        if 'stage' in data:
            task.stage = data['stage']
            if task.stage == 'completed' and not task.completion_date:
                from datetime import datetime
                task.completion_date = datetime.now().date()
            db.session.commit()
            
        return project_task_schema.dump(task), 200

class ProjectTaskCollaboratorListResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id, task_id):
        from models.project import ProjectActivityCollaborator
        from schemas.project import project_activity_collaborator_schema
        task, _, _ = _get_task_with_access(project_id, task_id, action='view')
        if not task:
            return {"message": "Acesso negado à atividade."}, 403
        collaborators = ProjectActivityCollaborator.query.filter_by(activity_id=task_id, is_deleted=False).all()
        return project_activity_collaborator_schema.dump(collaborators, many=True), 200

    @permission_required('projects', 'edit')
    def post(self, project_id, task_id):
        from models.project import ProjectActivityCollaborator
        from schemas.project import project_activity_collaborator_schema
        task, _, company_id = _get_task_with_access(project_id, task_id, action='edit')
        if not task:
            return {"message": "Acesso negado à atividade."}, 403
        if not has_company_full_access(company_id):
            return {"message": "Acesso negado: colaboradores não podem alterar alocação da atividade."}, 403
        data = request.get_json()
        new_collab = ProjectActivityCollaborator(
            activity_id=task_id,
            employee_id=data['employee_id'],
            role=data.get('role', 'executor'),
            notes=data.get('notes')
        )
        db.session.add(new_collab)
        db.session.commit()
        return project_activity_collaborator_schema.dump(new_collab), 201

class ProjectTaskCollaboratorResource(Resource):
    @permission_required('projects', 'edit')
    def delete(self, project_id, task_id, collaborator_id):
        from models.project import ProjectActivityCollaborator
        _, _, company_id = _get_task_with_access(project_id, task_id, action='edit')
        if not company_id:
            return {"message": "Projeto não encontrado no contexto ativo."}, 404
        if not has_company_full_access(company_id):
            return {"message": "Acesso negado: colaboradores não podem alterar alocação da atividade."}, 403
        collab = ProjectActivityCollaborator.query.filter_by(activity_id=task_id, id=collaborator_id).first_or_404()
        collab.is_deleted = True
        db.session.commit()
        return '', 204

class ProjectTaskHoursSummaryResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id, task_id):
        from models.project import ProjectTaskHoursSummary
        task, _, _ = _get_task_with_access(project_id, task_id, action='view')
        if not task:
            return {"message": "Acesso negado à atividade."}, 403
        summary = ProjectTaskHoursSummary.query.filter_by(task_id=task_id).first()
        if not summary:
            return {"total_estimated_hours": 0, "total_worked_hours": 0}, 200
        return {
            "total_estimated_hours": float(summary.total_estimated_hours),
            "total_worked_hours": float(summary.total_worked_hours)
        }, 200

class ProjectAllTasksResource(Resource):
    @permission_required('projects', 'view')
    def get(self):
        """List all tasks across all projects for a company, or all tasks if missing company context."""
        from flask_login import current_user
        from models.employee import Employee
        from models.project import Project, ProjectTask, ProjectActivityCollaborator
        from schemas.project import project_tasks_schema
        from sqlalchemy import or_

        company_id = get_request_company_id()
        if company_id:
            query = ProjectTask.query.join(Project).filter(Project.company_id == company_id)

            if not has_company_full_access(company_id):
                employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
                if not employee:
                    return [], 200
                query = query.filter(
                    or_(
                        ProjectTask.employee_id == employee.id,
                        ProjectTask.collaborators.any(ProjectActivityCollaborator.employee_id == employee.id)
                    )
                )

            tasks = query.all()
        else:
            # Fallback for admins with no context: all tasks
            if is_platform_admin():
                tasks = ProjectTask.query.all()
            else:
                return [], 200

        return project_tasks_schema.dump(tasks), 200
