"""
Serviço para gerenciamento de Usuários e Colaboradores (Employees)
Implementa a lógica de criação e vínculo entre User -> Employee -> Company
"""
from typing import Optional, List, Dict, Any
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from models.user_employee_assignment import UserEmployeeAssignment
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
                whatsapp=user_data.get('whatsapp'),
                telegram=user_data.get('telegram'),
                instagram=user_data.get('instagram'),
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
        from services.identity.user_employee_orchestrator_service import (
            UserEmployeeOrchestratorService,
        )

        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'error': 'Usuário não encontrado'}

        payload = dict(employee_data or {})
        if role_id and 'role_id' not in payload:
            payload['role_id'] = role_id
        payload.setdefault('name', user.name)
        payload.setdefault('email', user.email)

        result = UserEmployeeOrchestratorService.register_or_link_user_employee(
            company_id=company_id,
            existing_user_id=user_id,
            create_system_access=True,
            employee_payload=payload,
        )
        if not result.get('success'):
            return result
        return {'success': True, 'employee': result.get('employee'), 'assignment': result.get('assignment')}

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
        from services.identity.user_employee_orchestrator_service import (
            UserEmployeeOrchestratorService,
        )

        return UserEmployeeOrchestratorService.link_user_to_companies(
            user_id=user_id,
            company_ids=company_ids,
            employee_payload=employee_data,
        )

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
        from services.identity.user_employee_orchestrator_service import (
            UserEmployeeOrchestratorService,
        )

        result = UserEmployeeOrchestratorService.register_or_link_user_employee(
            company_id=company_id,
            employee_payload=employee_data,
            create_system_access=False,
        )
        if not result.get('success'):
            return result
        return {'success': True, 'employee': result.get('employee')}

    @staticmethod
    def assign_user_to_employee(
        user_id: int,
        employee_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cria o vínculo (Associação/Acesso) entre um Usuário e um Colaborador (posição).
        Utiliza controle por períodos.
        """
        from datetime import datetime, date
        try:
            # Validar entrada de datas
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else date.today()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
            
            # Verificar se já existe vínculo ativo para este employee
            existing_active = UserEmployeeAssignment.query.filter_by(
                employee_id=employee_id,
                is_active=True
            ).filter((UserEmployeeAssignment.end_date == None) | (UserEmployeeAssignment.end_date >= start_dt)).first()
            
            if existing_active:
                return {
                    'success': False,
                    'error': f'O colaborador já possui um usuário vinculado ativo (ID: {existing_active.user_id}). Finalize o vínculo atual primeiro.'
                }
            
            # Criar a nova associação
            assignment = UserEmployeeAssignment(
                user_id=user_id,
                employee_id=employee_id,
                start_date=start_dt,
                end_date=end_dt,
                notes=notes,
                is_active=True,
                status='active'
            )
            
            # Legado: atualizar o user_id no model Employee para manter compatibilidade e garantir que esteja ativo
            employee = Employee.query.get(employee_id)
            if employee:
                employee.user_id = user_id
                employee.status = 'active'
                
            db.session.add(assignment)
            db.session.commit()
            
            return {
                'success': True,
                'assignment': assignment.to_dict()
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    @staticmethod
    def terminate_assignment(assignment_id: int, end_date: Optional[str] = None) -> Dict[str, Any]:
        """Finaliza uma associação usuário x colaborador."""
        from datetime import datetime, date
        try:
            assignment = UserEmployeeAssignment.query.get(assignment_id)
            if not assignment:
                return {'success': False, 'error': 'Associação não encontrada'}
            
            terminate_dt = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else date.today()
            
            assignment.end_date = terminate_dt
            assignment.is_active = False
            assignment.status = 'closed'
            
            # Legado: remover user_id do Employee se for a associação atual ativa
            employee = Employee.query.get(assignment.employee_id)
            if employee and employee.user_id == assignment.user_id:
                employee.user_id = None
            
            db.session.commit()
            return {'success': True}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}
