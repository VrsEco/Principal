"""
User Logging Service
Responsible for recording all user activities and system operations
"""

import json
from datetime import datetime
from flask import request, current_app
from flask_login import current_user
from models.user_log import UserLog
from models import db

class LogService:
    """Service for logging user activities"""
    
    @staticmethod
    def get_user_context():
        """Get current user context for logging"""
        try:
            if current_user and current_user.is_authenticated:
                return {
                    'user_id': current_user.id,
                    'user_email': current_user.email,
                    'user_name': current_user.name
                }
        except RuntimeError:
            # Working outside of request context, try to get admin user
            try:
                from models.user import User
                admin_user = User.query.filter_by(email='admin@versus.com.br').first()
                if admin_user:
                    return {
                        'user_id': admin_user.id,
                        'user_email': admin_user.email,
                        'user_name': admin_user.name
                    }
            except:
                pass
        
        return {
            'user_id': None,
            'user_email': 'anonymous',
            'user_name': 'Usuário Anônimo'
        }
    
    @staticmethod
    def get_request_context():
        """Get current request context for logging"""
        try:
            return {
                'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR')),
                'user_agent': request.environ.get('HTTP_USER_AGENT', ''),
                'endpoint': request.endpoint or request.path,
                'method': request.method
            }
        except RuntimeError:
            # Working outside of request context
            return {
                'ip_address': '127.0.0.1',
                'user_agent': 'System/Setup',
                'endpoint': 'setup',
                'method': 'SYSTEM'
            }
    
    @staticmethod
    def create_log(action, entity_type, entity_id=None, entity_name=None, 
                   old_values=None, new_values=None, description=None, 
                   company_id=None, plan_id=None):
        """
        Create a new log entry
        
        Args:
            action (str): Action performed (CREATE, UPDATE, DELETE, LOGIN, LOGOUT, VIEW)
            entity_type (str): Type of entity affected (company, plan, participant, etc.)
            entity_id (str): ID of the affected entity
            entity_name (str): Name/title of the affected entity
            old_values (dict): Previous values (for updates/deletes)
            new_values (dict): New values (for creates/updates)
            description (str): Human readable description
            company_id (int): Related company ID
            plan_id (str): Related plan ID
        """
        try:
            user_context = LogService.get_user_context()
            request_context = LogService.get_request_context()
            
            # Convert dict to JSON string if needed
            try:
                old_values_str = json.dumps(old_values, ensure_ascii=True) if old_values else None
                new_values_str = json.dumps(new_values, ensure_ascii=True) if new_values else None
            except (TypeError, ValueError, UnicodeDecodeError) as e:
                # Fallback for encoding issues
                old_values_str = str(old_values) if old_values else None
                new_values_str = str(new_values) if new_values else None
            
            log_entry = UserLog(
                user_id=user_context['user_id'],
                user_email=user_context['user_email'],
                user_name=user_context['user_name'],
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id else None,
                entity_name=entity_name,
                old_values=old_values_str,
                new_values=new_values_str,
                ip_address=request_context['ip_address'],
                user_agent=request_context['user_agent'][:500],  # Limit size
                endpoint=request_context['endpoint'],
                method=request_context['method'],
                description=description,
                company_id=company_id,
                plan_id=plan_id
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
            return log_entry
            
        except Exception as e:
            # Don't let logging errors break the application
            current_app.logger.error(f"Failed to create log entry: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            return None
    
    @staticmethod
    def log_login(user, success=True):
        """Log user login attempt"""
        description = f"Login {'bem-sucedido' if success else 'falhado'}"
        return LogService.create_log(
            action='LOGIN' if success else 'LOGIN_FAILED',
            entity_type='user',
            entity_id=user.id if user else None,
            entity_name=user.name if user else 'Usuário Desconhecido',
            description=description
        )
    
    @staticmethod
    def log_logout(user):
        """Log user logout"""
        return LogService.create_log(
            action='LOGOUT',
            entity_type='user',
            entity_id=user.id,
            entity_name=user.name,
            description=f"Logout realizado por {user.name}"
        )
    
    @staticmethod
    def log_create(entity_type, entity_id, entity_name, new_values, description=None, company_id=None, plan_id=None):
        """Log entity creation"""
        return LogService.create_log(
            action='CREATE',
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            new_values=new_values,
            description=description or f"Criação de {entity_type}: {entity_name}",
            company_id=company_id,
            plan_id=plan_id
        )
    
    @staticmethod
    def log_update(entity_type, entity_id, entity_name, old_values, new_values, description=None, company_id=None, plan_id=None):
        """Log entity update"""
        return LogService.create_log(
            action='UPDATE',
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            old_values=old_values,
            new_values=new_values,
            description=description or f"Atualização de {entity_type}: {entity_name}",
            company_id=company_id,
            plan_id=plan_id
        )
    
    @staticmethod
    def log_delete(entity_type, entity_id, entity_name, old_values, description=None, company_id=None, plan_id=None):
        """Log entity deletion"""
        return LogService.create_log(
            action='DELETE',
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            old_values=old_values,
            description=description or f"Exclusão de {entity_type}: {entity_name}",
            company_id=company_id,
            plan_id=plan_id
        )
    
    @staticmethod
    def log_view(entity_type, entity_id=None, entity_name=None, description=None, company_id=None, plan_id=None):
        """Log entity view (for important views)"""
        return LogService.create_log(
            action='VIEW',
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description or f"Visualização de {entity_type}" + (f": {entity_name}" if entity_name else ""),
            company_id=company_id,
            plan_id=plan_id
        )
    
    @staticmethod
    def get_logs(user_id=None, entity_type=None, action=None, company_id=None, 
                 start_date=None, end_date=None, limit=100, offset=0):
        """
        Retrieve logs with filtering options
        
        Args:
            user_id (int): Filter by user ID
            entity_type (str): Filter by entity type
            action (str): Filter by action
            company_id (int): Filter by company ID
            start_date (datetime): Filter logs from this date
            end_date (datetime): Filter logs to this date
            limit (int): Maximum number of logs to return
            offset (int): Number of logs to skip
        
        Returns:
            List of UserLog objects
        """
        query = UserLog.query
        
        if user_id:
            query = query.filter(UserLog.user_id == user_id)
        if entity_type:
            query = query.filter(UserLog.entity_type == entity_type)
        if action:
            query = query.filter(UserLog.action == action)
        if company_id:
            query = query.filter(UserLog.company_id == company_id)
        if start_date:
            query = query.filter(UserLog.created_at >= start_date)
        if end_date:
            query = query.filter(UserLog.created_at <= end_date)
        
        return query.order_by(UserLog.created_at.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def get_log_stats(company_id=None, start_date=None, end_date=None):
        """
        Get logging statistics
        
        Returns:
            Dict with statistics
        """
        query = UserLog.query
        
        if company_id:
            query = query.filter(UserLog.company_id == company_id)
        if start_date:
            query = query.filter(UserLog.created_at >= start_date)
        if end_date:
            query = query.filter(UserLog.created_at <= end_date)
        
        total_logs = query.count()
        
        # Group by action
        actions = db.session.query(
            UserLog.action,
            db.func.count(UserLog.id)
        ).filter(
            UserLog.id.in_(query.with_entities(UserLog.id))
        ).group_by(UserLog.action).all()
        
        # Group by entity type
        entities = db.session.query(
            UserLog.entity_type,
            db.func.count(UserLog.id)
        ).filter(
            UserLog.id.in_(query.with_entities(UserLog.id))
        ).group_by(UserLog.entity_type).all()
        
        # Group by user
        users = db.session.query(
            UserLog.user_name,
            db.func.count(UserLog.id)
        ).filter(
            UserLog.id.in_(query.with_entities(UserLog.id))
        ).group_by(UserLog.user_name).order_by(db.func.count(UserLog.id).desc()).limit(10).all()
        
        return {
            'total_logs': total_logs,
            'actions': dict(actions),
            'entities': dict(entities),
            'top_users': dict(users)
        }

# Global instance
log_service = LogService()
