"""
User Logs API endpoints
"""

from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from services.log_service import log_service
from services.auth_service import auth_service

logs_bp = Blueprint('logs', __name__, url_prefix='/logs')

@logs_bp.route('/', methods=['GET'])
@login_required
def list_logs():
    """List user logs with filtering"""
    try:
        # Get query parameters
        entity_type = request.args.get('entity_type')
        action = request.args.get('action')
        user_id = request.args.get('user_id', type=int)
        company_id = request.args.get('company_id', type=int)
        
        # Date filtering
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            except Exception as exc:
                start_date = None
        
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            except Exception as exc:
                end_date = None
        
        # Pagination
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Restrict to current user unless admin
        if current_user.role != 'admin':
            user_id = current_user.id
        
        # Get logs
        logs = log_service.get_logs(
            user_id=user_id,
            entity_type=entity_type,
            action=action,
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        
        logs_data = [log.to_dict() for log in logs]
        
        return jsonify({
            'success': True,
            'logs': logs_data,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'count': len(logs_data)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao obter logs: {str(e)}'
        }), 500

@logs_bp.route('/stats', methods=['GET'])
@login_required
def get_log_stats():
    """Get logging statistics"""
    try:
        # Get query parameters
        company_id = request.args.get('company_id', type=int)
        
        # Date filtering (default to last 30 days)
        days = request.args.get('days', 30, type=int)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Restrict to current user unless admin
        if current_user.role != 'admin':
            # Non-admin users can only see their own stats
            user_id = current_user.id
            stats = log_service.get_log_stats(
                company_id=company_id,
                start_date=start_date,
                end_date=end_date
            )
            # Filter to only current user's logs
            user_logs = log_service.get_logs(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            stats['total_logs'] = len(user_logs)
        else:
            stats = log_service.get_log_stats(
                company_id=company_id,
                start_date=start_date,
                end_date=end_date
            )
        
        return jsonify({
            'success': True,
            'stats': stats,
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao obter estatÃ­sticas: {str(e)}'
        }), 500

@logs_bp.route('/dashboard', methods=['GET'])
@login_required
def logs_dashboard():
    """Logs dashboard page"""
    return render_template('logs/dashboard.html')

@logs_bp.route('/user-activity', methods=['GET'])
@login_required
def user_activity():
    """User activity page"""
    # Get user ID from query params or use current user
    user_id = request.args.get('user_id', type=int)
    
    # Restrict to current user unless admin
    if current_user.role != 'admin':
        user_id = current_user.id
    elif not user_id:
        user_id = current_user.id
    
    # Get user info
    user = auth_service.get_user_by_id(user_id)
    if not user:
        return jsonify({
            'success': False,
            'message': 'UsuÃ¡rio nÃ£o encontrado'
        }), 404
    
    return render_template('logs/user_activity.html', target_user=user)

@logs_bp.route('/entity-activity/<entity_type>/<entity_id>', methods=['GET'])
@login_required
def entity_activity(entity_type, entity_id):
    """Entity activity page"""
    try:
        # Get logs for specific entity
        logs = log_service.get_logs(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=100
        )
        
        logs_data = [log.to_dict() for log in logs]
        
        return jsonify({
            'success': True,
            'logs': logs_data,
            'entity': {
                'type': entity_type,
                'id': entity_id
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao obter atividade da entidade: {str(e)}'
        }), 500

@logs_bp.route('/export', methods=['GET'])
@login_required
def export_logs():
    """Export logs to CSV"""
    try:
        # Only admin can export all logs
        if current_user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acesso negado. Apenas administradores podem exportar logs.'
            }), 403
        
        # Get query parameters
        entity_type = request.args.get('entity_type')
        action = request.args.get('action')
        user_id = request.args.get('user_id', type=int)
        company_id = request.args.get('company_id', type=int)
        
        # Date filtering
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            except Exception as exc:
                start_date = None
        
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            except Exception as exc:
                end_date = None
        
        # Get all logs (no limit for export)
        logs = log_service.get_logs(
            user_id=user_id,
            entity_type=entity_type,
            action=action,
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Large limit for export
            offset=0
        )
        
        # Convert to CSV format
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Data/Hora',
            'UsuÃ¡rio',
            'Email',
            'AÃ§Ã£o',
            'Tipo de Entidade',
            'ID da Entidade',
            'Nome da Entidade',
            'DescriÃ§Ã£o',
            'IP',
            'Endpoint'
        ])
        
        # Write data
        for log in logs:
            writer.writerow([
                log.created_at.strftime('%d/%m/%Y %H:%M:%S'),
                log.user_name,
                log.user_email,
                log.action,
                log.entity_type,
                log.entity_id,
                log.entity_name,
                log.description,
                log.ip_address,
                log.endpoint
            ])
        
        output.seek(0)
        csv_content = output.getvalue()
        output.close()
        
        return jsonify({
            'success': True,
            'csv_content': csv_content,
            'filename': f'logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao exportar logs: {str(e)}'
        }), 500

