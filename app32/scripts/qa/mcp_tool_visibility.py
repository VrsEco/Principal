"""Diagnóstico SOMENTE LEITURA: por que uma ferramenta do mcp-versus aparece (ou não) para um usuário.

Uso (no servidor, na pasta app32):
    python scripts/qa/mcp_tool_visibility.py "Fabiano" delete_project delete_meeting_secure
    python scripts/qa/mcp_tool_visibility.py "Fabiano" --cohort deletions

Para cada ferramenta mostra: a coorte de escrita e se a flag está ligada no .env, a permissão exigida e, por empresa
com grant ativo, o teto do grant, se o perfil tem permissão total no APP32 e se a permissão exigida está entre as do
perfil. Não imprime senhas, tokens nem identificadores de identidade externa. Linhas começam com ``V|``.
"""
from __future__ import annotations

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
    print("V|", *parts)


def _flatten(permissions) -> set:
    flattened = set()
    for resource, actions in (permissions or {}).items():
        for action in actions if isinstance(actions, (list, tuple, set)) else [actions]:
            flattened.add(f"{str(resource).strip().lower()}.{str(action).strip().lower()}")
    return flattened


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    term = argv[0]
    cohort = None
    tools: list[str] = []
    rest = argv[1:]
    while rest:
        item = rest.pop(0)
        if item == "--cohort" and rest:
            cohort = rest.pop(0)
        else:
            tools.append(item)

    from app import create_app

    app = create_app()
    with app.app_context():
        from models.identity_principal import PrincipalCompanyGrant
        from models.user import User
        from src.core import mcp_write_cohorts
        from src.intelligence.security.runtime_identity import resolve_runtime_identity
        from src.intelligence.tool_catalog import catalog

        if cohort:
            tools = list(mcp_write_cohorts.WRITE_COHORT_TOOL_NAMES.get(cohort, ()))
        enabled = mcp_write_cohorts.enabled_write_domains()
        out("MCP_VERSUS_WRITE_DOMAINS no .env:", sorted(enabled) or "(vazio)")

        users = User.query.filter(User.name.ilike(f"%{term}%")).order_by(User.id.asc()).all()
        out("usuarios encontrados:", len(users))
        for user in users:
            out("---", f"user_id={user.id}", f"nome={user.name!r}", f"role_user={user.role!r}")
            grants = [
                g
                for g in PrincipalCompanyGrant.query.filter_by(status="active").all()
                if getattr(getattr(g, "principal", None), "user_id", None) == user.id and g.is_active
            ]
            out("  grants ativos:", len(grants))
            for tool_name in tools:
                capability = catalog.get_tool_capability(tool_name)
                subject = next(
                    (s for s, names in mcp_write_cohorts.WRITE_COHORT_TOOL_NAMES.items() if tool_name in names), None
                )
                if capability is None:
                    out(f"  {tool_name}: AUSENTE do catálogo")
                    continue
                permissions = tuple(capability.permissions or ())
                flag = "n/a" if subject is None else ("LIGADA" if subject in enabled else "DESLIGADA")
                out(f"  {tool_name}: coorte={subject} flag={flag} permissões exigidas={list(permissions)}")
                for grant in grants:
                    ceiling = {str(i).strip().lower() for i in (getattr(grant, "mcp_permissions", ()) or ())}
                    runtime = resolve_runtime_identity(user_id=int(user.id), company_id=int(grant.company_id))
                    full = bool(runtime.get("has_full_app32_permissions"))
                    have = _flatten(runtime.get("permissions"))
                    ceiling_ok = (not ceiling) or all(p in ceiling for p in permissions) or "financial" in ceiling
                    app_ok = full or all(p in have for p in permissions)
                    out(
                        f"    empresa={grant.company_id} teto={'(sem teto)' if not ceiling else 'restrito'} "
                        f"teto_permite={ceiling_ok} perfil_total={full} perfil_tem_permissao={app_ok} "
                        f"=> {'VISIVEL' if (ceiling_ok and app_ok) else 'OCULTA'}"
                    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
