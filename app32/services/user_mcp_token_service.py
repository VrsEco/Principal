from __future__ import annotations

import hashlib
import json
import os
import secrets
import base64
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterator

from flask import has_app_context

from models import Company, Employee, User, UserMcpToken, db
from services.email_service import email_service
from services.log_service import log_service
from services.whatsapp_service import whatsapp_service
from services.mcp_connection_snippet_service import MCPConnectionSnippetService
from services.sapiens_activation_service import SapiensActivationService
from services.squad_runtime_bootstrap_service import (
    OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS,
    SquadRuntimeBootstrapService,
)
from src.intelligence.mcp_contracts import APP32_PROFILE_CONTRACTS_MANIFEST
from src.intelligence.security.runtime_profiles import get_runtime_profile_spec
from utils.permissions import (
    can_access_company,
    get_access_profile,
    get_default_company_id,
    is_platform_admin,
)


DEFAULT_PUBLIC_BASE_URL = "https://app.gestaoversus.com.br"
TOKEN_EXPIRATION_DAYS = 30
ALLOWED_SURFACES = ("user",)
PROFILE_TO_FALLBACK_ROLE = {
    "administrator": "administrador",
    "client": "cliente",
    "collaborator": "colaborador",
}
RUNTIME_INSTALLER_RAW_URL = "https://raw.githubusercontent.com/VrsEco/Principal/main/app32/scripts/installers/install-sapiens-runtime.ps1"
CLAUDE_DESKTOP_INSTALLER_RAW_URL = "https://raw.githubusercontent.com/VrsEco/Principal/main/app32/scripts/installers/install-sapiens-claude-desktop-windows.ps1"
CLAUDE_SLASH_INSTALLER_RAW_URL = "https://raw.githubusercontent.com/VrsEco/Principal/main/app32/scripts/installers/install-claude-sapiens-slash-commands.ps1"
RUNTIME_LABELS = {
    "claude": "Claude Windows Desktop / Claude CLI",
    "codex": "Codex",
    "antigravity": "Antigravity",
    "other": "Genérica",
}
SQUAD_LABELS = {
    "squad_cliente": "Squad Cliente",
    "squad_versus": "Squad Versus",
    "engineering": "Squad de Engenharia",
}
SQUAD_EXPERIENCE_LABELS = {
    "squad_cliente": "Sapiens Cliente",
    "squad_versus": "Sapiens Consultor",
    "engineering": "Sapiens Engenharia",
}
SQUAD_COMMAND_ALIASES = {
    "squad_cliente": "/sapiens-cliente-on",
    "squad_versus": "/sapiens-consultor-on",
    "engineering": "/sapiens-engenharia-on",
}
ROLE_ALLOWED_SQUADS = {
    "admin": ("squad_cliente", "squad_versus", "engineering"),
    "administrator": ("squad_cliente", "squad_versus", "engineering"),
    "consultant": ("squad_cliente", "squad_versus"),
    "collaborator": ("squad_cliente",),
    "client": ("squad_cliente",),
    "user": ("squad_cliente",),
}
@dataclass(frozen=True)
class UserMcpResolvedContext:
    token_record_id: int
    user_id: int
    company_id: int | None
    fallback_role: str
    allowed_surfaces: tuple[str, ...]
    subject: str | None
    client_name: str | None
    company_resolution_source: str | None = None
    accessible_company_ids: tuple[int, ...] = ()
    multi_company: bool = False
    runtime_profile: str | None = None
    actor_type: str | None = None
    harness_key: str | None = None
    harness_label: str | None = None
    mcp_enabled: bool = True
    training_completed: bool = True


