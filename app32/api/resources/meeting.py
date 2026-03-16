from flask import request, session
from flask_restful import Resource
from flask_login import login_required, current_user
from models import Meeting, MeetingAgendaItem, Project, Company, Employee, db
from utils.permissions import get_default_company_id, has_company_full_access
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)
PUBLIC_ERROR_MESSAGE = "Erro interno do servidor. Tente novamente ou contate o suporte."


def _parse_optional_int(value):
    try:
        if value in (None, '', []):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def user_can_access_company(company_id):
    if not company_id or not current_user.is_authenticated:
        return False

    company = Company.query.get(company_id)
    if not company or not bool(getattr(company, 'is_active', True)):
        return False

    if str(getattr(current_user, 'role', '')).strip().lower() in {'admin', 'administrator'}:
        return True

    employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id, status='active').first()
    return employee is not None


def get_request_company_id():
    """Resolve current company scope for meeting operations."""
    val = request.args.get('company_id')
    if val not in (None, ''):
        try:
            return int(float(val))
        except (TypeError, ValueError):
            pass

    payload = request.get_json(silent=True) if request.is_json else None
    if isinstance(payload, dict):
        val = payload.get('company_id')
        if val not in (None, ''):
            try:
                return int(float(val))
            except (TypeError, ValueError):
                pass

    cid = session.get('active_company_id')
    if cid not in (None, ''):
        try:
            return int(float(cid))
        except (TypeError, ValueError):
            pass

    if current_user.is_authenticated:
        employee = Employee.query.filter_by(user_id=current_user.id, status='active').first()
        if employee:
            return employee.company_id

        default_company_id = get_default_company_id()
        if default_company_id:
            return default_company_id

    return None


def get_meeting_or_404(meeting_id):
    company_id = get_request_company_id()
    if not company_id:
        return None, ({"success": False, "message": "Contexto de empresa ativo é obrigatório."}, 400)

    if not user_can_access_company(company_id):
        return None, ({"success": False, "message": "Você não tem acesso à empresa informada."}, 403)

    meeting = Meeting.query.filter_by(id=meeting_id, company_id=company_id).first()
    if not meeting:
        return None, ({"success": False, "message": "Reunião não encontrada para a empresa informada."}, 404)

    return meeting, None

class MeetingListResource(Resource):
    @login_required
    def post(self, company_id):
        """Create a new meeting (draft)"""
        if not user_can_access_company(company_id):
            return {"success": False, "message": "Você não tem acesso à empresa informada."}, 403

        data = request.get_json()
        if not data:
            return {"success": False, "message": "No data provided"}, 400
            
        try:
            meeting = Meeting(
                company_id=company_id,
                title=data.get('title'),
                scheduled_date=datetime.strptime(data.get('scheduled_date'), '%Y-%m-%d').date() if data.get('scheduled_date') else None,
                scheduled_time=data.get('scheduled_time'),
                planned_duration_minutes=_parse_optional_int(data.get('planned_duration_minutes')),
                invite_notes=data.get('invite_notes'),
                guests_json=json.dumps(data.get('guests', {})),
                agenda_json=json.dumps(data.get('agenda', [])),
                status='draft'
            )
            db.session.add(meeting)
            db.session.commit()
            
            return {
                "success": True, 
                "message": "Reunião criada com sucesso!", 
                "meeting_id": meeting.id
            }, 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating meeting: {e}")
            return {"success": False, "message": PUBLIC_ERROR_MESSAGE}, 500

