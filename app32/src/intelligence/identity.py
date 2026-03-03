import logging
from typing import Optional, Tuple
from models.user import User
from models.employee import Employee
from models import db

logger = logging.getLogger(__name__)

def resolve_user_identity(identifier: str, channel: str) -> Optional[User]:
    """
    Resolve a identidade de um usuário baseado em um identificador de canal.
    Canais suportados: telegram, whatsapp, email, instagram.
    """
    if not identifier:
        return None

    # Normalização básica
    identifier = identifier.strip()
    
    # 1. Busca direta no Modelo User (Prioridade)
    user = None
    if channel == 'telegram':
        user = User.query.filter_by(telegram=identifier).first()
    elif channel == 'whatsapp':
        user = User.query.filter_by(whatsapp=identifier).first()
    elif channel == 'email':
        user = User.query.filter_by(email=identifier).first()
    elif channel == 'instagram':
        # Instagram costuma compartilhar o mesmo ID/User do Messenger ou ter campo próprio
        # TODO: Adicionar coluna 'instagram' ao modelo User via migração alembic
        pass

    if user:
        return user

    # 2. Busca via Modelo Employee (Secundário - vínculo empresa)
    employee = None
    if channel == 'telegram':
        employee = Employee.query.filter_by(telegram=identifier).first()
    elif channel == 'whatsapp':
        # Tenta whatsapp ou phone
        employee = Employee.query.filter((Employee.whatsapp == identifier) | (Employee.phone == identifier)).first()
    elif channel == 'email':
        employee = Employee.query.filter_by(email=identifier).first()

    if employee and employee.user_id:
        return db.session.get(User, employee.user_id)

    return None

def get_best_company_id(user: User) -> Optional[int]:
    """Tenta encontrar o ID da empresa mais relevante para o contexto do usuário."""
    # Se for admin e não tiver funcionários diretos, pegamos a primeira empresa ativa
    from models.company import Company
    if user.role == 'admin':
        first_company = Company.query.filter_by(status='active').first()
        if first_company:
            return first_company.id

    # Busca vínculos de funcionário
    employee = Employee.query.filter_by(user_id=user.id).first()
    if employee:
        return employee.company_id
        
    return None
