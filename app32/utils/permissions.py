from functools import wraps
from flask import abort, request, jsonify
from flask_login import current_user
from models import Employee, Role, db


def admin_required(f):
    """
    Decorator to restrict access to systems administrators.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            if request.path.startswith("/api/"):
                return jsonify({"error": "Acesso negado: Apenas administradores"}), 403
            abort(403, description="Acesso negado: Apenas administradores")
        return f(*args, **kwargs)

    return decorated_function

def has_permission(company_id, resource, action):
    """
    Checks if the current user has permission for a specific resource and action in a company.
    
    :param company_id: ID of the company
    :param resource: Name of the resource (e.g., 'projects', 'indicators', 'processes')
    :param action: Action to perform ('view', 'create', 'edit', 'delete')
    :return: Boolean
    """
    if not current_user.is_authenticated:
        return False
    
    # Global Admin has all permissions
    if current_user.role == 'admin':
        return True
    
    if not company_id:
        return False
        
    print(f"DEBUG: Checking perm for user {current_user.id} in company {company_id}: {resource}.{action}")
    
    # Get the employee record for the current user and company
    employee = Employee.query.filter_by(user_id=current_user.id, company_id=company_id).first()
    if not employee:
        print(f"DEBUG: No employee record found for user {current_user.id} in company {company_id}")
        return False
        
    if not employee.role_id:
        print(f"DEBUG: Employee found but no role_id assigned.")
        return False
    
    # Get the role permissions
    role = Role.query.get(employee.role_id)
    if not role or not role.permissions:
        print(f"DEBUG: Role {employee.role_id} not found or has no permissions.")
        return False
    
    resource_perms = role.permissions.get(resource)
    print(f"DEBUG: Resource permissions for '{resource}': {resource_perms}")
    
    if not resource_perms:
        return False
        
    if isinstance(resource_perms, list):
        result = action in resource_perms
        print(f"DEBUG: Action '{action}' in list: {result}")
        return result
    elif isinstance(resource_perms, dict):
        result = resource_perms.get(action, False)
        print(f"DEBUG: Action '{action}' in dict: {result}")
        return result
        
    return False

def permission_required(resource, action):
    """
    Decorator to enforce permissions on routes.
    Expects 'company_id' to be present in request.args or view kwargs.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from datetime import datetime
            log_path = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/logs/perm_debug.log'
            try:
                with open(log_path, 'a') as lf:
                    lf.write(f"[{datetime.now()}] PERM_REQUIRED check: {resource}.{action} for PATH {request.path}\n")
                    lf.write(f"  User: {current_user.id if current_user.is_authenticated else 'Anonymous'}, Role: {current_user.role if current_user.is_authenticated else 'None'}\n")
                    lf.write(f"  Args: {dict(request.args)}\n")
            except:
                pass
                
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
            
            try:
                with open(log_path, 'a') as lf:
                    lf.write(f"  Resolved company_id for perm: {company_id}\n")
            except:
                pass

            if not company_id:
                # 1. Admins have access to everything
                if current_user.role == 'admin':
                    try:
                        with open(log_path, 'a') as lf:
                            lf.write(f"  Admin bypass - proceeding\n")
                    except:
                        pass
                    return f(*args, **kwargs)
                
                # 2. For non-admins, check if they have permission in ANY company they belong to
                user_employees = Employee.query.filter_by(user_id=current_user.id).all()
                if not user_employees:
                    try:
                        with open(log_path, 'a') as lf:
                            lf.write(f"  Access denied: No company association\n")
                    except:
                        pass
                    if request.path.startswith('/api/'):
                        return {"error": "Access denied: User is not associated with any company."}, 403
                    abort(403, description="Access denied: User is not associated with any company.")
                
                has_any_permission = False
                for emp in user_employees:
                    if has_permission(emp.company_id, resource, action):
                        has_any_permission = True
                        break
                
                if not has_any_permission:
                    try:
                        with open(log_path, 'a') as lf:
                            lf.write(f"  Permission denied: No company with {action} on {resource}\n")
                    except:
                        pass
                    if request.path.startswith('/api/'):
                        return {"error": f"Permission denied: {action} on {resource}"}, 403
                    abort(403, description=f"Permission denied: User does not have '{action}' permission on '{resource}' in any associated company.")
                
                return f(*args, **kwargs)

            if not has_permission(company_id, resource, action):
                try:
                    with open(log_path, 'a') as lf:
                        lf.write(f"  Permission denied: {action} on {resource} for company {company_id}\n")
                except:
                    pass
                if request.path.startswith('/api/'):
                    return {"error": f"Permission denied: {action} on {resource}"}, 403
                abort(403, description=f"Permission denied: {action} on {resource}")
                
            try:
                with open(log_path, 'a') as lf:
                    lf.write(f"  Permission OK - proceeding\n")
            except:
                pass
            return f(*args, **kwargs)
        return decorated_function
    return decorator
