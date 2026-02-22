from flask import request
from flask_restful import Resource
from flask_login import login_required, current_user
from models import Meeting, MeetingAgendaItem, Project, db
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class MeetingListResource(Resource):
    @login_required
    def post(self, company_id):
        """Create a new meeting (draft)"""
        data = request.get_json()
        if not data:
            return {"success": False, "message": "No data provided"}, 400
            
        try:
            meeting = Meeting(
                company_id=company_id,
                title=data.get('title'),
                scheduled_date=datetime.strptime(data.get('scheduled_date'), '%Y-%m-%d').date() if data.get('scheduled_date') else None,
                scheduled_time=data.get('scheduled_time'),
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
            return {"success": False, "message": str(e)}, 500

class MeetingResource(Resource):
    @login_required
    def get(self, meeting_id):
        """Get meeting details"""
        meeting = Meeting.query.get_or_404(meeting_id)
        return {"success": True, "meeting": meeting.to_dict()}

    @login_required
    def put(self, meeting_id):
        """Update meeting details (preliminares)"""
        meeting = Meeting.query.get_or_404(meeting_id)
        data = request.get_json()
        
        try:
            if 'title' in data: meeting.title = data['title']
            if 'scheduled_date' in data: 
                meeting.scheduled_date = datetime.strptime(data['scheduled_date'], '%Y-%m-%d').date() if data['scheduled_date'] else None
            if 'scheduled_time' in data: meeting.scheduled_time = data['scheduled_time']
            if 'invite_notes' in data: meeting.invite_notes = data['invite_notes']
            if 'guests' in data: meeting.guests_json = json.dumps(data['guests'])
            if 'agenda' in data: meeting.agenda_json = json.dumps(data['agenda'])
            
            db.session.commit()
            return {"success": True, "message": "Dados atualizados!"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": str(e)}, 500

    @login_required
    def delete(self, meeting_id):
        """Delete a meeting"""
        meeting = Meeting.query.get_or_404(meeting_id)
        try:
            db.session.delete(meeting)
            db.session.commit()
            return {"success": True, "message": "Reunião excluída com sucesso!"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": str(e)}, 500

class MeetingExecutionResource(Resource):
    @login_required
    def put(self, meeting_id):
        """Save meeting execution data"""
        meeting = Meeting.query.get_or_404(meeting_id)
        data = request.get_json()
        
        try:
            if 'actual_date' in data: 
                meeting.actual_date = datetime.strptime(data['actual_date'], '%Y-%m-%d').date() if data['actual_date'] else None
            if 'actual_time' in data: meeting.actual_time = data['actual_time']
            if 'notes' in data: meeting.meeting_notes = data['notes']
            if 'participants' in data: meeting.participants_json = json.dumps(data['participants'])
            if 'discussions' in data: meeting.discussions_json = json.dumps(data['discussions'])
            if 'activities' in data: meeting.activities_json = json.dumps(data['activities'])
            
            db.session.commit()
            return {"success": True, "message": "Execução salva!"}
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": str(e)}, 500

class MeetingStartResource(Resource):
    @login_required
    def post(self, meeting_id):
        """Start meeting and link/create project"""
        meeting = Meeting.query.get_or_404(meeting_id)
        data = request.get_json() or {}
        project_type = data.get("project_type", "new")
        chosen_project_id = data.get("project_id")
        
        try:
            actual_date = datetime.now()
            meeting.actual_date = actual_date.date()
            meeting.actual_time = actual_date.strftime("%H:%M")
            meeting.status = 'in_progress'
            
            # Linking logic
            if not meeting.project_id:
                if project_type == "existing" and chosen_project_id:
                    meeting.project_id = int(chosen_project_id)
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
            return {"success": False, "message": str(e)}, 500

class MeetingFinishResource(Resource):
    @login_required
    def post(self, meeting_id):
        """Finalize meeting and create summary task in project"""
        from models import ProjectTask
        meeting = Meeting.query.get_or_404(meeting_id)
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
            return {"success": False, "message": str(e)}, 500

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
        meeting = Meeting.query.get_or_404(meeting_id)
        
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
        meeting = Meeting.query.get_or_404(meeting_id)
        
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
        meeting = Meeting.query.get_or_404(meeting_id)
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
            return {"success": False, "message": str(e)}, 500

class MeetingRemoveFromProjectResource(Resource):
    @login_required
    def post(self, meeting_id):
        """Remove a specific activity/task from the project"""
        from models import ProjectTask
        meeting = Meeting.query.get_or_404(meeting_id)
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
            return {"success": False, "message": str(e)}, 500
