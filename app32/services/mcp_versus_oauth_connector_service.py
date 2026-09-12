"""Configuração pública do conector OAuth remoto mcp-versus.

A service não emite segredos, tokens nem ``company_id``. Cada cliente recebe
somente a configuração do mesmo resource server; o contexto tenant-safe é
resolvido após o login, pelo principal e pelos grants persistidos.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Final


MCP_VERSUS_NAME: Final[str] = "mcp-versus"
SUPPORTED_RUNTIMES: Final[frozenset[str]] = frozenset({"codex", "claude", "antigravity", "other"})


def _enabled(name: str) -> bool:
    return str(os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _public_base_url() -> str:
    return str(os.getenv("APP32_PUBLIC_BASE_URL") or "https://app.gestaoversus.com.br").rstrip("/")


@dataclass(frozen=True)
class McpVersusOAuthConnectorService:
    """Monta configuração OAuth específica do runtime, sem mudar o servidor MCP."""

    server_name: str = MCP_VERSUS_NAME

    def build_config(self, runtime: str | None) -> dict[str, object]:
        normalized_runtime = str(runtime or "").strip().lower()
        if normalized_runtime not in SUPPORTED_RUNTIMES:
            raise ValueError("Runtime OAuth MCP inválido.")

        if normalized_runtime == "codex":
            return self._build_codex()
        if normalized_runtime == "claude":
            return self._build_claude()
        if normalized_runtime == "antigravity":
            return self._build_antigravity()
        return self._build_generic()

    @property
    def mcp_url(self) -> str:
        return f"{_public_base_url()}/mcp/pilot/user/"

    def _base_payload(self, runtime: str, client_id: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "available": True,
            "runtime": runtime,
            "server_name": self.server_name,
            "mcp_url": self.mcp_url,
            "authentication": "oauth",
            "security_note": (
                "A conexão mcp-versus não seleciona empresa nem concede acesso. "
                "Cada tool valida o grant do principal para o company_id solicitado."
            ),
        }
        # Client IDs estáticos só pertencem aos runtimes que os configuram
        # explicitamente. Clientes DCR, como Claude, registram seu próprio
        # client público durante o fluxo OAuth; exibir um ID de coorte nesse
        # caso induz o usuário a configurar o conector de forma incorreta.
        if client_id:
            payload["client_id"] = client_id
        return payload

    def _configured_client(self, runtime: str) -> tuple[bool, str]:
        flag = f"MCP_VERSUS_OAUTH_{runtime.upper()}_ENABLED"
        client_id = str(os.getenv(f"MCP_VERSUS_OAUTH_{runtime.upper()}_CLIENT_ID") or "").strip()
        return _enabled(flag), client_id

    def _build_codex(self) -> dict[str, object]:
        enabled, client_id = self._configured_client("codex")
        # Compatibilidade temporária com a coorte piloto já publicada.
        if not enabled:
            enabled = _enabled("APP32_MCP_OAUTH_CODEX_CONNECTOR_ENABLED")
            client_id = client_id or str(os.getenv("APP32_MCP_OAUTH_CODEX_CLIENT_ID") or "").strip()
        if not enabled or not client_id:
            return {"available": False, "runtime": "codex", "message": "OAuth do Codex ainda não está liberado para esta coorte."}
        payload = self._base_payload("codex", client_id)
        payload.update(
            {
                "add_command": f"codex mcp add {self.server_name} --url {self.mcp_url} --oauth-client-id {client_id}",
                "login_command": f"codex mcp login {self.server_name}",
                "verify_command": "codex mcp list",
                "instructions": [
                    "Execute a conexão no terminal onde o Codex está instalado.",
                    "Execute o login; o navegador abrirá o Keycloak para autenticação.",
                ],
            }
        )
        return payload

    def _build_claude(self) -> dict[str, object]:
        enabled, _client_id = self._configured_client("claude")
        if not enabled:
            return {"available": False, "runtime": "claude", "message": "OAuth do Claude ainda não está liberado para esta coorte."}
        payload = self._base_payload("claude")
        payload.update(
            {
                "connector_name": self.server_name,
                "registration_mode": "dynamic",
                "instructions": [
                    "Claude Code: adicione um conector MCP remoto HTTP com o nome mcp-versus e a URL indicada.",
                    "No Claude Desktop, use Settings > Connectors > Add custom connector e informe o mesmo nome e URL.",
                    "Clique em Connect/Authenticate e conclua o login OAuth no Keycloak. Não informe client ID nem token manualmente.",
                    "Ao concluir, peça ao Claude para listar suas capabilities para validar a conexão somente-leitura.",
                ],
                "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
            }
        )
        return payload

    def _build_antigravity(self) -> dict[str, object]:
        enabled, client_id = self._configured_client("antigravity")
        if not enabled or not client_id:
            return {"available": False, "runtime": "antigravity", "message": "OAuth do Antigravity ainda não está liberado para esta coorte."}
        payload = self._base_payload("antigravity", client_id)
        config = {
            "mcpServers": {
                self.server_name: {
                    "serverUrl": self.mcp_url,
                    "oauth": {"clientId": client_id},
                }
            }
        }
        payload.update(
            {
                "config_json": config,
                "config_text": json.dumps(config, ensure_ascii=False, indent=2),
                "redirect_uri": "https://antigravity.google/oauth-callback",
                "instructions": [
                    "Adicione o bloco JSON ao arquivo mcp_config.json do Antigravity.",
                    "Na tela de MCP, escolha Authenticate e conclua o login OAuth no Keycloak.",
                ],
            }
        )
        return payload

    def _build_generic(self) -> dict[str, object]:
        if not _enabled("MCP_VERSUS_OAUTH_GENERIC_ENABLED"):
            return {
                "available": False,
                "runtime": "other",
                "message": "OAuth genérico exige o cadastro administrativo do redirect URI do cliente antes da liberação.",
                "mcp_url": self.mcp_url,
                "server_name": self.server_name,
            }
        return {
            **self._base_payload("other", ""),
            "registration_required": True,
            "instructions": [
                "Informe ao administrador o nome do cliente e o redirect URI HTTPS exato.",
                "Após o cadastro, use a URL MCP e o client_id entregues para iniciar OAuth com PKCE.",
            ],
        }


mcp_versus_oauth_connector_service = McpVersusOAuthConnectorService()

__all__ = ["MCP_VERSUS_NAME", "McpVersusOAuthConnectorService", "mcp_versus_oauth_connector_service"]