class UserMcpTokenService:
    CLIENTE_VALIDATION_PROMPT = (
        "Digite Sapiens On (ou /sapiens-on) e confirme o fluxo com "
        "bootstrap_session_context, describe_app32_available_sapiens_squads_tool e "
        "resolve_app32_sapiens_activation_tool."
    )

    @staticmethod
    @contextmanager
    def _mcp_app_context_bootstrap_disabled() -> Iterator[None]:
        """Evita subir workers/scheduler ao criar app apenas para resolver token MCP."""

        names = ("APP_BOOTSTRAP_DB_SCHEMA", "APP_BOOTSTRAP_RUNTIME_SERVICES")
        previous = {name: os.environ.get(name) for name in names}
        os.environ.setdefault("APP_BOOTSTRAP_DB_SCHEMA", "0")
        os.environ.setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "0")
        try:
            yield
        finally:
            for name, value in previous.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    @staticmethod
    @contextmanager
    def _ensure_app_context() -> Iterator[None]:
        if has_app_context():
            yield
            return

        from app import create_app

        with UserMcpTokenService._mcp_app_context_bootstrap_disabled():
            app = create_app("production")
        with app.app_context():
            yield

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.utcnow()

    @staticmethod
    def _normalize_surface(surface: str | None) -> str:
        normalized = str(surface or "user").strip().lower()
        if normalized not in ALLOWED_SURFACES:
            raise ValueError("Surface MCP inválida para token pessoal.")
        return normalized

    @staticmethod
    def _normalize_runtime(runtime: str | None) -> str:
        normalized = str(runtime or "claude").strip().lower()
        allowed = {"codex", "claude", "antigravity", "other"}
        return normalized if normalized in allowed else "claude"

    @staticmethod
    def _normalize_squad(squad: str | None) -> str:
        normalized = str(squad or "squad_cliente").strip().lower()
        allowed = {"engineering", "squad_cliente", "squad_versus"}
        return normalized if normalized in allowed else "squad_cliente"

    @classmethod
    def _resolve_allowed_squads_for_user(cls, user: User | None) -> tuple[str, ...]:
        if user and is_platform_admin(user=user):
            return ROLE_ALLOWED_SQUADS["admin"]
        role = str(getattr(user, "role", "") or "client").strip().lower()
        return ROLE_ALLOWED_SQUADS.get(role, ("squad_cliente",))

    @classmethod
    def _resolve_authorized_squad_for_user(cls, user: User | None, squad: str | None) -> str:
        normalized = cls._normalize_squad(squad)
        allowed_squads = cls._resolve_allowed_squads_for_user(user)
        if normalized in allowed_squads:
            return normalized
        return allowed_squads[0] if allowed_squads else "squad_cliente"

    @classmethod
    def _resolve_runtime_squad_policy(
        cls,
        *,
        runtime: str | None,
        requested_squad: str | None,
        allowed_squads: list[str],
    ) -> dict[str, Any]:
        normalized_runtime = cls._normalize_runtime(runtime)
        normalized_requested_squad = cls._normalize_squad(requested_squad)
        fallback_squad = allowed_squads[0] if allowed_squads else "squad_cliente"
        runtime_label = RUNTIME_LABELS.get(normalized_runtime, normalized_runtime.title())
        if normalized_requested_squad in allowed_squads:
            return {
                "runtime": normalized_runtime,
                "requested_squad": normalized_requested_squad,
                "resolved_squad": normalized_requested_squad,
                "canonical_squad": None,
                "runtime_locked": False,
                "runtime_blocked": False,
                "runtime_note": (
                    f"O {runtime_label} aceita qualquer squad autorizado ao seu perfil."
                ),
                "fallback_runtime": None,
                "fallback_runtime_label": None,
            }
        fallback_runtime = "claude" if "squad_cliente" in allowed_squads else "other"
        fallback_runtime_label = RUNTIME_LABELS.get(fallback_runtime, fallback_runtime.title())
        return {
            "runtime": normalized_runtime,
            "requested_squad": normalized_requested_squad,
            "resolved_squad": fallback_squad,
            "canonical_squad": None,
            "runtime_locked": False,
            "runtime_blocked": True,
            "runtime_note": (
                f"Seu perfil não pode instalar {SQUAD_EXPERIENCE_LABELS.get(normalized_requested_squad, normalized_requested_squad)} "
                f"no {runtime_label}."
            ),
            "fallback_runtime": fallback_runtime,
            "fallback_runtime_label": fallback_runtime_label,
        }

    @classmethod
    def _resolve_exposed_harnesses(
        cls,
        runtime_profile_key: str,
        runtime_profile_spec: Any | None,
    ) -> list[dict[str, Any]]:
        harnesses = list(runtime_profile_spec.harnesses if runtime_profile_spec else ())
        if runtime_profile_key == "squad_cliente":
            allowed_keys = set(OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS)
            harnesses = [harness for harness in harnesses if harness.key in allowed_keys]
            harnesses.sort(
                key=lambda harness: OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS.index(harness.key)
                if harness.key in OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS
                else 999
            )
        return [
            {
                "key": harness.key,
                "label": harness.label,
                "business_role": harness.business_role,
            }
            for harness in harnesses
        ]

    @classmethod
    def _build_generic_install_command(
        cls,
        *,
        runtime_key: str | None,
        url: str,
        token_value: str,
        profile_key: str,
        surface: str,
        experience_label: str,
        canonical_label: str,
        harness_key: str | None,
        harness_label: str | None,
        server_name: str,
        command_alias: str | None,
    ) -> str:
        def _ps_quote(value: str | None) -> str:
            return "'" + str(value or "").replace("'", "''") + "'"

        script = " ".join(
            [
                f"$u={_ps_quote(RUNTIME_INSTALLER_RAW_URL)};",
                "$f=Join-Path $env:TEMP 'install-sapiens-runtime.ps1';",
                "Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $f;",
                "& $f",
                f"-ClientRuntime {_ps_quote(runtime_key or 'other')}",
                f"-ServerName {_ps_quote(server_name)}",
                f"-ServerUrl {_ps_quote(url)}",
                f"-BearerToken {_ps_quote(token_value)}",
                f"-Profile {_ps_quote(profile_key)}",
                f"-Surface {_ps_quote(surface)}",
                f"-ExperienceLabel {_ps_quote(experience_label)}",
                f"-CanonicalLabel {_ps_quote(canonical_label)}",
                f"-HarnessKey {_ps_quote(harness_key or '')}",
                f"-HarnessLabel {_ps_quote(harness_label or '')}",
                f"-CommandAlias {_ps_quote(command_alias or '')};",
                "Remove-Item $f -Force",
            ]
        )
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        return f"powershell -ExecutionPolicy Bypass -EncodedCommand {encoded}"

    @classmethod
    def _build_claude_desktop_windows_install_command(
        cls,
        *,
        url: str,
        token_value: str,
        profile_key: str,
        surface: str,
        experience_label: str,
        canonical_label: str,
        harness_key: str | None,
        harness_label: str | None,
        command_alias: str | None,
    ) -> str:
        def _ps_quote(value: str | None) -> str:
            return "'" + str(value or "").replace("'", "''") + "'"

        script = " ".join(
            [
                f"$u={_ps_quote(CLAUDE_DESKTOP_INSTALLER_RAW_URL)};",
                "$f=Join-Path $env:TEMP 'install-sapiens-claude-desktop-windows.ps1';",
                "Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $f;",
                "& $f",
                f"-ServerName {_ps_quote(experience_label)}",
                f"-ServerUrl {_ps_quote(url)}",
                f"-BearerToken {_ps_quote(token_value)}",
                f"-Profile {_ps_quote(profile_key)}",
                f"-Surface {_ps_quote(surface)}",
                f"-ExperienceLabel {_ps_quote(experience_label)}",
                f"-CanonicalLabel {_ps_quote(canonical_label)}",
                f"-HarnessKey {_ps_quote(harness_key or '')}",
                f"-HarnessLabel {_ps_quote(harness_label or '')}",
                f"-CommandAlias {_ps_quote(command_alias or '')};",
                "Remove-Item $f -Force",
            ]
        )
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        return f"powershell -ExecutionPolicy Bypass -EncodedCommand {encoded}"

    @classmethod
    def _build_guided_connection_fields(
        cls,
        *,
        connection_name: str,
        url: str,
        token_value: str,
        runtime_config: dict[str, Any],
    ) -> list[dict[str, str]]:
        fields = [
            {"label": "Nome da conexão", "value": connection_name},
            {"label": "URL MCP", "value": url},
            {"label": "Autenticação", "value": "Bearer Token"},
            {"label": "Token", "value": token_value},
        ]
        if runtime_config.get("runtime") == "claude":
            fields.extend(
                [
                    {
                        "label": "Usuário Normal",
                        "value": r"Claude Windows Desktop + proxy stdio em %APPDATA%\Claude",
                    },
                    {
                        "label": "Usuário Avançado",
                        "value": "Claude CLI via PowerShell usando claude mcp add --transport http",
                    },
                    {
                        "label": "Registry MCP do Claude Code",
                        "value": r"~/.claude.json (ou equivalente gerenciado da instalação)",
                    },
                ]
            )
        if runtime_config.get("harness_label"):
            fields.append({"label": "Agente de entrada", "value": runtime_config["harness_label"]})
        return fields

    @classmethod
    def _build_activation_commands(
        cls,
        allowed_squads: list[str],
    ) -> list[dict[str, str]]:
        normalized = [cls._normalize_squad(item) for item in allowed_squads if item]
        commands: list[dict[str, str]] = [
            {
                "command": "Sapiens On",
                "summary": "Entrada textual oficial. Equivale a /sapiens-on e inicia o fluxo guiado de ativação.",
            },
            {
                "command": "/sapiens-on",
                "summary": "Entrada slash oficial. Conecta ao MCP, resolve squads e ativa o squad escolhido.",
            },
        ]
        if "squad_cliente" in normalized:
            commands.append(
                {
                    "command": "/sapiens-cliente-on",
                    "summary": "Atalho direto do Sapiens Cliente. Resolve a ativação e executa a startup sequence oficial.",
                }
            )
        if "squad_versus" in normalized:
            commands.append(
                {
                    "command": "/sapiens-consultor-on",
                    "summary": "Atalho direto do Sapiens Consultor. Resolve a ativação e executa a startup sequence oficial.",
                }
            )
        if "engineering" in normalized:
            commands.append(
                {
                    "command": "/sapiens-engenharia-on",
                    "summary": "Atalho direto do Sapiens Engenharia. Resolve a ativação e executa a startup sequence oficial.",
                }
            )
        return commands

    @classmethod
    def _build_activation_selection_prompt(
        cls,
        allowed_squads: list[str],
    ) -> str | None:
        squads = SapiensActivationService.list_available_squads(
            role="administrador",
            installed_squads=allowed_squads,
        )
        return SapiensActivationService.selection_prompt_for_squads(squads)

    @classmethod
    def _build_deactivation_commands(
        cls,
        allowed_squads: list[str],
    ) -> list[dict[str, str]]:
        normalized = [cls._normalize_squad(item) for item in allowed_squads if item]
        commands: list[dict[str, str]] = [
            {
                "command": "Sapiens Off",
                "summary": "Encerra o squad ativo, remove o badge e mantém a sessão aberta sem contexto Sapiens.",
            },
            {
                "command": "/sapiens-off",
                "summary": "Versão slash do encerramento genérico do Sapiens.",
            },
        ]
        if "squad_cliente" in normalized:
            commands.append(
                {
                    "command": "Sapiens Cliente Off",
                    "summary": "Encerra explicitamente a sessão do Sapiens Cliente.",
                }
            )
        if "squad_versus" in normalized:
            commands.append(
                {
                    "command": "Sapiens Consultor Off",
                    "summary": "Encerra explicitamente a sessão do Sapiens Consultor.",
                }
            )
        if "engineering" in normalized:
            commands.append(
                {
                    "command": "Sapiens Engenharia Off",
                    "summary": "Encerra explicitamente a sessão do Sapiens Engenharia.",
                }
            )
        return commands

    @classmethod
    def _build_session_lifecycle(
        cls,
        *,
        runtime_config: dict[str, Any],
        allowed_squads: list[str],
        company_id: int | None,
    ) -> dict[str, Any]:
        activation_payload = SapiensActivationService.resolve_activation(
            role="administrador",
            squad=runtime_config["squad"],
            installed_squads=allowed_squads,
            company_id=company_id,
        )
        startup_tools = list(activation_payload.get("startup_tools") or [])
        selection_prompt = cls._build_activation_selection_prompt(allowed_squads)
        requires_selection = len(allowed_squads) > 1
        return {
            "entry_aliases": ["Sapiens On", "sapiens on", "/sapiens-on"],
            "preflight_tools": [
                "bootstrap_session_context",
                "describe_app32_session_company_scope_tool",
                "describe_app32_available_sapiens_squads_tool",
            ],
            "activation_tool": "resolve_app32_sapiens_activation_tool",
            "selection_prompt": selection_prompt,
            "requires_selection": requires_selection,
            "auto_activate_when_single_squad": not requires_selection,
            "available_squads_count": len(allowed_squads),
            "startup_tools": startup_tools,
            "session_badge": activation_payload.get("session_badge"),
            "session_title": activation_payload.get("session_title"),
            "activation_message": activation_payload.get("activation_message"),
            "deactivation_commands": cls._build_deactivation_commands(allowed_squads),
        }

    @classmethod
    def _build_claude_activation_install_command(
        cls,
        allowed_squads: list[str],
    ) -> str:
        normalized = [cls._normalize_squad(item) for item in allowed_squads if item]
        squad_args = ",".join(normalized) if normalized else "squad_cliente"
        script = (
            f"$u='{CLAUDE_SLASH_INSTALLER_RAW_URL}'; "
            "$f=Join-Path $env:TEMP 'install-claude-sapiens-slash-commands.ps1'; "
            "Write-Host 'Baixando instalador oficial do Sapiens...'; "
            "Invoke-WebRequest -Uri $u -OutFile $f; "
            "Write-Host 'Instalando comandos slash do Claude...'; "
            f"& $f -AvailableSquads '{squad_args}'; "
            "Remove-Item $f -Force; "
            "Write-Host 'Instalacao concluida em %USERPROFILE%\\.claude\\commands e %USERPROFILE%\\.claude\\skills.'"
        )
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        return f"powershell -ExecutionPolicy Bypass -EncodedCommand {encoded}"

    @classmethod
    def _build_claude_mcp_add_command(
        cls,
        *,
        runtime_config: dict[str, Any],
        url: str,
        token_value: str,
    ) -> str:
        server_name = f"sapiens-{runtime_config['resolved_surface']}"
        return (
            f'claude mcp add --scope user --transport http {server_name} "{url}" '
            f'--header "Authorization: Bearer {token_value}"'
        )

    @classmethod
    def _build_cli_install_text(
        cls,
        *,
        runtime_config: dict[str, Any],
        connection_name: str,
        url: str,
        token_value: str,
    ) -> str:
        runtime = runtime_config["runtime"]
        server_name = f"sapiens-{runtime_config['resolved_surface']}"
        if runtime == "claude":
            native_command = cls._build_claude_mcp_add_command(
                runtime_config=runtime_config,
                url=url,
                token_value=token_value,
            )
            return "\n".join(
                [
                    f"Instale {connection_name} no Claude Code usando apenas o registry nativo do próprio Claude.",
                    "",
                    "Passos:",
                    "1. Abra o Claude Code ou a aba Code do Claude Desktop.",
                    "2. Rode o comando abaixo no terminal do Claude.",
                    "3. Confirme que a conexão foi criada no próprio Claude Code.",
                    "4. Depois abra uma nova sessão e use Sapiens On.",
                    "",
                    native_command,
                ]
            )
        if runtime == "codex":
            return "\n".join(
                [
                    f"Configure {connection_name} somente no Codex.",
                    "",
                    "No próprio Codex, aplique esta configuração em ~/.codex/config.toml:",
                    f"[mcp_servers.{server_name}]",
                    f'url = "{url}"',
                    f'bearer_token_env_var = "APP32_MCP_TOKEN_{server_name.upper().replace("-", "_")}"',
                    "startup_timeout_sec = 20",
                    "tool_timeout_sec = 120",
                    "",
                    f'Depois defina a variável APP32_MCP_TOKEN_{server_name.upper().replace("-", "_")} com o valor abaixo:',
                    token_value,
                ]
            )
        if runtime == "antigravity":
            token_env_var = f"APP32_MCP_TOKEN_{server_name.upper().replace('-', '_')}"
            return "\n".join(
                [
                    f"Configure {connection_name} somente no Antigravity.",
                    "",
                    "No próprio Antigravity, grave esta entrada em ~/.gemini/antigravity/mcp_config.json:",
                    "{",
                    f'  "mcpServers": {{"{server_name}": {{',
                    '    "command": "npx",',
                    f'    "args": ["-y", "mcp-remote", "{url}", "--header", "Authorization: Bearer ${{{token_env_var}}}"],',
                    f'    "env": {{"{token_env_var}": "{token_value}"}}',
                    "  }}}",
                    "}",
                ]
            )
        return cls._build_guided_install_text(
            runtime_config=runtime_config,
            connection_name=connection_name,
            url=url,
            token_value=token_value,
        )

    @classmethod
    def _build_claude_desktop_normal_install_text(
        cls,
        *,
        connection_name: str,
        install_command: str,
    ) -> str:
        return "\n".join(
            [
                f"Usuário Normal — Claude Windows Desktop: instale {connection_name} sem usar Claude CLI.",
                "",
                "Use no PowerShell do Windows:",
                install_command,
                "",
                "O instalador vai:",
                "1. validar Node.js;",
                "2. gravar o proxy stdio versionado em %APPDATA%\\Claude;",
                "3. atualizar claude_desktop_config.json preservando outras conexões;",
                "4. executar smoke MCP initialize;",
                "5. pedir para fechar e reabrir o Claude Desktop.",
                "",
                "Depois do restart, use Sapiens On na conversa.",
            ]
        )

    @classmethod
    def _build_claude_cli_advanced_install_text(
        cls,
        *,
        connection_name: str,
        install_command: str,
        url: str,
        token_value: str,
    ) -> str:
        native_command = (
            f'claude mcp add --scope user --transport http sapiens-user "{url}" '
            f'--header "Authorization: Bearer {token_value}"'
        )
        return "\n".join(
            [
                f"Usuário Avançado — Claude CLI via PowerShell: instale {connection_name} em uma linha.",
                "",
                "Use no PowerShell do Windows:",
                install_command,
                "",
                "O instalador baixa o script oficial e registra o MCP com o CLI do Claude.",
                "Comando interno equivalente:",
                native_command,
                "",
                "Validação:",
                "1. rode claude mcp list;",
                "2. confirme sapiens-user como Connected;",
                "3. abra nova sessão e use Sapiens On.",
            ]
        )

    @classmethod
    def _build_guided_install_steps(
        cls,
        *,
        runtime_config: dict[str, Any],
        connection_name: str,
        url: str,
        token_value: str,
    ) -> list[str]:
        runtime = runtime_config["runtime"]
        activation_command = runtime_config.get("command_alias") or "Sapiens On"
        if runtime_config.get("runtime_blocked"):
            fallback_runtime_label = runtime_config.get("fallback_runtime_label") or "outro cliente MCP"
            return [
                f"O runtime {runtime_config['runtime_label']} não está liberado para o seu perfil atual.",
                runtime_config.get("runtime_note") or "A combinação pedida não faz parte do rollout autorizado.",
                f"Para continuar agora, use {fallback_runtime_label} com o squad disponível para o seu perfil.",
            ]
        if runtime_config.get("requires_company_selection"):
            return [
                "Escolha uma empresa padrão antes de gerar a instalação.",
                "Surfaces privilegiadas do Sapiens precisam sair do APP32 com company_id explícito.",
                "Depois de selecionar a empresa, gere novamente o fluxo guiado para publicar a conexão.",
            ]
        if runtime == "claude":
            claude_add_command = cls._build_claude_mcp_add_command(
                runtime_config=runtime_config,
                url=url,
                token_value=token_value,
            )
            return [
                "Usuário Normal: use o comando de instalação do Claude Windows Desktop; ele cria o proxy stdio local e atualiza claude_desktop_config.json.",
                "Usuário Normal: confirme que Node.js LTS está instalado quando o instalador solicitar; não é necessário Claude CLI.",
                "Usuário Normal: feche e reabra o Claude Desktop depois do smoke do proxy.",
                "Usuário Avançado: use a instalação via PowerShell/Claude CLI quando operar no Claude Code ou na aba Code.",
                f"Usuário Avançado: o instalador registra internamente o MCP com {claude_add_command}.",
                "Usuário Avançado: rode claude mcp list e confirme que a entrada sapiens-user aparece como HTTP, sem fluxo OAuth.",
                "Após qualquer modo, abra uma nova sessão e use o prompt de ativação recomendado pelo APP32.",
                "Como smoke inicial, digite Sapiens On e confirme o bootstrap remoto pelo instruction registry.",
            ]
        if runtime == "codex" and runtime_config.get("install_command"):
            return [
                "Abra o terminal onde o Codex está instalado.",
                "Copie o comando único do APP32 e execute exatamente como foi gerado.",
                "O instalador vai gravar a conexão em ~/.codex/config.toml e persistir o token em variável do usuário.",
                "Rode codex mcp list e confirme que a entrada sapiens-ops aparece habilitada.",
                f"Depois da instalação, abra uma conversa, use {activation_command} e confirme o bootstrap remoto.",
            ]
        if runtime == "antigravity" and runtime_config.get("install_command"):
            return [
                "Abra o ambiente em que o Antigravity está instalado.",
                "Copie o comando único do APP32 e execute exatamente como foi gerado.",
                "O instalador vai gravar a conexão em ~/.gemini/antigravity/mcp_config.json usando o bridge HTTP com token desta instalação.",
                "Reabra o painel MCP do Antigravity e confirme que a entrada sapiens-admin aparece instalada.",
                f"Depois da instalação, abra uma conversa, use {activation_command} e confirme o bootstrap remoto.",
            ]
        return [
            f"Abra a área de conectores ou MCP do cliente {runtime_config['runtime_label']}.",
            f"Crie uma conexão chamada {connection_name}.",
            f"Cole a URL {url}.",
            "Escolha autenticação Bearer Token.",
            f"Cole o token {token_value}.",
            f"Salve a conexão, use {activation_command} e confirme o bootstrap remoto.",
        ]

    @classmethod
    def _build_guided_install_text(
        cls,
        *,
        runtime_config: dict[str, Any],
        connection_name: str,
        url: str,
        token_value: str,
    ) -> str:
        steps = cls._build_guided_install_steps(
            runtime_config=runtime_config,
            connection_name=connection_name,
            url=url,
            token_value=token_value,
        )
        if runtime_config["runtime"] == "claude":
            claude_mcp_add_command = cls._build_claude_mcp_add_command(
                runtime_config=runtime_config,
                url=url,
                token_value=token_value,
            )
            claude_config_snippet = "\n".join(
                [
                    "{",
                    '  "mcpServers": {',
                    '    "sapiens-user": {',
                    '      "type": "http",',
                    f'      "url": "{url}",',
                    '      "headers": {',
                    f'        "Authorization": "Bearer {token_value}"',
                    "      }",
                    "    }",
                    "  }",
                    "}",
                ]
            )
            lines = [
                f"Instale a conexão MCP {connection_name} no cliente {runtime_config['runtime_label']}.",
                "",
                "Passo a passo:",
            ]
            lines.extend([f"{idx}. {step}" for idx, step in enumerate(steps, start=1)])
            lines.extend(
                [
                    "",
                    "Dados para preencher:",
                    f"- Nome: {connection_name}",
                    f"- URL: {url}",
                    "- Autenticação: Bearer Token",
                    f"- Token: {token_value}",
                    f"- Perfil técnico: {runtime_config['runtime_profile']}",
                    f"- Surface: {runtime_config['resolved_surface']}",
                    f"- Harness inicial: {runtime_config['harness_label'] or '-'}",
                    "",
                    "Usuário Normal — Claude Windows Desktop:",
                    "Use a opção de instalação normal gerada pelo APP32. Ela grava um proxy stdio local no Claude Desktop e não exige Claude CLI.",
                    "",
                    "Usuário Avançado — Claude CLI / Claude Code:",
                    "```bash",
                    claude_mcp_add_command,
                    "```",
                    "",
                    "JSON de referência avançada esperado no registry do Claude Code (~/.claude.json ou equivalente gerenciado da instalação):",
                    "```json",
                    claude_config_snippet,
                    "```",
                    "",
                    "Teste inicial recomendado:",
                    cls.CLIENTE_VALIDATION_PROMPT,
                ]
            )
            return "\n".join(lines)
        lines = [
            f"Instale a conexão MCP {connection_name} no cliente {runtime_config['runtime_label']}.",
            "",
            "Passo a passo:",
        ]
        lines.extend([f"{idx}. {step}" for idx, step in enumerate(steps, start=1)])
        lines.extend(
            [
                "",
                "Dados para preencher:",
                f"- Nome: {connection_name}",
                f"- URL: {url}",
                "- Autenticação: Bearer Token",
                f"- Token: {token_value}",
                f"- Perfil técnico: {runtime_config['runtime_profile']}",
                f"- Surface: {runtime_config['resolved_surface']}",
                f"- Harness inicial: {runtime_config['harness_label'] or '-'}",
                "",
                "Teste inicial recomendado:",
                cls.CLIENTE_VALIDATION_PROMPT,
            ]
        )
        return "\n".join(lines)

    @classmethod
    def _build_company_context_rules(
        cls,
        *,
        companies: list[dict[str, Any]],
        selected_company: dict[str, Any] | None,
        surface: str = "user",
    ) -> dict[str, Any]:
        multiple_companies = len(companies) > 1
        privileged_surface = surface != "user"
        if privileged_surface:
            return {
                "session_company_required": True,
                "multiple_companies": multiple_companies,
                "default_company_optional": False,
                "active_company_id": selected_company.get("id") if selected_company else None,
                "active_company_label": selected_company.get("label") if selected_company else None,
                "read_scope": (
                    "Esta instalação privilegiada deve operar com company_id explícito e isolado por tenant."
                ),
                "write_scope": (
                    "Toda leitura crítica, mutação ou workflow privilegiado exige empresa definida antes da ativação."
                ),
                "selection_policy": (
                    "Selecione a empresa antes de publicar esta instalação. O APP32 não deve abrir surfaces privilegiadas em escopo dinâmico."
                ),
            }
        return {
            "session_company_required": False,
            "multiple_companies": multiple_companies,
            "default_company_optional": True,
            "active_company_id": selected_company.get("id") if selected_company else None,
            "active_company_label": selected_company.get("label") if selected_company else None,
            "read_scope": (
                "Consultas pessoais podem operar em escopo multiempresa e devem retornar agrupadas por empresa."
                if multiple_companies
                else "Consultas pessoais podem operar diretamente na única empresa autorizada."
            ),
            "write_scope": (
                "Ações operacionais, mutações e consultas ambíguas devem pedir empresa quando houver mais de uma elegível."
                if multiple_companies
                else "Ações operacionais usam a empresa autorizada desta instalação, salvo instrução explícita em contrário."
            ),
            "selection_policy": (
                "Não perguntar empresa na abertura da sessão; perguntar somente quando a intenção exigir escopo único."
                if multiple_companies
                else "Não perguntar empresa na abertura da sessão; a única empresa autorizada pode ser usada automaticamente."
            ),
        }

    @classmethod
    def _build_harness_summary_text(
        cls,
        *,
        runtime_config: dict[str, Any],
    ) -> str:
        lines = [
            f"Harness inicial: {runtime_config.get('harness_label') or '-'}",
            f"Profile técnico: {runtime_config.get('resolved_profile') or '-'}",
            f"Surface resolvida: {runtime_config.get('resolved_surface') or '-'}",
            "",
        ]
        official_agents = list(runtime_config.get("official_agents") or [])
        available_harnesses = list(runtime_config.get("available_harnesses") or [])
        if official_agents:
            lines.append("Agentes/harnesses oficiais expostos nesta instalação:")
            for item in official_agents:
                lines.append(f"- {item.get('label')}: {item.get('summary')}")
        elif available_harnesses:
            lines.append("Harnesses disponíveis nesta instalação:")
            for item in available_harnesses:
                role = item.get("business_role") or ""
                suffix = f" — {role}" if role else ""
                lines.append(f"- {item.get('label')}{suffix}")
        lines.extend(
            [
                "",
                "Regra operacional:",
                "A entrada sempre começa pelo harness inicial resolvido pelo APP32. Depois disso, o runtime pode rotear internamente para especialistas do mesmo squad conforme o contrato da família.",
            ]
        )
        return "\n".join(lines)

    @classmethod
    def _build_smoke_guided_text(
        cls,
        *,
        runtime_config: dict[str, Any],
        connection_name: str,
        session_lifecycle: dict[str, Any],
        company_context_rules: dict[str, Any],
    ) -> str:
        validation_prompt = cls.CLIENTE_VALIDATION_PROMPT
        preflight_tools = list(session_lifecycle.get("preflight_tools") or [])
        startup_tools = list(session_lifecycle.get("startup_tools") or [])
        lines = [
            f"Smoke guiado da instalação: {connection_name}",
            "",
            "Sequência recomendada:",
            f"1. Abra uma conversa no cliente {runtime_config.get('runtime_label') or 'selecionado'}.",
            f"2. Rode: {validation_prompt}",
            "3. Confirme que o runtime perguntou pelo squad quando houver mais de um disponível e que o badge da sessão foi aplicado.",
            "4. Confirme que a resposta identifica profile, surface, harness inicial e company_id.",
            "5. Se a leitura for pessoal e houver múltiplas empresas, confirme retorno agrupado por empresa sem exigir escolha inicial.",
            "6. Só depois execute uma operação do domínio desejado.",
            "",
            "Política de empresa na sessão:",
            f"- {company_context_rules.get('selection_policy')}",
            f"- {company_context_rules.get('write_scope')}",
            "",
            "Pré-flight obrigatório:",
        ]
        lines.extend([f"- {tool_name}" for tool_name in preflight_tools])
        lines.extend(
            [
                "",
                "Startup tools que devem estar carregadas após a escolha do squad:",
            ]
        )
        lines.extend([f"- {tool_name}" for tool_name in startup_tools])
        lines.extend(
            [
                "",
                "Smokes documentais esperados no backend:",
                "- MCP_USER_ADMIN_RUNBOOK_SMOKE_OK True True",
                "- AI_MCP_RELEASE_CHECKLIST_OK 7 3",
                "- AI_MCP_TOOL_FREEZE_OK 7 4",
                "- AI_MCP_EXTERNAL_ONBOARDING_OK 4 5",
                "- AI_MCP_OPERATIONAL_READINESS_OK 5 5",
            ]
        )
        return "\n".join(lines)

    @classmethod
    def _build_onboarding_summary_text(
        cls,
        *,
        runtime_config: dict[str, Any],
        allowed_squads: list[str],
        session_lifecycle: dict[str, Any],
        company_context_rules: dict[str, Any],
    ) -> str:
        lines = [
            "Onboarding operacional desta instalação:",
            "",
            f"- Runtime: {runtime_config.get('runtime_label') or '-'}",
            f"- Squad publicado: {runtime_config.get('experience_label') or runtime_config.get('squad_label') or '-'}",
            f"- Surface resultante: {runtime_config.get('resolved_surface') or '-'}",
            f"- Token pessoal permitido: {'sim' if runtime_config.get('supports_personal_token') else 'não'}",
            f"- Badge esperado da sessão: {session_lifecycle.get('session_badge') or '-'}",
            f"- Seleção de squad obrigatória: {'sim' if session_lifecycle.get('requires_selection') else 'não'}",
            f"- Empresa padrão ativa: {company_context_rules.get('active_company_label') or 'não definida (escopo dinâmico)'}",
            "",
            "Checklist de abertura:",
            "1. Intake do provider e do caso de uso.",
            "2. Confirmar menor privilégio por squad/profile/surface.",
            "3. Registrar a conexão sem expor token em prompt ou log.",
            "4. Executar o fluxo Sapiens On com preflight, escolha do squad e startup sequence completa.",
            "5. Operar com monitoramento e freeze/rollback conhecidos.",
            "6. Encerrar com Sapiens Off quando a sessão não precisar mais do contexto ativo.",
            "",
            "Política de empresa na sessão:",
            f"- {company_context_rules.get('selection_policy')}",
            f"- {company_context_rules.get('read_scope')}",
            f"- {company_context_rules.get('write_scope')}",
            "",
            "Squads disponíveis para este usuário:",
        ]
        lines.extend([f"- {SQUAD_EXPERIENCE_LABELS.get(item, item)}" for item in allowed_squads])
        return "\n".join(lines)

    @classmethod
    def _resolve_runtime_installation(
        cls,
        *,
        runtime: str | None,
        squad: str | None,
        company_id: int | None,
        runtime_policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_runtime = cls._normalize_runtime(runtime)
        normalized_squad = cls._normalize_squad(squad)
        runtime_policy = runtime_policy or {}
        runtime_label = RUNTIME_LABELS.get(normalized_runtime, normalized_runtime.title())
        squad_label = SQUAD_LABELS.get(normalized_squad, normalized_squad)
        experience_label = SQUAD_EXPERIENCE_LABELS.get(normalized_squad, squad_label)
        command_alias = SQUAD_COMMAND_ALIASES.get(normalized_squad)
        runtime_profile_spec = get_runtime_profile_spec(normalized_squad)

        resolved_profile = "squad_cliente"
        resolved_surface = "user"
        install_mode = "guided"
        availability_label = "Instalação guiada"
        install_command = None
        instruction_text = (
            "Use o gerador guiado para receber o passo a passo de instalação conforme o cliente escolhido."
        )

        if normalized_squad == "squad_cliente":
            resolved_profile = "squad_cliente"
            resolved_surface = "user"
            if normalized_runtime == "claude":
                install_mode = "self_service"
                availability_label = "Instalação automática"
                instruction_text = (
                    f"Você está preparando o {experience_label} para uso no {runtime_label}. "
                    "Padrão recomendado: Usuário Normal no Claude Windows Desktop. "
                    "Alternativa avançada: Claude CLI via PowerShell em uma linha."
                )
            elif normalized_runtime == "other":
                instruction_text = (
                    f"Você está preparando o {experience_label} para uso em outro cliente de IA. "
                    "Use o comando de instalação quando o cliente suportar automação; caso contrário, abra o modo técnico."
                )
            else:
                install_mode = "self_service"
                availability_label = "Instalação automática"
                instruction_text = (
                    f"Você está preparando o {experience_label} para uso no {runtime_label}. "
                    "O APP32 vai gerar instalação via CLI e via PowerShell, sempre gravando a configuração apenas no cliente escolhido."
                )
        elif normalized_squad == "engineering":
            resolved_profile = "engineering"
            resolved_surface = "ops"
            install_mode = "self_service"
            availability_label = "Instalação automática"
            instruction_text = (
                f"Você está preparando o {experience_label} para uso no {runtime_label}. "
                "O APP32 vai gerar instalação via CLI e via PowerShell para o Codex."
            )
        elif normalized_squad == "squad_versus":
            resolved_profile = "squad_versus"
            resolved_surface = "admin"
            install_mode = "self_service"
            availability_label = "Instalação automática"
            instruction_text = (
                f"Você está preparando o {experience_label} para uso no {runtime_label}. "
                "O APP32 vai gerar instalação via CLI e via PowerShell para o Antigravity."
            )

        runtime_blocked = bool(runtime_policy.get("runtime_blocked"))
        requires_company_selection = resolved_surface != "user" and company_id is None
        if runtime_blocked:
            install_mode = "blocked"
            availability_label = "Indisponível para seu perfil"
            install_command = None
            fallback_runtime_label = runtime_policy.get("fallback_runtime_label") or "outro cliente MCP"
            canonical_label = SQUAD_EXPERIENCE_LABELS.get(runtime_policy.get("canonical_squad"), runtime_policy.get("canonical_squad") or "outro squad")
            instruction_text = (
                f"O runtime {runtime_label} não está liberado para o seu perfil atual. "
                f"Ele publica canonicamente {canonical_label}. "
                f"Para continuar agora, use {fallback_runtime_label} com o squad disponível para sua permissão."
            )
        elif requires_company_selection:
            install_mode = "selection_required"
            availability_label = "Selecione uma empresa para continuar"
            install_command = None
            instruction_text = (
                f"Você está preparando o {experience_label} para uso no {runtime_label}. "
                "Como esta instalação usa surface privilegiada, escolha uma empresa padrão antes de gerar a conexão. "
                "O APP32 não deve publicar admin/ops sem company_id explícito."
            )

        return {
            "runtime": normalized_runtime,
            "runtime_label": runtime_label,
            "squad": normalized_squad,
            "squad_label": squad_label,
            "experience_label": experience_label,
            "command_alias": command_alias,
            "runtime_profile": runtime_profile_spec.key if runtime_profile_spec else normalized_squad,
            "actor_type": runtime_profile_spec.actor_type if runtime_profile_spec else "client_agent",
            "runtime_family": runtime_profile_spec.family_key if runtime_profile_spec else normalized_squad,
            "runtime_family_label": runtime_profile_spec.family_label if runtime_profile_spec else squad_label,
            "harness_key": runtime_profile_spec.default_harness_key if runtime_profile_spec else None,
            "harness_label": runtime_profile_spec.default_harness_label if runtime_profile_spec else None,
            "available_harnesses": cls._resolve_exposed_harnesses(
                normalized_squad,
                runtime_profile_spec,
            ),
            "official_agents": SquadRuntimeBootstrapService.list_official_squad_cliente_agents() if normalized_squad == "squad_cliente" else [],
            "official_phase_label": "Fase 1 oficial" if normalized_squad == "squad_cliente" else None,
            "requires_training": runtime_profile_spec.requires_training if runtime_profile_spec else True,
            "resolved_profile": resolved_profile,
            "resolved_surface": resolved_surface,
            "install_mode": install_mode,
            "availability_label": availability_label,
            "install_command": install_command,
            "instruction_text": instruction_text,
            "supports_personal_token": resolved_surface == "user" and not runtime_blocked,
            "runtime_locked": bool(runtime_policy.get("runtime_locked")),
            "runtime_blocked": runtime_blocked,
            "runtime_note": runtime_policy.get("runtime_note"),
            "canonical_squad": runtime_policy.get("canonical_squad"),
            "fallback_runtime": runtime_policy.get("fallback_runtime"),
            "fallback_runtime_label": runtime_policy.get("fallback_runtime_label"),
            "requires_company_selection": requires_company_selection,
        }

    @staticmethod
    def _generate_plaintext_token() -> str:
        return f"mcpu_{secrets.token_urlsafe(32)}"

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()

    @classmethod
    def _mask_prefix(cls, prefix: str) -> str:
        raw = str(prefix or "").strip()
        if len(raw) <= 8:
            return raw
        return f"{raw[:6]}****{raw[-2:]}"

    @classmethod
    def _expire_if_needed(cls, record: UserMcpToken) -> None:
        if record.status == "active" and record.expires_at and record.expires_at <= cls._utcnow():
            record.status = "expired"
            record.updated_at = cls._utcnow()

    @classmethod
    def _revoke_record(cls, record: UserMcpToken, *, commit: bool = False) -> None:
        if record.status == "revoked":
            return
        record.status = "revoked"
        record.revoked_at = cls._utcnow()
        record.updated_at = cls._utcnow()
        if commit:
            db.session.commit()

    @classmethod
    def get_active_token_record(cls, user_id: int) -> UserMcpToken | None:
        with cls._ensure_app_context():
            record = (
                UserMcpToken.query.filter_by(user_id=user_id, status="active")
                .order_by(UserMcpToken.created_at.desc())
                .first()
            )
            if record:
                cls._expire_if_needed(record)
            db.session.commit()
            return record if record and record.status == "active" else None

    @classmethod
    def _normalize_connector_name(
        cls,
        *,
        client_name: str | None = None,
        runtime: str | None = None,
        squad: str | None = None,
    ) -> str:
        explicit = str(client_name or "").strip()
        if explicit:
            return explicit[:120]
        runtime_key = str(runtime or "mcp").strip().lower() or "mcp"
        squad_key = str(squad or "default").strip().lower() or "default"
        return f"{runtime_key}:{squad_key}"[:120]

    @classmethod
    def _connector_identity(cls, value: str | None) -> str:
        return str(value or "").strip().lower()

    @classmethod
    def _serialize_company(cls, company: Company, *, selected: bool = False) -> dict[str, Any]:
        label = f"{company.client_code} - {company.name}" if getattr(company, "client_code", None) else company.name
        return {
            "id": company.id,
            "name": company.name,
            "client_code": getattr(company, "client_code", None),
            "label": label,
            "selected": bool(selected),
        }

    @classmethod
    def _build_identity_payload(
        cls,
        user: User,
        *,
        companies: list[dict[str, Any]] | None = None,
        resolved_company_id: int | None = None,
    ) -> dict[str, Any]:
        normalized_companies = list(companies or [])
        active_company = next(
            (company for company in normalized_companies if company.get("id") == resolved_company_id),
            None,
        )
        return {
            "user_id": getattr(user, "id", None),
            "email": getattr(user, "email", None),
            "name": getattr(user, "name", None),
            "role": getattr(user, "role", None),
            "accessible_company_ids": [
                company["id"]
                for company in normalized_companies
                if isinstance(company.get("id"), int)
            ],
            "accessible_companies_count": len(normalized_companies),
            "active_company_id": resolved_company_id,
            "active_company_label": active_company.get("label") if active_company else None,
        }

    @classmethod
    def _build_identity_summary_text(
        cls,
        user: User,
        *,
        companies: list[dict[str, Any]] | None = None,
        resolved_company_id: int | None = None,
    ) -> str:
        identity = cls._build_identity_payload(
            user,
            companies=companies,
            resolved_company_id=resolved_company_id,
        )
        companies_lines: list[str] = []
        for company in companies or []:
            prefix = company.get("client_code") or "SEM PREFIXO"
            marker = " [ATIVA]" if company.get("id") == resolved_company_id else ""
            companies_lines.append(
                f"- ID: {company.get('id')} | Prefixo: {prefix} | Nome: {company.get('name')}{marker}"
            )
        if not companies_lines:
            companies_lines.append("- Nenhuma empresa acessível vinculada ao token.")
        active_company_label = identity.get("active_company_label") or "não definida"
        return (
            "Identidade MCP confirmada:\n"
            f"- user_id: {identity.get('user_id')}\n"
            f"- email: {identity.get('email') or '-'}\n"
            f"- nome: {identity.get('name') or '-'}\n"
            f"- papel: {identity.get('role') or '-'}\n"
            f"- empresa ativa: {active_company_label}\n"
            f"- total de empresas acessíveis: {identity.get('accessible_companies_count')}\n"
            "Empresas acessíveis:\n"
            + "\n".join(companies_lines)
        )

    @classmethod
    def _build_sapiens_session_welcome_short(
        cls,
        *,
        user: User,
        resolved_company_id: int | None,
        company_label: str | None,
    ) -> str:
        return SapiensActivationService.build_session_welcome_short(
            user_id=getattr(user, "id", None),
            role_label=getattr(user, "role", None),
            company_id=resolved_company_id,
            company_label=company_label,
        )

    @classmethod
    def _build_sapiens_session_welcome_full(
        cls,
        *,
        user: User,
        resolved_company_id: int | None,
        company_label: str | None,
    ) -> str:
        return SapiensActivationService.build_session_welcome_full(
            user_id=getattr(user, "id", None),
            role_label=getattr(user, "role", None),
            company_id=resolved_company_id,
            company_label=company_label,
        )

    @classmethod
    def list_accessible_companies(cls, user: User) -> list[dict[str, Any]]:
        with cls._ensure_app_context():
            if is_platform_admin(user=user):
                companies = (
                    Company.query.filter(Company.is_active.isnot(False))
                    .order_by(Company.name.asc())
                    .all()
                )
            else:
                company_ids = [
                    row.company_id
                    for row in Employee.query.filter_by(user_id=user.id, status="active").all()
                    if getattr(row, "company_id", None) is not None
                ]
                companies = []
                if company_ids:
                    companies = (
                        Company.query.filter(
                            Company.id.in_(company_ids),
                            Company.is_active.isnot(False),
                        )
                        .order_by(Company.name.asc())
                        .all()
                    )
            default_company_id = get_default_company_id(user=user)
            return [
                cls._serialize_company(company, selected=company.id == default_company_id)
                for company in companies
            ]

    @classmethod
    def _list_accessible_company_ids(cls, user: User) -> tuple[int, ...]:
        companies = cls.list_accessible_companies(user)
        normalized: list[int] = []
        for company in companies:
            company_id = company.get("id")
            if isinstance(company_id, int) and company_id not in normalized:
                normalized.append(company_id)
        return tuple(normalized)

    @classmethod
    def _resolve_company_id_for_user(cls, user: User, requested_company_id: int | None) -> int | None:
        candidate = requested_company_id or get_default_company_id(user=user)
        if candidate and can_access_company(candidate, user=user):
            return int(candidate)
        return None

    @classmethod
    def _resolve_explicit_company_id_for_user(cls, user: User, requested_company_id: int | None) -> int | None:
        if requested_company_id in (None, 0, '0', ''):
            return None
        candidate = int(requested_company_id)
        if can_access_company(candidate, user=user):
            return candidate
        return None

    @classmethod
    def _resolve_runtime_company_context(
        cls,
        user: User,
        *,
        requested_company_id: int | None = None,
        persisted_company_id: int | None = None,
    ) -> tuple[int | None, str | None, tuple[int, ...]]:
        accessible_company_ids = cls._list_accessible_company_ids(user)
        explicit_company_id = cls._resolve_explicit_company_id_for_user(user, requested_company_id)
        if explicit_company_id is not None:
            return explicit_company_id, "request.company_id", accessible_company_ids

        persisted_selection = cls._resolve_explicit_company_id_for_user(user, persisted_company_id)
        if persisted_selection is not None:
            return persisted_selection, "token.last_company_id", accessible_company_ids

        if len(accessible_company_ids) == 1:
            return accessible_company_ids[0], "user.single_accessible_company_id", accessible_company_ids

        return None, None, accessible_company_ids

    @classmethod
    def build_runtime_company_scope(
        cls,
        user: User,
        *,
        requested_company_id: int | None = None,
        persisted_company_id: int | None = None,
    ) -> dict[str, Any]:
        companies = cls.list_accessible_companies(user)
        resolved_company_id, resolution_source, accessible_company_ids = cls._resolve_runtime_company_context(
            user,
            requested_company_id=requested_company_id,
            persisted_company_id=persisted_company_id,
        )
        company_lookup = {item["id"]: item for item in companies if isinstance(item.get("id"), int)}
        active_company = company_lookup.get(resolved_company_id) if resolved_company_id is not None else None
        for company in companies:
            company["selected"] = bool(
                resolved_company_id is not None and company.get("id") == resolved_company_id
            )
        multi_company = len(accessible_company_ids) > 1
        return {
            "user_id": getattr(user, "id", None),
            "accessible_company_ids": list(accessible_company_ids),
            "accessible_company_count": len(accessible_company_ids),
            "company_scope_basis": "current_user_authorizations",
            "companies": companies,
            "active_company_id": resolved_company_id,
            "active_company_label": active_company.get("label") if active_company else None,
            "company_resolution_source": resolution_source,
            "multi_company": multi_company,
            "selection_required_for_mutations": multi_company and resolved_company_id is None,
        }

    @classmethod
    def describe_runtime_company_scope(
        cls,
        *,
        token: str,
        requested_company_id: int | None = None,
    ) -> dict[str, Any]:
        token_hash = cls._hash_token(token)
        with cls._ensure_app_context():
            record = (
                UserMcpToken.query.filter_by(token_hash=token_hash)
                .order_by(UserMcpToken.created_at.desc())
                .first()
            )
            if not record:
                raise ValueError("Token MCP inválido.")
            cls._expire_if_needed(record)
            if record.status != "active":
                db.session.commit()
                raise ValueError("Token MCP inativo.")
            user = User.query.get(record.user_id)
            if not user or not getattr(user, "is_active", False):
                raise ValueError("Usuário inválido para escopo MCP.")
            return cls.build_runtime_company_scope(
                user,
                requested_company_id=requested_company_id,
                persisted_company_id=record.last_company_id,
            )

    @classmethod
    def select_runtime_company(
        cls,
        *,
        token: str,
        company_id: int,
        client_name: str | None = None,
    ) -> dict[str, Any]:
        token_hash = cls._hash_token(token)
        with cls._ensure_app_context():
            record = (
                UserMcpToken.query.filter_by(token_hash=token_hash)
                .order_by(UserMcpToken.created_at.desc())
                .first()
            )
            if not record:
                raise ValueError("Token MCP inválido.")
            cls._expire_if_needed(record)
            if record.status != "active":
                db.session.commit()
                raise ValueError("Token MCP inativo.")
            user = User.query.get(record.user_id)
            if not user or not getattr(user, "is_active", False):
                raise ValueError("Usuário inválido para seleção de empresa.")
            selected_company_id = cls._resolve_explicit_company_id_for_user(user, company_id)
            if selected_company_id is None:
                raise ValueError("Empresa não autorizada para este token MCP.")
            record.last_company_id = selected_company_id
            record.last_client_name = (client_name or "").strip() or record.last_client_name
            record.updated_at = cls._utcnow()
            db.session.commit()
            return cls.build_runtime_company_scope(
                user,
                requested_company_id=selected_company_id,
                persisted_company_id=selected_company_id,
            )

    @classmethod
    def clear_runtime_company(cls, *, token: str) -> dict[str, Any]:
        token_hash = cls._hash_token(token)
        with cls._ensure_app_context():
            record = (
                UserMcpToken.query.filter_by(token_hash=token_hash)
                .order_by(UserMcpToken.created_at.desc())
                .first()
            )
            if not record:
                raise ValueError("Token MCP inválido.")
            cls._expire_if_needed(record)
            if record.status != "active":
                db.session.commit()
                raise ValueError("Token MCP inativo.")
            user = User.query.get(record.user_id)
            if not user or not getattr(user, "is_active", False):
                raise ValueError("Usuário inválido para limpeza de empresa.")
            record.last_company_id = None
            record.updated_at = cls._utcnow()
            db.session.commit()
            return cls.build_runtime_company_scope(user, persisted_company_id=None)

    @classmethod
    def _build_status_payload(cls, user: User, record: UserMcpToken | None) -> dict[str, Any]:
        companies = cls.list_accessible_companies(user)
        default_company_id = get_default_company_id(user=user)
        days_to_expire = None
        if record and record.expires_at:
            days_to_expire = (record.expires_at.date() - cls._utcnow().date()).days
        active_company_id = record.last_company_id if record and record.last_company_id else default_company_id
        identity = cls._build_identity_payload(
            user,
            companies=companies,
            resolved_company_id=active_company_id,
        )

        return {
            "has_active_token": bool(record and record.status == "active"),
            "token_prefix": record.token_prefix if record else None,
            "token_masked": cls._mask_prefix(record.token_prefix) if record else None,
            "status": record.status if record else "missing",
            "created_at": record.created_at.isoformat() if record and record.created_at else None,
            "expires_at": record.expires_at.isoformat() if record and record.expires_at else None,
            "days_to_expire": days_to_expire,
            "last_used_at": record.last_used_at.isoformat() if record and record.last_used_at else None,
            "last_client_name": record.last_client_name if record else None,
            "last_surface": record.last_surface if record else None,
            "last_company_id": record.last_company_id if record else None,
            "default_company_id": default_company_id,
            "allowed_surfaces": list(ALLOWED_SURFACES),
            "companies": companies,
            "identity": identity,
            "identity_summary_text": cls._build_identity_summary_text(
                user,
                companies=companies,
                resolved_company_id=active_company_id,
            ),
        }

    @classmethod
    def get_status(cls, user_id: int) -> dict[str, Any]:
        with cls._ensure_app_context():
            user = User.query.get(user_id)
            if not user or not getattr(user, "is_active", False):
                raise ValueError("Usuário inválido para token MCP.")
            record = cls.get_active_token_record(user.id)
            return cls._build_status_payload(user, record)

    @classmethod
    def _issue_token(
        cls,
        user: User,
        *,
        created_by_user_id: int | None = None,
        client_name: str | None = None,
        runtime: str | None = None,
        squad: str | None = None,
    ) -> tuple[UserMcpToken, str]:
        connector_name = cls._normalize_connector_name(
            client_name=client_name,
            runtime=runtime,
            squad=squad,
        )
        connector_identity = cls._connector_identity(connector_name)
        # Serializa a emissão por usuário. Sem o bloqueio, requisições
        # simultâneas leem a mesma lista de tokens ativos e todas criam um
        # novo registro antes que qualquer uma consiga revogar as demais.
        locked_user = (
            User.query.filter_by(id=user.id)
            .with_for_update()
            .first()
        )
        if not locked_user:
            raise ValueError("Usuário inválido para geração do token MCP.")
        user = locked_user
        active_records = UserMcpToken.query.filter_by(user_id=user.id, status="active").all()
        for active in active_records:
            if cls._connector_identity(getattr(active, "last_client_name", None)) == connector_identity:
                cls._revoke_record(active)

        plaintext = cls._generate_plaintext_token()
        expires_at = cls._utcnow() + timedelta(days=TOKEN_EXPIRATION_DAYS)
        record = UserMcpToken(
            user_id=user.id,
            token_hash=cls._hash_token(plaintext),
            token_prefix=plaintext[:12],
            status="active",
            created_by_user_id=created_by_user_id or user.id,
            expires_at=expires_at,
            last_client_name=connector_name,
            last_company_id=None,
        )
        db.session.add(record)
        db.session.commit()
        return record, plaintext

    @classmethod
    def generate_token(
        cls,
        *,
        user_id: int,
        created_by_user_id: int | None = None,
        company_id: int | None = None,
        surface: str = "user",
        client_name: str | None = None,
        runtime: str | None = None,
        squad: str | None = None,
    ) -> dict[str, Any]:
        with cls._ensure_app_context():
            user = User.query.get(user_id)
            if not user or not getattr(user, "is_active", False):
                raise ValueError("Usuário inválido para geração do token MCP.")
            normalized_surface = cls._normalize_surface(surface)
            resolved_company_id = cls._resolve_explicit_company_id_for_user(user, company_id)
            record, plaintext = cls._issue_token(
                user,
                created_by_user_id=created_by_user_id,
                client_name=client_name,
                runtime=runtime,
                squad=squad,
            )
            log_service.log_create(
                entity_type="user_mcp_token",
                entity_id=record.id,
                entity_name=f"Token MCP de {user.email}",
                new_values={
                    "user_id": user.id,
                    "surface": normalized_surface,
                    "expires_at": record.expires_at.isoformat(),
                    "company_id_context": resolved_company_id,
                },
                description=f"Token MCP pessoal gerado para {user.email}",
                company_id=resolved_company_id,
            )
            status = cls._build_status_payload(user, record)
            config = cls.build_client_config(
                user_id=user.id,
                plaintext_token=plaintext,
                company_id=resolved_company_id,
                surface=normalized_surface,
                client_name=client_name,
                runtime=runtime,
                squad=squad,
            )
            return {"token": plaintext, "status": status, "config": config}

    @classmethod
    def renew_token(
        cls,
        *,
        user_id: int,
        renewed_by_user_id: int | None = None,
        company_id: int | None = None,
        surface: str = "user",
        client_name: str | None = None,
        runtime: str | None = None,
        squad: str | None = None,
    ) -> dict[str, Any]:
        return cls.generate_token(
            user_id=user_id,
            created_by_user_id=renewed_by_user_id,
            company_id=company_id,
            surface=surface,
            client_name=client_name,
            runtime=runtime,
            squad=squad,
        )

    @classmethod
    def revoke_token(cls, *, user_id: int, revoked_by_user_id: int | None = None) -> dict[str, Any]:
        with cls._ensure_app_context():
            user = User.query.get(user_id)
            if not user:
                raise ValueError("Usuário inválido para revogação do token MCP.")
            record = cls.get_active_token_record(user.id)
            if record:
                cls._revoke_record(record)
                db.session.commit()
                log_service.log_delete(
                    entity_type="user_mcp_token",
                    entity_id=record.id,
                    entity_name=f"Token MCP de {user.email}",
                    old_values={"status": "active", "expires_at": record.expires_at.isoformat() if record.expires_at else None},
                    description=f"Token MCP revogado para {user.email}",
                    company_id=record.last_company_id,
                )
            return cls._build_status_payload(user, None)

    @classmethod
    def build_client_config(
        cls,
        *,
        user_id: int,
        plaintext_token: str | None = None,
        company_id: int | None = None,
        surface: str = "user",
        client_name: str | None = None,
        runtime: str | None = None,
        squad: str | None = None,
    ) -> dict[str, Any]:
        with cls._ensure_app_context():
            user = User.query.get(user_id)
            if not user:
                raise ValueError("Usuário inválido para configuração MCP.")
            allowed_squads = list(cls._resolve_allowed_squads_for_user(user))
            runtime_policy = cls._resolve_runtime_squad_policy(
                runtime=runtime,
                requested_squad=squad,
                allowed_squads=allowed_squads,
            )
            companies = cls.list_accessible_companies(user)
            public_base = str(os.environ.get("APP32_MCP_PUBLIC_BASE_URL") or DEFAULT_PUBLIC_BASE_URL).rstrip("/")
            runtime_config = cls._resolve_runtime_installation(
                runtime=runtime,
                squad=runtime_policy["resolved_squad"],
                company_id=cls._resolve_explicit_company_id_for_user(user, company_id),
                runtime_policy=runtime_policy,
            )
            resolved_surface = runtime_config["resolved_surface"]
            if resolved_surface == "user":
                resolved_company_id = cls._resolve_explicit_company_id_for_user(user, company_id)
            else:
                resolved_company_id, _, _ = cls._resolve_runtime_company_context(
                    user,
                    requested_company_id=company_id,
                )
                runtime_config = cls._resolve_runtime_installation(
                    runtime=runtime,
                    squad=runtime_policy["resolved_squad"],
                    company_id=resolved_company_id,
                    runtime_policy=runtime_policy,
                )
                resolved_surface = runtime_config["resolved_surface"]
            company_lookup = {item["id"]: item for item in companies}
            selected_company = company_lookup.get(resolved_company_id) if resolved_company_id else None
            display_name = (
                selected_company["label"]
                if selected_company
                else ("Escopo dinâmico multiempresa" if resolved_surface == "user" else "Sem empresa padrão")
            )
            identity = cls._build_identity_payload(
                user,
                companies=companies,
                resolved_company_id=resolved_company_id,
            )
            identity_summary_text = cls._build_identity_summary_text(
                user,
                companies=companies,
                resolved_company_id=resolved_company_id,
            )
            activation_welcome_short = cls._build_sapiens_session_welcome_short(
                user=user,
                resolved_company_id=resolved_company_id,
                company_label=display_name,
            )
            activation_welcome_opening = SapiensActivationService.build_session_welcome_opening()
            activation_welcome_full = cls._build_sapiens_session_welcome_full(
                user=user,
                resolved_company_id=resolved_company_id,
                company_label=display_name,
            )
            has_plaintext_token = bool(str(plaintext_token or "").strip())
            token_placeholder = "TOKEN_GERADO_APENAS_NA_RENOVACAO"
            token_value = plaintext_token or token_placeholder
            url = f"{public_base}/mcp/{resolved_surface}/"
            if resolved_surface != "user" and resolved_company_id:
                url = f"{url}?company_id={resolved_company_id}"
            connection_name = runtime_config["experience_label"]
            snippet_payload = {
                "profile": runtime_config["runtime_profile"],
                "name": connection_name,
                "default_company": display_name,
                "url": url,
                "auth_type": "bearer",
                "token": token_value,
                "harness_key": runtime_config["harness_key"],
            }
            technical_config_text = MCPConnectionSnippetService.build_raw_config(snippet_payload)
            activation_prompt = MCPConnectionSnippetService.build_prompt(snippet_payload)
            config_json = json.loads(technical_config_text)
            guided_fields = cls._build_guided_connection_fields(
                connection_name=connection_name,
                url=url,
                token_value=token_value,
                runtime_config=runtime_config,
            )
            guided_steps = cls._build_guided_install_steps(
                runtime_config=runtime_config,
                connection_name=connection_name,
                url=url,
                token_value=token_value,
            )
            guided_install_text = cls._build_guided_install_text(
                runtime_config=runtime_config,
                connection_name=connection_name,
                url=url,
                token_value=token_value,
            )
            session_allowed_squads = (
                allowed_squads
                if runtime_config["runtime_blocked"]
                else [runtime_config["squad"]]
            )
            activation_commands = cls._build_activation_commands(session_allowed_squads)
            deactivation_commands = cls._build_deactivation_commands(session_allowed_squads)
            activation_selection_prompt = cls._build_activation_selection_prompt(session_allowed_squads)
            activation_commands_install_command = (
                cls._build_claude_activation_install_command(session_allowed_squads)
                if runtime_config["runtime"] == "claude"
                else None
            )
            session_lifecycle = cls._build_session_lifecycle(
                runtime_config=runtime_config,
                allowed_squads=session_allowed_squads,
                company_id=resolved_company_id,
            )
            company_context_rules = cls._build_company_context_rules(
                companies=companies,
                selected_company=selected_company,
                surface=resolved_surface,
            )
            harness_summary_text = cls._build_harness_summary_text(runtime_config=runtime_config)
            smoke_guided_text = cls._build_smoke_guided_text(
                runtime_config=runtime_config,
                connection_name=connection_name,
                session_lifecycle=session_lifecycle,
                company_context_rules=company_context_rules,
            )
            onboarding_summary_text = cls._build_onboarding_summary_text(
                runtime_config=runtime_config,
                allowed_squads=allowed_squads,
                session_lifecycle=session_lifecycle,
                company_context_rules=company_context_rules,
            )
            config_text = (
                f"Conexão: {connection_name}\n"
                f"Família canônica: {runtime_config['squad_label']}\n"
                f"Empresa padrão: {display_name}\n"
                f"Runtime: {runtime_config['runtime_label']}\n"
                f"Comando sugerido: {runtime_config['command_alias'] or '-'}\n"
                f"URL: {url}\n"
                f"Perfil: {runtime_config['runtime_profile']}\n"
                f"Harness inicial: {runtime_config['harness_label'] or '-'}"
            )
            server_name = f"sapiens-{runtime_config['resolved_surface']}"
            advanced_install_command = (
                cls._build_generic_install_command(
                    runtime_key=runtime_config["runtime"],
                    url=url,
                    token_value=token_value,
                    profile_key=runtime_config["resolved_profile"],
                    surface=runtime_config["resolved_surface"],
                    experience_label=runtime_config["experience_label"],
                    canonical_label=runtime_config["squad_label"],
                    harness_key=runtime_config["harness_key"],
                    harness_label=runtime_config["harness_label"],
                    server_name=server_name,
                    command_alias=runtime_config["command_alias"],
                )
                if runtime_config["install_mode"] == "self_service"
                else runtime_config["install_command"]
            )
            installation_command = advanced_install_command
            normal_install_command = None
            normal_install_text = None
            advanced_install_text = None
            cli_install_text = cls._build_cli_install_text(
                runtime_config=runtime_config,
                connection_name=connection_name,
                url=url,
                token_value=token_value,
            )
            installation_instruction = runtime_config["instruction_text"]
            copy_install_command_text = installation_command
            if runtime_config["runtime"] == "claude" and runtime_config["squad"] == "squad_cliente":
                normal_install_command = cls._build_claude_desktop_windows_install_command(
                    url=url,
                    token_value=token_value,
                    profile_key=runtime_config["resolved_profile"],
                    surface=runtime_config["resolved_surface"],
                    experience_label=runtime_config["experience_label"],
                    canonical_label=runtime_config["squad_label"],
                    harness_key=runtime_config["harness_key"],
                    harness_label=runtime_config["harness_label"],
                    command_alias=runtime_config["command_alias"],
                )
                installation_command = normal_install_command
                copy_install_command_text = normal_install_command
                normal_install_text = cls._build_claude_desktop_normal_install_text(
                    connection_name=connection_name,
                    install_command=normal_install_command,
                )
                advanced_install_text = cls._build_claude_cli_advanced_install_text(
                    connection_name=connection_name,
                    install_command=advanced_install_command or "",
                    url=url,
                    token_value=token_value,
                )
                cli_install_text = advanced_install_text
                installation_instruction = (
                    "Experiência recomendada: Usuário Normal no Claude Windows Desktop. "
                    "Use o instalador Desktop para gravar proxy stdio local. "
                    "Se for usuário técnico, use a opção Usuário Avançado para registrar via Claude CLI."
                )
            if runtime_config["squad"] == "squad_cliente":
                installation_instruction = (
                    f"{installation_instruction}\n\n"
                "A instalação publica o Sapiens Cliente com entrada pelo Agente Coordenador. "
                "A família inicial oficial do Squad Cliente é composta por Comercial, Operacional e Adm/Financeiro."
            )
            if runtime_config["supports_personal_token"]:
                installation_instruction = (
                    f"{installation_instruction}\n\n"
                    "Durante a instalação, use o token MCP pessoal gerado nesta página."
                )
            else:
                installation_instruction = (
                    f"{installation_instruction}\n\n"
                    "Este perfil usa rollout controlado. A credencial final pode ser provisionada pela Versus ou por administrador autorizado."
                )
            if installation_command and runtime_config["install_mode"] == "self_service":
                install_scope_text = (
                    "No Claude, o modo Normal baixa o instalador Desktop e grava proxy stdio local; "
                    "o modo Avançado usa Claude CLI/registry HTTP."
                    if runtime_config["runtime"] == "claude" and runtime_config["squad"] == "squad_cliente"
                    else "O instalador baixa o script oficial online e grava a configuração somente no cliente escolhido: Claude Code, Codex ou Antigravity."
                )
                installation_instruction = (
                    f"{installation_instruction}\n\n"
                    f"Comando sugerido:\n{installation_command}\n\n"
                    f"{install_scope_text}"
                )
            elif installation_command:
                installation_instruction = (
                    f"{installation_instruction}\n\n"
                    f"Comando de referência:\n{installation_command}"
                )
            if runtime_config["runtime"] == "claude":
                activation_prompt = (
                    f"{guided_install_text}\n\n"
                    "Prompt de ativação recomendado no Claude Code ou na aba Code do Claude Desktop:\n"
                    f"Use a conexão MCP {connection_name} desta sessão.\n\n"
                    "Quando o usuário digitar `Sapiens On`, `sapiens on` ou `/sapiens-on`, execute exatamente este fluxo:\n"
                    "1. Verifique se a conexão MCP do APP32 está disponível na sessão.\n"
                    "2. Rode `bootstrap_session_context`.\n"
                    "3. Rode `describe_app32_available_sapiens_squads_tool`.\n"
                    f"4. Se houver mais de um squad, pergunte exatamente: `{activation_selection_prompt or 'Com qual squad você vai trabalhar?'}`.\n"
                    f"5. Rode `resolve_app32_sapiens_activation_tool` com o squad escolhido ou resolvido.\n"
                    "6. Execute a startup sequence retornada em `startup_tools`, na ordem, para pré-carregar schema e contexto.\n"
                    "7. Se o fluxo funcionar, responda primeiro com a mensagem inicial mínima de boas-vindas, em linguagem acessível e sem jargão técnico, e mantenha o squad ativo nesta sessão.\n"
                    "8. Se o usuário pedir instruções, mostre a versão inicial das instruções.\n"
                    "9. Se depois disso o usuário pedir mais detalhes, responda com a versão completa das instruções.\n\n"
                    "Startup sequence esperada após a escolha do squad:\n"
                    + "\n".join([f"- {item}" for item in session_lifecycle["startup_tools"]])
                    + "\n\n"
                    f"Badge esperado: `{session_lifecycle['session_badge'] or runtime_config['experience_label'] + ' On'}`.\n"
                    "Antes de responder à primeira pergunta operacional do usuário, exponha explicitamente a identidade e o escopo resolvidos nesta sessão:\n"
                    f"{identity_summary_text}\n\n"
                      "Mensagem inicial mínima obrigatória de boas-vindas:\n"
                      f"{activation_welcome_opening}\n\n"
                      "Versão inicial das instruções para usar se o usuário pedir instruções:\n"
                      f"{activation_welcome_short}\n\n"
                      "Mensagem completa para usar somente se o usuário pedir mais detalhes:\n"
                      f"{activation_welcome_full}\n\n"
                    "Se o runtime suportar título/badge de sessão, aplique esse badge no canto superior esquerdo ou no título visível da conversa.\n"
                    "Quando o usuário digitar `Sapiens Off` ou um off explícito do squad, remova o badge, descarte o bundle/contexto do squad e mantenha a sessão aberta.\n"
                    "Depois disso, responda à demanda do usuário.\n\n"
                    "Entradas oficiais de ativação:\n"
                    + "\n".join([f"- {item['command']}: {item['summary']}" for item in activation_commands])
                    + "\n\n"
                    + "Entradas oficiais de encerramento:\n"
                    + "\n".join([f"- {item['command']}: {item['summary']}" for item in deactivation_commands])
                    + (
                        f"\n\nQuando houver mais de um squad disponível, o comando genérico deve perguntar exatamente:\n{activation_selection_prompt}"
                        if activation_selection_prompt
                        else ""
                    )
                    + (
                        f"\n\nSe você quiser instalar atalhos slash opcionais nesta máquina, use:\n{activation_commands_install_command}"
                        if activation_commands_install_command
                        else ""
                    )
                    + "\n\nImportante: no Claude Windows Desktop, o caminho canônico para usuário normal é o proxy stdio instalado no `claude_desktop_config.json` + prompt de ativação. Para usuário avançado no Claude Code/CLI, o caminho canônico é `claude mcp add` + prompt de ativação. Slash commands são opcionais e podem variar conforme a versão do runtime."
                )
            return {
                "client_name": (client_name or "").strip() or None,
                "surface": resolved_surface,
                "company_id": resolved_company_id,
                "company_label": display_name,
                "url": url,
                "runtime": runtime_config["runtime"],
                "runtime_label": runtime_config["runtime_label"],
                "squad": runtime_config["squad"],
                "squad_label": runtime_config["squad_label"],
                "experience_label": runtime_config["experience_label"],
                "command_alias": runtime_config["command_alias"],
                "runtime_profile": runtime_config["runtime_profile"],
                "actor_type": runtime_config["actor_type"],
                "runtime_family": runtime_config["runtime_family"],
                "runtime_family_label": runtime_config["runtime_family_label"],
                "harness_key": runtime_config["harness_key"],
                "harness_label": runtime_config["harness_label"],
                "available_harnesses": runtime_config["available_harnesses"],
                "official_agents": runtime_config["official_agents"],
                "official_phase_label": runtime_config["official_phase_label"],
                "requires_training": runtime_config["requires_training"],
                "resolved_profile": runtime_config["resolved_profile"],
                "resolved_surface": runtime_config["resolved_surface"],
                "install_mode": runtime_config["install_mode"],
                "availability_label": runtime_config["availability_label"],
                "runtime_locked": runtime_config["runtime_locked"],
                "runtime_blocked": runtime_config["runtime_blocked"],
                "runtime_note": runtime_config["runtime_note"],
                "canonical_squad": runtime_config["canonical_squad"],
                "fallback_runtime": runtime_config["fallback_runtime"],
                "fallback_runtime_label": runtime_config["fallback_runtime_label"],
                "requires_company_selection": runtime_config["requires_company_selection"],
                "has_plaintext_token": has_plaintext_token,
                "token_required": not has_plaintext_token and runtime_config["supports_personal_token"],
                "token_placeholder": token_placeholder,
                "install_command": installation_command,
                "copy_install_command_text": copy_install_command_text,
                "powershell_install_command": installation_command,
                "normal_install_command": normal_install_command,
                "normal_install_text": normal_install_text,
                "advanced_install_command": advanced_install_command,
                "advanced_install_text": advanced_install_text,
                "install_profiles": {
                    "normal": {
                        "label": "Usuário Normal - Claude Windows Desktop",
                        "command": normal_install_command,
                        "description": "Instalador Desktop com proxy stdio local e claude_desktop_config.json.",
                    } if normal_install_command else None,
                    "advanced": {
                        "label": "Usuário Avançado - Claude CLI via PowerShell",
                        "command": advanced_install_command,
                        "description": "Instalador CLI que usa claude mcp add --transport http.",
                    } if advanced_install_command else None,
                },
                "cli_install_text": cli_install_text,
                "instruction_text": installation_instruction,
                "supports_personal_token": runtime_config["supports_personal_token"],
                "guided_install_steps": guided_steps,
                "guided_connection_fields": guided_fields,
                "guided_install_text": guided_install_text,
                "onboarding_summary_text": onboarding_summary_text,
                "harness_summary_text": harness_summary_text,
                "smoke_guided_text": smoke_guided_text,
                "validation_prompt": cls.CLIENTE_VALIDATION_PROMPT,
                "activation_commands": activation_commands,
                "deactivation_commands": deactivation_commands,
                "activation_selection_prompt": activation_selection_prompt,
                "activation_commands_install_command": activation_commands_install_command,
                "identity": identity,
                "identity_summary_text": identity_summary_text,
                "activation_welcome_opening": activation_welcome_opening,
                "activation_welcome_short": activation_welcome_short,
                "activation_welcome_full": activation_welcome_full,
                "session_badge": session_lifecycle["session_badge"],
                "startup_tools": session_lifecycle["startup_tools"],
                "preflight_tools": session_lifecycle["preflight_tools"],
                "activation_tool": session_lifecycle["activation_tool"],
                "requires_squad_selection": session_lifecycle["requires_selection"],
                "auto_activate_when_single_squad": session_lifecycle["auto_activate_when_single_squad"],
                "company_context_rules": company_context_rules,
                "text": config_text,
                "json": config_json,
                "technical_config_text": technical_config_text,
                "activation_prompt": activation_prompt,
                "companies": companies,
                "allowed_squads": allowed_squads,
                "session_lifecycle": session_lifecycle,
            }

    @classmethod
    def _resolve_squad_cliente_harness(cls, harness_key: str | None):
        runtime_spec = get_runtime_profile_spec("squad_cliente")
        default_key = runtime_spec.default_harness_key if runtime_spec else "harness_coordenador_cliente_v1"
        normalized = str(harness_key or default_key or "").strip().lower()
        available = {str(item.key).strip().lower(): item for item in (runtime_spec.harnesses if runtime_spec else ())}
        harness = available.get(normalized)
        if harness is None or normalized not in set(OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS):
            raise ValueError("Harness não pertence ao Squad Cliente oficial.")
        overlay = APP32_PROFILE_CONTRACTS_MANIFEST.get_overlay(normalized)
        if overlay is None or overlay.runtime_profile != "squad_cliente" or overlay.surface != "user":
            raise ValueError("Harness sem contrato MCP válido para a surface user.")
        return harness, overlay

    @classmethod
    def describe_runtime_harness_scope(cls, *, token: str) -> dict[str, Any]:
        token_hash = cls._hash_token(token)
        with cls._ensure_app_context():
            record = UserMcpToken.query.filter_by(token_hash=token_hash).order_by(UserMcpToken.created_at.desc()).first()
            if not record:
                raise ValueError("Token MCP inválido.")
            cls._expire_if_needed(record)
            if record.status != "active":
                db.session.commit()
                raise ValueError("Token MCP inativo ou expirado.")
            user = User.query.get(record.user_id)
            if not user or not getattr(user, "is_active", False):
                raise ValueError("Usuário MCP inativo.")
            harness, overlay = cls._resolve_squad_cliente_harness(getattr(record, "last_harness_key", None))
            base_profile = get_access_profile(record.last_company_id, user=user) if record.last_company_id else "collaborator"
            profile = PROFILE_TO_FALLBACK_ROLE.get(base_profile, "colaborador")
            available = []
            runtime_spec = get_runtime_profile_spec("squad_cliente")
            for item in (runtime_spec.harnesses if runtime_spec else ()):
                if item.key not in set(OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS):
                    continue
                contract = APP32_PROFILE_CONTRACTS_MANIFEST.get_overlay(item.key)
                if contract and profile in set(contract.compatible_profiles):
                    available.append({"key": item.key, "label": item.label, "business_role": item.business_role})
            return {
                "user_id": user.id,
                "active_company_id": record.last_company_id,
                "runtime_profile": "squad_cliente",
                "active_harness_key": harness.key,
                "active_harness_label": harness.label,
                "active_overlay": overlay.overlay,
                "available_harnesses": available,
            }

    @classmethod
    def select_runtime_harness(cls, *, token: str, harness_key: str) -> dict[str, Any]:
        token_hash = cls._hash_token(token)
        with cls._ensure_app_context():
            record = UserMcpToken.query.filter_by(token_hash=token_hash).order_by(UserMcpToken.created_at.desc()).first()
            if not record:
                raise ValueError("Token MCP inválido.")
            cls._expire_if_needed(record)
            if record.status != "active":
                db.session.commit()
                raise ValueError("Token MCP inativo ou expirado.")
            user = User.query.get(record.user_id)
            if not user or not getattr(user, "is_active", False):
                raise ValueError("Usuário MCP inativo.")
            harness, overlay = cls._resolve_squad_cliente_harness(harness_key)
            base_profile = get_access_profile(record.last_company_id, user=user) if record.last_company_id else "collaborator"
            profile = PROFILE_TO_FALLBACK_ROLE.get(base_profile, "colaborador")
            if profile not in set(overlay.compatible_profiles):
                raise ValueError("Harness incompatível com o perfil autenticado.")
            record.last_harness_key = harness.key
            record.updated_at = cls._utcnow()
            db.session.commit()
            return {
                "user_id": user.id,
                "active_company_id": record.last_company_id,
                "runtime_profile": "squad_cliente",
                "active_harness_key": harness.key,
                "active_harness_label": harness.label,
                "active_overlay": overlay.overlay,
                "catalog_refresh_required": True,
            }

    @classmethod
    def resolve_for_http_request(
        cls,
        *,
        token: str,
        surface: str,
        company_id: int | None,
        client_name: str | None,
    ) -> UserMcpResolvedContext | None:
        try:
            normalized_surface = cls._normalize_surface(surface)
        except ValueError:
            return None
        token_hash = cls._hash_token(token)
        with cls._ensure_app_context():
            record = (
                UserMcpToken.query.filter_by(token_hash=token_hash)
                .order_by(UserMcpToken.created_at.desc())
                .first()
            )
            if not record:
                return None
            cls._expire_if_needed(record)
            if record.status != "active":
                db.session.commit()
                return None
            user = User.query.get(record.user_id)
            if not user or not getattr(user, "is_active", False):
                return None
            resolved_company_id, resolution_source, accessible_company_ids = cls._resolve_runtime_company_context(
                user,
                requested_company_id=company_id,
                persisted_company_id=record.last_company_id,
            )
            profile = (
                get_access_profile(resolved_company_id, user=user) or "collaborator"
                if resolved_company_id is not None
                else "collaborator"
            )
            fallback_role = PROFILE_TO_FALLBACK_ROLE.get(profile, "colaborador")
            record.last_used_at = cls._utcnow()
            record.last_surface = normalized_surface
            if resolution_source in {"request.company_id", "token.last_company_id", "user.single_accessible_company_id"}:
                record.last_company_id = resolved_company_id
            record.last_client_name = (client_name or "").strip() or record.last_client_name
            record.updated_at = cls._utcnow()
            db.session.commit()
            try:
                active_harness, _active_overlay = cls._resolve_squad_cliente_harness(getattr(record, "last_harness_key", None))
            except ValueError:
                active_harness, _active_overlay = cls._resolve_squad_cliente_harness(None)
                record.last_harness_key = active_harness.key
                db.session.commit()
            return UserMcpResolvedContext(
                token_record_id=record.id,
                user_id=user.id,
                company_id=resolved_company_id,
                fallback_role=fallback_role,
                allowed_surfaces=ALLOWED_SURFACES,
                subject=user.email,
                client_name=record.last_client_name,
                company_resolution_source=resolution_source,
                accessible_company_ids=accessible_company_ids,
                multi_company=len(accessible_company_ids) > 1,
                runtime_profile="squad_cliente",
                actor_type="client_agent",
                harness_key=active_harness.key,
                harness_label=active_harness.label,
                mcp_enabled=True,
                training_completed=True,
            )

    @classmethod
    def _build_notification_body(cls, user: User, record: UserMcpToken, *, days_remaining: int) -> tuple[str, str, str]:
        expiry = record.expires_at.strftime("%d/%m/%Y %H:%M") if record.expires_at else "-"
        profile_url = "/profile"
        if days_remaining > 0:
            subject = "Seu token MCP expira em 3 dias"
            body = (
                f"Olá, {user.name}!\n\n"
                f"Seu token MCP do Sapiens expira em {days_remaining} dias, em {expiry}.\n"
                f"Acesse {profile_url} para renovar o token antes do vencimento."
            )
            whatsapp_message = (
                f"Olá, {user.name}! Seu token MCP do Sapiens expira em {days_remaining} dias ({expiry}). "
                f"Entre em /profile e renove o token para não perder a conexão."
            )
        else:
            subject = "Seu token MCP venceu hoje"
            body = (
                f"Olá, {user.name}!\n\n"
                f"Seu token MCP do Sapiens vence hoje ({expiry}).\n"
                f"Acesse {profile_url} para renovar e atualizar a configuração do seu cliente remoto."
            )
            whatsapp_message = (
                f"Olá, {user.name}! Seu token MCP vence hoje ({expiry}). "
                f"Entre em /profile e renove o token do Sapiens para continuar usando a conexão remota."
            )
        html_body = email_service.build_transactional_email_html(
            subject=subject,
            body=body,
            title=subject,
            footer_note="Aviso automático do acesso MCP do Sapiens.",
        )
        return subject, html_body, whatsapp_message

    @classmethod
    def send_expiration_notifications(cls, *, reference_date: date | None = None) -> dict[str, Any]:
        with cls._ensure_app_context():
            today = reference_date or cls._utcnow().date()
            tokens = (
                UserMcpToken.query.filter(UserMcpToken.status == "active")
                .order_by(UserMcpToken.expires_at.asc())
                .all()
            )
            processed = 0
            notified = 0
            for candidate in tokens:
                # Each scheduler execution must claim the row before checking
                # the notification marker. PostgreSQL SKIP LOCKED makes a
                # concurrent execution skip a token already being processed.
                record = (
                    UserMcpToken.query.filter_by(id=candidate.id)
                    .with_for_update(skip_locked=True)
                    .populate_existing()
                    .first()
                )
                if not record:
                    continue
                cls._expire_if_needed(record)
                if record.status != "active" or not record.expires_at:
                    continue
                days_remaining = (record.expires_at.date() - today).days
                if days_remaining not in {3, 0}:
                    continue
                if days_remaining == 3 and record.notice_d3_sent_at:
                    continue
                if days_remaining == 0 and record.notice_d0_sent_at:
                    continue
                user = User.query.get(record.user_id)
                if not user or not getattr(user, "is_active", False):
                    continue
                subject, html_body, whatsapp_message = cls._build_notification_body(
                    user,
                    record,
                    days_remaining=days_remaining,
                )
                plain_text = html_body.replace("<br>", "\n")
                email_ok = bool(user.email) and email_service.send_email([user.email], subject, plain_text, html_body=html_body)
                whatsapp_ok = bool(user.whatsapp) and whatsapp_service.send_message(user.whatsapp, whatsapp_message)
                if email_ok or whatsapp_ok:
                    notified += 1
                    if days_remaining == 3:
                        record.notice_d3_sent_at = cls._utcnow()
                    else:
                        record.notice_d0_sent_at = cls._utcnow()
                processed += 1
            db.session.commit()
            return {"processed": processed, "notified": notified}


user_mcp_token_service = UserMcpTokenService()
