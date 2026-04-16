from functools import wraps

from flask import abort, request
from flask_login import current_user
from sqlalchemy import func, or_

_ADMIN_ROLE_TITLES = {"superuser", "administrador", "administrator", "admin"}
_COLLABORATOR_BASELINE_VIEW = {"projects", "processes"}

PROFILE_ADMINISTRATOR = "administrator"
PROFILE_CLIENT = "client"
PROFILE_COLLABORATOR = "collaborator"


def _resolve_authenticated_user(user=None):
    candidate = user if user is not None else current_user
    if not candidate or not getattr(candidate, "is_authenticated", False):
        return None
    return candidate


def _normalize_role_title(value):
    return str(value or "").strip().lower()


def _normalize_user_role(value):
    role = str(value or "").strip().lower()
    if role in {"admin", "administrator"}:
        return "admin"
    if role == "client":
        return "client"
    return "collaborator"


def _employee_query(company_id=None, user=None):
    from models.employee import Employee

    actor = _resolve_authenticated_user(user)
    if actor is None:
        return Employee.query.filter(False)

    query = Employee.query.filter(Employee.user_id == actor.id).filter(
        or_(Employee.status.is_(None), func.lower(Employee.status) == "active")
    )
    if company_id is not None:
        query = query.filter(Employee.company_id == company_id)
    return query


def _has_admin_employee_role(company_id=None, user=None):
    actor = _resolve_authenticated_user(user)
    if actor is None:
        return False

    for employee in _employee_query(company_id, user=actor).all():
        role_title = _normalize_role_title(
            employee.role.title if employee and employee.role else None
        )
        if role_title in _ADMIN_ROLE_TITLES:
            return True
    return False


def _employee_has_permission(employee, resource, action):
    if not employee:
        return False

    perms = employee.role.permissions if employee.role and employee.role.permissions else {}
    res_perms = perms.get(resource, [])
    if isinstance(res_perms, str):
        res_perms = [res_perms]
    if action in res_perms:
        return True

    if action == "view" and resource in _COLLABORATOR_BASELINE_VIEW:
        return True

    return False


def is_platform_admin(user=None):
    actor = _resolve_authenticated_user(user)
    return bool(
        actor
        and _normalize_user_role(getattr(actor, "role", None)) == "admin"
    )


def is_client_user(user=None):
    actor = _resolve_authenticated_user(user)
    return bool(
        actor
        and _normalize_user_role(getattr(actor, "role", None)) == "client"
    )


def get_default_company_id(user=None):
    actor = _resolve_authenticated_user(user)
    if actor is None:
        return None

    from models.company import Company
    from models.employee import Employee

    employee = _employee_query(user=actor).order_by(Employee.company_id.asc()).first()
    if employee and employee.company_id:
        return employee.company_id

    if is_platform_admin(user=actor):
        first = (
            Company.query.filter(
                or_(Company.is_active.is_(None), Company.is_active.is_(True))
            )
            .order_by(Company.id.asc())
            .first()
        )
        if first:
            return first.id

    return None


def can_access_company(company_id, user=None):
    actor = _resolve_authenticated_user(user)
    if actor is None or not company_id:
        return False
    if is_platform_admin(user=actor):
        return True
    return _employee_query(company_id, user=actor).first() is not None


def get_access_profile(company_id=None, user=None):
    """
    Resolve o perfil efetivo do usuário no contexto informado.

    Perfis:
      - administrator: admin global ou administrador da empresa
      - client: cliente dentro de empresa vinculada
      - collaborator: colaborador restrito
    """
    actor = _resolve_authenticated_user(user)
    if actor is None:
        return None

    if is_platform_admin(user=actor):
        return PROFILE_ADMINISTRATOR

    if company_id is not None and not can_access_company(company_id, user=actor):
        return None

    if is_client_user(user=actor):
        if company_id is None or can_access_company(company_id, user=actor):
            return PROFILE_CLIENT
        return None

    if _has_admin_employee_role(company_id, user=actor):
        return PROFILE_ADMINISTRATOR

    employee = _employee_query(company_id, user=actor).first()
    if employee:
        return PROFILE_COLLABORATOR

    if company_id is None and _employee_query(user=actor).first():
        return PROFILE_COLLABORATOR

    return None


