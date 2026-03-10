from functools import wraps
from flask import abort, request, session
from flask_login import current_user
def has_permission(company_id, resource, action):
    """
    Checks if the current user has a specific permission in a company.
    
    Hierarquia de acesso (User.role no modelo User):
      - 'admin'        → acesso total (sem restrição)
      - 'client'       → acesso total às empresas vinculadas (Cliente)
      - 'collaborator' → acesso restrito: somente objetos onde é responsável/executor
      - 'user'         → idem ao collaborator (acesso via permissões do cargo)
    """
    from models.employee import Employee
    if not current_user.is_authenticated:
        return False
    
    # Admin e Client têm acesso irrestrito
    if current_user.role in ('admin', 'client'):
        return True
        
    employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
    if not employee:
        return False
        
    # Superusers no cargo do employee também têm acesso irrestrito
    if employee.role and employee.role.title and employee.role.title.lower() == 'superuser':
        return True
        
    # Demais: verifica permissões específicas do cargo (JSON)
    perms = {}
    if employee.role and employee.role.permissions:
        perms = employee.role.permissions
        
    res_perms = perms.get(resource, [])
    return action in res_perms

def permission_required(resource, action):
    """
    Decorator to enforce permissions on routes.
    Expects 'company_id' to be present in request.args or view kwargs.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Try to find company_id in kwargs or request.args
            company_id = kwargs.get('company_id') or request.args.get('company_id', type=int)
            
            # If not found, try to find it in the JSON body
            if not company_id and request.is_json:
                try:
                    data = request.get_json(silent=True)
                    if data:
                        company_id = data.get('company_id')
                except:
                    pass

            if not company_id:
                # Admins e Clients têm acesso a tudo
                if current_user.role in ('admin', 'client'):
                    return f(*args, **kwargs)
                
                # Para os demais, verifica permissão em ALGUMA empresa vinculada
                from models.employee import Employee
                user_employees = Employee.query.filter_by(user_id=current_user.id).all()
                if not user_employees:
                    if request.path.startswith('/api/'):
                        return {"error": "Access denied: User is not associated with any company."}, 403
                    abort(403, description="Access denied: User is not associated with any company.")
                
                has_any_permission = False
                for emp in user_employees:
                    if has_permission(emp.company_id, resource, action):
                        has_any_permission = True
                        break
                
                if not has_any_permission:
                    if request.path.startswith('/api/'):
                        return {"error": f"Permission denied: {action} on {resource}"}, 403
                    abort(403, description=f"Permission denied: User does not have '{action}' permission on '{resource}' in any associated company.")
                
                return f(*args, **kwargs)

            if not has_permission(company_id, resource, action):
                if request.path.startswith('/api/'):
                    return {"error": f"Permission denied: {action} on {resource}"}, 403
                abort(403, description=f"Permission denied: {action} on {resource}")
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_collaborator_only():
    """
    Retorna True se o usuário atual é tratado como Colaborador restrito:
    - user.role == 'collaborator' (não é admin nem client)
    - E não tem cargo 'superuser' em nenhuma empresa vinculada
    """
    if not current_user.is_authenticated:
        return True
    if current_user.role in ('admin', 'client'):
        return False
    # Verifica se tem cargo superuser em alguma empresa
    from models.employee import Employee
    emps = Employee.query.filter_by(user_id=current_user.id).all()
    for emp in emps:
        if emp.role and emp.role.title and emp.role.title.lower() == 'superuser':
            return False
    return True

def is_collaborator_in_company(company_id):
    """
    Retorna True se o usuário atual é tratado como Colaborador restrito na empresa específica.
    """
    if not current_user.is_authenticated:
        return True
    if current_user.role in ('admin', 'client'):
        return False
    from models.employee import Employee
    emp = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
    if emp and emp.role and emp.role.title and emp.role.title.lower() == 'superuser':
        return False
    return True

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403, description="Acesso negado: Apenas administradores")
        return f(*args, **kwargs)
    return decorated_function
