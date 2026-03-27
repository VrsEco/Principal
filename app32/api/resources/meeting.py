from flask import request, session
from flask_restful import Resource
from flask_login import login_required, current_user
from models import Meeting, MeetingAgendaItem, Project, Company, Employee, db
from utils.permissions import get_default_company_id, has_company_full_access
from datetime import datetime
import json
import logging
import re
from services.email_service import email_service
from services.whatsapp_service import whatsapp_service

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


def _safe_json_loads(value, fallback):
    if value in (None, '', []):
        return fallback
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except Exception:
        return fallback
    return fallback if parsed is None else parsed


def _normalize_people_bucket(raw_value):
    if isinstance(raw_value, dict):
        internal = raw_value.get('internal')
        external = raw_value.get('external')
        return {
            "internal": internal if isinstance(internal, list) else [],
            "external": external if isinstance(external, list) else [],
        }
    if isinstance(raw_value, list):
        return {"internal": raw_value, "external": []}
    return {"internal": [], "external": []}


def _clean_text(value):
    return str(value or '').strip()


def _normalize_phone(value):
    return ''.join(ch for ch in str(value or '') if ch.isdigit())


def _normalize_name_key(value):
    return re.sub(r'\s+', ' ', _clean_text(value).lower())


def _build_summary_recipient_key(recipient):
    employee_id = _parse_optional_int(recipient.get('employee_id') or recipient.get('id'))
    if employee_id:
        return f"employee:{employee_id}"

    email = _clean_text(recipient.get('email')).lower()
    if email:
        return f"email:{email}"

    whatsapp = _normalize_phone(recipient.get('whatsapp') or recipient.get('phone'))
    if whatsapp:
        return f"whatsapp:{whatsapp}"

    name_key = _normalize_name_key(recipient.get('name'))
    return f"name:{name_key or 'sem-nome'}"


def _meeting_status_label(status):
    mapping = {
        'draft': 'Rascunho',
        'in_progress': 'Em andamento',
        'completed': 'Concluída',
    }
    normalized = _clean_text(status).lower()
    return mapping.get(normalized, status or 'Sem status')


def _format_summary_date(value):
    raw = _clean_text(value)
    if not raw:
        return ''
    try:
        return datetime.fromisoformat(raw).strftime('%d/%m/%Y')
    except Exception:
        return raw


def _truncate_text(value, limit=260):
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)].rstrip() + '…'


def _build_company_employees_maps(company_id):
    employees = Employee.query.filter_by(company_id=company_id, status='active').all()
    employees_by_id = {}
    employees_by_name = {}

    for employee in employees:
        employee_id = _parse_optional_int(getattr(employee, 'id', None))
        if employee_id is not None:
            employees_by_id[employee_id] = employee

        normalized_name = _normalize_name_key(getattr(employee, 'name', None))
        if normalized_name:
            employees_by_name.setdefault(normalized_name, []).append(employee)

    return employees_by_id, employees_by_name


def _resolve_internal_employee(person, employees_by_id, employees_by_name):
    employee_id = _parse_optional_int(person.get('employee_id') or person.get('id'))
    if employee_id is not None and employee_id in employees_by_id:
        return employee_id, employees_by_id[employee_id]

    normalized_name = _normalize_name_key(person.get('name'))
    if normalized_name:
        matches = employees_by_name.get(normalized_name) or []
        if len(matches) == 1:
            employee = matches[0]
            return _parse_optional_int(getattr(employee, 'id', None)), employee

    return employee_id, None


def _merge_meeting_recipient(recipient_store, recipient_data):
    key = recipient_data['key']
    existing = recipient_store.get(key)
    if not existing:
        recipient_store[key] = {
            "key": key,
            "name": recipient_data.get('name') or 'Destinatário',
            "email": recipient_data.get('email') or '',
            "whatsapp": recipient_data.get('whatsapp') or '',
            "employee_id": recipient_data.get('employee_id'),
            "origins": list(recipient_data.get('origins') or []),
        }
        return

    if not existing.get('name') and recipient_data.get('name'):
        existing['name'] = recipient_data['name']
    if not existing.get('email') and recipient_data.get('email'):
        existing['email'] = recipient_data['email']
    if not existing.get('whatsapp') and recipient_data.get('whatsapp'):
        existing['whatsapp'] = recipient_data['whatsapp']
    if not existing.get('employee_id') and recipient_data.get('employee_id'):
        existing['employee_id'] = recipient_data['employee_id']

    for origin in recipient_data.get('origins') or []:
        if origin not in existing['origins']:
            existing['origins'].append(origin)


