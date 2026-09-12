from __future__ import annotations

from services.keycloak_identity_provisioning_service import (
    KeycloakIdentityProvisioningService,
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
    assert session.calls[2][2]["json"]["requiredActions"] == ["UPDATE_PASSWORD"]
    assert session.calls[3][2]["json"] == {"type": "password", "value": "SenhaTemporaria!12", "temporary": True}


def test_keycloak_provisioning_reuses_existing_identity():
    session = _Session([
        _Response(200, {"access_token": "token"}),
        _Response(200, [{"id": "subject-existing"}]),
        _Response(204),
    ])

    subject = KeycloakIdentityProvisioningService(_settings(), session=session).ensure_user(
        email="ana@example.com", name="Ana", temporary_password="SenhaTemporaria!12"
    )

    assert subject == "subject-existing"
    assert [call[0] for call in session.calls] == ["post", "get", "put"]
