"""Cliente mínimo do Admin REST do Keycloak para o onboarding controlado pelo APP32.

Somente opera quando as credenciais de service-account estiverem explicitamente
configuradas. Senhas transitam apenas na requisição de provisionamento e nunca
são persistidas ou registradas em log.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests


class KeycloakProvisioningError(RuntimeError):
    pass


@dataclass(frozen=True)
class KeycloakProvisioningSettings:
    base_url: str
    admin_realm: str
    target_realm: str
    client_id: str
    client_secret: str

    @classmethod
    def from_environment(cls) -> "KeycloakProvisioningSettings":
        values = {
            "base_url": str(os.getenv("APP32_KEYCLOAK_ADMIN_BASE_URL") or "").rstrip("/"),
            "admin_realm": str(os.getenv("APP32_KEYCLOAK_ADMIN_REALM") or "app32").strip(),
            "target_realm": str(os.getenv("APP32_KEYCLOAK_REALM") or "app32").strip(),
            "client_id": str(os.getenv("APP32_KEYCLOAK_ADMIN_CLIENT_ID") or "").strip(),
            "client_secret": str(os.getenv("APP32_KEYCLOAK_ADMIN_CLIENT_SECRET") or "").strip(),
        }
        if not all(values.values()):
            raise KeycloakProvisioningError("Onboarding Keycloak não está configurado para este ambiente.")
        return cls(**values)


class KeycloakIdentityProvisioningService:
    timeout_seconds = 12

    def __init__(self, settings: KeycloakProvisioningSettings | None = None, *, session: requests.Session | None = None):
        self.settings = settings or KeycloakProvisioningSettings.from_environment()
        self.session = session or requests.Session()

    def _access_token(self) -> str:
        response = self.session.post(
            f"{self.settings.base_url}/realms/{self.settings.admin_realm}/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.settings.client_id,
                "client_secret": self.settings.client_secret,
            },
            timeout=self.timeout_seconds,
        )
        if response.status_code != 200:
            raise KeycloakProvisioningError("Não foi possível autenticar o provisionador no Keycloak.")
        token = (response.json() or {}).get("access_token")
        if not token:
            raise KeycloakProvisioningError("Keycloak não retornou token para o provisionador.")
        return str(token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token()}", "Content-Type": "application/json"}

    def _users_url(self) -> str:
        return f"{self.settings.base_url}/admin/realms/{self.settings.target_realm}/users"

    def ensure_user(self, *, email: str, name: str, temporary_password: str) -> str:
        normalized_email = str(email or "").strip().lower()
        if not normalized_email or not temporary_password:
            raise KeycloakProvisioningError("E-mail e senha temporária são obrigatórios para habilitar OAuth.")
        headers = self._headers()
        lookup = self.session.get(
            self._users_url(),
            headers=headers,
            params={"username": normalized_email, "exact": "true"},
            timeout=self.timeout_seconds,
        )
        if lookup.status_code != 200:
            raise KeycloakProvisioningError("Não foi possível consultar o usuário no Keycloak.")
        users: list[dict[str, Any]] = lookup.json() or []
        if users:
            keycloak_user_id = str(users[0].get("id") or "")
        else:
            first_name, _, last_name = str(name or "").strip().partition(" ")
            create = self.session.post(
                self._users_url(),
                headers=headers,
                json={
                    "username": normalized_email,
                    "email": normalized_email,
                    "firstName": first_name or normalized_email,
                    "lastName": last_name,
                    "enabled": True,
                    "emailVerified": True,
                    "requiredActions": ["UPDATE_PASSWORD"],
                },
                timeout=self.timeout_seconds,
            )
            if create.status_code not in (201, 204):
                raise KeycloakProvisioningError("Não foi possível criar o usuário no Keycloak.")
            location = create.headers.get("Location") or ""
            keycloak_user_id = location.rstrip("/").rsplit("/", 1)[-1]
        if not keycloak_user_id:
            raise KeycloakProvisioningError("Keycloak não retornou o identificador do usuário.")
        reset = self.session.put(
            f"{self._users_url()}/{keycloak_user_id}/reset-password",
            headers=headers,
            json={"type": "password", "value": temporary_password, "temporary": True},
            timeout=self.timeout_seconds,
        )
        if reset.status_code not in (200, 204):
            raise KeycloakProvisioningError("Não foi possível definir a senha temporária do usuário.")
        return keycloak_user_id