def _serialize_meeting_recipient(recipient):
    email = _clean_text(recipient.get('email'))
    whatsapp = _normalize_phone(recipient.get('whatsapp'))
    origins = recipient.get('origins') or []
    return {
        "key": recipient['key'],
        "name": recipient.get('name') or 'Destinatário',
        "email": email or None,
        "whatsapp": whatsapp or None,
        "employee_id": recipient.get('employee_id'),
        "origins": origins,
        "has_email": bool(email),
        "has_whatsapp": bool(whatsapp),
        "is_guest": 'convidado' in origins,
        "is_participant": 'participante' in origins,
    }


def _build_meeting_recipients_catalog(meeting):
    guests_bucket = _normalize_people_bucket(_safe_json_loads(meeting.guests_json, {}))
    participants_bucket = _normalize_people_bucket(_safe_json_loads(meeting.participants_json, {}))
    employees_by_id, employees_by_name = _build_company_employees_maps(meeting.company_id)
    recipient_store = {}

    external_guest_contacts = {}
    for guest in guests_bucket['external']:
        if not isinstance(guest, dict):
            continue
        normalized_name = _normalize_name_key(guest.get('name'))
        if normalized_name and normalized_name not in external_guest_contacts:
            external_guest_contacts[normalized_name] = {
                "email": _clean_text(guest.get('email')),
                "whatsapp": _normalize_phone(guest.get('whatsapp')),
            }

    for guest in guests_bucket['internal']:
        if not isinstance(guest, dict):
            continue
        employee_id, employee = _resolve_internal_employee(guest, employees_by_id, employees_by_name)
        payload = {
            "employee_id": employee_id,
            "name": _clean_text(guest.get('name')) or _clean_text(getattr(employee, 'name', None)),
            "email": _clean_text(guest.get('email')) or _clean_text(getattr(employee, 'email', None)),
            "whatsapp": _normalize_phone(guest.get('whatsapp')) or _normalize_phone(getattr(employee, 'whatsapp', None)) or _normalize_phone(getattr(employee, 'phone', None)),
            "origins": ['convidado'],
        }
        payload['key'] = _build_summary_recipient_key(payload)
        _merge_meeting_recipient(recipient_store, payload)

    for participant in participants_bucket['internal']:
        if not isinstance(participant, dict):
            continue
        employee_id, employee = _resolve_internal_employee(participant, employees_by_id, employees_by_name)
        payload = {
            "employee_id": employee_id,
            "name": _clean_text(participant.get('name')) or _clean_text(getattr(employee, 'name', None)),
            "email": _clean_text(participant.get('email')) or _clean_text(getattr(employee, 'email', None)),
            "whatsapp": _normalize_phone(participant.get('whatsapp')) or _normalize_phone(getattr(employee, 'whatsapp', None)) or _normalize_phone(getattr(employee, 'phone', None)),
            "origins": ['participante'],
        }
        payload['key'] = _build_summary_recipient_key(payload)
        _merge_meeting_recipient(recipient_store, payload)

    for guest in guests_bucket['external']:
        if not isinstance(guest, dict):
            continue
        payload = {
            "employee_id": None,
            "name": _clean_text(guest.get('name')),
            "email": _clean_text(guest.get('email')),
            "whatsapp": _normalize_phone(guest.get('whatsapp')),
            "origins": ['convidado'],
        }
        payload['key'] = _build_summary_recipient_key(payload)
        _merge_meeting_recipient(recipient_store, payload)

    for participant in participants_bucket['external']:
        if not isinstance(participant, dict):
            continue
        normalized_name = _normalize_name_key(participant.get('name'))
        guest_fallback = external_guest_contacts.get(normalized_name, {})
        payload = {
            "employee_id": None,
            "name": _clean_text(participant.get('name')),
            "email": _clean_text(participant.get('email')) or _clean_text(guest_fallback.get('email')),
            "whatsapp": _normalize_phone(participant.get('whatsapp')) or _normalize_phone(guest_fallback.get('whatsapp')),
            "origins": ['participante'],
        }
        payload['key'] = _build_summary_recipient_key(payload)
        _merge_meeting_recipient(recipient_store, payload)

    recipients = [_serialize_meeting_recipient(item) for item in recipient_store.values()]
    recipients.sort(key=lambda item: (not (item['has_email'] or item['has_whatsapp']), item['name'].lower()))
    return recipients


