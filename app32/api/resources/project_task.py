from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
from models import db, ProjectTask, Project
from schemas.project import project_task_schema, project_tasks_schema
from utils.permissions import permission_required
from datetime import datetime

def apply_task_employee_filter(query, company_id):
    from flask_login import current_user
    from models.employee import Employee
    from models.project import ProjectTask, ProjectActivityCollaborator
    from sqlalchemy import or_
    
    if not current_user.is_authenticated:
        return query

    # Admin e Client veem todas as tarefas
    if current_user.role in ('admin', 'client'):
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

class ProjectTaskListResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id):
        """List all tasks for a project with dependency status."""
        from flask import session
        from services.task_dependency_service import TaskDependencyService
        from models.project import ProjectTaskDependency

        from .project import get_request_company_id
        company_id = get_request_company_id()
            
        query = ProjectTask.query.filter_by(project_id=project_id).order_by(ProjectTask.id.asc())
        query = apply_task_employee_filter(query, company_id)
        tasks = query.all()
        dumped_tasks = project_tasks_schema.dump(tasks)
        
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

    @permission_required('projects', 'edit')
    def post(self, project_id):
        """Create a new task for a project."""
        try:
            data = request.get_json()
            data['project_id'] = project_id
            
            # Basic validation check
            if not data.get('what'):
                return {"error": "Description is required"}, 400
            
            # Garantir sincronia status/stage na criação
            if data.get('stage') == 'completed':
                data['status'] = 'completed'
            elif data.get('stage') == 'inbox' or data.get('stage') == 'todo':
                data['status'] = 'planned'
                if data.get('stage') == 'todo': data['stage'] = 'inbox'
            
            task = project_task_schema.load(data)
            db.session.add(task)
            
            # Update project progress
            project = Project.query.get(project_id)
            if project:
                project.update_progress()
                
            db.session.commit()
            return project_task_schema.dump(task), 201
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ProjectTaskResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id, task_id):
        """Get a single task."""
        from .project import get_request_company_id
        company_id = get_request_company_id()
        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()
        return project_task_schema.dump(task), 200

    @permission_required('projects', 'edit')
    def put(self, project_id, task_id):
        """Update a task."""
        from .project import get_request_company_id
        company_id = get_request_company_id()
        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()
        try:
            data = request.get_json()
            
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
            return project_task_schema.dump(task), 200
        except ValidationError as err:
            return {"errors": err.messages}, 400
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    @permission_required('projects', 'edit')
    def patch(self, project_id, task_id):
        """Partial update (e.g. for stage moves)."""
        return self.put(project_id, task_id)

    @permission_required('projects', 'edit')
    def delete(self, project_id, task_id):
        """Delete a task."""
        from .project import get_request_company_id
        company_id = get_request_company_id()
        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()
        try:
            db.session.delete(task)
            
            # Update project progress
            project = Project.query.get(project_id)
            if project:
                project.update_progress()
                
            db.session.commit()
            return {"message": "Task deleted successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ProjectTaskStageResource(Resource):
    @permission_required('projects', 'edit')
    def patch(self, project_id, task_id):
        """Update task stage (Kanban drag & drop)."""
        from .project import get_request_company_id
        company_id = get_request_company_id()
        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()
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
            return project_task_schema.dump(task), 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

class ProjectTaskCollaboratorListResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id, task_id):
        """List collaborators and their hours for a task."""
        from models.project import ProjectActivityCollaborator
        collaborators = ProjectActivityCollaborator.query.filter_by(activity_id=task_id, is_deleted=False).all()
        return [c.to_dict() for c in collaborators], 200

    @permission_required('projects', 'edit')
    def post(self, project_id, task_id):
        """Add or update a collaborator/hours for a task."""
        from models.project import ProjectActivityCollaborator
        try:
            data = request.get_json()
            employee_id = data.get('employee_id')
            role = data.get('role', 'executor')
            hours = float(data.get('hours', 0))
            notes = data.get('notes', '')

            if not employee_id:
                return {"error": "Employee ID is required"}, 400

            # Check if already exists for this role? Or just add a new entry (log style)
            # APP31 seems to treat this as a log of work.
            collaborator = ProjectActivityCollaborator(
                activity_id=task_id,
                employee_id=employee_id,
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
            return {"error": str(e)}, 500

class ProjectTaskCollaboratorResource(Resource):
    @permission_required('projects', 'edit')
    def delete(self, project_id, task_id, collaborator_id):
        """Delete a specific work log entry for a task."""
        from models.project import ProjectActivityCollaborator
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
            return {"error": str(e)}, 500

class ProjectTaskHoursSummaryResource(Resource):

    @permission_required('projects', 'view')
    def get(self, project_id, task_id):
        """Get summary of hours for a task."""
        from models.project import ProjectActivityCollaborator
        from .project import get_request_company_id
        company_id = get_request_company_id()
        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id)
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
            
            return project_tasks_schema.dump(tasks), 200
        except Exception as e:
            import traceback
            print("ERROR in ProjectAllTasksResource:", str(e))
            print(traceback.format_exc())
            return {"error": str(e)}, 500
class ProjectTaskTransferResource(Resource):
    @permission_required('projects', 'edit')
    def post(self, project_id, task_id):
        """Transfer a task to another project."""
        from .project import get_request_company_id
        company_id = get_request_company_id()
        query = ProjectTask.query.filter_by(id=task_id, project_id=project_id)
        query = apply_task_employee_filter(query, company_id)
        task = query.first_or_404()
        data = request.get_json()
        target_project_id = data.get('target_project_id')
        note = data.get('note', '')

        if not target_project_id:
            return {"error": "Target project ID is required"}, 400
        
        if int(target_project_id) == int(project_id):
            return {"error": "Target project must be different from current project"}, 400

        target_project = Project.query.get(target_project_id)
        if not target_project:
            return {"error": "Target project not found"}, 404

        # Verify target project belongs to the same company
        current_project = Project.query.get(project_id)
        if target_project.company_id != current_project.company_id:
             return {"error": "Target project must belong to the same company"}, 403

        # Update task
        old_project_name = current_project.name
        new_project_name = target_project.name
        
        task.project_id = target_project_id
        task.stage = 'inbox' # Reset to inbox as per legacy requirements
        task.status = 'planned'
        
        # Log the transfer
        if not task.logs:
            task.logs = []
        
        from flask_login import current_user
        user_name = current_user.name if hasattr(current_user, 'name') else "Usuário"
        
        transfer_log = {
            "timestamp": datetime.now().isoformat(),
            "text": f"Atividade transferida de '{old_project_name}' para '{new_project_name}'",
            "type": "transfer",
            "note": note,
            "old_project_id": project_id,
            "new_project_id": target_project_id,
            "user_name": user_name
        }
        
        # Ensure task.logs is a list and append
        current_logs = list(task.logs) if task.logs else []
        current_logs.append(transfer_log)
        task.logs = current_logs

        try:
            db.session.commit()
            # Update both projects progress
            current_project.update_progress()
            target_project.update_progress()
            db.session.commit()
            
            return {"success": True, "message": "Atividade transferida com sucesso"}, 200
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return {"error": str(e)}, 500


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
            id=task_id, project_id=project_id
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
            import traceback
            traceback.print_exc()
            return {"error": f"Erro interno ao processar dependência: {str(e)}"}, 500


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

