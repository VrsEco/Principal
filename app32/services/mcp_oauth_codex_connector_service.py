"""Contrato seguro da conexão remota OAuth do APP32 para o Codex.

Não cria client OAuth, não emite token e não aceita ``company_id``. A empresa
é autorizada somente no resource server, após o login OAuth, pelo grant do
principal autenticado.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _enabled(name: str) -> bool:
    return str(os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class McpOAuthCodexConnectorService:
    """Monta somente dados públicos e copiáveis do conector Codex."""

    feature_flag: str = "APP32_MCP_OAUTH_CODEX_CONNECTOR_ENABLED"

    def build_config(self) -> dict[str, object]:
        if not _enabled(self.feature_flag):
            return {
                "available": False,
                "message": "Conexão OAuth do Codex ainda não está liberada para esta coorte.",
            }

        base_url = str(os.getenv("APP32_PUBLIC_BASE_URL") or "https://app.gestaoversus.com.br").rstrip("/")
        client_id = str(os.getenv("APP32_MCP_OAUTH_CODEX_CLIENT_ID") or "").strip()
        if not client_id:
            return {
                "available": False,
                "message": "A coorte OAuth do Codex ainda não possui client configurado.",
            }

        # Nome da conexão local do Codex. Não é client_id OAuth, nem uma
        # fronteira de autorização: renomeá-lo não altera grants ou tokens.
        server_name = str(os.getenv("APP32_MCP_OAUTH_CODEX_SERVER_NAME") or "mcp-versus").strip()
        if not server_name:
            server_name = "mcp-versus"
        mcp_url = f"{base_url}/mcp/pilot/user/"
        return {
            "available": True,
            "server_name": server_name,
            "mcp_url": mcp_url,
            "client_id": client_id,
            "add_command": f"codex mcp add {server_name} --url {mcp_url} --oauth-client-id {client_id}",
            "login_command": f"codex mcp login {server_name}",
            "verify_command": "codex mcp list",
            "instructions": [
                "Copie e execute o comando de conexão no terminal onde o Codex está instalado.",
                "Execute o comando de login; o Codex abrirá o navegador para autenticação no Keycloak.",
                "Entre com sua própria conta. Não copie senha, código OAuth ou token para o APP32.",
                "Depois do retorno ao Codex, confirme a conexão e faça uma leitura autorizada.",
            ],
            "security_note": "A conexão não seleciona empresa nem concede acesso. Cada tool valida o grant do principal para o company_id solicitado.",
        }


mcp_oauth_codex_connector_service = McpOAuthCodexConnectorService()


__all__ = ["McpOAuthCodexConnectorService", "mcp_oauth_codex_connector_service"]
