"""Diagnóstico SOMENTE LEITURA: por que um usuário não consegue usar o mcp-versus.

Uso (no servidor, na pasta app32):
    python scripts/qa/mcp_diagnose_user.py "Joseane"

Imprime ids e status (usuário, vínculos com empresas, principal OAuth, identidade externa, grants e a
decisão da política para ``list_my_companies``). Não imprime senhas, tokens nem o ``subject`` do OIDC
(só um prefixo de hash). Linhas começam com ``J|`` para facilitar o filtro.
"""
from __future__ import annotations

import hashlib
import os
import sys

os.environ.setdefault("APP_BOOTSTRAP_DB_SCHEMA", "0")
os.environ.setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "0")
sys.path.insert(0, os.getcwd())

try:
    from dotenv import load_dotenv

    load_dotenv(".env")
except Exception:  # pragma: no cover
    pass


def out(*parts) -> None:
    print("J|", *parts)


def main(term: str) -> int:
    from app import create_app

    app = create_app()
    with app.app_context():
        from datetime import datetime

        from models.employee import Employee
        from models.identity_principal import ExternalIdentity, IdentityPrincipal, PrincipalCompanyGrant
        from models.user import User
        from src.intelligence.security.runtime_identity import resolve_runtime_identity
        from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy
        from src.intelligence.tool_catalog import catalog
        from src.intelligence.tooling.capabilities import infer_tool_action

        users = User.query.filter(User.name.ilike(f"%{term}%")).order_by(User.id.asc()).all()
        out("usuarios encontrados:", len(users))
        now = datetime.utcnow()
        for user in users:
            out("---", f"user_id={user.id}", f"nome={user.name!r}", f"role_user={user.role!r}", f"ativo={user.is_active}")
            employees = Employee.query.filter(Employee.user_id == user.id).all()
            for employee in employees:
                out(
                    "  colaborador:", f"employee_id={employee.id}", f"empresa={employee.company_id}",
                    f"status={employee.status}", f"cargo={getattr(employee.role, 'title', None)!r}",
                )
            if not employees:
                out("  colaborador: NENHUM vínculo Employee")
            identity = resolve_runtime_identity(user_id=user.id, company_id=None)
            out(
                "  identidade APP32:", f"perfil={identity.get('role')!r}", f"acessa_empresas={identity.get('accessible_company_ids')}",
                f"acesso_total={identity.get('has_full_app32_permissions')}", f"permissoes={sorted((identity.get('permissions') or {}).keys())[:12]}",
            )
            principals = IdentityPrincipal.query.filter_by(user_id=user.id).all()
            if not principals:
                out("  principal OAuth: NENHUM (o login OIDC não está vinculado a este usuário)")
            for principal in principals:
                out("  principal:", f"id={principal.id}", f"status={principal.status}", f"revogado_em={principal.revoked_at}")
                for ext in ExternalIdentity.query.filter_by(principal_id=principal.id).all():
                    digest = hashlib.sha256(ext.subject.encode()).hexdigest()[:10]
                    out("    identidade externa:", f"issuer={ext.issuer}", f"subject#={digest}", f"visto_em={ext.last_seen_at}")
                grants = PrincipalCompanyGrant.query.filter_by(principal_id=principal.id).order_by(PrincipalCompanyGrant.company_id).all()
                if not grants:
                    out("    grants: NENHUM")
                for grant in grants:
                    out(
                        "    grant:", f"empresa={grant.company_id}", f"status={grant.status}", f"role={grant.role}",
                        f"inicio={grant.starts_at}", f"expira={grant.expires_at}", f"motivo_inativo={grant.inactive_reason_at(now)}",
                        f"teto_mcp={grant.mcp_permissions}",
                    )
                # Decisão da política para list_my_companies com a identidade real
                cap = catalog.get_tool_capability("list_my_companies")
                source = {
                    "principal_id": principal.id, "subject_type": "USER", "user_id": user.id,
                    "auth_method": "oauth_oidc_bearer", "token_scopes": ["mcp:access", "mcp:user"],
                    "issuer": "diagnostico", "subject": "diagnostico", "client_id": "diagnostico",
                    "company_id": None, "employee_id": None,
                    "role": str(identity.get("role") or "colaborador").lower(),
                    "permissions": ("*",) if identity.get("has_full_app32_permissions") else tuple((identity.get("permissions") or {}).keys()),
                    "metadata": {},
                }
                request = ToolPolicyRequest(
                    tool_name="list_my_companies", surface="user", domain=cap.domain,
                    action=infer_tool_action("list_my_companies", cap.domain), risk="low",
                    requested_company_id=None, accessible_company_ids=tuple(identity.get("accessible_company_ids") or ()),
                    required_permissions=tuple(cap.permissions or ()), required_context=tuple(cap.required_context or ()),
                    catalog_discovery=True, metadata={},
                )
                decision = evaluate_tool_policy(source, request)
                out("  política list_my_companies:", f"permitida={decision.allowed}", f"motivo={decision.reason!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "Joseane"))
