from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any

from src.intelligence.security.runtime_profiles import get_runtime_profile_spec


class MCPConnectionSnippetService:
    """Gera saídas prontas para copiar de uma conexão MCP remota."""

    RUNTIME_PROFILES = {
        "sapiens_default": {
            "label": "Sapiens",
            "experience_label": "Sapiens",
            "canonical_label": "Sapiens Default",
            "cli_command": "sapiens on",
            "activation_subject": "ative o Sapiens neste cliente usando a conexão MCP abaixo.",
            "url": "https://app.gestaoversus.com.br/mcp/user",
            "surface": "user",
            "startup_tools": [
                "bootstrap_session_context",
                "describe_app32_available_sapiens_squads_tool",
                "list_user_app32_capabilities",
                "describe_app32_surface_playbooks_tool",
            ],
            "routing_note": "Se você pedir para registrar, abrir card, encaminhar ao squad ou anotar uma melhoria, eu devo usar a tool request_engineering_suggestion.",
        },
        "squad_versus": {
            "label": "Sapiens Consultor",
            "experience_label": "Sapiens Consultor",
            "canonical_label": "Squad Versus",
            "cli_command": "sapiens consultor on",
            "activation_subject": "ative o Sapiens Consultor neste cliente usando a conexão MCP abaixo.",
            "url": "https://app.gestaoversus.com.br/mcp/admin",
            "surface": "admin",
            "startup_tools": [
                "bootstrap_session_context",
                "describe_app32_squad_runtime_tool",
                "list_admin_app32_capabilities",
                "describe_app32_profile_contracts_tool",
                "describe_app32_surface_playbooks_tool",
                "describe_app32_domain_playbooks_tool",
                "describe_app32_release_checklist_tool",
                "describe_app32_tool_freeze_procedure_tool",
                "describe_app32_external_ai_onboarding_tool",
                "describe_app32_operational_readiness_tool",
            ],
            "routing_note": "O Squad Versus deve operar como consultoria e governança: começar por discovery, respeitar company_id explícito nas surfaces privilegiadas e evitar mutações sem necessidade e sem trilha.",
        },
        "squad_cliente": {
            "label": "Sapiens Cliente",
            "experience_label": "Sapiens Cliente",
            "canonical_label": "Squad Cliente",
            "cli_command": "sapiens cliente on",
            "activation_subject": "ative o Sapiens Cliente neste cliente usando a conexão MCP abaixo.",
            "url": "https://app.gestaoversus.com.br/mcp/user",
            "surface": "user",
            "startup_tools": [
                "bootstrap_session_context",
                "resolve_app32_instruction_bundle_tool",
                "describe_app32_squad_runtime_tool",
                "list_user_app32_capabilities",
                "describe_app32_profile_contracts_tool",
                "describe_app32_surface_playbooks_tool",
                "describe_app32_domain_playbooks_tool",
                "describe_app32_release_checklist_tool",
                "describe_app32_tool_freeze_procedure_tool",
                "describe_app32_external_ai_onboarding_tool",
            ],
            "routing_note": "O Squad Cliente deve operar em menor privilégio, com utilização assistida, foco operacional e sem tentar contornar restrições de admin, analytics ou ops.",
        },
        "engineering": {
            "label": "Sapiens Engenharia",
            "experience_label": "Sapiens Engenharia",
            "canonical_label": "Squad de Engenharia",
            "cli_command": "sapiens engenharia on",
            "activation_subject": "ative o Sapiens Engenharia neste ambiente usando a conexão MCP abaixo.",
            "url": "https://app.gestaoversus.com.br/mcp/ops",
            "surface": "ops",
            "startup_tools": [
                "bootstrap_session_context",
                "describe_app32_squad_runtime_tool",
                "list_ops_app32_capabilities",
                "describe_app32_profile_contracts_tool",
                "describe_app32_surface_playbooks_tool",
                "describe_app32_domain_playbooks_tool",
                "describe_app32_release_checklist_tool",
                "describe_app32_tool_freeze_procedure_tool",
                "describe_app32_external_ai_onboarding_tool",
                "describe_app32_operational_readiness_tool",
            ],
            "routing_note": "O Squad de Engenharia deve operar com disciplina técnica: triagem via coordenador, discovery antes de intervenção, company_id explícito quando aplicável e trilha auditável em ops/admin/analytics.",
        },
    }

    @classmethod
    def build_prompt(cls, payload: dict[str, Any]) -> str:
        normalized = cls._normalize(payload)
        source_json = cls._build_source_json(normalized)
        profile = cls.RUNTIME_PROFILES[normalized["profile"]]
        runtime_spec = get_runtime_profile_spec(normalized["profile"])
        startup_tools = ", ".join(profile["startup_tools"])
        harness_label = normalized.get("harness_label") or (
            runtime_spec.default_harness_label if runtime_spec is not None else None
        )
        experience_label = profile["experience_label"]
        canonical_label = profile["canonical_label"]
        cli_command = profile["cli_command"]

        lines = [
            f"Quero que você {profile['activation_subject']}",
            "",
            "Dados da conexão:",
            f"- Nome: {normalized['name']}",
            f"- Empresa padrão: {normalized['default_company']}",
            f"- URL: {normalized['url']}",
            f"- Autenticação: {normalized['auth_label']}",
            f"- Experiência visível: {experience_label}",
            f"- Família canônica: {canonical_label}",
            f"- Surface alvo: {profile['surface']}",
            f"- Token: {normalized['token']}",
        ]
        if harness_label:
            lines.append(f"- Harness inicial: {harness_label}")
        lines.extend(
            [
                "",
                "JSON:",
                source_json,
                "",
                "Sua tarefa:",
                "1. Verifique se este cliente suporta configuração MCP automática.",
                "2. Se suportar, faça a configuração.",
                f"3. Se este cliente permitir criar atalho, comando, agente ou persona, crie a entrada visível chamada {experience_label}.",
                f"4. Se este cliente permitir alias textual, configure também o comando simples `{cli_command}`.",
                "5. Explique que a entrada começa pelo agente coordenador do squad e pode rotear internamente para especialistas conforme a necessidade.",
                "5.1. Se o profile for `squad_cliente`, explique também que a família inicial oficial é composta por Coordenador, Comercial, Operacional e Adm/Financeiro, com economia de tokens por padrão.",
                f"6. Assim que a conexão MCP estiver ativa, execute primeiro as tools de startup: {startup_tools}.",
                "6.1. Use `resolve_app32_instruction_bundle_tool` para carregar o bundle mínimo, versionado e cacheável da sessão.",
                "6.2. Use `describe_app32_squad_runtime_tool` como contrato operacional curto do squad antes de agir.",
                "6.3. Antes de operar, trate profile contracts, surface/domain playbooks, release checklist, tool freeze e onboarding externo como discovery obrigatório.",
                f"7. Ao ativar, use esta mensagem inicial do {experience_label}:",
                "",
                "◆ SAPIENS · Gestão Versus ● ativo",
                "",
                f"Olá! Sou o {experience_label}, assistente virtual da Versus.",
                "Estamos conectados ao Sistema de Gestão Versus — pode começar.",
                "",
                "Se você encontrar algum bug, tiver uma observação ou sugestão, me avise que eu registro um card formal para o Squad de Engenharia.",
                profile["routing_note"],
                "",
                "8. Se este cliente não suportar configuração automática, atalho, agente ou integração MCP nativa, responda exatamente assim:",
                f"- Este cliente não suporta ativação automática do {experience_label}.",
                "- A conexão técnica está pronta, mas precisa ser configurada manualmente.",
                "- Se quiser, eu posso te mostrar o passo a passo manual para este cliente.",
                f"9. Se este cliente suportar MCP mas não suportar atalho, mantenha a conexão ativa, execute a sequência de startup informada e explique ao usuário como chamar o {experience_label} de forma simples na conversa.",
                "10. Não invente valores. Use exatamente os dados fornecidos.",
                "",
                "Formato da resposta:",
                "1. Diagnóstico",
                "2. Ação executada",
                "3. Resultado final",
                f"4. Como usar o {experience_label} neste cliente",
                "5. Se não suportar, mostrar a resposta padrão",
            ]
        )
        return "\n".join(lines)

    @classmethod
    def build_raw_config(cls, payload: dict[str, Any]) -> str:
        normalized = cls._normalize(payload)
        profile = cls.RUNTIME_PROFILES[normalized["profile"]]
        config = OrderedDict(
            [
                ("name", normalized["name"]),
                ("transport", "http"),
                ("url", normalized["url"]),
                (
                    "metadata",
                    OrderedDict(
                        [
                            ("profile", normalized["profile"]),
                            ("profile_label", profile["canonical_label"]),
                            ("experience_label", profile["experience_label"]),
                            ("surface", profile["surface"]),
                            ("harness_key", normalized.get("harness_key")),
                            ("harness_label", normalized.get("harness_label")),
                        ]
                    ),
                ),
                (
                    "headers",
                    OrderedDict(
                        [
                            ("Authorization", f"Bearer {normalized['token']}"),
                        ]
                    ),
                ),
            ]
        )
        return json.dumps(config, ensure_ascii=False, indent=2)

    @classmethod
    def build_source_json(cls, payload: dict[str, Any]) -> str:
        normalized = cls._normalize(payload)
        return cls._build_source_json(normalized)

    @classmethod
    def _build_source_json(cls, normalized: dict[str, str]) -> str:
        profile = cls.RUNTIME_PROFILES[normalized["profile"]]
        source = OrderedDict(
            [
                ("auth_type", "bearer"),
                ("name", normalized["name"]),
                ("profile", normalized["profile"]),
                ("experience_label", profile["experience_label"]),
                ("surface", profile["surface"]),
                ("harness_key", normalized.get("harness_key")),
                ("harness_label", normalized.get("harness_label")),
                ("token", normalized["token"]),
                ("url", normalized["url"]),
            ]
        )
        return json.dumps(source, ensure_ascii=False, indent=2)

    @classmethod
    def _normalize(cls, payload: dict[str, Any]) -> dict[str, str]:
        name = str(payload.get("name") or "").strip()
        default_company = str(payload.get("default_company") or "sem empresa padrão").strip()
        url = str(payload.get("url") or "").strip()
        auth_type = str(payload.get("auth_type") or "bearer").strip().lower()
        token = str(payload.get("token") or "").strip()
        profile = str(payload.get("profile") or "sapiens_default").strip().lower()
        harness_key = str(payload.get("harness_key") or "").strip()

        if profile not in cls.RUNTIME_PROFILES:
            raise ValueError("Perfil de runtime MCP inválido.")

        profile_defaults = cls.RUNTIME_PROFILES[profile]
        runtime_spec = get_runtime_profile_spec(profile)
        if not name:
            name = str(profile_defaults["label"]).strip()
        if not url:
            url = str(profile_defaults["url"]).strip()
        if not harness_key and runtime_spec is not None:
            harness_key = runtime_spec.default_harness_key or ""
        harness_label = None
        if runtime_spec is not None and harness_key:
            harness = next((item for item in runtime_spec.harnesses if item.key == harness_key), None)
            if harness is not None:
                harness_label = harness.label

        if not name:
            raise ValueError("Nome da conexão é obrigatório.")
        if not url:
            raise ValueError("URL da conexão é obrigatória.")
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL inválida. Use http:// ou https://.")
        if auth_type != "bearer":
            raise ValueError("No momento, apenas autenticação Bearer Token é suportada.")
        if not token:
            raise ValueError("Token Bearer é obrigatório.")

        return {
            "name": name,
            "default_company": default_company or "sem empresa padrão",
            "url": url,
            "auth_type": auth_type,
            "auth_label": "Bearer Token",
            "token": token,
            "profile": profile,
            "harness_key": harness_key or None,
            "harness_label": harness_label,
        }
