"""Política pura do control plane de deploy: sem Flask, banco ou rede.

Concentra o que precisa ser verificável isoladamente: identidade do ator,
máquina de estados, vínculo dos claims OIDC do GitHub e evidência de sucesso.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping

WORKFLOW_FILE = "deploy-app32.yml"
DEPLOY_REF = "refs/heads/main"
DEPLOY_ENVIRONMENT = "production"

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CORRELATION_RE = re.compile(r"^[0-9a-f]{32}$")
MODES = frozenset({"quick", "standard", "full"})
ACTOR_KINDS = frozenset({"codex", "claude", "human"})

PENDING, APPROVED, DISPATCHED, RUNNING = "pending_approval", "approved", "dispatched", "running"
SUCCEEDED, FAILED, CANCELLED = "succeeded", "failed", "cancelled"
TERMINAL = frozenset({SUCCEEDED, FAILED, CANCELLED})
ACTIVE = frozenset({APPROVED, DISPATCHED, RUNNING})

# Única fonte das transições; qualquer outra é inválida e nunca vem do cliente.
TRANSITIONS: dict[str, frozenset[str]] = {
    PENDING: frozenset({APPROVED, CANCELLED}),
    APPROVED: frozenset({DISPATCHED, RUNNING, FAILED, CANCELLED}),
    DISPATCHED: frozenset({RUNNING, FAILED}),
    RUNNING: frozenset({SUCCEEDED, FAILED}),
    SUCCEEDED: frozenset(),
    FAILED: frozenset(),
    CANCELLED: frozenset(),
}

STAGE_NAMES = frozenset({"preflight", "code_synced", "migrations", "restart", "health", "smoke"})
_FORBIDDEN_EVIDENCE_KEY = re.compile(r"token|secret|password|passwd|private|key|authorization|cookie", re.I)
_MAX_EVIDENCE_BYTES = 4096


class DeploymentRequestError(ValueError):
    """Pedido inválido ou não autorizado no control plane de deploy."""


class DeploymentCallbackError(PermissionError):
    """Callback do workflow sem prova verificável de origem/vínculo."""


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, frozenset())


def require_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise DeploymentRequestError(f"transição de status inválida: {current} → {target}")


# ---------------------------------------------------------------- identidade

def load_client_kinds(raw: str | None = None) -> dict[str, str]:
    """client_id OAuth → tipo de ator. Vem de configuração do servidor.

    Fail-closed: clientes não mapeados não solicitam nem aprovam deploy.
    """
    text = os.environ.get("AGENT_DEPLOY_CLIENT_KINDS", "") if raw is None else raw
    if not text.strip():
        return {}
    try:
        parsed = json.loads(text)
    except ValueError as exc:
        raise DeploymentRequestError("AGENT_DEPLOY_CLIENT_KINDS inválido") from exc
    if not isinstance(parsed, dict):
        raise DeploymentRequestError("AGENT_DEPLOY_CLIENT_KINDS inválido")
    result: dict[str, str] = {}
    for client_id, kind in parsed.items():
        if isinstance(client_id, str) and client_id.strip() and kind in ACTOR_KINDS:
            result[client_id.strip()] = kind
    return result


def resolve_actor_kind(identity: Any, client_kinds: Mapping[str, str]) -> str:
    """Deriva o tipo de ator do client_id autenticado; nunca do payload."""
    client_id = str(getattr(identity, "client_id", "") or "").strip()
    subject = str(getattr(identity, "subject", "") or "").strip()
    if not client_id or not subject:
        raise DeploymentRequestError("identidade MCP autenticada é obrigatória")
    kind = client_kinds.get(client_id)
    if kind not in ACTOR_KINDS:
        raise DeploymentRequestError("client_id não autorizado para o control plane de deploy")
    if kind == "human" and not getattr(identity, "user_id", None):
        raise DeploymentRequestError("aprovação humana exige usuário vinculado à identidade")
    return kind


# ------------------------------------------------------------------ evidência

def sanitize_evidence(evidence: Any) -> dict[str, Any]:
    """Aceita apenas JSON pequeno, sem chaves que sugiram segredo."""
    if evidence is None:
        return {}
    if not isinstance(evidence, dict):
        raise DeploymentCallbackError("evidence deve ser objeto")

    def walk(value: Any, depth: int) -> Any:
        if depth > 3:
            raise DeploymentCallbackError("evidence excede profundidade")
        if isinstance(value, dict):
            out = {}
            for key, item in value.items():
                if not isinstance(key, str) or _FORBIDDEN_EVIDENCE_KEY.search(key):
                    raise DeploymentCallbackError("evidence contém chave não permitida")
                out[key] = walk(item, depth + 1)
            return out
        if isinstance(value, list):
            return [walk(item, depth + 1) for item in value[:50]]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return value[:512]
        raise DeploymentCallbackError("evidence contém tipo não permitido")

    clean = walk(evidence, 0)
    if len(json.dumps(clean, ensure_ascii=False).encode()) > _MAX_EVIDENCE_BYTES:
        raise DeploymentCallbackError("evidence excede o tamanho permitido")
    return clean


def validate_success_evidence(evidence: Mapping[str, Any]) -> None:
    """Sucesso exige health 200 e smoke 200 de todos os assets declarados."""
    if evidence.get("health_status") != 200:
        raise DeploymentCallbackError("sucesso exige health_status=200")
    smoke = evidence.get("smoke")
    if not isinstance(smoke, dict) or not smoke:
        raise DeploymentCallbackError("sucesso exige smoke dos assets declarados")
    if any(status != 200 for status in smoke.values()):
        raise DeploymentCallbackError("smoke com asset diferente de 200")


# ---------------------------------------------------------- claims do GitHub

def verify_workflow_claims(claims: Mapping[str, Any], *, repository: str, target_sha: str,
                           bound_run_id: int | None = None,
                           bound_run_attempt: int | None = None) -> dict[str, Any]:
    """Confere claims OIDC já verificados contra o deploy do ledger.

    Devolve somente os campos que podem ser gravados como evidência.
    """
    if not repository:
        raise DeploymentCallbackError("repositório de deploy não configurado")
    if claims.get("repository") != repository:
        raise DeploymentCallbackError("claim repository não corresponde")
    if claims.get("ref") != DEPLOY_REF:
        raise DeploymentCallbackError("apenas refs/heads/main é aceito")
    if claims.get("event_name") != "workflow_dispatch":
        raise DeploymentCallbackError("evento do workflow não é workflow_dispatch")
    if claims.get("environment") != DEPLOY_ENVIRONMENT:
        raise DeploymentCallbackError("run não passou pelo environment production")
    expected_workflow = f"{repository}/.github/workflows/{WORKFLOW_FILE}@{DEPLOY_REF}"
    if claims.get("job_workflow_ref") != expected_workflow and claims.get("workflow_ref") != expected_workflow:
        raise DeploymentCallbackError("workflow não é o deploy oficial")
    sha = str(claims.get("sha") or "").lower()
    if not SHA_RE.fullmatch(sha) or sha != target_sha:
        raise DeploymentCallbackError("SHA do run não corresponde ao deploy aprovado")
    try:
        run_id = int(claims.get("run_id"))
        attempt = int(claims.get("run_attempt"))
    except (TypeError, ValueError) as exc:
        raise DeploymentCallbackError("run_id/run_attempt inválidos") from exc
    if run_id <= 0 or attempt <= 0:
        raise DeploymentCallbackError("run_id/run_attempt inválidos")
    if bound_run_id is not None and (run_id != bound_run_id or attempt != bound_run_attempt):
        raise DeploymentCallbackError("run diferente do run já vinculado ao deploy")
    return {
        "github_run_id": run_id,
        "github_run_attempt": attempt,
        "github_actor": str(claims.get("actor") or "")[:255],
        "github_triggering_actor": str(claims.get("triggering_actor") or claims.get("actor") or "")[:255],
        "github_workflow_ref": expected_workflow,
        "github_sha": sha,
        "github_run_url": f"https://github.com/{repository}/actions/runs/{run_id}",
    }
