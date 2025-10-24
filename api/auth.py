"""
Authentication API endpoints
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user, login_user, logout_user
from services.auth_service import auth_service
from services.log_service import log_service

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication"""
    if request.method == 'GET':
        # If already logged in, redirect to dashboard
        if current_user and current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('auth/login.html')
    
    elif request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get('email', '').strip()
            password = data.get('password', '')
            
            if not email or not password:
                return jsonify({
                    'success': False,
                    'message': 'Email e senha são obrigatórios'
                }), 400
            
            # Authenticate user
            user = auth_service.authenticate_user(email, password)
            
            if user:
                # Login user
                remember = data.get('remember', False)
                auth_service.login_user_session(user, remember=remember)
                
                return jsonify({
                    'success': True,
                    'message': 'Login realizado com sucesso',
                    'user': user.to_dict(),
                    'redirect': url_for('dashboard')
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Email ou senha incorretos'
                }), 401
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Erro no login: {str(e)}'
            }), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    try:
        auth_service.logout_user_session()
        
        return jsonify({
            'success': True,
            'message': 'Logout realizado com sucesso',
            'redirect': url_for('login')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro no logout: {str(e)}'
        }), 500

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration (admin only)"""
    if request.method == 'GET':
        if not current_user or not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acesso negado. Apenas administradores podem criar usuários.', 'error')
            return redirect(url_for('login'))
        
        return render_template('auth/register.html')
    
    elif request.method == 'POST':
        if not current_user or not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Acesso negado'
            }), 403
        
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get('email', '').strip()
            password = data.get('password', '')
            name = data.get('name', '').strip()
            role = data.get('role', 'consultant').strip()
            
            if not email or not password or not name:
                return jsonify({
                    'success': False,
                    'message': 'Email, senha e nome são obrigatórios'
                }), 400
            
            # Create user
            user = auth_service.create_user(email, password, name, role)
            
            if user:
                return jsonify({
                    'success': True,
                    'message': 'Usuário criado com sucesso',
                    'user': user.to_dict()
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Email já está em uso'
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Erro ao criar usuário: {str(e)}'
            }), 500

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management"""
    if request.method == 'GET':
        return render_template('auth/profile.html', user=current_user)
    
    elif request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            # Update profile
            name = data.get('name', '').strip()
            role = data.get('role', '').strip() if current_user.role == 'admin' else None
            is_active = data.get('is_active') if current_user.role == 'admin' else None
            
            if is_active is not None:
                is_active = is_active.lower() in ['true', '1', 'yes', 'on']
            
            success = auth_service.update_user_profile(
                current_user,
                name=name if name else None,
                role=role if role else None,
                is_active=is_active
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Perfil atualizado com sucesso',
                    'user': current_user.to_dict()
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Falha ao atualizar perfil'
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Erro ao atualizar perfil: {str(e)}'
            }), 500

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.get_json() if request.is_json else request.form
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
        
        if not old_password or not new_password:
            return jsonify({
                'success': False,
                'message': 'Senha atual e nova senha são obrigatórias'
            }), 400
        
        if new_password != confirm_password:
            return jsonify({
                'success': False,
                'message': 'Nova senha e confirmação não coincidem'
            }), 400
        
        if len(new_password) < 6:
            return jsonify({
                'success': False,
                'message': 'Nova senha deve ter pelo menos 6 caracteres'
            }), 400
        
        success = auth_service.change_password(current_user, old_password, new_password)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Senha alterada com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Senha atual incorreta'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao alterar senha: {str(e)}'
        }), 500

@auth_bp.route('/users/page', methods=['GET'])
@login_required
def list_users_page():
    """User management page (admin only)"""
    if not current_user or current_user.role != 'admin':
        flash('Acesso negado. Apenas administradores podem gerenciar usuários.', 'error')
        return redirect(url_for('main'))
    
    return render_template('auth/users.html')

@auth_bp.route('/users', methods=['GET'])
@login_required
def list_users():
    """List all users API (admin only)"""
    if not current_user or current_user.role != 'admin':
        return jsonify({
            'success': False,
            'message': 'Acesso negado'
        }), 403
    
    try:
        users = auth_service.get_all_users(active_only=False)
        users_data = [user.to_dict() for user in users]
        
        return jsonify({
            'success': True,
            'users': users_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao listar usuários: {str(e)}'
        }), 500

@auth_bp.route('/users/<int:user_id>/status', methods=['PUT'])
@login_required
def toggle_user_status(user_id):
    """Toggle user active status (admin only)"""
    if not current_user or current_user.role != 'admin':
        return jsonify({
            'success': False,
            'message': 'Acesso negado'
        }), 403
    
    try:
        data = request.get_json() if request.is_json else request.form
        is_active = data.get('is_active', True)
        
        if isinstance(is_active, str):
            is_active = is_active.lower() in ['true', '1', 'yes', 'on']
        
        success = auth_service.update_user_status(user_id, is_active)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Usuário {"ativado" if is_active else "desativado"} com sucesso'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Usuário não encontrado'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar status: {str(e)}'
        }), 500

@auth_bp.route('/current-user', methods=['GET'])
@login_required
def get_current_user():
    """Get current user information"""
    try:
        return jsonify({
            'success': True,
            'user': current_user.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao obter usuário: {str(e)}'
        }), 500
