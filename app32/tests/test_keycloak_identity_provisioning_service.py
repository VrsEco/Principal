from __future__ import annotations

import pytest

from services.keycloak_identity_provisioning_service import (
    KeycloakIdentityProvisioningService,
    KeycloakProvisioningError,
    KeycloakProvisioningSettings,
)


class _Response:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code, self._payload, self.headers = status_code, payload or {}, headers or {}
    def json(self):
        return self._payload


class _Session:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []
    def _next(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)
    def post(self, url, **kwargs): return self._next("post", url, **kwargs)
    def get(self, url, **kwargs): return self._next("get", url, **kwargs)
    def put(self, url, **kwargs): return self._next("put", url, **kwargs)


def _settings():
    return KeycloakProvisioningSettings("https://id.example", "master", "app32", "provisioner", "secret")


@pytest.mark.parametrize("existing", [True, False])
def test_parenthesized_name_is_normalized_before_invitation(existing):
    session = _Session([
        _Response(200, {"access_token": "token"}),
        _Response(200, [{"id": "subject-1"}] if existing else []),
        _Response(204 if existing else 201, headers={"Location": "https://id.example/users/subject-1"}),
        _Response(204),
    ])
    name = "Magno (Meu Chapa)"
    service = KeycloakIdentityProvisioningService(_settings(), session=session)
    assert service.ensure_user(
        email="operacao@example.com", name=name, send_password_setup_email=True
    ) == "subject-1"
    payload = session.calls[2][2]["json"]
    assert payload["firstName"] == "Magno"
    assert payload["lastName"] == "Meu Chapa"
    assert payload["username"] == payload["email"] == "operacao@example.com"
    assert name == "Magno (Meu Chapa)"
    assert session.calls[2][0] == ("put" if existing else "post")
    assert session.calls[3][1].endswith("/subject-1/execute-actions-email")
    assert session.calls[3][2]["json"] == ["UPDATE_PASSWORD"]


@pytest.mark.parametrize("name, expected", [
    ("João D'Ávila-Souza", ("João", "D'Ávila-Souza")),
    ("  Magno  (Meu Chapa)  ", ("Magno", "Meu Chapa")),
    ("Magno(Meu Chapa)", ("Magno", "Meu Chapa")),
    ("Ana", ("Ana", "")),
    ("", ("ana@example.com", "")),
])
def test_name_parts_preserves_valid_names(name, expected):
    assert KeycloakIdentityProvisioningService._name_parts(name, "ana@example.com") == expected


def test_keycloak_provisioning_creates_user_and_sets_temporary_password_without_logging_it():
    session = _Session([
        _Response(200, {"access_token": "token"}),
        _Response(200, []),
        _Response(201, headers={"Location": "https://id.example/admin/realms/app32/users/subject-1"}),
        _Response(204),
    ])
    service = KeycloakIdentityProvisioningService(_settings(), session=session)

    subject = service.ensure_user(email="ana@example.com", name="Ana Silva", temporary_password="SenhaTemporaria!12")

    assert subject == "subject-1"
    assert session.calls[2][2]["json"]["enabled"] is True
    assert session.calls[3][2]["json"] == {"type": "password", "value": "SenhaTemporaria!12", "temporary": True}


def test_keycloak_provisioning_reuses_existing_identity():
    session = _Session([
        _Response(200, {"access_token": "token"}),
        _Response(200, [{"id": "subject-existing"}]),
        _Response(204),
        _Response(204),
    ])

    subject = KeycloakIdentityProvisioningService(_settings(), session=session).ensure_user(
        email="ana@example.com", name="Ana", temporary_password="SenhaTemporaria!12"
    )

    assert subject == "subject-existing"
    assert [call[0] for call in session.calls] == ["post", "get", "put", "put"]


def test_keycloak_provisioning_sends_password_setup_email_without_receiving_password():
    session = _Session([
        _Response(200, {"access_token": "token"}),
        _Response(200, []),
        _Response(201, headers={"Location": "https://id.example/admin/realms/app32/users/subject-2"}),
        _Response(204),
    ])
    subject = KeycloakIdentityProvisioningService(_settings(), session=session).ensure_user(
        email="novo@example.com", name="Novo Usuário", send_password_setup_email=True
    )

    assert subject == "subject-2"
    assert session.calls[-1][1].endswith("/subject-2/execute-actions-email")
    assert session.calls[-1][2]["json"] == ["UPDATE_PASSWORD"]


def test_keycloak_provisioning_retries_password_setup_email_when_remote_user_already_exists():
    """Um retry do outbox deve recuperar criação remota incompleta."""
    session = _Session([
        _Response(200, {"access_token": "token"}),
        _Response(200, [{"id": "subject-existing"}]),
        _Response(204),
        _Response(204),
    ])

    subject = KeycloakIdentityProvisioningService(_settings(), session=session).ensure_user(
        email="novo@example.com", name="Novo Usuário", send_password_setup_email=True
    )

    assert subject == "subject-existing"
    assert session.calls[-1][1].endswith("/subject-existing/execute-actions-email")
    assert session.calls[-1][2]["json"] == ["UPDATE_PASSWORD"]


def test_keycloak_update_failure_exposes_only_http_status_not_response_body():
    session = _Session([
        _Response(200, {"access_token": "token"}),
        _Response(200, [{"id": "subject-existing"}]),
        _Response(403, {"error": "sensitive internal detail"}),
    ])

    with pytest.raises(KeycloakProvisioningError) as exc:
        KeycloakIdentityProvisioningService(_settings(), session=session).ensure_user(
            email="ana@example.com", name="Ana Silva", send_password_setup_email=True
        )

    assert "HTTP 403" in str(exc.value)
    assert "sensitive internal detail" not in str(exc.value)
    assert len(session.calls) == 3  # O convite não foi solicitado após a falha de atualização.
