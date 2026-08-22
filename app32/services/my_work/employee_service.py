from datetime import date
from typing import List, Dict, Any, Optional, Sequence, Tuple, Set
import logging
from models import db
from models.employee import Employee
from models.company import Company
from models.user import User
from models.user_employee_assignment import UserEmployeeAssignment
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from .utils import normalize_identity_value

logger = logging.getLogger(__name__)

def build_employee_lookup_v2(company_ids: List[int]) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Set[int]]]:
    """
    Build a directory and lookup table for employees in given companies.
    """
    if not company_ids:
        return {}, {}
    
    employees = Employee.query.filter(Employee.company_id.in_(company_ids)).all()
    
    directory = {}
    lookup = {}
    
    for emp in employees:
        directory[emp.id] = {"name": emp.name, "email": emp.email}
        for val in (emp.name, emp.email):
            key = normalize_identity_value(val)
            if not key:
                continue
            if key not in lookup:
                lookup[key] = set()
            lookup[key].add(emp.id)
            
    return directory, lookup

def get_employee_id_from_user(user_id: int) -> Optional[int]:
    """
    Map user_id to employee_id with fallback to email.
    Updated to use SQLAlchemy ORM.
    """
    try:
        # 1. Direct fetch by user_id
        employee = Employee.query.filter_by(user_id=user_id).first()
        if employee:
            return employee.id

        # 2. Fallback by email (legacy)
        user = User.query.get(user_id)
        if user and user.email:
            employee = Employee.query.filter(
                db.func.lower(Employee.email) == db.func.lower(user.email)
            ).first()
            
            if employee:
                logger.info(
                    "Employee fallback match found for user_id=%s by email on employee_id=%s "
                    "(sem auto-link legado).",
                    user_id,
                    employee.id,
                )
                return employee.id
        return None
    except Exception as e:
        logger.error(f"Error mapping user_id to employee_id: {e}")
        return None

def get_user_associated_companies(user_id: int) -> List[Dict[str, Any]]:
    """
    Return companies/employees explicitly associated with a user.

    Identity is resolved only through ``employees.user_id`` or an active
    ``user_employee_assignments`` record. Matching an employee by e-mail is
    intentionally forbidden here because it creates an implicit tenant grant.
    """
    user = User.query.get(user_id)
    if not user:
        return []

    query = db.session.query(
        Employee.id,
        Employee.name,
        Employee.email,
        Employee.user_id,
        Employee.status.label("employee_status"),
        Employee.company_id,
        Company.name.label("company_name"),
        Company.client_code.label("company_code"),
        Company.is_active.label("is_active"),
    ).outerjoin(Company, Company.id == Employee.company_id)

    # Compatibilidade explícita: Employee.user_id ainda é mantido pelo
    # orquestrador enquanto UserEmployeeAssignment preserva o histórico.
    results_by_id = query.filter(Employee.user_id == user_id).all()

    today = date.today()
    assignment_rows = db.session.query(UserEmployeeAssignment.employee_id).filter(
        UserEmployeeAssignment.user_id == user_id,
        UserEmployeeAssignment.is_active.is_(True),
        or_(
            UserEmployeeAssignment.start_date.is_(None),
            UserEmployeeAssignment.start_date <= today,
        ),
        or_(
            UserEmployeeAssignment.end_date.is_(None),
            UserEmployeeAssignment.end_date >= today,
        ),
    ).all()
    assignment_employee_ids = [row.employee_id for row in assignment_rows if row.employee_id]
    results_by_assignment = (
        query.filter(Employee.id.in_(assignment_employee_ids)).all()
        if assignment_employee_ids
        else []
    )

    merged_results = {r.id: r for r in (results_by_id + results_by_assignment)}
    results = list(merged_results.values())

    companies_data = {}
    for r in results:
        if not r.company_id:
            continue
        
        companies_data[r.company_id] = {
            "company_id": r.company_id,
            "company_name": r.company_name or "Empresa sem nome",
            "company_code": r.company_code,
            "employee_id": r.id,
            "employee_name": r.name,
            "employee_email": r.email,
            "employee_status": r.employee_status,
            "user_id": user_id,
            "is_active": r.is_active,
        }
    
    return list(companies_data.values())

def fetch_collaborator_directory(company_ids: List[int]) -> List[Dict[str, Any]]:
    """
    Fetch all collaborators for a list of companies.
    """
    if not company_ids:
        return []

    # Using joinedload to avoid N+1 is good but here we just need a few fields
    results = db.session.query(
        Employee.id,
        Employee.name,
        Employee.email,
        Employee.user_id,
        Employee.company_id,
        Company.name.label("company_name")
    ).join(Company, Company.id == Employee.company_id, isouter=True)\
     .filter(Employee.company_id.in_(company_ids))\
     .filter(db.or_(
         Employee.status == None,
         db.func.lower(Employee.status) != 'inactive'
     ))\
     .order_by(Company.name, Employee.name).all()

    return [
        {
            "id": r.id,
            "name": r.name or "Colaborador",
            "email": r.email,
            "user_id": r.user_id,
            "company_id": r.company_id,
            "company_name": r.company_name,
        }
        for r in results if r.id is not None
    ]
