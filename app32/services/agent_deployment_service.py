"""Serviço do control plane de deploy: tenant-safe, auditável e sem segredos.

Fluxo: solicitação (MCP) → aprovação humana (MCP) → dispatch server-side →
GitHub Actions → callbacks autenticados por OIDC. Agentes nunca escrevem
sucesso/falha: só o workflow oficial, com claims verificados, fecha o ledger.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime
from typing import Any, Callable, Mapping

from services import agent_deployment_policy as policy
from services.agent_deployment_policy import (
    DeploymentCallbackError,
    DeploymentRequestError,
)

__all__ = [
    "DeploymentCallbackError",
    "DeploymentRequestError",
    "create_agent_deployment",
    "approve_agent_deployment",
    "get_agent_deployment",
    "list_agent_deployments",
    "apply_workflow_callback",
]


def _governance_company_id() -> int:
    raw = os.environ.get("AGENT_DEPLOY_GOVERNANCE_COMPANY_ID", "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        raise DeploymentRequestError("tenant de governança do deploy não configurado")
    return int(raw)


def _authorize_tenant(company_id: Any, identity: Any) -> int:
    """O tenant é o de governança configurado no servidor, nunca livre do cliente."""
    if isinstance(company_id, bool) or not isinstance(company_id, int) or company_id <= 0:
        raise DeploymentRequestError("company_id inválido")
    if company_id != _governance_company_id():
        raise DeploymentRequestError("company_id não é o tenant de governança do deploy")
    bound = getattr(identity, "company_id", None)
    if bound is not None and bound != company_id:
        raise DeploymentRequestError("company_id não corresponde à identidade autenticada")
    return company_id


def _actor_kind(identity: Any) -> str:
    return policy.resolve_actor_kind(identity, policy.load_client_kinds())


def _identity_ref(identity: Any) -> str:
    return f"{getattr(identity, 'client_id', '')}:{getattr(identity, 'subject', '')}"[:255]


def _add_event(deployment: Any, *, event_type: str, from_status: str | None, to_status: str | None,
               source: str, actor_ref: str | None, evidence: Mapping[str, Any] | None = None) -> None:
    from models import db
    from models.agent_deployment import AgentDeploymentEvent

    db.session.add(AgentDeploymentEvent(
        deployment_id=deployment.id,
        company_id=deployment.company_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        source=source,
        actor_ref=actor_ref,
        evidence_json=dict(evidence or {}),
    ))


def _transition(deployment: Any, target: str, *, event_type: str, source: str,
                actor_ref: str | None, evidence: Mapping[str, Any] | None = None) -> None:
    current = deployment.status
    policy.require_transition(current, target)
    deployment.status = target
    if target in policy.TERMINAL:
        deployment.finished_at = datetime.utcnow()
    _add_event(deployment, event_type=event_type, from_status=current, to_status=target,
               source=source, actor_ref=actor_ref, evidence=evidence)


def _get_locked(company_id: int, deployment_id: Any) -> Any:
    from models.agent_deployment import AgentDeployment

    if isinstance(deployment_id, bool) or not isinstance(deployment_id, int) or deployment_id <= 0:
        raise DeploymentRequestError("deployment_id inválido")
    deployment = AgentDeployment.query.filter_by(
        id=deployment_id, company_id=company_id).with_for_update().one_or_none()
    if deployment is None:
        raise DeploymentRequestError("deployment_id não encontrado no tenant")
    return deployment


# ------------------------------------------------------------------ MCP tools

def create_agent_deployment(*, company_id: int, identity: Any, mode: str, restart_mcp: bool,
                            target_sha: str, migration_confirmed: bool = False) -> dict[str, Any]:
    """Registra a intenção em ``pending_approval``. Não dispara nenhum deploy."""
    from models import db
    from models.agent_deployment import AgentDeployment

    company_id = _authorize_tenant(company_id, identity)
    actor_kind = _actor_kind(identity)
    mode = str(mode).strip().lower()
    if mode not in policy.MODES:
        raise DeploymentRequestError("mode inválido")
    if not isinstance(restart_mcp, bool) or not isinstance(migration_confirmed, bool):
        raise DeploymentRequestError("restart_mcp e migration_confirmed devem ser booleanos")
    if mode == "full" and not migration_confirmed:
        raise DeploymentRequestError("mode=full exige migration_confirmed=true")
    target_sha = str(target_sha).strip().lower()
    if not policy.SHA_RE.fullmatch(target_sha):
        raise DeploymentRequestError("target_sha deve ser SHA git completo (40 hex)")

    deployment = AgentDeployment(
        company_id=company_id,
        requested_by_principal_id=getattr(identity, "principal_id", None),
        requested_by_user_id=getattr(identity, "user_id", None),
        actor_subject=str(identity.subject).strip(),
        actor_client_id=str(identity.client_id).strip(),
        actor_kind=actor_kind,
        mode=mode,
        restart_mcp=restart_mcp,
        target_sha=target_sha,
        correlation_id=secrets.token_hex(16),
        status=policy.PENDING,
        evidence_json={"requested_via": "mcp", "executor": "github_actions",
                       "migration_confirmed": migration_confirmed},
    )
    db.session.add(deployment)
    db.session.flush()
    _add_event(deployment, event_type="requested", from_status=None, to_status=policy.PENDING,
               source="mcp", actor_ref=_identity_ref(identity), evidence={"actor_kind": actor_kind})
    db.session.commit()
    return deployment.to_dict()


def approve_agent_deployment(*, company_id: int, identity: Any, deployment_id: int,
                             dispatcher: Callable[..., None] | None = None) -> dict[str, Any]:
    """Aprovação humana + dispatch. Agentes nunca aprovam; sem retry automático."""
    from models import db
    from models.agent_deployment import AgentDeployment

    company_id = _authorize_tenant(company_id, identity)
    if _actor_kind(identity) != "human":
        raise DeploymentRequestError("somente um humano pode aprovar deploy")
    deployment = _get_locked(company_id, deployment_id)
    if deployment.status != policy.PENDING:
        raise DeploymentRequestError(f"deploy não está pendente de aprovação: {deployment.status}")
    busy = AgentDeployment.query.filter(
        AgentDeployment.company_id == company_id,
        AgentDeployment.status.in_(policy.ACTIVE),
        AgentDeployment.id != deployment.id,
    ).first()
    if busy is not None:
        raise DeploymentRequestError("já existe deploy ativo neste tenant")

    deployment.approved_by_principal_id = getattr(identity, "principal_id", None)
    deployment.approved_by_user_id = getattr(identity, "user_id", None)
    deployment.approved_by_subject = str(identity.subject).strip()
    deployment.approved_at = datetime.utcnow()
    _transition(deployment, policy.APPROVED, event_type="approved", source="mcp",
                actor_ref=_identity_ref(identity))
    db.session.commit()

    if dispatcher is None:
        from services.agent_deployment_github import dispatch_deployment_workflow as dispatcher
    try:
        dispatcher(correlation_id=deployment.correlation_id, mode=deployment.mode,
                   restart_mcp=deployment.restart_mcp)
    except Exception as exc:
        deployment = _get_locked(company_id, deployment_id)
        if deployment.status == policy.APPROVED:
            deployment.failure_reason = "dispatch_failed"
            _transition(deployment, policy.FAILED, event_type="dispatch_failed", source="system",
                        actor_ref=None, evidence={"error": type(exc).__name__})
            db.session.commit()
        return deployment.to_dict()

    deployment = _get_locked(company_id, deployment_id)
    if deployment.status == policy.APPROVED:  # o callback pode já ter chegado
        _transition(deployment, policy.DISPATCHED, event_type="dispatched", source="system", actor_ref=None)
        db.session.commit()
    return deployment.to_dict()


def get_agent_deployment(*, company_id: int, identity: Any, deployment_id: int) -> dict[str, Any]:
    from models.agent_deployment import AgentDeployment, AgentDeploymentEvent

    company_id = _authorize_tenant(company_id, identity)
    _actor_kind(identity)
    if isinstance(deployment_id, bool) or not isinstance(deployment_id, int) or deployment_id <= 0:
        raise DeploymentRequestError("deployment_id inválido")
    deployment = AgentDeployment.query.filter_by(id=deployment_id, company_id=company_id).one_or_none()
    if deployment is None:
        raise DeploymentRequestError("deployment_id não encontrado no tenant")
    events = AgentDeploymentEvent.query.filter_by(
        deployment_id=deployment.id, company_id=company_id).order_by(AgentDeploymentEvent.id).all()
    return {**deployment.to_dict(), "events": [item.to_dict() for item in events]}


def list_agent_deployments(*, company_id: int, identity: Any, limit: int = 20) -> list[dict[str, Any]]:
    from models.agent_deployment import AgentDeployment

    company_id = _authorize_tenant(company_id, identity)
    _actor_kind(identity)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise DeploymentRequestError("limit deve estar entre 1 e 100")
    return [item.to_dict() for item in AgentDeployment.query.filter_by(company_id=company_id).order_by(
        AgentDeployment.created_at.desc(), AgentDeployment.id.desc()).limit(limit).all()]


# ---------------------------------------------------------- callback do workflow

_CALLBACK_EVENTS = frozenset({"started", "stage", "succeeded", "failed"})


def apply_workflow_callback(*, claims: Mapping[str, Any], repository: str, correlation_id: Any,
                            event: Any, stage: Any = None, evidence: Any = None,
                            failure_reason: Any = None) -> dict[str, Any]:
    """Aplica evento do workflow. ``claims`` já passou pela verificação OIDC.

    O tenant vem do ledger (correlation_id é 128 bits aleatórios e único), nunca
    do corpo. O service reconfere claims × deploy antes de qualquer mudança.
    """
    from models import db
    from models.agent_deployment import AgentDeployment

    if not isinstance(correlation_id, str) or not policy.CORRELATION_RE.fullmatch(correlation_id):
        raise DeploymentCallbackError("correlation_id inválido")
    if event not in _CALLBACK_EVENTS:
        raise DeploymentCallbackError("evento inválido")
    clean_evidence = policy.sanitize_evidence(evidence)

    deployment = AgentDeployment.query.filter_by(
        correlation_id=correlation_id).with_for_update().one_or_none()
    if deployment is None:
        raise DeploymentCallbackError("deployment não encontrado")

    bound = deployment.github_run_id is not None
    verified = policy.verify_workflow_claims(
        claims, repository=repository, target_sha=deployment.target_sha,
        bound_run_id=deployment.github_run_id if bound else None,
        bound_run_attempt=deployment.github_run_attempt if bound else None,
    )
    actor_ref = f"github:{verified['github_run_id']}/{verified['github_run_attempt']}"

    try:
        if event == "started":
            if bound:
                raise DeploymentCallbackError("deploy já vinculado a um run")
            for field, value in verified.items():
                setattr(deployment, field, value)
            deployment.started_at = datetime.utcnow()
            _transition(deployment, policy.RUNNING, event_type="started", source="github_oidc",
                        actor_ref=actor_ref, evidence={k: verified[k] for k in (
                            "github_run_id", "github_run_attempt", "github_actor", "github_sha")})
        else:
            if not bound and event != "failed":
                raise DeploymentCallbackError("deploy sem run vinculado")
            if event == "stage":
                if deployment.status != policy.RUNNING:
                    raise DeploymentRequestError(f"estágio recusado com status {deployment.status}")
                if stage not in policy.STAGE_NAMES:
                    raise DeploymentCallbackError("estágio inválido")
                _add_event(deployment, event_type=f"stage:{stage}", from_status=deployment.status,
                           to_status=deployment.status, source="github_oidc", actor_ref=actor_ref,
                           evidence=clean_evidence)
            elif event == "succeeded":
                policy.validate_success_evidence(clean_evidence)
                _transition(deployment, policy.SUCCEEDED, event_type="succeeded", source="github_oidc",
                            actor_ref=actor_ref, evidence=clean_evidence)
            else:  # failed
                if not bound:
                    for field, value in verified.items():
                        setattr(deployment, field, value)
                deployment.failure_reason = str(failure_reason or "workflow_failed")[:255]
                _transition(deployment, policy.FAILED, event_type="failed", source="github_oidc",
                            actor_ref=actor_ref, evidence=clean_evidence)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return deployment.to_dict()
