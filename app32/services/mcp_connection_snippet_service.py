from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any


class MCPConnectionSnippetService:
    """Gera saídas prontas para copiar de uma conexão MCP remota."""

    @classmethod
    def build_prompt(cls, payload: dict[str, Any]) -> str:
        normalized = cls._normalize(payload)
        source_json = cls._build_source_json(normalized)

        lines = [
            "Quero que você ative o Sapiens neste cliente usando a conexão MCP abaixo.",
            "",
            "Dados da conexão:",
            f"- Nome: {normalized['name']}",
            f"- Empresa padrão: {normalized['default_company']}",
            f"- URL: {normalized['url']}",
            f"- Autenticação: {normalized['auth_label']}",
            f"- Token: {normalized['token']}",
            "",
            "JSON:",
            source_json,
            "",
            "Sua tarefa:",
            "1. Verifique se este cliente suporta configuração MCP automática.",
            "2. Se suportar, faça a configuração.",
            "3. Se este cliente permitir criar atalho, comando, agente ou persona, crie um atalho chamado Sapiens.",
            "4. Assim que a conexão MCP estiver ativa, faça automaticamente uma chamada de discovery inicial com a tool bootstrap_session_context para carregar o catálogo resumido permitido.",
            "5. Ao ativar, use esta mensagem inicial:",
            "",
            "◆ SAPIENS · Gestão Versus ● ativo",
            "",
            "Olá! Sou o Sapiens, assistente virtual da Versus.",
            "Estamos conectados ao Sistema de Gestão Versus — pode começar.",
            "",
            "Se você encontrar algum bug, tiver uma observação ou sugestão, me avise que eu registro um card formal para o Squad de Engenharia.",
            "Se você pedir para registrar, abrir card, encaminhar ao squad ou anotar uma melhoria, eu devo usar a tool request_engineering_suggestion.",
            "",
            "6. Se este cliente não suportar configuração automática, atalho, agente ou integração MCP nativa, responda exatamente assim:",
            "- Este cliente não suporta ativação automática do Sapiens.",
            "- A conexão técnica está pronta, mas precisa ser configurada manualmente.",
            "- Se quiser, eu posso te mostrar o passo a passo manual para este cliente.",
            "7. Se este cliente suportar MCP mas não suportar atalho, mantenha a conexão ativa, execute o bootstrap_session_context e informe ao usuário como chamar o Sapiens de forma simples na conversa.",
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
        config = OrderedDict(
            [
                ("name", normalized["name"]),
                ("transport", "http"),
                ("url", normalized["url"]),
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
        source = OrderedDict(
            [
                ("auth_type", "bearer"),
                ("name", normalized["name"]),
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
        }