def _build_projects_by_id(company_id):
    return {str(project.id): project for project in Project.query.filter_by(company_id=company_id).all()}


def _enrich_meeting_activity_projects(meeting_data, projects_by_id):
    activities = meeting_data.get('activities') or []
    if not isinstance(activities, list):
        return []

    enriched = []
    for activity in activities:
        if not isinstance(activity, dict):
            enriched.append(activity)
            continue

        activity_data = dict(activity)
        activity_project_id = activity_data.get('project_id') or activity_data.get('projectId')
        project = projects_by_id.get(str(activity_project_id)) if activity_project_id is not None else None

        if project:
            activity_data.setdefault('project_title', project.name)
            activity_data.setdefault('project_code', getattr(project, 'code', None))
        elif (
            activity_project_id is not None
            and meeting_data.get('project_id') is not None
            and str(activity_project_id) == str(meeting_data.get('project_id'))
        ):
            activity_data.setdefault('project_title', meeting_data.get('project_title'))
            activity_data.setdefault('project_code', meeting_data.get('project_code'))

        enriched.append(activity_data)

    return enriched


def _build_meeting_summary_payload(meeting, company):
    company_name = _clean_text(getattr(company, 'name', None))
    report_url = f"{request.host_url.rstrip('/')}/meetings/company/{meeting.company_id}/meeting/{meeting.id}/report"
    meeting_data = meeting.to_dict() if hasattr(meeting, 'to_dict') else {}
    projects_by_id = _build_projects_by_id(meeting.company_id)
    meeting_data['activities'] = _enrich_meeting_activity_projects(meeting_data, projects_by_id)

    agenda_items = meeting_data.get('agenda') or []
    discussions = meeting_data.get('discussions') or []
    activities = meeting_data.get('activities') or []
    notes = _clean_text(meeting_data.get('meeting_notes'))

    date_label = _format_summary_date(meeting_data.get('actual_date') or meeting_data.get('scheduled_date')) or 'Não informada'
    time_label = _clean_text(meeting_data.get('actual_time') or meeting_data.get('scheduled_time')) or 'Não informado'
    project_title = _clean_text(meeting_data.get('project_title'))
    project_code = _clean_text(meeting_data.get('project_code'))
    project_label = ''
    if project_title:
        project_label = f"{project_code} - {project_title}" if project_code else project_title

    body_lines = [
        "Resumo da reunião",
        "",
        f"Empresa: {company_name or 'Não informada'}",
        f"Reunião: {_clean_text(meeting.title) or 'Sem título'}",
        f"Status: {_meeting_status_label(meeting_data.get('status'))}",
        f"Data: {date_label}",
        f"Horário: {time_label}",
    ]

    if project_label:
        body_lines.append(f"Projeto: {project_label}")

    if agenda_items:
        body_lines.extend(["", "Pauta:"])
        for item in agenda_items[:8]:
            if not isinstance(item, dict):
                continue
            body_lines.append(f"- {_truncate_text(item.get('title'), 160) or 'Item de pauta'}")

    if discussions:
        body_lines.extend(["", "Pontos discutidos:"])
        for discussion in discussions[:8]:
            if not isinstance(discussion, dict):
                continue
            title = _truncate_text(discussion.get('title'), 160) or 'Tópico'
            detail = _truncate_text(discussion.get('discussion') or discussion.get('decision'), 220)
            body_lines.append(f"- {title}{': ' + detail if detail else ''}")

    if activities:
        body_lines.extend(["", "Plano de ação:"])
        for activity in activities[:10]:
            if not isinstance(activity, dict):
                continue
            activity_title = _truncate_text(activity.get('title'), 150) or 'Atividade'
            activity_project = _clean_text(activity.get('project_title') or activity.get('project_name') or project_title) or 'Sem projeto vinculado'
            responsible = _clean_text(activity.get('responsible')) or 'A definir'
            deadline = _format_summary_date(activity.get('deadline')) or 'A definir'
            body_lines.append(
                f"- {activity_title} | Projeto: {activity_project} | Responsável: {responsible} | Prazo: {deadline}"
            )

    if notes:
        body_lines.extend(["", "Conclusões:"])
        body_lines.append(_truncate_text(notes, 700))

    body_lines.extend(["", f"Ata completa: {report_url}"])
    body = "\n".join(body_lines).strip()

    subject = f"Resumo da Reunião: {_clean_text(meeting.title) or f'#{meeting.id}'}"
    html_body = email_service.build_transactional_email_html(
        subject=subject,
        body=body,
        title="Resumo da Reunião",
        preheader=_truncate_text(f"{company_name} • {meeting.title} • {date_label}", 140),
        footer_note="Resumo enviado a partir do módulo de Gestão de Reuniões.",
    )

    whatsapp_message = f"📋 *RESUMO DA REUNIÃO*\n\n{body}"
    return {
        "subject": subject,
        "body": body,
        "html_body": html_body,
        "whatsapp_message": whatsapp_message,
        "report_url": report_url,
    }


