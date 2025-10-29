"""
Authentication Service
Handles user authentication, session management, and user creation
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User
from models import db
from services.log_service import log_service

class AuthService:
    """Service for user authentication and management"""
    
    @staticmethod
    def create_user(email, password, name, role='consultant'):
        """
        Create a new user
        
        Args:
            email (str): User email
            password (str): Plain text password
            name (str): User full name
            role (str): User role (admin, consultant, client)
        
        Returns:
            User object if created successfully, None otherwise
        """
        try:
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return None
            
            # Create new user
            user = User(
                email=email,
                name=name,
                role=role,
                is_active=True
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # Log user creation - Temporarily disabled
            # log_service.log_create(
            #     entity_type='user',
            #     entity_id=user.id,
            #     entity_name=user.name,
            #     new_values={
            #         'email': user.email,
            #         'name': user.name,
            #         'role': user.role
            #     },
            #     description=f"Usuário criado: {user.name} ({user.email})"
            # )
            
            return user
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def authenticate_user(email, password):
        """
        Authenticate user with email and password
        
        Args:
            email (str): User email
            password (str): Plain text password
        
        Returns:
            User object if authenticated, None otherwise
        """
        try:
            user = User.query.filter_by(email=email, is_active=True).first()
            
            if user and user.check_password(password):
                # Log successful login - Temporarily disabled
                # log_service.log_login(user, success=True)
                return user
            else:
                # Log failed login attempt - Temporarily disabled
                # log_service.log_login(user, success=False)
                return None
                
        except Exception as e:
            # Log failed login attempt - Temporarily disabled
            # log_service.log_login(None, success=False)
            raise e
    
    @staticmethod
    def login_user_session(user, remember=False):
        """
        Login user and start session
        
        Args:
            user (User): User object
            remember (bool): Remember user login
        
        Returns:
            bool: True if login successful
        """
        try:
            success = login_user(user, remember=remember)
            if success:
                log_service.log_login(user, success=True)
            return success
        except Exception as e:
            log_service.log_login(user, success=False)
            raise e
    
    @staticmethod
    def logout_user_session():
        """
        Logout current user
        
        Returns:
            bool: True if logout successful
        """
        try:
            if current_user and current_user.is_authenticated:
                log_service.log_logout(current_user)
                logout_user()
                return True
            return False
        except Exception as e:
            raise e
    
    @staticmethod
    def change_password(user, old_password, new_password):
        """
        Change user password
        
        Args:
            user (User): User object
            old_password (str): Current password
            new_password (str): New password
        
        Returns:
            bool: True if password changed successfully
        """
        try:
            if not user.check_password(old_password):
                return False
            
            user.set_password(new_password)
            user.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log password change
            log_service.log_update(
                entity_type='user',
                entity_id=user.id,
                entity_name=user.name,
                old_values={'password': '***'},
                new_values={'password': '***'},
                description=f"Senha alterada por {user.name}"
            )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def update_user_profile(user, name=None, role=None, is_active=None):
        """
        Update user profile
        
        Args:
            user (User): User object
            name (str): New name
            role (str): New role
            is_active (bool): Active status
        
        Returns:
            bool: True if updated successfully
        """
        try:
            old_values = {
                'name': user.name,
                'role': user.role,
                'is_active': user.is_active
            }
            
            if name is not None:
                user.name = name
            if role is not None:
                user.role = role
            if is_active is not None:
                user.is_active = is_active
            
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Log profile update
            log_service.log_update(
                entity_type='user',
                entity_id=user.id,
                entity_name=user.name,
                old_values=old_values,
                new_values={
                    'name': user.name,
                    'role': user.role,
                    'is_active': user.is_active
                },
                description=f"Perfil atualizado por {user.name}"
            )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        return User.query.get(user_id)
    
    @staticmethod
    def get_user_by_email(email):
        """Get user by email"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def get_all_users(active_only=True):
        """Get all users"""
        query = User.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(User.name).all()
    
    @staticmethod
    def update_user_status(user_id, is_active):
        """
        Update user active status
        
        Args:
            user_id (int): User ID
            is_active (bool): New active status
        
        Returns:
            bool: True if updated successfully, False if user not found
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            old_status = user.is_active
            user.is_active = is_active
            user.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log status change
            log_service.log_update(
                entity_type='user',
                entity_id=user.id,
                entity_name=user.name,
                old_values={'is_active': old_status},
                new_values={'is_active': is_active},
                description=f"Status do usuário {user.name} alterado para {'ativo' if is_active else 'inativo'}"
            )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def create_admin_user():
        """
        Create default admin user if it doesn't exist
        """
        try:
            admin_email = 'admin@versus.com.br'
            admin_user = User.query.filter_by(email=admin_email).first()
            
            if not admin_user:
                admin_user = AuthService.create_user(
                    email=admin_email,
                    password='123456',
                    name='Administrador',
                    role='admin'
                )
                
                if admin_user:
                    print(f"✅ Usuário administrador criado: {admin_email}")
                    return admin_user
                else:
                    print(f"❌ Falha ao criar usuário administrador")
                    return None
            else:
                print(f"ℹ️ Usuário administrador já existe: {admin_email}")
                return admin_user
                
        except Exception as e:
            print(f"❌ Erro ao criar usuário administrador: {str(e)}")
            return None

# Global instance
auth_service = AuthService()
