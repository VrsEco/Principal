from types import SimpleNamespace

import pytest

from services.agent_deployment_service import DeploymentRequestError, create_agent_deployment


def test_deployment_rejects_identity_from_another_tenant_before_persistence():
    identity = SimpleNamespace(company_id=2, subject="agent:codex", client_id="gv-codex-deploy")
    with pytest.raises(DeploymentRequestError, match="company_id não corresponde"):
        create_agent_deployment(
            company_id=1, identity=identity, actor_kind="codex", target_sha="ac292f1ac", mode="quick", restart_mcp=False
        )


@pytest.mark.parametrize("actor_kind", ["operator", "", "CODEX2"])
def test_deployment_rejects_unrecognized_agent(actor_kind):
    identity = SimpleNamespace(company_id=1, subject="agent:codex", client_id="gv-codex-deploy")
    with pytest.raises(DeploymentRequestError, match="actor_kind"):
        create_agent_deployment(
            company_id=1, identity=identity, actor_kind=actor_kind, target_sha="ac292f1ac", mode="quick", restart_mcp=False
        )
