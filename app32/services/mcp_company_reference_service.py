"""Resolução somente-leitura; nomes nunca concedem acesso a um tenant."""
from __future__ import annotations

import unicodedata


def _key(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join("".join(c for c in value if not unicodedata.combining(c))
                    .casefold().replace("—", "-").replace("–", "-").split())


def select_company_reference(reference: str, candidates: list[dict], explicit_id=None) -> int:
    """Candidates MUST already be authorized. Do not query globally here."""
    if not isinstance(reference, str) or not reference.strip() or len(reference) > 250:
        raise ValueError("Referência de empresa inválida.")
    key = _key(reference)
    matches = [c for c in candidates if key in {
        str(c["id"]), _key(c["name"]), _key(c["code"]),
        _key(f'{c["code"]} - {c["name"]}'),
    }]
    if not matches:
        raise PermissionError("Empresa não encontrada entre as autorizadas.")
    if len(matches) != 1:
        options = "; ".join(f'{c["id"]}: {c["code"]} - {c["name"]}' for c in matches)
        raise ValueError(f"Empresa ambígua; escolha o ID e repita sem company_ref: {options}")
    resolved = int(matches[0]["id"])
    if explicit_id is not None and int(explicit_id) != resolved:
        raise ValueError("company_id e company_ref identificam empresas diferentes.")
    return resolved


def resolve_company_reference(reference: str, *, principal_id=None, user_id=None,
                              explicit_id=None, accessible_company_ids=None) -> int:
    from models.company import Company
    from models.user import User
    from models.identity_principal import IdentityPrincipal, PrincipalCompanyGrant
    from services.principal_authorization_service import principal_authorization_service
    from utils.company_access import get_accessible_company_ids
    from utils.permissions import is_platform_admin

    grant_ids = None
    if principal_id is not None:
        principal = IdentityPrincipal.query.filter_by(id=principal_id).one_or_none()
        if principal is None or not principal.is_active:
            raise PermissionError("Principal indisponível.")
        user_id = principal.user_id  # Nunca aceitar identidade do payload.
        grant_ids = set()
        for grant in PrincipalCompanyGrant.query.filter_by(principal_id=principal_id).all():
            decision = principal_authorization_service.evaluate_grant(
                principal=principal, grant=grant, company_id=grant.company_id)
            if decision.allowed:
                grant_ids.add(int(grant.company_id))
    if not user_id:
        raise PermissionError("Busca de empresa exige usuário autenticado.")
    user = User.query.filter_by(id=user_id).one_or_none()
    if user is None or not user.is_active:
        raise PermissionError("Usuário indisponível.")
    ids = get_accessible_company_ids(user=user)
    query = Company.query.filter(Company.is_active.is_(True))
    if ids is not None:
        query = query.filter(Company.id.in_(list(ids)))
    elif not is_platform_admin(user=user):
        raise PermissionError("Nenhuma empresa autorizada.")
    if grant_ids is not None:
        query = query.filter(Company.id.in_(grant_ids))
    if accessible_company_ids is not None:
        query = query.filter(Company.id.in_(accessible_company_ids))
    candidates = [{"id": c.id, "name": c.name, "code": c.client_code or ""}
                  for c in query.order_by(Company.id).all()]
    return select_company_reference(reference, candidates, explicit_id)
