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
GENERIC_INSTALLER_COMMAND = ".\\app32\\scripts\\installers\\install-sapiens-runtime.ps1"
SAPIENS_CLIENTE_INSTALLER_COMMAND = ".\\app32\\scripts\\installers\\install-sapiens-cliente.ps1"
CLAUDE_SLASH_INSTALLER_RAW_URL = "https://raw.githubusercontent.com/VrsEco/Principal/main/app32/scripts/installers/install-claude-sapiens-slash-commands.ps1"
RUNTIME_LABELS = {
    "claude": "Claude Code / aba Code do Claude Desktop",
    "codex": "Codex",
    "antigravity": "Antigravity",
    "other": "Outro cliente MCP",
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
    def _ensure_app_context() -> Iterator[None]:
        if has_app_context():
            yield
            return

        from app import create_app

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
        company_id: int | None,
        profile_key: str,
        surface: str,
        experience_label: str,
        canonical_label: str,
        harness_key: str | None,
        harness_label: str | None,
        command_alias: str | None,
    ) -> str:
        company_arg = f" -CompanyId {company_id}" if company_id else ""
        harness_key_value = harness_key or ""
        harness_label_value = harness_label or ""
        command_alias_value = command_alias or ""
        server_name = experience_label.strip().lower().replace(" ", "-")
        return (
            "powershell -ExecutionPolicy Bypass -File "
            f"\"{GENERIC_INSTALLER_COMMAND}\""
            f" -ClientRuntime \"{runtime_key or 'other'}\""
            f"{company_arg}"
            f" -Profile \"{profile_key}\""
            f" -Surface \"{surface}\""
            f" -ExperienceLabel \"{experience_label}\""
            f" -CanonicalLabel \"{canonical_label}\""
            f" -HarnessKey \"{harness_key_value}\""
            f" -HarnessLabel \"{harness_label_value}\""
            f" -ServerName \"{server_name}\""
            f" -CommandAlias \"{command_alias_value}\""
        )

    @classmethod
    def _build_squad_cliente_install_command(
        cls,
        *,
        runtime_key: str | None,
        company_id: int | None,
    ) -> str:
        company_arg = f" -CompanyId {company_id}" if company_id else ""
        return (
            "powershell -ExecutionPolicy Bypass -File "
            f"\"{SAPIENS_CLIENTE_INSTALLER_COMMAND}\""
            f" -ClientRuntime \"{runtime_key or 'other'}\""
            f"{company_arg}"
        )

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
                    {"label": "Comando Claude", "value": "claude mcp add --scope user --transport http ..."},
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
    def _build_guided_install_steps(
        cls,
        *,
        runtime_config: dict[str, Any],
        connection_name: str,
        url: str,
        token_value: str,
    ) -> list[str]:
        runtime = runtime_config["runtime"]
        if runtime == "claude":
            claude_add_command = cls._build_claude_mcp_add_command(
                runtime_config=runtime_config,
                url=url,
                token_value=token_value,
            )
            return [
                "No terminal do Windows, confirme que o Claude Code está instalado com claude --version.",
                "Se estiver no Claude Desktop, abra a aba Code. Não use a aba Chat para este onboarding MCP local.",
                f"Execute o comando oficial do APP32 para registrar o MCP no registry real do Claude Code: {claude_add_command}.",
                "Se o Claude solicitar aprovação do servidor, confirme a inclusão do MCP user.",
                "Rode claude mcp list e confirme que a entrada sapiens-user aparece como HTTP, sem fluxo OAuth.",
                "Se necessário, confira o registry do Claude Code (~/.claude.json ou equivalente gerenciado da instalação) e valide que mcpServers.sapiens-user foi gravado ali.",
                "Abra uma nova sessão do Claude Code, ou uma nova sessão na aba Code do Claude Desktop, e use o prompt de ativação recomendado pelo APP32.",
                "Como smoke inicial, rode /sapiens-cliente-on e confirme o bootstrap remoto pelo instruction registry.",
            ]
        if runtime in {"codex", "antigravity"} and runtime_config.get("install_command"):
            return [
                f"Abra o terminal do cliente {runtime_config['runtime_label']}.",
                "Execute o comando de instalação sugerido pelo APP32.",
                "Quando o instalador pedir, cole o token MCP gerado nesta página.",
                "Confirme a gravação da conexão MCP no cliente.",
                "Depois da instalação, abra uma conversa, rode /sapiens-cliente-on e confirme o bootstrap remoto.",
            ]
        return [
            f"Abra a área de conectores ou MCP do cliente {runtime_config['runtime_label']}.",
            f"Crie uma conexão chamada {connection_name}.",
            f"Cole a URL {url}.",
            "Escolha autenticação Bearer Token.",
            f"Cole o token {token_value}.",
            "Salve a conexão, rode /sapiens-cliente-on e confirme o bootstrap remoto.",
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
                    "Comando oficial recomendado para o Claude Code:",
                    "```bash",
                    claude_mcp_add_command,
                    "```",
                    "",
                    "JSON de referência esperado no registry do Claude Code (~/.claude.json ou equivalente gerenciado da instalação):",
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
    ) -> dict[str, Any]:
        multiple_companies = len(companies) > 1
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
    ) -> dict[str, Any]:
        normalized_runtime = cls._normalize_runtime(runtime)
        normalized_squad = cls._normalize_squad(squad)
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
            if normalized_runtime in {"codex", "antigravity"}:
                install_mode = "self_service"
                availability_label = "Instalação automática guiada"
                install_command = cls._build_squad_cliente_install_command(
                    runtime_key=normalized_runtime,
                    company_id=company_id,
                )
            elif normalized_runtime == "claude":
                install_mode = "guided_manual"
                availability_label = "Instalação manual guiada"
                install_command = None
            instruction_text = (
                f"Você está preparando o {experience_label} para uso no {runtime_label}. "
                "Gere o código para IA conforme as configurações escolhidas e siga o passo a passo orientado pelo APP32. "
                "A instalação entra pelo Coordenador e depois pode chamar Comercial, Operacional e Administrativo/Financeiro quando necessário."
            )
            if normalized_runtime == "claude":
                instruction_text = (
                    f"Você está preparando o {experience_label} para uso no {runtime_label}. "
                    "Neste cliente, a conexão MCP usa o registry nativo do Claude Code (~/.claude.json ou equivalente gerenciado da instalação). "
                    "Use a aba Code do Claude Desktop, não a aba Chat. O APP32 vai te entregar o token, a URL, o comando claude mcp add e o prompt de ativação para operar sem depender de slash commands."
                )
            if normalized_runtime == "other":
                instruction_text = (
                    f"Você está preparando o {experience_label} para uso em outro cliente de IA. "
                    "Gere o código para IA conforme as configurações escolhidas. "
                    "Se este cliente não suportar integração automática, use o modo avançado com a configuração técnica."
                )
        elif normalized_squad == "engineering":
            resolved_profile = "engineering"
            resolved_surface = "ops"
            install_mode = "guided_controlled"
            availability_label = "Instalação guiada controlada"
            install_command = cls._build_generic_install_command(
                runtime_key=normalized_runtime,
                company_id=company_id,
                profile_key=resolved_profile,
                surface=resolved_surface,
                experience_label=experience_label,
                canonical_label=squad_label,
                harness_key=runtime_profile_spec.default_harness_key if runtime_profile_spec else None,
                harness_label=runtime_profile_spec.default_harness_label if runtime_profile_spec else None,
                command_alias=command_alias,
            )
            instruction_text = (
                f"Você está preparando o {experience_label} para uso no {runtime_label}. "
                "O Squad de Engenharia opera em ambiente técnico controlado e prioriza excelência técnica. "
                "Use o instalador apenas em rollout autorizado pela Versus."
            )
        elif normalized_squad == "squad_versus":
            resolved_profile = "squad_versus"
            resolved_surface = "admin"
            install_mode = "guided_controlled"
            availability_label = "Instalação guiada controlada"
            install_command = cls._build_generic_install_command(
                runtime_key=normalized_runtime,
                company_id=company_id,
                profile_key=resolved_profile,
                surface=resolved_surface,
                experience_label=experience_label,
                canonical_label=squad_label,
                harness_key=runtime_profile_spec.default_harness_key if runtime_profile_spec else None,
                harness_label=runtime_profile_spec.default_harness_label if runtime_profile_spec else None,
                command_alias=command_alias,
            )
            instruction_text = (
                f"Você está preparando o {experience_label} para uso no {runtime_label}. "
                "O Squad Versus usa surface administrativa e fica sob rollout controlado. "
                "Gere o comando apenas para instalação assistida pela Versus."
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
            "supports_personal_token": resolved_surface == "user",
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
        multi_company = len(accessible_company_ids) > 1
        return {
            "user_id": getattr(user, "id", None),
            "accessible_company_ids": list(accessible_company_ids),
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
    ) -> tuple[UserMcpToken, str]:
        active = cls.get_active_token_record(user.id)
        if active:
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
            last_client_name=(client_name or "").strip() or None,
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
            authorized_squad = cls._resolve_authorized_squad_for_user(user, squad)
            resolved_company_id = cls._resolve_explicit_company_id_for_user(user, company_id)
            companies = cls.list_accessible_companies(user)
            company_lookup = {item["id"]: item for item in companies}
            selected_company = company_lookup.get(resolved_company_id) if resolved_company_id else None
            public_base = str(os.environ.get("APP32_MCP_PUBLIC_BASE_URL") or DEFAULT_PUBLIC_BASE_URL).rstrip("/")
            runtime_config = cls._resolve_runtime_installation(
                runtime=runtime,
                squad=authorized_squad,
                company_id=resolved_company_id,
            )
            resolved_surface = runtime_config["resolved_surface"]
            display_name = (
                selected_company["label"]
                if selected_company
                else ("Escopo dinâmico multiempresa" if resolved_surface == "user" else "Sem empresa padrão")
            )
            token_value = plaintext_token or "TOKEN_GERADO_APENAS_NA_RENOVACAO"
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
            activation_commands = cls._build_activation_commands(allowed_squads)
            deactivation_commands = cls._build_deactivation_commands(allowed_squads)
            activation_selection_prompt = cls._build_activation_selection_prompt(allowed_squads)
            activation_commands_install_command = (
                cls._build_claude_activation_install_command(allowed_squads)
                if runtime_config["runtime"] == "claude"
                else None
            )
            session_lifecycle = cls._build_session_lifecycle(
                runtime_config=runtime_config,
                allowed_squads=allowed_squads,
                company_id=resolved_company_id,
            )
            company_context_rules = cls._build_company_context_rules(
                companies=companies,
                selected_company=selected_company,
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
            installation_command = runtime_config["install_command"]
            installation_instruction = runtime_config["instruction_text"]
            copy_install_command_text = installation_command
            if runtime_config["runtime"] == "claude" and runtime_config["squad"] == "squad_cliente":
                claude_mcp_add_command = cls._build_claude_mcp_add_command(
                    runtime_config=runtime_config,
                    url=url,
                    token_value=token_value,
                )
                installation_instruction = (
                    "Experiência recomendada: instalar o Sapiens Cliente no Claude Code / aba Code do Claude Desktop pelo comando nativo claude mcp add. "
                    "Gere ou renove o token, registre o servidor HTTP no registry real do Claude Code (~/.claude.json ou equivalente gerenciado da instalação) e use o prompt de ativação recomendado pelo APP32 na aba Code."
                )
                installation_command = claude_mcp_add_command
                copy_install_command_text = claude_mcp_add_command
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
                installation_instruction = (
                    f"{installation_instruction}\n\n"
                    f"Comando sugerido:\n{installation_command}\n\n"
                    "Quando o instalador abrir, ele vai localizar o arquivo MCP do cliente, pedir seu e-mail e solicitar o token MCP no momento correto, de forma interativa e segura."
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
                    "7. Se o fluxo funcionar, responda com a mensagem de ativação e mantenha o squad ativo nesta sessão.\n\n"
                    "Startup sequence esperada após a escolha do squad:\n"
                    + "\n".join([f"- {item}" for item in session_lifecycle["startup_tools"]])
                    + "\n\n"
                    f"Badge esperado: `{session_lifecycle['session_badge'] or runtime_config['experience_label'] + ' On'}`.\n"
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
                    + "\n\nImportante: o caminho canônico de operação é o MCP registrado por `claude mcp add` + prompt de ativação no Claude Code ou na aba Code do Claude Desktop. Slash commands são opcionais e podem variar conforme a versão do runtime."
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
                "install_command": installation_command,
                "copy_install_command_text": copy_install_command_text,
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
                harness_key="harness_coordenador_cliente_v1",
                harness_label="Harness Coordenador do Squad Cliente",
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
            for record in tokens:
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