def _normalize_requested_channels(raw_channels):
    if isinstance(raw_channels, str):
        raw_channels = [raw_channels]
    if not isinstance(raw_channels, list):
        return []
    valid = []
    for channel in raw_channels:
        normalized = _clean_text(channel).lower()
        if normalized in {'email', 'whatsapp'} and normalized not in valid:
            valid.append(normalized)
    return valid

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
                "meeting_id": meeting.id,
                "updated_at": meeting.updated_at.isoformat() if meeting.updated_at else None,
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
            return {
                "success": True,
                "message": "Dados atualizados!",
                "meeting_id": meeting.id,
                "updated_at": meeting.updated_at.isoformat() if meeting.updated_at else None,
            }
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
            return {
                "success": True,
                "message": "Execução salva!",
                "meeting_id": meeting.id,
                "updated_at": meeting.updated_at.isoformat() if meeting.updated_at else None,
            }
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
                "project_code": project.code if project else None,
                "actual_date": meeting.actual_date.isoformat(),
                "actual_time": meeting.actual_time,
                "updated_at": meeting.updated_at.isoformat() if meeting.updated_at else None,
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
            return {
                "success": True,
                "message": "Reunião finalizada e resumida no projeto!",
                "updated_at": meeting.updated_at.isoformat() if meeting.updated_at else None,
            }
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": PUBLIC_ERROR_MESSAGE}, 500


class MeetingSummaryRecipientsResource(Resource):
    @login_required
    def get(self, meeting_id):
        """Load normalized recipients for meeting summary sharing."""
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response

        try:
            company = Company.query.get(meeting.company_id)
            recipients = _build_meeting_recipients_catalog(meeting)
            summary_payload = _build_meeting_summary_payload(meeting, company)

            email_available = sum(1 for item in recipients if item['has_email'])
            whatsapp_available = sum(1 for item in recipients if item['has_whatsapp'])
            default_channels = ['email'] if email_available else (['whatsapp'] if whatsapp_available else [])

            return {
                "success": True,
                "meeting_id": meeting.id,
                "meeting_title": meeting.title,
                "meeting_status": meeting.status,
                "report_url": summary_payload['report_url'],
                "summary_subject": summary_payload['subject'],
                "default_channels": default_channels,
                "email_available_count": email_available,
                "whatsapp_available_count": whatsapp_available,
                "recipients": recipients,
            }
        except Exception as exc:
            logger.exception("Erro ao montar catálogo de destinatários da reunião %s: %s", meeting_id, exc)
            return {"success": False, "message": PUBLIC_ERROR_MESSAGE}, 500


