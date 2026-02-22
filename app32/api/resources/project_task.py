from flask import request
from flask_restful import Resource
from marshmallow import ValidationError
from models import db, ProjectTask, Project
from schemas.project import project_task_schema, project_tasks_schema
from utils.permissions import permission_required
from datetime import datetime

class ProjectTaskListResource(Resource):
    @permission_required('projects', 'view')
    def get(self, project_id):
        """List all tasks for a project."""
        tasks = ProjectTask.query.filter_by(project_id=project_id).order_by(ProjectTask.id.asc()).all()
        return project_tasks_schema.dump(tasks), 200

    @permission_required('projects', 'edit')
    def post(self, project_id):
        """Create a new task for a project."""
        try:
            data = request.get_json()
            data['project_id'] = project_id
            
            # Basic validation check
            if not data.get('what'):
                return {"error": "Description is required"}, 400
                
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
        task = ProjectTask.query.filter_by(id=task_id, project_id=project_id).first_or_404()
        return project_task_schema.dump(task), 200

    @permission_required('projects', 'edit')
    def put(self, project_id, task_id):
        """Update a task."""
        task = ProjectTask.query.filter_by(id=task_id, project_id=project_id).first_or_404()
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
        task = ProjectTask.query.filter_by(id=task_id, project_id=project_id).first_or_404()
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
        task = ProjectTask.query.filter_by(id=task_id, project_id=project_id).first_or_404()
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
        task = ProjectTask.query.filter_by(id=task_id, project_id=project_id).first_or_404()
        
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
            print(f"DEBUG: ProjectAllTasksResource.get - company_id: {company_id}")
            if not company_id:
                return [], 200
                
            # Efficiently fetch tasks for projects of the current company
            from models import Project
            tasks = ProjectTask.query.join(Project, ProjectTask.project_id == Project.id)\
                                     .filter(Project.company_id == company_id)\
                                     .order_by(ProjectTask.id.asc()).all()
            
            print(f"DEBUG: ProjectAllTasksResource.get - found {len(tasks)} tasks")
            return project_tasks_schema.dump(tasks), 200
        except Exception as e:
            import traceback
            print("ERROR in ProjectAllTasksResource:", str(e))
            print(traceback.format_exc())
            return {"error": str(e)}, 500
