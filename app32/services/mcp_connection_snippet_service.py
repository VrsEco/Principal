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
            "Quero que você configure esta conexão MCP neste cliente.",
            "",
            "Use exatamente estes dados:",
            f"- Nome: {normalized['name']}",
            f"- Empresa padrão: {normalized['default_company']}",
            f"- URL: {normalized['url']}",
            f"- Autenticação: {normalized['auth_label']}",
            f"- Token: {normalized['token']}",
            "",
            "JSON de referência:",
            source_json,
            "",
            "Sua tarefa não é apenas explicar. Sua tarefa é tentar realizar a configuração desta conexão neste cliente.",
            "",
            "Antes de continuar, pergunte ao usuário se ele quer:",
            "- configuração automática",
            "- configuração manual",
            "",
            "Regras:",
            "1. Se este cliente permitir configuração automática e o usuário autorizar, faça a configuração.",
            "2. Se a configuração automática não for possível, gere tudo pronto para configuração manual.",
            "3. Se este cliente não suportar MCP nativamente, informe isso com clareza e apresente a melhor alternativa.",
            "4. Não invente valores. Use exatamente os dados fornecidos.",
            "5. No final, entregue a solução final já pronta para o usuário usar.",
            "",
            "Responda neste formato:",
            "1. Pergunta ao usuário: automático ou manual?",
            "2. Diagnóstico rápido",
            "3. Configuração pronta",
            "4. Como aplicar",
            "5. Como testar",
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