class MeetingResource(Resource):
    @login_required
    def get(self, meeting_id):
        """Get meeting details"""
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response
        return {"success": True, "meeting": meeting.to_dict()}

    @login_required
    def put(self, meeting_id):
        """Update meeting details (preliminares)"""
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response
        data = request.get_json()
        
        try:
            if 'title' in data: meeting.title = data['title']
            if 'scheduled_date' in data: 
                meeting.scheduled_date = datetime.strptime(data['scheduled_date'], '%Y-%m-%d').date() if data['scheduled_date'] else None
            if 'scheduled_time' in data: meeting.scheduled_time = data['scheduled_time']
            if 'planned_duration_minutes' in data: meeting.planned_duration_minutes = _parse_optional_int(data.get('planned_duration_minutes'))
            if 'invite_notes' in data: meeting.invite_notes = data['invite_notes']
            if 'guests' in data: meeting.guests_json = json.dumps(data['guests'])
            if 'agenda' in data: meeting.agenda_json = json.dumps(data['agenda'])
            
            db.session.commit()
            return {"success": True, "message": "Dados atualizados!"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": PUBLIC_ERROR_MESSAGE}, 500

    @login_required
    def delete(self, meeting_id):
        """Delete a meeting"""
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response
        try:
            db.session.delete(meeting)
            db.session.commit()
            return {"success": True, "message": "Reunião excluída com sucesso!"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": PUBLIC_ERROR_MESSAGE}, 500

class MeetingExecutionResource(Resource):
    @login_required
    def put(self, meeting_id):
        """Save meeting execution data"""
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response
        data = request.get_json()
        
        try:
            if 'actual_date' in data: 
                meeting.actual_date = datetime.strptime(data['actual_date'], '%Y-%m-%d').date() if data['actual_date'] else None
            if 'actual_time' in data: meeting.actual_time = data['actual_time']
            if 'actual_duration_minutes' in data: meeting.actual_duration_minutes = _parse_optional_int(data.get('actual_duration_minutes'))
            if 'notes' in data: meeting.meeting_notes = data['notes']
            if 'meeting_notes' in data: meeting.meeting_notes = data['meeting_notes']
            if 'participants' in data: meeting.participants_json = json.dumps(data['participants'])
            if 'discussions' in data: meeting.discussions_json = json.dumps(data['discussions'])
            if 'activities' in data: meeting.activities_json = json.dumps(data['activities'])
            
            db.session.commit()
            return {"success": True, "message": "Execução salva!"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": PUBLIC_ERROR_MESSAGE}, 500

class MeetingStartResource(Resource):
    @login_required
    def post(self, meeting_id):
        """Start meeting and link/create project"""
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response
        data = request.get_json() or {}
        project_type = data.get("project_type", "new")
        chosen_project_id = data.get("project_id")
        
        try:
            actual_date = datetime.now()
            meeting.actual_date = actual_date.date()
            meeting.actual_time = actual_date.strftime("%H:%M")
            if meeting.actual_duration_minutes is None:
                meeting.actual_duration_minutes = meeting.planned_duration_minutes
            meeting.status = 'in_progress'
            
            # Linking logic
            if not meeting.project_id:
                if project_type == "existing" and chosen_project_id:
                    project = Project.query.filter_by(id=int(chosen_project_id), company_id=meeting.company_id).first()
                    if not project:
                        return {"success": False, "message": "Projeto informado não pertence à empresa da reunião."}, 404
                    meeting.project_id = project.id
                else:
                    # Create new project
                    display_date = meeting.actual_date.strftime("%d/%m/%Y")
                    project_title = f"Reunião - {meeting.title} ({display_date})"
                    
                    new_project = Project(
                        company_id=meeting.company_id,
                        name=project_title,
                        status="in_progress",
                        priority="medium",
                        owner="Sistema",
                        deadline=meeting.actual_date,
                        notes=f"Projeto gerado automaticamente para a reunião: {meeting.title}\n\nProjeto vinculado a reunião ID {meeting.id}"
                    )
                    db.session.add(new_project)
                    db.session.flush() # To get ID
                    meeting.project_id = new_project.id
            
            db.session.commit()
            
            project = Project.query.get(meeting.project_id) if meeting.project_id else None
            
            return {
                "success": True,
                "message": "Reunião iniciada!",
                "project_id": meeting.project_id,
                "project_title": project.name if project else None,
                "actual_date": meeting.actual_date.isoformat(),
                "actual_time": meeting.actual_time
            }
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error starting meeting: {e}")
            return {"success": False, "message": PUBLIC_ERROR_MESSAGE}, 500

class MeetingFinishResource(Resource):
    @login_required
    def post(self, meeting_id):
        """Finalize meeting and create summary task in project"""
        from models import ProjectTask
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response
        try:
            meeting.status = 'completed'
            
            # Create summary task in project
            if meeting.project_id:
                try:
                    task_title = f"Resumo da Reunião: {meeting.title}"
                    task_desc = f"Atas da reunião (ID: {meeting.id})\n\n"
                    
                    discussions = json.loads(meeting.discussions_json or "[]")
                    if discussions:
                        task_desc += "Principais Deliberações:\n"
                        for d in discussions:
                            task_desc += f"- {d.get('title', 'Tópico')}: {d.get('discussion', '')}\n"
                    
                    summary_task = ProjectTask(
                        project_id=meeting.project_id,
                        what=task_title,
                        how=task_desc,
                        status="completed",
                        due_date=datetime.utcnow().date(),
                        priority="low"
                    )
                    db.session.add(summary_task)
                except Exception as ex:
                    logger.error(f"Erro ao criar tarefa resumo: {ex}")
            
            db.session.commit()
            return {"success": True, "message": "Reunião finalizada e resumida no projeto!"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": PUBLIC_ERROR_MESSAGE}, 500

class MeetingAgendaUseResource(Resource):
    @login_required
    def post(self, item_id):
        """Track usage of agenda item"""
        item = MeetingAgendaItem.query.get_or_404(item_id)
        try:
            item.usage_count = (item.usage_count or 0) + 1
            db.session.commit()
            return {"success": True}
        except Exception as e:
            db.session.rollback()
            return {"success": False}, 500

class MeetingActivitiesResource(Resource):
    @login_required
    def get(self, meeting_id):
        """Get all activities related to this meeting (from multiple possible projects)"""
        from models import ProjectTask, Project
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response
        
        # 1. Activities stored in the meeting JSON (planned)
        meeting_activities = []
        try:
            meeting_activities = json.loads(meeting.activities_json or "[]")
        except:
            pass

        # 2. Activities already created in projects
        project_activities = []
        if meeting.project_id:
            tasks = ProjectTask.query.filter_by(project_id=meeting.project_id).all()
            for t in tasks:
                d = t.to_dict()
                # Map fields to match what the frontend expects
                d['title'] = t.what
                d['responsible'] = t.who or t.employee_name
                d['deadline'] = t.due_date.isoformat() if t.due_date else None
                project_activities.append(d)

        # 3. Project details
        project = Project.query.get(meeting.project_id) if meeting.project_id else None
        
        return {
            "success": True,
            "meeting_activities": meeting_activities,
            "project_activities": project_activities,
            "project_id": meeting.project_id,
            "project_title": project.name if project else None
        }

class MeetingSyncCheckResource(Resource):
    @login_required
    def get(self, meeting_id):
        """Check if meeting activities are in sync with the linked project"""
        from models import ProjectTask
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response
        
        if not meeting.project_id:
            return {"success": True, "is_synced": False, "message": "Sem projeto vinculado", 
                    "meeting_count": 0, "project_count": 0, "missing_in_project": [], "extra_in_project": []}
        
        try:
            m_acts = json.loads(meeting.activities_json or "[]")
        except:
            m_acts = []
            
        p_tasks = ProjectTask.query.filter_by(project_id=meeting.project_id).all()
        
        m_titles = [a.get('title') for a in m_acts if a.get('title')]
        p_titles = [t.what for t in p_tasks]
        
        missing = [t for t in m_titles if t not in p_titles]
        extra = [t for t in p_titles if t not in m_titles]
        
        return {
            "success": True,
            "is_synced": len(missing) == 0 and len(extra) == 0,
            "meeting_count": len(m_titles),
            "project_count": len(p_titles),
            "missing_in_project": missing,
            "extra_in_project": extra
        }

class MeetingSyncActivitiesResource(Resource):
    @login_required
    def post(self, meeting_id):
        """Sync meeting activities with the project by creating missing ones"""
        from models import ProjectTask, Project
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response
        data = request.get_json() or {}
        
        if not meeting.project_id:
            # Optionally create project if not exists
            return {"success": False, "message": "Inicie a reunião primeiro para vincular um projeto"}, 400

        try:
            m_acts = data.get('activities', [])
            p_tasks = ProjectTask.query.filter_by(project_id=meeting.project_id).all()
            p_titles = [t.what for t in p_tasks]
            
            created_count = 0
            for act in m_acts:
                title = act.get('title')
                if not title: continue
                
                if title not in p_titles:
                    try:
                        due_date = datetime.strptime(act.get('deadline'), '%Y-%m-%d').date() if act.get('deadline') else None
                    except:
                        due_date = None
                        
                    task = ProjectTask(
                        project_id=meeting.project_id,
                        what=title,
                        how=act.get('how', ''),
                        who=act.get('responsible'),
                        employee_id=act.get('employee_id'),
                        due_date=due_date,
                        status='not_started',
                        priority='medium'
                    )
                    db.session.add(task)
                    created_count += 1
            
            # Update meeting itself
            if 'meeting_notes' in data: meeting.meeting_notes = data['meeting_notes']
            if 'participants' in data: meeting.participants_json = json.dumps(data['participants'])
            if 'discussions' in data: meeting.discussions_json = json.dumps(data['discussions'])
            if 'activities' in data: meeting.activities_json = json.dumps(data['activities'])
            if 'actual_duration_minutes' in data: meeting.actual_duration_minutes = _parse_optional_int(data.get('actual_duration_minutes'))
            if 'planned_duration_minutes' in data: meeting.planned_duration_minutes = _parse_optional_int(data.get('planned_duration_minutes'))
            if 'status' in data: meeting.status = data['status']
            
            db.session.commit()
            
            project = Project.query.get(meeting.project_id)
            return {
                "success": True, 
                "message": f"Sincronização concluída. {created_count} novas atividades criadas.",
                "synced_count": created_count,
                "project_id": meeting.project_id,
                "project_title": project.name if project else None
            }
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": PUBLIC_ERROR_MESSAGE}, 500

class MeetingRemoveFromProjectResource(Resource):
    @login_required
    def post(self, meeting_id):
        """Remove a specific activity/task from the project"""
        from models import ProjectTask
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response
        data = request.get_json() or {}
        title = data.get('title')
        
        if not title or not meeting.project_id:
            return {"success": False, "message": "Título ou Projeto não identificado"}, 400
            
        try:
            task = ProjectTask.query.filter_by(project_id=meeting.project_id, what=title).first()
            if task:
                db.session.delete(task)
                db.session.commit()
                return {"success": True, "message": "Atividade removida do projeto"}
            return {"success": True, "message": "Atividade não encontrada no projeto"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": PUBLIC_ERROR_MESSAGE}, 500
