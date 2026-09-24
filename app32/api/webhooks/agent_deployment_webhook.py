"""Callback autenticado do workflow oficial de deploy (rota fina).

Autentica o JWT OIDC do GitHub Actions, valida o formato e delega ao service.
Nenhuma regra de política vive aqui.
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from services.agent_deployment_policy import DeploymentCallbackError, DeploymentRequestError

logger = logging.getLogger(__name__)

agent_deployment_webhook_bp = Blueprint("agent_deployment_webhook", __name__)


@agent_deployment_webhook_bp.route("/agent-deployments/github", methods=["POST"])
def github_deployment_callback():
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return jsonify({"error": "não autenticado"}), 401
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "corpo inválido"}), 400
    from services import agent_deployment_github as github
    from services.agent_deployment_service import apply_workflow_callback
    try:
        claims = github.verify_github_oidc_token(token.strip())
        result = apply_workflow_callback(
            claims=claims,
            repository=github.deploy_repository(),
            correlation_id=body.get("correlation_id"),
            event=body.get("event"),
            stage=body.get("stage"),
            evidence=body.get("evidence"),
            failure_reason=body.get("failure_reason"),
        )
    except DeploymentCallbackError as exc:
        logger.warning("Callback de deploy recusado: %s", exc)
        return jsonify({"error": "callback recusado"}), 403
    except DeploymentRequestError as exc:
        logger.warning("Callback de deploy com transição inválida: %s", exc)
        return jsonify({"error": "transição recusada"}), 409
    return jsonify({"deployment_id": result["deployment_id"], "status": result["status"]}), 200
