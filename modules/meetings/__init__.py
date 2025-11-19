import logging
"""
Módulo de Gestão de Reuniões - Reorganizado
Gerir reuniões com 3 abas: Dados Preliminares, Execução, Atividades Geradas
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from config_database import get_db
from datetime import datetime
import json
from utils.project_activity_utils import normalize_project_activities

meetings_bp = Blueprint("meetings", __name__, url_prefix="/meetings")
logger = logging.getLogger(__name__)

# PÃ¡gina principal de gerenciamento de reuniÃµes
@meetings_bp.route("/company/<int:company_id>")
@meetings_bp.route("/company/<int:company_id>/list")
def meetings_manage(company_id):
    """PÃ¡gina principal de gerenciamento de reuniÃµes"""
    try:
        db = get_db()
        company = db.get_company(company_id)
        if not company:
            flash('Empresa nÃ£o encontrada', 'error')
            return redirect(url_for('dashboard'))
        
        meetings = db.list_company_meetings(company_id)
        
        # Buscar colaboradores da empresa
        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrÃ£o
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, email, whatsapp 
            FROM employees 
            WHERE company_id = %s 
            ORDER BY name
        ''', (company_id,))
        employees = [dict(row) for row in cursor.fetchall()]
        
        # Buscar itens de pauta reutilizÃ¡veis
        cursor.execute('''
            SELECT id, title, description, usage_count
            FROM meeting_agenda_items
            WHERE company_id = %s
            ORDER BY usage_count DESC, title
        ''', (company_id,))
        agenda_items = [dict(row) for row in cursor.fetchall()]
        
        # Buscar projetos da empresa
        projects = db.get_company_projects(company_id)
        
        conn.close()
        
        return render_template(
            'meetings_manage.html',
            company=company,
            meetings=meetings,
            employees=employees,
            agenda_items=agenda_items,
            projects=projects,
            active_id='meetings-manage'
        )
    except Exception as e:
        logger.info(f"Erro ao carregar gerenciamento de reuniÃµes: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao carregar reuniÃµes: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


# Alias para meetings_list (compatibilidade com template)
meetings_list = meetings_manage




# PÃ¡gina de ediÃ§Ã£o de uma reuniÃ£o
@meetings_bp.route("/company/<int:company_id>/meeting/<int:meeting_id>/edit")
def meeting_edit(company_id, meeting_id):
    """PÃ¡gina de ediÃ§Ã£o de uma reuniÃ£o"""
    try:
        db = get_db()
        company = db.get_company(company_id)
        if not company:
            flash('Empresa nÃ£o encontrada', 'error')
            return redirect(url_for('dashboard'))
        
        meeting = db.get_meeting(meeting_id)
        if not meeting:
            flash('ReuniÃ£o nÃ£o encontrada', 'error')
            return redirect(url_for('meetings.meetings_manage', company_id=company_id))
        
        # Verificar se a reuniÃ£o pertence Ã  empresa
        if meeting.get('company_id') != company_id:
            flash('ReuniÃ£o nÃ£o pertence a esta empresa', 'error')
            return redirect(url_for('meetings.meetings_manage', company_id=company_id))
        
        # Buscar colaboradores da empresa
        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrÃ£o
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, email, whatsapp 
            FROM employees 
            WHERE company_id = %s 
            ORDER BY name
        ''', (company_id,))
        employees = [dict(row) for row in cursor.fetchall()]
        
        # Buscar itens de pauta reutilizÃ¡veis
        cursor.execute('''
            SELECT id, title, description, usage_count
            FROM meeting_agenda_items
            WHERE company_id = %s
            ORDER BY usage_count DESC, title
        ''', (company_id,))
        agenda_items = [dict(row) for row in cursor.fetchall()]
        
        # Buscar projetos da empresa
        projects = db.get_company_projects(company_id)
        
        conn.close()
        
        return render_template(
            'meeting_form.html',
            company=company,
            meeting=meeting,
            employees=employees,
            agenda_items=agenda_items,
            projects=projects,
            is_edit=True
        )
        
    except Exception as e:
        logger.info(f"Erro ao carregar ediÃ§Ã£o da reuniÃ£o: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao carregar reuniÃ£o: {str(e)}', 'error')
        return redirect(url_for('meetings.meetings_manage', company_id=company_id))


# API: Deletar reuniÃ£o (POST para compatibilidade com JavaScript)
@login_required
@meetings_bp.route("/company/<int:company_id>/meeting/<int:meeting_id>/delete", methods=['POST'])
def meeting_delete(company_id, meeting_id):
    """Deletar uma reuniÃ£o"""
    try:
        db = get_db()
        
        # Verificar se a reuniÃ£o pertence Ã  empresa
        meeting = db.get_meeting(meeting_id)
        if not meeting or meeting.get('company_id') != company_id:
            return jsonify({'success': False, 'message': 'ReuniÃ£o nÃ£o encontrada'}), 404
        
        if db.delete_meeting(meeting_id):
            return jsonify({'success': True, 'message': 'ReuniÃ£o excluÃ­da com sucesso!'})
        else:
            return jsonify({'success': False, 'message': 'Erro ao excluir reuniÃ£o'}), 500
            
    except Exception as e:
        logger.info(f"Erro ao deletar reuniÃ£o: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# API: Criar nova reuniÃ£o
@login_required
@meetings_bp.route("/api/company/<int:company_id>/meeting", methods=['POST'])
def api_create_meeting(company_id):
    """API: Criar nova reuniÃ£o"""
    try:
        data = request.get_json()
        db = get_db()
        
        meeting_data = {
            'title': data.get('title'),
            'scheduled_date': data.get('scheduled_date'),
            'scheduled_time': data.get('scheduled_time'),
            'invite_notes': data.get('invite_notes', ''),
            'status': 'draft',
            'guests': data.get('guests', {'internal': [], 'external': []}),
            'agenda': data.get('agenda', []),
            'participants': {'internal': [], 'external': []},
            'discussions': [],
            'activities': []
        }
        
        meeting_id = db.create_meeting(company_id, meeting_data)
        
        if meeting_id:
            return jsonify({'success': True, 'meeting_id': meeting_id, 'message': 'ReuniÃ£o criada com sucesso!'})
        else:
            return jsonify({'success': False, 'message': 'Erro ao criar reuniÃ£o'}), 500
            
    except Exception as e:
        logger.info(f"Erro ao criar reuniÃ£o: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# API: Gerar relatÃ³rio de reuniÃµes
@meetings_bp.route("/api/company/<int:company_id>/meetings/report", methods=['GET'])
def api_generate_meetings_report(company_id):
    """API: Gerar relatÃ³rio de reuniÃµes"""
    try:
        db = get_db()
        company = db.get_company(company_id)
        if not company:
            return jsonify({'success': False, 'error': 'company_not_found'}), 404
        
        # Capturar parÃ¢metros da URL
        meeting_id = request.args.get('meeting_id', type=int)
        model_id = request.args.get('model', type=int)
        sections = request.args.getlist('sections')
        
        logger.info(f"ðŸ”„ Gerando relatÃ³rio de reuniÃµes - Empresa: {company_id}")
        logger.info(f"ðŸ“‹ ReuniÃ£o especÃ­fica: {meeting_id if meeting_id else 'Todas'}")
        logger.info(f"ðŸ“„ Modelo de pÃ¡gina: {model_id if model_id else 'PadrÃ£o'}")
        logger.info(f"ðŸ“‹ SeÃ§Ãµes selecionadas: {', '.join(sections) if sections else 'Todas'}")
        
        # Importar gerador de relatÃ³rios de reuniÃµes
        from relatorios.generators.meetings_report import MeetingsReportGenerator
        
        # Criar gerador aplicando o modelo desejado (padrÃ£o Model_7)
        report = MeetingsReportGenerator(report_model_id=model_id or 7)
        
        # Configurar seÃ§Ãµes baseado na seleÃ§Ã£o do usuÃ¡rio
        report.configure(
            info='info' in sections if sections else True,
            guests='guests' in sections if sections else True,
            agenda='agenda' in sections if sections else True,
            participants='participants' in sections if sections else True,
            discussions='discussions' in sections if sections else True,
            activities='activities' in sections if sections else True
        )
        
        # Gerar HTML usando o template especÃ­fico
        html_content = report.generate_html(
            company_id=company_id,
            meeting_id=meeting_id
        )
        
        logger.info(f"âœ… RelatÃ³rio de reuniÃµes gerado com sucesso!")
        
        # Retornar HTML
        from flask import make_response
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
        
    except Exception as e:
        logger.info(f"âŒ ERRO ao gerar relatÃ³rio de reuniÃµes: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro ao gerar relatÃ³rio de reuniÃµes. Verifique os logs do servidor.'
        }), 500


# API: Listar reuniÃµes da empresa
@meetings_bp.route("/api/company/<int:company_id>/meetings")
def api_list_company_meetings(company_id):
    """API: Listar reuniÃµes da empresa em formato JSON"""
    try:
        db = get_db()
        company = db.get_company(company_id)
        if not company:
            return jsonify({'success': False, 'error': 'company_not_found'}), 404
        
        meetings = db.list_company_meetings(company_id)
        
        return jsonify({
            'success': True,
            'company': {
                'id': company['id'],
                'name': company['name']
            },
            'meetings': meetings,
            'total': len(meetings)
        })
        
    except Exception as e:
        logger.info(f"Erro ao listar reuniÃµes: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# API: Buscar reuniÃ£o especÃ­fica
@meetings_bp.route("/api/meeting/<int:meeting_id>")
def api_get_meeting(meeting_id):
    """API: Buscar dados de uma reuniÃ£o"""
    try:
        db = get_db()
        meeting = db.get_meeting(meeting_id)
        
        if meeting:
            return jsonify({'success': True, 'meeting': meeting})
        else:
            return jsonify({'success': False, 'message': 'ReuniÃ£o nÃ£o encontrada'}), 404
            
    except Exception as e:
        logger.info(f"Erro ao buscar reuniÃ£o: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# API: Atualizar dados preliminares
@login_required
@meetings_bp.route("/api/meeting/<int:meeting_id>/preliminares", methods=['PUT'])
def api_update_preliminares(meeting_id):
    """API: Atualizar dados preliminares/convite"""
    try:
        data = request.get_json()
        db = get_db()
        
        meeting_data = {
            'title': data.get('title'),
            'scheduled_date': data.get('scheduled_date'),
            'scheduled_time': data.get('scheduled_time'),
            'invite_notes': data.get('invite_notes'),
            'guests': data.get('guests'),
            'agenda': data.get('agenda')
        }
        
        if db.update_meeting(meeting_id, meeting_data):
            return jsonify({'success': True, 'message': 'Dados preliminares atualizados!'})
        else:
            return jsonify({'success': False, 'message': 'Erro ao atualizar'}), 500
            
    except Exception as e:
        logger.info(f"Erro ao atualizar dados preliminares: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# API: Iniciar reuniÃ£o
@login_required
@meetings_bp.route("/api/meeting/<int:meeting_id>/iniciar", methods=['POST'])
def api_start_meeting(meeting_id):
    """API: Iniciar reuniÃ£o - cria projeto automaticamente"""
    try:
        db = get_db()
        meeting = db.get_meeting(meeting_id)

        if not meeting:
            return jsonify({'success': False, 'message': 'ReuniÃ£o nÃ£o encontrada'}), 404

        # Criar projeto se ainda nÃ£o existir
        if not meeting.get('project_id'):
            execution_date = (
                meeting.get('actual_date')
                or meeting.get('scheduled_date')
                or datetime.now().strftime('%Y-%m-%d')
            )
            try:
                display_date = datetime.strptime(execution_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            except Exception:
                display_date = execution_date

            project_title = f"ReuniÃ£o - {meeting['title']} ({display_date})"
            actual_date_str = datetime.now().strftime('%Y-%m-%d')
            actual_time_str = datetime.now().strftime('%H:%M')

            project_data = {
                'title': project_title,
                'description': f"Projeto gerado automaticamente para a reuniÃ£o: {meeting['title']}",
                'status': 'in_progress',
                'priority': 'medium',
                'owner': 'Sistema',
                'start_date': execution_date,
                'notes': f"Projeto vinculado a reuniÃ£o ID {meeting_id}"
            }

            project_id = db.create_company_project(meeting['company_id'], project_data)
            if not project_id:
                return jsonify({'success': False, 'message': 'Falha ao criar projeto vinculado'}), 500

            db.update_meeting(meeting_id, {
                'project_id': project_id,
                'status': 'in_progress',
                'actual_date': actual_date_str,
                'actual_time': actual_time_str
            })

            return jsonify({
                'success': True,
                'message': 'ReuniÃ£o iniciada e projeto criado!',
                'project_id': project_id,
                'actual_date': actual_date_str,
                'actual_time': actual_time_str
            })

        actual_date_str = datetime.now().strftime('%Y-%m-%d')
        actual_time_str = datetime.now().strftime('%H:%M')
        db.update_meeting(meeting_id, {
            'status': 'in_progress',
            'actual_date': actual_date_str,
            'actual_time': actual_time_str
        })

        return jsonify({
            'success': True,
            'message': 'ReuniÃ£o iniciada!',
            'project_id': meeting['project_id'],
            'actual_date': actual_date_str,
            'actual_time': actual_time_str
        })

    except Exception as e:
        logger.info(f'Erro ao iniciar reuniÃ£o: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
# API: Atualizar execuÃ§Ã£o da reuniÃ£o
@login_required
@meetings_bp.route("/api/meeting/<int:meeting_id>/execucao", methods=['PUT'])
def api_update_execucao(meeting_id):
    """API: Atualizar dados da execuÃ§Ã£o da reuniÃ£o"""
    try:
        data = request.get_json()
        db = get_db()
        
        meeting_data = {
            'actual_date': data.get('actual_date'),
            'actual_time': data.get('actual_time'),
            'status': data.get('status'),
            'participants': data.get('participants'),
            'discussions': data.get('discussions'),
            'activities': data.get('activities'),
            'meeting_notes': data.get('meeting_notes')
        }
        
        if db.update_meeting(meeting_id, meeting_data):
            return jsonify({'success': True, 'message': 'ExecuÃ§Ã£o atualizada!'})
        else:
            return jsonify({'success': False, 'message': 'Erro ao atualizar'}), 500
            
    except Exception as e:
        logger.info(f"Erro ao atualizar execuÃ§Ã£o: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# API: Finalizar reuniÃ£o
@login_required
@meetings_bp.route("/api/meeting/<int:meeting_id>/finalizar", methods=['POST'])
def api_finish_meeting(meeting_id):
    """API: Finalizar reuniÃ£o - cria atividade resumo"""
    try:
        db = get_db()
        meeting = db.get_meeting(meeting_id)
        
        if not meeting:
            return jsonify({'success': False, 'message': 'ReuniÃ£o nÃ£o encontrada'}), 404
        
        if not meeting.get('project_id'):
            return jsonify({'success': False, 'message': 'ReuniÃ£o sem projeto vinculado'}), 400
        
        # Criar resumo da reuniÃ£o
        resumo = f"""RESUMO DA REUNIÃƒO: {meeting['title']}

