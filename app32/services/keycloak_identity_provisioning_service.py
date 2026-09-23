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
            raise KeycloakProvisioningError(
                f"Não foi possível autenticar o provisionador no Keycloak (HTTP {response.status_code})."
            )
        token = (response.json() or {}).get("access_token")
        if not token:
            raise KeycloakProvisioningError("Keycloak não retornou token para o provisionador.")
        return str(token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token()}", "Content-Type": "application/json"}

    def _users_url(self) -> str:
        return f"{self.settings.base_url}/admin/realms/{self.settings.target_realm}/users"

    @staticmethod
    def _name_parts(name: str, email: str) -> tuple[str, str]:
        # APP32 aceita qualificadores como "Magno (Meu Chapa)". Parênteses
        # são proibidos pelo person-name-prohibited-characters do Keycloak.
        # Normalize apenas a representação externa, sem alterar o cadastro
        # local, o e-mail usado como identidade ou as validações do IdP.
        external_name = " ".join(str(name or "").replace("(", " ").replace(")", " ").split())
        first_name, _, last_name = external_name.partition(" ")
        return first_name or email, last_name

    def ensure_user(
        self,
        *,
        email: str,
        name: str,
        temporary_password: str | None = None,
        send_password_setup_email: bool = False,
        enabled: bool = True,
    ) -> str:
        normalized_email = str(email or "").strip().lower()
        if not normalized_email:
            raise KeycloakProvisioningError("E-mail é obrigatório para provisionar a identidade OAuth.")
        headers = self._headers()
        lookup = self.session.get(
            self._users_url(),
            headers=headers,
            params={"username": normalized_email, "exact": "true"},
            timeout=self.timeout_seconds,
        )
        if lookup.status_code != 200:
            raise KeycloakProvisioningError(
                f"Não foi possível consultar o usuário no Keycloak (HTTP {lookup.status_code})."
            )
        users: list[dict[str, Any]] = lookup.json() or []
        first_name, last_name = self._name_parts(name, normalized_email)
        if users:
            keycloak_user_id = str(users[0].get("id") or "")
            update = self.session.put(
                f"{self._users_url()}/{keycloak_user_id}",
                headers=headers,
                json={
                    "username": normalized_email,
                    "email": normalized_email,
                    "firstName": first_name,
                    "lastName": last_name,
                    "enabled": bool(enabled),
                },
                timeout=self.timeout_seconds,
            )
            if update.status_code not in (200, 204):
                # Persistir somente o status HTTP permite diagnosticar falhas
                # como 403/409 sem gravar no audit body da resposta, que pode
                # conter dados pessoais ou detalhes internos do IdP.
                raise KeycloakProvisioningError(
                    f"Não foi possível atualizar o usuário no Keycloak (HTTP {update.status_code})."
                )
        else:
            create = self.session.post(
                self._users_url(),
                headers=headers,
                json={
                    "username": normalized_email,
                    "email": normalized_email,
                    "firstName": first_name or normalized_email,
                    "lastName": last_name,
                    "enabled": bool(enabled),
                    "emailVerified": False,
                },
                timeout=self.timeout_seconds,
            )
            if create.status_code not in (201, 204):
                raise KeycloakProvisioningError(
                    f"Não foi possível criar o usuário no Keycloak (HTTP {create.status_code})."
                )
            location = create.headers.get("Location") or ""
            keycloak_user_id = location.rstrip("/").rsplit("/", 1)[-1]
        if not keycloak_user_id:
            raise KeycloakProvisioningError("Keycloak não retornou o identificador do usuário.")
        if temporary_password:
            reset = self.session.put(
                f"{self._users_url()}/{keycloak_user_id}/reset-password",
                headers=headers,
                json={"type": "password", "value": temporary_password, "temporary": True},
                timeout=self.timeout_seconds,
            )
            if reset.status_code not in (200, 204):
                raise KeycloakProvisioningError(
                    f"Não foi possível definir a senha temporária do usuário (HTTP {reset.status_code})."
                )
        # O outbox pode falhar depois de o Keycloak criar o usuário, mas antes
        # de o vínculo local ser persistido. Na repetição a identidade remota
        # já existe; ainda assim, o convite precisa ser enviado. A decisão de
        # solicitar o convite é do chamador (somente quando ainda não há
        # ExternalIdentity local), evitando reenvios em atualizações normais.
        elif send_password_setup_email:
            self._send_password_setup_email(keycloak_user_id, headers)
        return keycloak_user_id

    def send_password_setup_email(self, *, subject: str) -> None:
        """Envia a ação nativa após o chamador reconciliar o vínculo local."""
        self._send_password_setup_email(subject, self._headers())

    def _send_password_setup_email(self, subject: str, headers: dict) -> None:
        if not subject:
            raise KeycloakProvisioningError("Identificador Keycloak ausente para envio do convite.")
        invite = self.session.put(
            f"{self._users_url()}/{subject}/execute-actions-email",
            headers=headers,
            json=["UPDATE_PASSWORD"],
            timeout=self.timeout_seconds,
        )
        if invite.status_code not in (200, 204):
            raise KeycloakProvisioningError(
                "Não foi possível enviar o convite de definição de senha pelo Keycloak "
                f"(HTTP {invite.status_code})."
            )

    def disable_user(self, *, email: str, name: str = "") -> str:
        return self.ensure_user(email=email, name=name, enabled=False)
