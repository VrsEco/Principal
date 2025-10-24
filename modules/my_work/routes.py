"""
Rotas do Módulo My Work
APIs e páginas para gestão de atividades
"""
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from . import my_work_bp
from services.my_work_service import (
    get_employee_from_user,
    get_user_activities,
    get_user_stats,
    count_activities_by_scope,
    get_team_overview,
    get_company_overview,
    add_work_hours,
    add_comment,
    complete_activity
)
from middleware.auto_log_decorator import auto_log_crud


# ============================================================================
# PÁGINAS
# ============================================================================

@my_work_bp.route('/')
@login_required
def dashboard():
    """
    Página principal - My Work Dashboard
    """
    return render_template('my_work.html')


# ============================================================================
# APIs - LISTAGEM
# ============================================================================

@my_work_bp.route('/api/activities')
@login_required
def get_activities():
    """
    API: Lista de atividades conforme escopo
    
    Query Params:
        - scope: 'me', 'team' ou 'company'
        - filter: 'all', 'today', 'week', 'overdue'
        - search: texto de busca
        - sort: 'deadline', 'priority', 'status'
    """
    try:
        # Mapear user para employee
        employee_id = get_employee_from_user(current_user.id)
        
        # Parâmetros
        scope = request.args.get('scope', 'me')
        filters = {
            'filter': request.args.get('filter', 'all'),
            'search': request.args.get('search', ''),
            'sort': request.args.get('sort', 'deadline')
        }
        
        # Buscar atividades
        activities = get_user_activities(employee_id, scope, filters)
        
        # Buscar estatísticas
        stats = get_user_stats(employee_id, scope)
        
        # Contadores das abas
        counts = count_activities_by_scope(employee_id)
        
        return jsonify({
            'success': True,
            'data': activities,
            'stats': stats,
            'counts': counts
        })
        
    except PermissionError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 403
    except Exception as e:
        print(f"Erro ao buscar atividades: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@my_work_bp.route('/api/team-overview')
@login_required
def api_team_overview():
    """
    API: Dados do Team Overview
    """
    try:
        employee_id = get_employee_from_user(current_user.id)
        
        data = get_team_overview(employee_id)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except PermissionError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@my_work_bp.route('/api/company-overview')
@login_required
def api_company_overview():
    """
    API: Dados executivos para Company Overview
    """
    try:
        employee_id = get_employee_from_user(current_user.id)
        
        data = get_company_overview(employee_id)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except PermissionError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# APIs - AÇÕES
# ============================================================================

@my_work_bp.route('/api/work-hours', methods=['POST'])
@login_required
@auto_log_crud('activity_work_log')
def api_add_work_hours():
    """
    API: Adicionar horas trabalhadas
    
    Payload:
        {
            "activity_type": "project" | "process",
            "activity_id": 123,
            "work_date": "2025-10-21",
            "hours": 2.5,
            "description": "..."
        }
    """
    try:
        employee_id = get_employee_from_user(current_user.id)
        
        data = request.get_json()
        
        # Validações
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não fornecidos'
            }), 400
        
        if 'activity_type' not in data or 'activity_id' not in data:
            return jsonify({
                'success': False,
                'error': 'activity_type e activity_id obrigatórios'
            }), 400
        
        if 'hours' not in data or data['hours'] <= 0:
            return jsonify({
                'success': False,
                'error': 'Horas devem ser maior que zero'
            }), 400
        
        # Adicionar horas
        result = add_work_hours(
            employee_id,
            data['activity_type'],
            data['activity_id'],
            {
                'work_date': data.get('work_date', datetime.now().date().isoformat()),
                'hours': data['hours'],
                'description': data.get('description')
            }
        )
        
        return jsonify({
            'success': True,
            'data': result,
            'message': result['message']
        })
        
    except Exception as e:
        print(f"Erro ao adicionar horas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@my_work_bp.route('/api/comments', methods=['POST'])
@login_required
@auto_log_crud('activity_comment')
def api_add_comment():
    """
    API: Adicionar comentário em atividade
    
    Payload:
        {
            "activity_type": "project" | "process",
            "activity_id": 123,
            "comment_type": "note",
            "comment": "...",
            "is_private": false
        }
    """
    try:
        employee_id = get_employee_from_user(current_user.id)
        
        data = request.get_json()
        
        # Validações
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não fornecidos'
            }), 400
        
        if 'activity_type' not in data or 'activity_id' not in data:
            return jsonify({
                'success': False,
                'error': 'activity_type e activity_id obrigatórios'
            }), 400
        
        if 'comment' not in data or not data['comment'].strip():
            return jsonify({
                'success': False,
                'error': 'Comentário não pode ser vazio'
            }), 400
        
        # Adicionar comentário
        result = add_comment(
            employee_id,
            data['activity_type'],
            data['activity_id'],
            {
                'comment_type': data.get('comment_type', 'note'),
                'comment': data['comment'],
                'is_private': data.get('is_private', False)
            }
        )
        
        return jsonify({
            'success': True,
            'data': result,
            'message': result['message']
        })
        
    except Exception as e:
        print(f"Erro ao adicionar comentário: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@my_work_bp.route('/api/complete', methods=['POST'])
@login_required
@auto_log_crud('activity')
def api_complete_activity():
    """
    API: Finalizar atividade
    
    Payload:
        {
            "activity_type": "project" | "process",
            "activity_id": 123,
            "completion_comment": "..." (opcional)
        }
    """
    try:
        employee_id = get_employee_from_user(current_user.id)
        
        data = request.get_json()
        
        # Validações
        if not data:
            return jsonify({
                'success': False,
                'error': 'Dados não fornecidos'
            }), 400
        
        if 'activity_type' not in data or 'activity_id' not in data:
            return jsonify({
                'success': False,
                'error': 'activity_type e activity_id obrigatórios'
            }), 400
        
        # Finalizar
        result = complete_activity(
            employee_id,
            data['activity_type'],
            data['activity_id'],
            {
                'completion_comment': data.get('completion_comment')
            }
        )
        
        return jsonify({
            'success': True,
            'data': result,
            'message': result['message']
        })
        
    except Exception as e:
        print(f"Erro ao finalizar atividade: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# APIs - DETALHAMENTO
# ============================================================================

@my_work_bp.route('/activity/<int:activity_id>')
@login_required
def view_project_activity(activity_id):
    """
    Página de detalhes da atividade de projeto
    """
    # TODO: Implementar página de detalhamento
    return f"<h1>Detalhes da Atividade de Projeto #{activity_id}</h1><p>Em desenvolvimento...</p>"


@my_work_bp.route('/process-instance/<int:instance_id>')
@login_required
def view_process_instance(instance_id):
    """
    Página de detalhes da instância de processo
    """
    # TODO: Implementar página de detalhamento
    return f"<h1>Detalhes da Instância de Processo #{instance_id}</h1><p>Em desenvolvimento...</p>"