Data: {meeting.get('actual_date', meeting['scheduled_date'])}
Hora: {meeting.get('actual_time', meeting['scheduled_time'])}

PARTICIPANTES:
"""
        
        # Adicionar participantes
        participants = meeting.get('participants', {})
        if participants.get('internal'):
            resumo += "\nInternos:\n"
            for p in participants['internal']:
                resumo += f"- {p.get('name', p)}\n"
        
        if participants.get('external'):
            resumo += "\nExternos:\n"
            for p in participants['external']:
                resumo += f"- {p.get('name', p)}\n"
        
        # Adicionar discussÃµes
        discussions = meeting.get('discussions', [])
        if discussions:
            resumo += "\n\nDISCUSSÃ•ES E DEFINIÃ‡Ã•ES:\n"
            for disc in discussions:
                resumo += f"\nâ€¢ {disc.get('title', 'Sem tÃ­tulo')}\n"
                resumo += f"  {disc.get('discussion', '')}\n"
        
        # Adicionar atividades
        activities = meeting.get('activities', [])
        if activities:
            resumo += "\n\nATIVIDADES CRIADAS:\n"
            for act in activities:
                resumo += f"- {act.get('title', 'Sem tÃ­tulo')}"
                if act.get('responsible'):
                    resumo += f" (ResponsÃ¡vel: {act['responsible']})"
                if act.get('deadline'):
                    resumo += f" (Prazo: {act['deadline']})"
                if act.get('how'):
                    resumo += f"\n  Como: {act['how']}"
                resumo += "\n"
        
        # Criar atividade de resumo no projeto
        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrÃ£o  # Importante: configurar row_factory
        cursor = conn.cursor()
        
        # Buscar o JSON de atividades do projeto
        cursor.execute('SELECT code, activities FROM company_projects WHERE id = %s', (meeting['project_id'],))
        row = cursor.fetchone()

        project_code = row['code'] if row else None
        activities_raw = row['activities'] if row else None

        project_activities = []
        if activities_raw:
            try:
                project_activities = json.loads(activities_raw) if isinstance(activities_raw, str) else activities_raw
                if not isinstance(project_activities, list):
                    project_activities = []
            except Exception:
                project_activities = []

        project_activities, _, _ = normalize_project_activities(project_activities, project_code)

        # Adicionar atividades individuais da reuniÃ£o ao projeto
        activities = meeting.get('activities', [])
        if activities:
            for act in activities:
                # Converter atividade da reuniÃ£o para formato do projeto
                meeting_title = act.get('title') or 'Sem tÃ­tulo'
                meeting_responsible = act.get('responsible') or ''
                meeting_deadline = act.get('deadline') or ''
                meeting_how = act.get('how') or ''

                project_activity = {
                    'title': meeting_title,
                    'what': meeting_title,
                    'description': meeting_how,
                    'how': meeting_how,
                    'responsible': meeting_responsible,
                    'who': meeting_responsible,
                    'deadline': meeting_deadline,
                    'when': meeting_deadline,
                    'status': act.get('status') or 'pending',  # Status inicial como pendente
                    'stage': act.get('stage') or 'inbox',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat(),
                    'source': 'meeting',  # Marcar origem como reuniÃ£o
                    'meeting_id': meeting_id
                }
                project_activities.append(project_activity)
        
        # Adicionar atividade de resumo
        resumo_text = resumo or ''
        resumo_titulo = f'ðŸ“‹ Resumo da ReuniÃ£o - {meeting["title"]}'
        resumo_activity = {
            'title': resumo_titulo,
            'what': resumo_titulo,
            'description': resumo_text,
            'how': resumo_text,
            'responsible': '',
            'who': '',
            'deadline': '',
            'when': '',
            'status': 'completed',
            'stage': 'inbox',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'source': 'meeting_summary',
            'meeting_id': meeting_id
        }
        project_activities.append(resumo_activity)

        project_activities, _, _ = normalize_project_activities(project_activities, project_code)
        
        # Atualizar projeto
        cursor.execute(
            'UPDATE company_projects SET activities = %s WHERE id = %s',
            (json.dumps(project_activities, ensure_ascii=False), meeting['project_id'])
        )
        
        # Atualizar status da reuniÃ£o
        cursor.execute(
            "UPDATE meetings SET status = 'completed' WHERE id = %s",
            (meeting_id,)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'ReuniÃ£o finalizada e resumo criado!',
            'project_id': meeting['project_id']
        })
            
    except Exception as e:
        logger.info(f"Erro ao finalizar reuniÃ£o: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@login_required
@meetings_bp.route("/api/meeting/<int:meeting_id>/sync-activities", methods=['POST'])
def api_sync_meeting_activities(meeting_id):
    """API: Sincronizar atividades entre reuniÃ£o e projeto"""
    try:
        db = get_db()
        meeting = db.get_meeting(meeting_id)

        if not meeting:
            return jsonify({'success': False, 'message': 'ReuniÃ£o nÃ£o encontrada'}), 404

        if not meeting.get('project_id'):
            return jsonify({'success': False, 'message': 'ReuniÃ£o sem projeto vinculado'}), 400

        payload = request.get_json(silent=True) or {}
        meeting_activities = payload.get('activities', meeting.get('activities', []))

        update_payload = {}
        for key in ('activities', 'participants', 'discussions', 'meeting_notes', 'status', 'actual_date', 'actual_time'):
            if key in payload and payload[key] is not None:
                update_payload[key] = payload[key]

        if update_payload:
            db.update_meeting(meeting_id, update_payload)

        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrÃ£o
        cursor = conn.cursor()

        cursor.execute('SELECT code, activities FROM company_projects WHERE id = %s', (meeting['project_id'],))
        row = cursor.fetchone()

        project_activities = []
        project_code = row['code'] if row else None
        if row and row['activities']:
            try:
                project_activities = json.loads(row['activities'])
                if not isinstance(project_activities, list):
                    project_activities = []
            except Exception:
                project_activities = []

        project_activities, _, _ = normalize_project_activities(project_activities, project_code)

        meeting_activity_titles = [act.get('title', '') for act in meeting_activities]
        project_activities = [
            act for act in project_activities
            if not (act.get('source') == 'meeting' and act.get('meeting_id') == meeting_id)
            or act.get('title', '') in meeting_activity_titles
        ]

        for act in meeting_activities:
            existing_activity = None
            for proj_act in project_activities:
                if (
                    proj_act.get('source') == 'meeting' and
                    proj_act.get('meeting_id') == meeting_id and
                    proj_act.get('title') == act.get('title', '')
                ):
                    existing_activity = proj_act
                    break

            meeting_title = act.get('title') or 'Sem tÃ­tulo'
            meeting_responsible = act.get('responsible') or ''
            meeting_deadline = act.get('deadline') or ''
            meeting_how = act.get('how') or ''

            normalized_fields = {
                'title': meeting_title,
                'what': meeting_title,
                'description': meeting_how,
                'how': meeting_how,
                'responsible': meeting_responsible,
                'who': meeting_responsible,
                'deadline': meeting_deadline,
                'when': meeting_deadline,
                'updated_at': datetime.now().isoformat()
            }

            if existing_activity:
                existing_activity.update(normalized_fields)
            else:
                project_activity = {
                    **normalized_fields,
                    'status': act.get('status') or 'pending',
                    'stage': act.get('stage') or 'inbox',
                    'created_at': datetime.now().isoformat(),
                    'source': 'meeting',
                    'meeting_id': meeting_id
                }
                project_activities.append(project_activity)

        project_activities, _, _ = normalize_project_activities(project_activities, project_code)

        cursor.execute(
            'UPDATE company_projects SET activities = %s WHERE id = %s',
            (json.dumps(project_activities, ensure_ascii=False), meeting['project_id'])
        )

        conn.commit()
        conn.close()

        project_title = meeting.get('project_title')
        if not project_title and meeting.get('project_id'):
            project_record = db.get_company_project(meeting['company_id'], meeting['project_id'])
            if project_record:
                project_title = project_record.get('title')

        return jsonify({
            'success': True,
            'message': 'Atividades sincronizadas com sucesso!',
            'synced_count': len(meeting_activities),
            'project_id': meeting['project_id'],
            'project_title': project_title,
            'project_activities': project_activities,
            'meeting_activities': meeting_activities
        })

    except Exception as e:
        logger.info(f"Erro ao sincronizar atividades: {e}")
        return jsonify({'success': False, 'message': f'Erro ao sincronizar: {str(e)}'}), 500


@meetings_bp.route("/api/meeting/<int:meeting_id>/check-sync", methods=['GET'])
def api_check_meeting_sync(meeting_id):
    """API: Verificar status de sincronizaÃ§Ã£o entre reuniÃ£o e projeto"""
    try:
        db = get_db()
        meeting = db.get_meeting(meeting_id)
        
        if not meeting or not meeting.get('project_id'):
            return jsonify({'success': False, 'message': 'ReuniÃ£o ou projeto nÃ£o encontrado'}), 404
        
        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrÃ£o
        cursor = conn.cursor()
        
        # Buscar atividades da reuniÃ£o
        meeting_activities = meeting.get('activities', [])
        
        # Buscar atividades do projeto
        cursor.execute('SELECT code, activities FROM company_projects WHERE id = %s', (meeting['project_id'],))
        row = cursor.fetchone()
        
        project_activities = []
        project_code = row['code'] if row else None
        if row and row['activities']:
            try:
                project_activities = json.loads(row['activities'])
            except Exception as exc:
                pass

        project_activities, _, _ = normalize_project_activities(project_activities, project_code)
        
        # Filtrar atividades que vieram da reuniÃ£o
        meeting_sourced_activities = [act for act in project_activities if act.get('source') == 'meeting' and act.get('meeting_id') == meeting_id]
        
        # Verificar sincronizaÃ§Ã£o
        meeting_titles = set(act.get('title', '') for act in meeting_activities)
        project_titles = set(act.get('title', '') for act in meeting_sourced_activities)
        
        is_synced = meeting_titles == project_titles
        missing_in_project = meeting_titles - project_titles
        extra_in_project = project_titles - meeting_titles
        
        conn.close()
        
        return jsonify({
            'success': True,
            'is_synced': is_synced,
            'meeting_count': len(meeting_activities),
            'project_count': len(meeting_sourced_activities),
            'missing_in_project': list(missing_in_project),
            'extra_in_project': list(extra_in_project)
        })
        
    except Exception as e:
        logger.info(f"Erro ao verificar sincronizaÃ§Ã£o: {e}")
        return jsonify({'success': False, 'message': f'Erro ao verificar: {str(e)}'}), 500


@login_required
@meetings_bp.route("/api/meeting/<int:meeting_id>/remove-from-project", methods=['POST'])
def api_remove_activity_from_project(meeting_id):
    """API: Remover atividade do projeto quando removida da reuniÃ£o"""
    try:
        data = request.get_json()
        activity_title = data.get('title')
        
        if not activity_title:
            return jsonify({'success': False, 'message': 'TÃ­tulo da atividade nÃ£o fornecido'}), 400
        
        db = get_db()
        meeting = db.get_meeting(meeting_id)
        
        if not meeting or not meeting.get('project_id'):
            return jsonify({'success': False, 'message': 'ReuniÃ£o ou projeto nÃ£o encontrado'}), 404
        
        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        # PostgreSQL retorna Row objects por padrÃ£o
        cursor = conn.cursor()
        
        # Buscar atividades do projeto
        cursor.execute('SELECT code, activities FROM company_projects WHERE id = %s', (meeting['project_id'],))
        row = cursor.fetchone()
        
        project_activities = []
        project_code = row['code'] if row else None
        if row and row['activities']:
            try:
                project_activities = json.loads(row['activities'])
            except Exception as exc:
                pass
        project_activities, _, _ = normalize_project_activities(project_activities, project_code)
        
        # Remover atividade especÃ­fica
        original_count = len(project_activities)
        project_activities = [act for act in project_activities if not (
            act.get('source') == 'meeting' and 
            act.get('meeting_id') == meeting_id and 
            act.get('title') == activity_title
        )]
        
        removed_count = original_count - len(project_activities)
        
        project_activities, _, _ = normalize_project_activities(project_activities, project_code)

        # Atualizar projeto
        cursor.execute(
            'UPDATE company_projects SET activities = %s WHERE id = %s',
            (json.dumps(project_activities, ensure_ascii=False), meeting['project_id'])
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Atividade removida do projeto',
            'removed_count': removed_count
        })
        
    except Exception as e:
        logger.info(f"Erro ao remover atividade do projeto: {e}")
        return jsonify({'success': False, 'message': f'Erro ao remover: {str(e)}'}), 500


# API: Deletar reuniÃ£o
@login_required
@meetings_bp.route("/api/meeting/<int:meeting_id>", methods=['DELETE'])
def api_delete_meeting(meeting_id):
    """API: Deletar reuniÃ£o"""
    try:
        db = get_db()
        
        if db.delete_meeting(meeting_id):
            return jsonify({'success': True, 'message': 'ReuniÃ£o excluÃ­da com sucesso!'})
        return jsonify({'success': False, 'message': 'ReuniÃ£o nÃ£o encontrada.'}), 404
            
    except Exception as e:
        logger.info(f"Erro ao deletar reuniÃ£o: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# API: Buscar atividades geradas pela reuniÃ£o
@meetings_bp.route("/api/meeting/<int:meeting_id>/atividades")
def api_get_meeting_activities(meeting_id):
    """API: Buscar todas as atividades geradas pela reuniÃ£o"""
    try:
        db = get_db()
        meeting = db.get_meeting(meeting_id)

        if not meeting:
            return jsonify({'success': False, 'message': 'ReuniÃ£o nÃ£o encontrada'}), 404

        project_activities = []
        project_title = meeting.get('project_title')
        project_code = meeting.get('project_code')

        if meeting.get('project_id'):
            project = db.get_company_project(meeting['company_id'], meeting['project_id'])
            if project:
                project_title = project.get('title') or project_title
                project_code = project.get('code') or project_code
                activities_data = project.get('activities')
                if activities_data:
                    try:
                        if isinstance(activities_data, str):
                            project_activities = json.loads(activities_data)
                        else:
                            project_activities = list(activities_data)
                    except Exception:
                        project_activities = []

        meeting_activities = meeting.get('activities', [])

        return jsonify({
            'success': True,
            'project_activities': project_activities,
            'meeting_activities': meeting_activities,
            'project_id': meeting.get('project_id'),
            'project_title': project_title,
            'project_code': project_code
        })
            
    except Exception as e:
        logger.info(f"Erro ao buscar atividades: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@login_required
@meetings_bp.route("/api/company/<int:company_id>/agenda-item", methods=['POST'])
def api_save_agenda_item(company_id):
    """API: Salvar item de pauta para reutilizaÃ§Ã£o"""
    try:
        data = request.get_json()
        
        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO meeting_agenda_items (company_id, title, description, usage_count)
            VALUES (%s, %s, %s, 0)
        ''', (company_id, data.get('title'), data.get('description', '')))
        
        item_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'item_id': item_id, 'message': 'Item salvo para reutilizaÃ§Ã£o!'})
            
    except Exception as e:
        logger.info(f"Erro ao salvar item de pauta: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# RELATÃ“RIO SIMPLIFICADO
# ========================================

@meetings_bp.route("/company/<int:company_id>/meeting/<int:meeting_id>/report")
def meeting_report(company_id, meeting_id):
    """Gera relatÃ³rio individual de uma reuniÃ£o (versÃ£o unificada)"""
    try:
        db = get_db()
        meeting = db.get_meeting(meeting_id)
        
        if not meeting:
            flash('ReuniÃ£o nÃ£o encontrada', 'error')
            return redirect(url_for('meetings.meetings_manage', company_id=company_id))
        
        if meeting.get('company_id') != company_id:
            flash('ReuniÃ£o nÃ£o pertence a esta empresa', 'error')
            return redirect(url_for('meetings.meetings_manage', company_id=company_id))
            
        # Importar o gerador de relatÃ³rios unificado
        from relatorios.generators.meetings_report import MeetingsReportGenerator
        
        # Instanciar gerador usando Model_7
        report_generator = MeetingsReportGenerator(report_model_id=7)
        
        # Configurar para incluir todas as seÃ§Ãµes (garante que os participantes sejam incluÃ­dos)
        report_generator.configure(
            info=True,
            guests=True,
            agenda=True,
            participants=True,
            discussions=True,
            activities=True
        )
        
        # Gerar o conteÃºdo HTML
        html_content = report_generator.generate_html(
            company_id=company_id,
            meeting_id=meeting_id
        )
        
        # Retornar HTML diretamente
        from flask import Response
        return Response(html_content, mimetype='text/html; charset=utf-8')

    except Exception as e:
        logger.info(f"Erro ao gerar relatÃ³rio: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Erro ao gerar relatÃ³rio: {str(e)}', 'error')
        return redirect(url_for('meetings.meetings_manage', company_id=company_id))


# API: Incrementar uso de item de pauta
@login_required
@meetings_bp.route("/api/agenda-item/<int:item_id>/use", methods=['POST'])
def api_use_agenda_item(item_id):
    """API: Incrementar contador de uso de item de pauta"""
    try:
        from database.postgres_helper import connect as pg_connect
        conn = pg_connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE meeting_agenda_items 
            SET usage_count = usage_count + 1 
            WHERE id = %s
        ''', (item_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
            
    except Exception as e:
        logger.info(f"Erro ao incrementar uso: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500








