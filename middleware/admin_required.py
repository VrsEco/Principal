"""
Admin Required Decorator
Decorator para proteger rotas que requerem permissão de administrador
"""

from functools import wraps
from flask import jsonify, redirect, url_for, flash, request
from flask_login import current_user


def admin_required(f):
    """
    Decorator que verifica se o usuário é administrador.
    
    Uso:
        @admin_required
        @login_required
        @auth_bp.route("/users")
        def list_users():
            ...
    
    Retorna:
        - 403 JSON se for requisição API
        - Redirect para main se for requisição de página
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar se usuário está autenticado
        if not current_user or not current_user.is_authenticated:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    "success": False,
                    "message": "Não autenticado"
                }), 401
            flash("Faça login para acessar esta página.", "error")
            return redirect(url_for("auth.login"))
        
        # Verificar se é admin
        if getattr(current_user, "role", None) != "admin":
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    "success": False,
                    "message": "Acesso negado. Apenas administradores podem acessar este recurso."
                }), 403
            
            flash(
                "Acesso negado. Apenas administradores podem acessar esta página.",
                "error"
            )
            return redirect(url_for("main"))
        
        return f(*args, **kwargs)
    
    return decorated_function


