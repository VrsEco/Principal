"""Projeto operacional VIGENTE de engenharia (backlog de sugestões e pedidos de integração).

Convenção documentada (SPEC identidade_oauth_keycloak_app32_mcp_v1): o projeto vigente é o que carrega o
marcador ``ENGINEERING_OPERATIONAL_CURRENT=1`` na nota, na empresa ``AA``; nunca se fixa o código nem se
deduz o projeto de códigos históricos. Os serviços de backlog usavam ``AA.J.1`` (arquivado) e ``AA.J.31``
(inexistente em produção), e por isso os cards eram gravados no projeto errado ou nem eram criados.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

OPERATIONAL_MARKER = "ENGINEERING_OPERATIONAL_CURRENT=1"
ENGINEERING_COMPANY_CODE = "AA"


def _find_marked_project():
    from models.company import Company
    from models.project import Project

    query = (
        Project.query.join(Company, Company.id == Project.company_id)
        .filter(
            Company.client_code == ENGINEERING_COMPANY_CODE,
            Project.notes.ilike(f"%{OPERATIONAL_MARKER}%"),
        )
    )
    if hasattr(Project, "is_deleted"):
        query = query.filter(Project.is_deleted.isnot(True))
    return query.order_by(Project.id.desc()).first()


def current_engineering_project_code(fallback: str) -> str:
    """Código do projeto vigente (pelo marcador) ou ``fallback`` quando não houver ou a consulta falhar."""
    try:
        project = _find_marked_project()
    except Exception:  # sem contexto de app ou banco indisponível: manter o comportamento anterior
        logger.warning("Projeto operacional vigente de engenharia não resolvido; usando %s", fallback)
        return fallback
    code = getattr(project, "code", None) if project is not None else None
    return str(code) if code else fallback


def backlog_project_code(fallback: str, env_key: str | None = None) -> str:
    """Projeto que recebe os cards de backlog: env explícita, senão o projeto operacional vigente, senão ``fallback``."""
    explicit = os.environ.get(env_key) if env_key else None
    if explicit:
        return explicit
    return current_engineering_project_code(fallback)