def is_administrator(company_id=None):
    return get_access_profile(company_id) == PROFILE_ADMINISTRATOR


def is_company_admin(company_id):
    if not current_user.is_authenticated or not company_id:
        return False
    if is_platform_admin():
        return False
    return _has_admin_employee_role(company_id)


def has_company_full_access(company_id=None):
    """
    Full access inside a tenant context.

    - platform admin -> all companies
    - client -> all resources only in linked companies
    - employee role Administrador/Superuser -> all resources in that company
    """
    return get_access_profile(company_id) in {PROFILE_ADMINISTRATOR, PROFILE_CLIENT}


def has_permission(company_id, resource, action):
    """
    Checks if the current user has a specific permission in a company.

    Hierarquia de acesso:
      - Administrador global -> acesso total
      - Cliente -> acesso total somente nas empresas vinculadas
      - Administrador da empresa -> acesso total na empresa
      - Colaborador -> acesso via JSON de permissões do cargo e fallback mínimo seguro
    """
    if not current_user.is_authenticated:
        return False

    profile = get_access_profile(company_id)
    if profile in {PROFILE_ADMINISTRATOR, PROFILE_CLIENT}:
        return True

    if company_id is None:
        for employee in _employee_query().all():
            if _employee_has_permission(employee, resource, action):
                return True
        return False

    employee = _employee_query(company_id).first()
    return _employee_has_permission(employee, resource, action)


def permission_required(resource, action):
    """
    Decorator to enforce permissions on routes.
    Expects 'company_id' to be present in request.args or view kwargs.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            company_id = kwargs.get("company_id") or request.args.get("company_id", type=int)

            if not company_id and request.is_json:
                try:
                    data = request.get_json(silent=True)
                    if data:
                        company_id = data.get("company_id")
                except Exception:
                    pass

            if not company_id:
                if has_permission(None, resource, action):
                    return f(*args, **kwargs)

                user_employees = _employee_query().all()
                if not user_employees:
                    if request.path.startswith("/api/"):
                        return {"error": "Access denied: User is not associated with any company."}, 403
                    abort(403, description="Access denied: User is not associated with any company.")

                has_any_permission = any(
                    has_permission(emp.company_id, resource, action)
                    for emp in user_employees
                )

                if not has_any_permission:
                    if request.path.startswith("/api/"):
                        return {"error": f"Permission denied: {action} on {resource}"}, 403
                    abort(
                        403,
                        description=(
                            f"Permission denied: User does not have '{action}' permission "
                            f"on '{resource}' in any associated company."
                        ),
                    )

                return f(*args, **kwargs)

            if not has_permission(company_id, resource, action):
                if request.path.startswith("/api/"):
                    return {"error": f"Permission denied: {action} on {resource}"}, 403
                abort(403, description=f"Permission denied: {action} on {resource}")

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def is_collaborator_only():
    """
    Retorna True se o usuario atual e tratado como Colaborador restrito.
    """
    if not current_user.is_authenticated:
        return True
    return get_access_profile() == PROFILE_COLLABORATOR


def is_collaborator_in_company(company_id):
    """
    Retorna True se o usuario atual e tratado como Colaborador restrito na empresa especifica.
    """
    if not current_user.is_authenticated:
        return True
    return get_access_profile(company_id) == PROFILE_COLLABORATOR


def admin_required(f):
    """Decorator to require global admin role"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_platform_admin():
            abort(403, description="Acesso negado: Apenas administradores")
        return f(*args, **kwargs)

    return decorated_function
