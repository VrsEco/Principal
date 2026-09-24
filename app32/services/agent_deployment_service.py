"""Serviço do control plane de deploy: tenant-safe e sem segredos de GitHub."""
from __future__ import annotations

import re
import secrets
from typing import Any

_SHA_RE = re.compile(r"^[0-9a-f]{7,64}$", re.I)
_ACTORS = {"codex", "claude"}
_MODES = {"quick", "standard", "full"}


class DeploymentRequestError(ValueError):
    pass


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DeploymentRequestError(f"{field} inválido")
    return value


def create_agent_deployment(*, company_id: int, identity: Any, actor_kind: str, mode: str,
                            restart_mcp: bool, target_sha: str) -> dict[str, Any]:
    """Persiste intenção; o executor continua sendo exclusivamente GitHub Actions."""
    from models import db
    from models.agent_deployment import AgentDeployment

    company_id = _positive_int(company_id, "company_id")
    bound_company = getattr(identity, "company_id", None)
    if bound_company != company_id:
        raise DeploymentRequestError("company_id não corresponde à identidade autenticada")
    actor_kind = str(actor_kind).strip().lower()
    if actor_kind not in _ACTORS:
        raise DeploymentRequestError("actor_kind deve ser codex ou claude")
    mode = str(mode).strip().lower()
    if mode not in _MODES:
        raise DeploymentRequestError("mode inválido")
    if not isinstance(restart_mcp, bool):
        raise DeploymentRequestError("restart_mcp deve ser booleano")
    target_sha = str(target_sha).strip().lower()
    if not _SHA_RE.fullmatch(target_sha):
        raise DeploymentRequestError("target_sha deve ser SHA git hexadecimal")

    subject = str(getattr(identity, "subject", "") or "").strip()
    client_id = str(getattr(identity, "client_id", "") or "").strip()
    if not subject or not client_id:
        raise DeploymentRequestError("identidade MCP autenticada é obrigatória")
    correlation_id = secrets.token_hex(16)
    deployment = AgentDeployment(
        company_id=company_id,
        requested_by_principal_id=getattr(identity, "principal_id", None),
        requested_by_user_id=getattr(identity, "user_id", None),
        actor_subject=subject,
        actor_client_id=client_id,
        actor_kind=actor_kind,
        mode=mode,
        restart_mcp=restart_mcp,
        target_sha=target_sha,
        correlation_id=correlation_id,
        evidence_json={"requested_via": "mcp", "executor": "github_actions"},
    )
    db.session.add(deployment)
    db.session.commit()
    return deployment.to_dict()


def list_agent_deployments(*, company_id: int, identity: Any, limit: int = 20) -> list[dict[str, Any]]:
    from models.agent_deployment import AgentDeployment
    company_id = _positive_int(company_id, "company_id")
    if getattr(identity, "company_id", None) != company_id:
        raise DeploymentRequestError("company_id não corresponde à identidade autenticada")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise DeploymentRequestError("limit deve estar entre 1 e 100")
    return [item.to_dict() for item in AgentDeployment.query.filter_by(company_id=company_id).order_by(
        AgentDeployment.created_at.desc(), AgentDeployment.id.desc()).limit(limit).all()]


def record_agent_deployment_run(*, company_id: int, identity: Any, deployment_id: int,
                                github_run_url: str, status: str) -> dict[str, Any]:
    """Anexa evidência de run ao pedido do mesmo tenant e mesmo principal."""
    from models import db
    from models.agent_deployment import AgentDeployment
    company_id = _positive_int(company_id, "company_id")
    deployment_id = _positive_int(deployment_id, "deployment_id")
    if getattr(identity, "company_id", None) != company_id:
        raise DeploymentRequestError("company_id não corresponde à identidade autenticada")
    deployment = AgentDeployment.query.filter_by(id=deployment_id, company_id=company_id).with_for_update().one_or_none()
    if deployment is None:
        raise DeploymentRequestError("deployment_id não encontrado no tenant")
    if deployment.actor_subject != str(getattr(identity, "subject", "") or "").strip() or deployment.actor_client_id != str(getattr(identity, "client_id", "") or "").strip():
        raise DeploymentRequestError("identidade autenticada não é autora do deploy")
    if status not in {"dispatched", "succeeded", "failed"}:
        raise DeploymentRequestError("status inválido")
    if not isinstance(github_run_url, str) or not github_run_url.startswith("https://github.com/"):
        raise DeploymentRequestError("github_run_url inválida")
    deployment.status = status
    deployment.github_run_url = github_run_url
    evidence = dict(deployment.evidence_json or {})
    evidence["github_run_recorded"] = True
    deployment.evidence_json = evidence
    db.session.commit()
    return deployment.to_dict()
