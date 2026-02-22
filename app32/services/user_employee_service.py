"""
Serviço para gerenciamento de Usuários e Colaboradores (Employees)
Implementa a lógica de criação e vínculo entre User -> Employee -> Company
"""
from typing import Optional, List, Dict, Any
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from models.role import Role
from werkzeug.security import generate_password_hash


class UserEmployeeService:
    """Serviço para gerenciar a relação User-Employee-Company"""

    @staticmethod
    def create_user_with_company(
        user_data: Dict[str, Any],
        company_data: Dict[str, Any],
        employee_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Cria um novo usuário, empresa e o vínculo de colaborador em uma transação.
        
        Args:
            user_data: Dados do usuário (name, email, password)
            company_data: Dados da empresa (name, cnpj, etc)
            employee_data: Dados adicionais do colaborador (opcional)
            
        Returns:
            Dict com user, company e employee criados
        """
        try:
            # 1. Criar o User (credenciais de acesso)
            user = User(
                name=user_data['name'],
                email=user_data['email'],
                role=user_data.get('role', 'client')  # admin, collaborator, client
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            db.session.flush()  # Gera o ID sem commitar
            
            # 2. Criar a Company
            company = Company(
                name=company_data['name'],
                legal_name=company_data.get('legal_name'),
                cnpj=company_data.get('cnpj'),
                segment=company_data.get('segment'),  # Campo segment existe no modelo
                city=company_data.get('city'),
                state=company_data.get('state')
            )
            
            # Definir client_code se fornecido
            if 'client_code' in company_data and company_data['client_code']:
                # client_code é gerenciado pelo database helper
                # Será definido via create_company se necessário
                pass
            db.session.add(company)
            db.session.flush()
            
            # 3. Criar o Employee (vínculo)
            employee = Employee(
                user_id=user.id,
                company_id=company.id,
                name=user_data['name'],  # Usa o nome do usuário por padrão
                email=user_data['email'],
                status='active'
            )
            
            # Adicionar dados extras do colaborador se fornecidos
            if employee_data:
                for key, value in employee_data.items():
                    if hasattr(employee, key):
                        setattr(employee, key, value)
            
            db.session.add(employee)
            db.session.commit()
            
            return {
                'success': True,
                'user': user.to_dict(),
                'company': company.to_dict(),
                'employee': employee.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def add_employee_to_company(
        user_id: int,
        company_id: int,
        role_id: Optional[int] = None,
        employee_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Adiciona um usuário existente como colaborador de uma empresa.
        Permite que um usuário trabalhe em múltiplas empresas.
        
        Args:
            user_id: ID do usuário existente
            company_id: ID da empresa
            role_id: ID do cargo (opcional)
            employee_data: Dados adicionais do colaborador
            
        Returns:
            Dict com employee criado
        """
        try:
            # Verificar se o usuário já é colaborador desta empresa
            existing = Employee.query.filter_by(
                user_id=user_id,
                company_id=company_id
            ).first()
            
            if existing:
                return {
                    'success': False,
                    'error': 'Usuário já é colaborador desta empresa'
                }
            
            # Buscar dados do usuário
            user = User.query.get(user_id)
            if not user:
                return {
                    'success': False,
                    'error': 'Usuário não encontrado'
                }
            
            # Criar novo Employee
            employee = Employee(
                user_id=user_id,
                company_id=company_id,
                role_id=role_id,
                name=user.name,
                email=user.email,
                status='active'
            )
            
            if employee_data:
                for key, value in employee_data.items():
                    if hasattr(employee, key):
                        setattr(employee, key, value)
            
            db.session.add(employee)
            db.session.commit()
            
            return {
                'success': True,
                'employee': employee.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            # Tratar erro de constraint única de forma mais amigável
            error_msg = str(e)
            if 'unique' in error_msg.lower() or 'duplicate' in error_msg.lower() or 'idx_employees' in error_msg.lower():
                return {
                    'success': False,
                    'error': 'Usuário já é colaborador desta empresa'
                }
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def add_employee_to_multiple_companies(
        user_id: int,
        company_ids: List[int],
        employee_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Adiciona um usuário existente como colaborador de múltiplas empresas de uma vez.
        
        Args:
            user_id: ID do usuário existente
            company_ids: Lista de IDs das empresas
            employee_data: Dados adicionais do colaborador (opcional)
            
        Returns:
            Dict com employees criados e contadores
        """
        try:
            # Validar entrada
            if not company_ids or len(company_ids) == 0:
                return {
                    'success': False,
                    'error': 'Nenhuma empresa foi fornecida'
                }
            
            # Verificar se usuário existe
            user = User.query.get(user_id)
            if not user:
                return {
                    'success': False,
                    'error': 'Usuário não encontrado'
                }
            
            # Verificar quais empresas já estão vinculadas
            existing_employees = Employee.query.filter(
                Employee.user_id == user_id,
                Employee.company_id.in_(company_ids)
            ).all()
            
            existing_company_ids = {emp.company_id for emp in existing_employees}
            new_company_ids = [cid for cid in company_ids if cid not in existing_company_ids]
            
            if not new_company_ids:
                return {
                    'success': False,
                    'error': 'Usuário já é colaborador de todas as empresas selecionadas'
                }
            
            # Criar novos Employees para empresas não vinculadas
            employees_created = []
            for company_id in new_company_ids:
                # Verificar se empresa existe usando query SQL direta (evita carregar colunas inexistentes)
                try:
                    from sqlalchemy import text
                    result = db.session.execute(
                        text("SELECT id FROM companies WHERE id = :company_id"),
                        {"company_id": company_id}
                    ).fetchone()
                    if not result:
                        continue  # Pula se empresa não existir
                except Exception as e:
                    # Se falhar, tentar verificar apenas se existe pelo ID usando exists()
                    try:
                        from sqlalchemy import exists
                        company_exists = db.session.query(
                            exists().where(Company.id == company_id)
                        ).scalar()
                        if not company_exists:
                            continue
                    except Exception:
                        # Se ainda falhar, pular esta empresa
                        continue
                
                employee = Employee(
                    user_id=user_id,
                    company_id=company_id,
                    name=user.name,
                    email=user.email,
                    status='active'
                )
                
                if employee_data:
                    for key, value in employee_data.items():
                        if hasattr(employee, key):
                            setattr(employee, key, value)
                
                db.session.add(employee)
                employees_created.append(employee)
            
            db.session.commit()
            
            return {
                'success': True,
                'linked_count': len(employees_created),
                'skipped_count': len(existing_company_ids),
                'employees': [emp.to_dict() for emp in employees_created]
            }
            
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            if 'unique' in error_msg.lower() or 'duplicate' in error_msg.lower() or 'idx_employees' in error_msg.lower():
                return {
                    'success': False,
                    'error': 'Erro ao vincular: uma ou mais empresas já estão vinculadas'
                }
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_user_companies(user_id: int) -> List[Dict[str, Any]]:
        """
        Retorna todas as empresas em que o usuário é colaborador.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Lista de empresas com informações do vínculo
        """
        employees = Employee.query.filter_by(user_id=user_id).all()
        
        result = []
        for emp in employees:
            # Buscar empresa usando apenas colunas que existem
            try:
                company = db.session.query(
                    Company.id, Company.name, Company.legal_name
                ).filter_by(id=emp.company_id).first()
                
                if company:
                    # Criar dict manualmente para evitar to_dict() que tenta acessar colunas inexistentes
                    company_dict = {
                        'id': company.id,
                        'name': company.name,
                        'legal_name': company.legal_name
                    }
                    result.append({
                        'employee_id': emp.id,
                        'company': company_dict,
                        'role_id': emp.role_id,
                        'status': emp.status
                    })
            except Exception as e:
                # Se falhar, tentar método alternativo
                try:
                    company = Company.query.with_entities(
                        Company.id, Company.name, Company.legal_name
                    ).filter_by(id=emp.company_id).first()
                    if company:
                        company_dict = {
                            'id': company.id,
                            'name': company.name,
                            'legal_name': company.legal_name
                        }
                        result.append({
                            'employee_id': emp.id,
                            'company': company_dict,
                            'role_id': emp.role_id,
                            'status': emp.status
                        })
                except Exception:
                    # Se ainda falhar, pular esta empresa
                    continue
        
        return result

    @staticmethod
    def get_user_activities(user_id: int) -> List[Dict[str, Any]]:
        """
        Retorna todas as atividades do usuário em todas as empresas.
        
        Args:
            user_id: ID do usuário
            
        Returns:
            Lista de atividades agregadas
        """
        from models.project import ProjectTask
        
        # Buscar todos os employee_ids do usuário
        employees = Employee.query.filter_by(user_id=user_id).all()
        employee_ids = [emp.id for emp in employees]
        
        if not employee_ids:
            return []
        
        # Buscar todas as tarefas onde o usuário é executor
        tasks = ProjectTask.query.filter(
            ProjectTask.employee_id.in_(employee_ids)
        ).all()
        
        result = []
        for task in tasks:
            # Encontrar qual employee está vinculado
            employee = next((e for e in employees if e.id == task.employee_id), None)
            
            result.append({
                'task': task.to_dict(),
                'company_id': employee.company_id if employee else None,
                'employee_name': employee.name if employee else None
            })
        
        return result

    @staticmethod
    def create_employee_without_user(
        company_id: int,
        employee_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cria um colaborador sem vínculo com usuário do sistema.
        Útil para funcionários que não precisam de acesso ao sistema.
        
        Args:
            company_id: ID da empresa
            employee_data: Dados do colaborador (name, email, etc)
            
        Returns:
            Dict com employee criado
        """
        try:
            employee = Employee(
                company_id=company_id,
                user_id=None,  # Sem vínculo com User
                name=employee_data['name'],
                email=employee_data.get('email'),
                phone=employee_data.get('phone'),
                department=employee_data.get('department'),
                status='active'
            )
            
            db.session.add(employee)
            db.session.commit()
            
            return {
                'success': True,
                'employee': employee.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
