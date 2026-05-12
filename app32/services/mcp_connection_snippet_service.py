from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any


class MCPConnectionSnippetService:
    """Gera saídas prontas para copiar de uma conexão MCP remota."""

    RUNTIME_PROFILES = {
        "sapiens_default": {
            "label": "Sapiens User",
            "activation_subject": "ative o Sapiens neste cliente usando a conexão MCP abaixo.",
            "url": "https://app.gestaoversus.com.br/mcp/user",
            "surface": "user",
            "startup_tools": [
                "list_user_app32_capabilities",
                "describe_app32_surface_playbooks_tool",
            ],
            "routing_note": "Se você pedir para registrar, abrir card, encaminhar ao squad ou anotar uma melhoria, eu devo usar a tool request_engineering_suggestion.",
        },
        "squad_versus": {
            "label": "Squad Versus",
            "activation_subject": "ative o Squad Versus neste cliente usando a conexão MCP abaixo.",
            "url": "https://app.gestaoversus.com.br/mcp/admin",
            "surface": "admin",
            "startup_tools": [
                "list_admin_app32_capabilities",
                "describe_app32_profile_contracts_tool",
                "describe_app32_surface_playbooks_tool",
                "describe_app32_domain_playbooks_tool",
            ],
            "routing_note": "O Squad Versus deve operar como consultoria e governança: começar por discovery, respeitar company_id explícito nas surfaces privilegiadas e evitar mutações sem necessidade e sem trilha.",
        },
        "squad_cliente": {
            "label": "Squad Cliente",
            "activation_subject": "ative o Squad Cliente neste cliente usando a conexão MCP abaixo.",
            "url": "https://app.gestaoversus.com.br/mcp/user",
            "surface": "user",
            "startup_tools": [
                "list_user_app32_capabilities",
                "describe_app32_profile_contracts_tool",
                "describe_app32_surface_playbooks_tool",
            ],
            "routing_note": "O Squad Cliente deve operar em menor privilégio, com utilização assistida, foco operacional e sem tentar contornar restrições de admin, analytics ou ops.",
        },
    }

    @classmethod
    def build_prompt(cls, payload: dict[str, Any]) -> str:
        normalized = cls._normalize(payload)
        source_json = cls._build_source_json(normalized)
        profile = cls.RUNTIME_PROFILES[normalized["profile"]]
        startup_tools = ", ".join(profile["startup_tools"])

        lines = [
            f"Quero que você {profile['activation_subject']}",
            "",
            "Dados da conexão:",
            f"- Nome: {normalized['name']}",
            f"- Empresa padrão: {normalized['default_company']}",
            f"- URL: {normalized['url']}",
            f"- Autenticação: {normalized['auth_label']}",
            f"- Perfil de runtime: {profile['label']}",
            f"- Surface alvo: {profile['surface']}",
            f"- Token: {normalized['token']}",
            "",
            "JSON:",
            source_json,
            "",
            "Sua tarefa:",
            "1. Verifique se este cliente suporta configuração MCP automática.",
            "2. Se suportar, faça a configuração.",
            "3. Se este cliente permitir criar atalho, comando, agente ou persona, crie um atalho chamado Sapiens.",
            f"4. Assim que a conexão MCP estiver ativa, execute primeiro as tools de startup: {startup_tools}.",
            "5. Ao ativar, use esta mensagem inicial:",
            "",
            "◆ SAPIENS · Gestão Versus ● ativo",
            "",
            "Olá! Sou o Sapiens, assistente virtual da Versus.",
            "Estamos conectados ao Sistema de Gestão Versus — pode começar.",
            "",
            "Se você encontrar algum bug, tiver uma observação ou sugestão, me avise que eu registro um card formal para o Squad de Engenharia.",
            profile["routing_note"],
            "",
            "6. Se este cliente não suportar configuração automática, atalho, agente ou integração MCP nativa, responda exatamente assim:",
            "- Este cliente não suporta ativação automática do Sapiens.",
            "- A conexão técnica está pronta, mas precisa ser configurada manualmente.",
            "- Se quiser, eu posso te mostrar o passo a passo manual para este cliente.",
            "7. Se este cliente suportar MCP mas não suportar atalho, mantenha a conexão ativa, execute a sequência de startup informada e explique ao usuário como chamar o Sapiens de forma simples na conversa.",
            "8. Não invente valores. Use exatamente os dados fornecidos.",
            "",
            "Formato da resposta:",
            "1. Diagnóstico",
            "2. Ação executada",
            "3. Resultado final",
            "4. Como usar o Sapiens neste cliente",
            "5. Se não suportar, mostrar a resposta padrão",
        ]
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
                            ("profile_label", profile["label"]),
                            ("surface", profile["surface"]),
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
                ("surface", profile["surface"]),
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

        if profile not in cls.RUNTIME_PROFILES:
            raise ValueError("Perfil de runtime MCP inválido.")

        profile_defaults = cls.RUNTIME_PROFILES[profile]
        if not name:
            name = str(profile_defaults["label"]).strip()
        if not url:
            url = str(profile_defaults["url"]).strip()

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
        }
