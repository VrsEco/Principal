"""
Audit Middleware
Automatically logs all CRUD operations across the system
"""

from flask import request, current_app, g
from functools import wraps
from services.log_service import log_service
from flask_login import current_user
import json

class AuditMiddleware:
    """Middleware for automatic audit logging"""
    
    @staticmethod
    def log_request(f):
        """Decorator to log API requests"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip logging for certain endpoints
            skip_endpoints = [
                'static',
                'favicon',
                'logs.list_logs',
                'logs.get_log_stats'
            ]
            
            if request.endpoint in skip_endpoints:
                return f(*args, **kwargs)
            
            # Get request info
            method = request.method
            endpoint = request.endpoint or request.path
            entity_type = None
            entity_id = None
            entity_name = None
            
            # Try to extract entity info from URL
            if '/companies/' in request.path:
                entity_type = 'company'
                # Extract company ID from path
                path_parts = request.path.split('/')
                for i, part in enumerate(path_parts):
                    if part == 'companies' and i + 1 < len(path_parts):
                        try:
                            entity_id = path_parts[i + 1]
                            break
                        except:
                            pass
            
            elif '/plans/' in request.path:
                entity_type = 'plan'
                # Extract plan ID from path
                path_parts = request.path.split('/')
                for i, part in enumerate(path_parts):
                    if part == 'plans' and i + 1 < len(path_parts):
                        try:
                            entity_id = path_parts[i + 1]
                            break
                        except:
                            pass
            
            elif '/participants/' in request.path:
                entity_type = 'participant'
                # Extract participant ID from path
                path_parts = request.path.split('/')
                for i, part in enumerate(path_parts):
                    if part == 'participants' and i + 1 < len(path_parts):
                        try:
                            entity_id = path_parts[i + 1]
                            break
                        except:
                            pass
            
            # Store request info in g for use in response
            g.audit_info = {
                'entity_type': entity_type,
                'entity_id': entity_id,
                'entity_name': entity_name,
                'method': method,
                'endpoint': endpoint
            }
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    @staticmethod
    def log_response(response):
        """Log response after request processing"""
        try:
            # Skip logging for certain endpoints
            skip_endpoints = [
                'static',
                'favicon',
                'logs.list_logs',
                'logs.get_log_stats'
            ]
            
            if not hasattr(g, 'audit_info') or request.endpoint in skip_endpoints:
                return response
            
            audit_info = g.audit_info
            method = audit_info['method']
            entity_type = audit_info['entity_type']
            entity_id = audit_info['entity_id']
            
            # Determine action based on HTTP method and response status
            if response.status_code == 200:
                if method == 'POST':
                    action = 'CREATE'
                elif method == 'PUT' or method == 'PATCH':
                    action = 'UPDATE'
                elif method == 'DELETE':
                    action = 'DELETE'
                elif method == 'GET':
                    action = 'VIEW'
                else:
                    action = 'ACCESS'
                
                # Log the operation
                if entity_type and action in ['CREATE', 'UPDATE', 'DELETE']:
                    log_service.create_log(
                        action=action,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        entity_name=audit_info.get('entity_name'),
                        description=f"{action} {entity_type} via {method} {request.path}",
                        endpoint=request.endpoint,
                        method=method
                    )
            
        except Exception as e:
            # Don't let logging errors break the application
            current_app.logger.error(f"Audit logging error: {str(e)}")
        
        return response

def init_audit_middleware(app):
    """Initialize audit middleware for the Flask app"""
    
    # Add request logging decorator to all routes
    @app.before_request
    def before_request():
        AuditMiddleware.log_request(lambda: None)()
    
    # Add response logging
    @app.after_request
    def after_request(response):
        return AuditMiddleware.log_response(response)

# Decorators for manual logging
def log_operation(action, entity_type, entity_id=None, entity_name=None, 
                  old_values=None, new_values=None, description=None):
    """Decorator to manually log operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Call the original function
                result = f(*args, **kwargs)
                
                # Log the operation
                log_service.create_log(
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    old_values=old_values,
                    new_values=new_values,
                    description=description
                )
                
                return result
            except Exception as e:
                # Log error
                log_service.create_log(
                    action='ERROR',
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    description=f"Erro em {action} {entity_type}: {str(e)}"
                )
                raise e
        
        return decorated_function
    return decorator

def log_create(entity_type, get_entity_id=None, get_entity_name=None):
    """Decorator to log CREATE operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            
            if result:
                entity_id = None
                entity_name = None
                
                if get_entity_id:
                    entity_id = get_entity_id(result)
                if get_entity_name:
                    entity_name = get_entity_name(result)
                
                log_service.log_create(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    new_values=result.to_dict() if hasattr(result, 'to_dict') else None,
                    description=f"Criação de {entity_type}"
                )
            
            return result
        return decorated_function
    return decorator

def log_update(entity_type, get_entity_id=None, get_entity_name=None):
    """Decorator to log UPDATE operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get old values before update
            entity_id = None
            if get_entity_id:
                entity_id = get_entity_id(*args, **kwargs)
            
            old_values = None
            if entity_id:
                # Try to get old values from database
                try:
                    if entity_type == 'company':
                        from models.company import Company
                        old_entity = Company.query.get(entity_id)
                    elif entity_type == 'plan':
                        from models.plan import Plan
                        old_entity = Plan.query.get(entity_id)
                    elif entity_type == 'participant':
                        from models.participant import Participant
                        old_entity = Participant.query.get(entity_id)
                    else:
                        old_entity = None
                    
                    if old_entity and hasattr(old_entity, 'to_dict'):
                        old_values = old_entity.to_dict()
                except:
                    pass
            
            # Call the original function
            result = f(*args, **kwargs)
            
            if result:
                entity_name = None
                if get_entity_name:
                    entity_name = get_entity_name(result)
                
                new_values = result.to_dict() if hasattr(result, 'to_dict') else None
                
                log_service.log_update(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    old_values=old_values,
                    new_values=new_values,
                    description=f"Atualização de {entity_type}"
                )
            
            return result
        return decorated_function
    return decorator

def log_delete(entity_type, get_entity_id=None, get_entity_name=None):
    """Decorator to log DELETE operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get entity info before deletion
            entity_id = None
            entity_name = None
            old_values = None
            
            if get_entity_id:
                entity_id = get_entity_id(*args, **kwargs)
            
            if entity_id:
                # Try to get entity info from database
                try:
                    if entity_type == 'company':
                        from models.company import Company
                        entity = Company.query.get(entity_id)
                    elif entity_type == 'plan':
                        from models.plan import Plan
                        entity = Plan.query.get(entity_id)
                    elif entity_type == 'participant':
                        from models.participant import Participant
                        entity = Participant.query.get(entity_id)
                    else:
                        entity = None
                    
                    if entity:
                        if hasattr(entity, 'to_dict'):
                            old_values = entity.to_dict()
                        if get_entity_name:
                            entity_name = get_entity_name(entity)
                        elif hasattr(entity, 'name'):
                            entity_name = entity.name
                except:
                    pass
            
            # Call the original function
            result = f(*args, **kwargs)
            
            # Log the deletion
            log_service.log_delete(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                old_values=old_values,
                description=f"Exclusão de {entity_type}"
            )
            
            return result
        return decorated_function
    return decorator
