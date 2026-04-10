from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_DOMAIN_EXAMPLES_MANIFEST,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, *, domain: str | None = None, example_id: str | None = None) -> MCPResponseMeta:
    tags = ["domain_examples"]
    if domain:
        tags.append(f"domain:{domain}")
    if example_id:
        tags.append(f"example:{example_id}")
    return MCPResponseMeta(
        domain="mcp_domain_examples",
        operation=operation,
        scope="mcp_user",
        capability=f"mcp_domain_examples.{operation}",
        permissions=["mcp.domain_examples.read"],
        tags=tags,
    )


def _success(operation: str, data: Any, *, domain: str | None = None, example_id: str | None = None) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, domain=domain, example_id=example_id),
    ).model_dump(mode="json")


def _error(operation: str, code: str, message: str, *, domain: str | None = None, example_id: str | None = None) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code=code, message=message),
        meta=_meta(operation, domain=domain, example_id=example_id),
    ).model_dump(mode="json")


def register_domain_example_tools(mcp: Any) -> None:
    """Registra tools MCP de descoberta dos exemplos oficiais por domínio IA/MCP."""

    @mcp.tool()
    def describe_app32_domain_examples_tool(
        domain: Optional[str] = None,
        example_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Descreve exemplos oficiais de fluxos MCP do APP32 para os domínios
        routine, strategy e finance.
        """
        if example_id:
            example = APP32_DOMAIN_EXAMPLES_MANIFEST.get_example(example_id)
            if example is None:
                return _error(
                    "domain_examples.describe",
                    "domain_example_not_found",
                    f"Exemplo MCP não encontrado: {example_id}.",
                    example_id=(example_id or "").strip().lower() or None,
                )
            return _success(
                "domain_examples.describe",
                example.model_dump(mode="json"),
                domain=example.domain,
                example_id=example.example_id,
            )

        if domain:
            normalized = domain.strip().lower()
            examples = APP32_DOMAIN_EXAMPLES_MANIFEST.get_domain_examples(normalized)
            if not examples:
                return _error(
                    "domain_examples.describe",
                    "domain_examples_not_found",
                    f"Nenhum exemplo MCP encontrado para o domínio: {domain}.",
                    domain=normalized or None,
                )
            return _success(
                "domain_examples.describe",
                [example.model_dump(mode="json") for example in examples],
                domain=normalized,
            )

        return _success(
            "domain_examples.describe",
            APP32_DOMAIN_EXAMPLES_MANIFEST.model_dump(mode="json"),
        )


__all__ = ["register_domain_example_tools"]
