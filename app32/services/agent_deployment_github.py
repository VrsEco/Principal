"""Adaptadores GitHub do control plane: verificação OIDC e dispatch do workflow.

Segredos (token de dispatch) vêm apenas do ambiente do servidor e nunca são
persistidos, registrados em log ou devolvidos ao chamador.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from services.agent_deployment_policy import (
    WORKFLOW_FILE,
    DEPLOY_REF,
    DeploymentCallbackError,
    DeploymentRequestError,
)

logger = logging.getLogger(__name__)

GITHUB_OIDC_ISSUER = "https://token.actions.githubusercontent.com"
GITHUB_OIDC_JWKS_URL = f"{GITHUB_OIDC_ISSUER}/.well-known/jwks"
GITHUB_API = "https://api.github.com"


def deploy_repository() -> str:
    return os.environ.get("AGENT_DEPLOY_GITHUB_REPOSITORY", "").strip()


def verify_github_oidc_token(token: str) -> dict[str, Any]:
    """Valida assinatura, emissor, audiência e expiração do JWT do GitHub Actions."""
    audience = os.environ.get("AGENT_DEPLOY_OIDC_AUDIENCE", "").strip()
    if not audience or not deploy_repository():
        raise DeploymentCallbackError("callback de deploy não configurado")
    if not isinstance(token, str) or token.count(".") != 2 or len(token) > 8192:
        raise DeploymentCallbackError("token OIDC ausente ou malformado")
    try:
        import jwt
        from jwt import PyJWKClient

        signing_key = PyJWKClient(GITHUB_OIDC_JWKS_URL, cache_keys=True).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=GITHUB_OIDC_ISSUER,
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
    except DeploymentCallbackError:
        raise
    except Exception as exc:  # assinatura/emissor/audiência/expiração inválidos
        logger.warning("Falha na verificação OIDC do callback de deploy (%s)", type(exc).__name__)
        raise DeploymentCallbackError("token OIDC inválido") from exc


def dispatch_deployment_workflow(*, correlation_id: str, mode: str, restart_mcp: bool) -> None:
    """Dispara o workflow oficial em main. Nunca reexecuta automaticamente."""
    token = os.environ.get("AGENT_DEPLOY_GITHUB_DISPATCH_TOKEN", "").strip()
    repository = deploy_repository()
    if not token or not repository:
        raise DeploymentRequestError("dispatch de deploy não configurado")
    import requests

    response = requests.post(
        f"{GITHUB_API}/repos/{repository}/actions/workflows/{WORKFLOW_FILE}/dispatches",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "ref": DEPLOY_REF.removeprefix("refs/heads/"),
            "inputs": {
                "mode": mode,
                "restart_mcp": "true" if restart_mcp else "false",
                "deployment_id": correlation_id,
            },
        },
        timeout=10,
    )
    if response.status_code != 204:
        raise DeploymentRequestError(f"GitHub recusou o dispatch (HTTP {response.status_code})")