class MeetingShareSummaryResource(Resource):
    @login_required
    def post(self, meeting_id):
        """Send meeting summary through selected channels to selected meeting recipients."""
        meeting, error_response = get_meeting_or_404(meeting_id)
        if error_response:
            return error_response

        data = request.get_json() or {}
        requested_channels = _normalize_requested_channels(data.get('channels'))
        requested_keys = data.get('recipient_keys')

        if not requested_channels:
            return {"success": False, "message": "Selecione pelo menos um canal de envio."}, 400
        if not isinstance(requested_keys, list) or not requested_keys:
            return {"success": False, "message": "Selecione pelo menos um destinatário."}, 400

        try:
            recipients_catalog = _build_meeting_recipients_catalog(meeting)
            catalog_by_key = {item['key']: item for item in recipients_catalog}
            selected_keys = []
            for key in requested_keys:
                normalized_key = _clean_text(key)
                if normalized_key and normalized_key not in selected_keys:
                    selected_keys.append(normalized_key)

            selected_recipients = [catalog_by_key[key] for key in selected_keys if key in catalog_by_key]
            if not selected_recipients:
                return {"success": False, "message": "Nenhum destinatário válido foi encontrado para esta reunião."}, 400

            company = Company.query.get(meeting.company_id)
            summary_payload = _build_meeting_summary_payload(meeting, company)

            sent_email = 0
            sent_whatsapp = 0
            skipped = []
            failures = []

            for recipient in selected_recipients:
                recipient_name = recipient.get('name') or 'Destinatário'

                if 'email' in requested_channels:
                    recipient_email = recipient.get('email')
                    if recipient_email:
                        ok = email_service.send_email(
                            to_emails=[recipient_email],
                            subject=summary_payload['subject'],
                            body=summary_payload['body'],
                            html_body=summary_payload['html_body'],
                        )
                        if ok:
                            sent_email += 1
                        else:
                            failures.append({
                                "name": recipient_name,
                                "channel": "email",
                                "target": recipient_email,
                            })
                    else:
                        skipped.append({
                            "name": recipient_name,
                            "channel": "email",
                            "reason": "Sem e-mail cadastrado.",
                        })

                if 'whatsapp' in requested_channels:
                    recipient_whatsapp = recipient.get('whatsapp')
                    if recipient_whatsapp:
                        ok = whatsapp_service.send_message(
                            recipient_whatsapp,
                            summary_payload['whatsapp_message'],
                        )
                        if ok:
                            sent_whatsapp += 1
                        else:
                            failures.append({
                                "name": recipient_name,
                                "channel": "whatsapp",
                                "target": recipient_whatsapp,
                            })
                    else:
                        skipped.append({
                            "name": recipient_name,
                            "channel": "whatsapp",
                            "reason": "Sem WhatsApp cadastrado.",
                        })

            if sent_email == 0 and sent_whatsapp == 0:
                return {
                    "success": False,
                    "message": "Nenhuma mensagem foi enviada. Verifique os canais e contatos selecionados.",
                    "sent_email": sent_email,
                    "sent_whatsapp": sent_whatsapp,
                    "selected_count": len(selected_recipients),
                    "skipped_count": len(skipped),
                    "failed_count": len(failures),
                    "skipped": skipped,
                    "failures": failures,
                }, 400

            return {
                "success": True,
                "message": "Resumo da reunião enviado com sucesso.",
                "sent_email": sent_email,
                "sent_whatsapp": sent_whatsapp,
                "selected_count": len(selected_recipients),
                "skipped_count": len(skipped),
                "failed_count": len(failures),
                "skipped": skipped,
                "failures": failures,
            }
        except Exception as exc:
            logger.exception("Erro ao enviar resumo da reunião %s: %s", meeting_id, exc)
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
        except Exception:
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
            "project_title": project.name if project else None,
            "project_code": project.code if project else None,
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
        except Exception:
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
                    except Exception:
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
