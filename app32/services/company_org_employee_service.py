"""Cadastro estrutural sem criação de login ou alteração de permissões."""
from models import Company, Employee, Role, db
from services.identity.identity_normalizer import normalize_name
from services.identity.user_employee_orchestrator_service import UserEmployeeOrchestratorService


def create_org_employee(company_id, role_id, payload):
    if not isinstance(payload, dict) or set(payload) - {"name"}:
        raise ValueError("Informe apenas o nome do colaborador; acesso é uma operação separada.")
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 200:
        raise ValueError("Nome obrigatório, com até 200 caracteres.")
    name = name.strip()
    # Serializa cadastros deste fluxo no tenant para impedir duplo clique concorrente.
    Company.query.filter_by(id=company_id).with_for_update().first_or_404()
    role = Role.query.filter_by(id=role_id, company_id=company_id).first_or_404()
    employees = Employee.query.filter_by(company_id=company_id).all()
    if any(normalize_name(employee.name) == normalize_name(name) for employee in employees):
        raise ValueError("Já existe colaborador com esse nome nesta empresa. Revise o cadastro existente; não será criado outro automaticamente.")
    result = UserEmployeeOrchestratorService.register_or_link_user_employee(
        company_id=company_id,
        create_system_access=False,
        employee_payload={"name": name, "role_id": role.id, "department": role.department},
    )
    if not result.get("success"):
        raise RuntimeError("Não foi possível cadastrar o colaborador.")
    return result["employee"]


def link_org_employee(company_id, role_id, payload):
    """Primeira lotação legada, sem substituir cargo ou conceder acesso."""
    if not isinstance(payload, dict) or set(payload) != {"employee_id"}:
        raise ValueError("Informe apenas employee_id.")
    employee_id = payload["employee_id"]
    if type(employee_id) is not int or not 0 < employee_id <= 2147483647:
        raise ValueError("Colaborador inválido.")
    Company.query.filter_by(id=company_id).with_for_update().first_or_404()
    role = Role.query.filter_by(id=role_id, company_id=company_id).first_or_404()
    employee = Employee.query.filter_by(id=employee_id, company_id=company_id).with_for_update().first_or_404()
    if employee.user_id is not None:
        raise ValueError("Colaborador com login exige fluxo específico de revisão de acesso.")
    if (employee.status or "").strip().lower() not in {"", "active", "ativo"}:
        raise ValueError("Selecione um colaborador ativo.")
    if employee.role_id is not None and employee.role_id != role.id:
        raise ValueError("Colaborador já possui cargo. Este fluxo não substitui nem acumula cargos.")
    employee.role_id = role.id
    db.session.commit()
    return employee.to_dict()
