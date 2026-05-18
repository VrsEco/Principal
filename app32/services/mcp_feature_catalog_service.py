from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class MCPFeatureCatalogError(RuntimeError):
    """Erro base do catálogo documental MCP."""


class MCPFeatureCatalogContextError(MCPFeatureCatalogError):
    """Contexto insuficiente para acessar o catálogo."""


class MCPFeatureCatalogAccessError(MCPFeatureCatalogError):
    """Feature existe, mas não está autorizada para a surface atual."""


class MCPFeatureCatalogNotFoundError(MCPFeatureCatalogError):
    """Feature ou guia não encontrado."""


@dataclass(frozen=True)
class MCPDocumentationContext:
    company_id: int | None
    user_id: int | None
    role: str
    surface: str
    client: str
    transport: str
    thread_id: str | None = None


class MCPFeatureCatalogService:
    """Leitura do catálogo operacional usado por humano e IA via MCP."""

    def __init__(
        self,
        *,
        catalog_path: Path | None = None,
        guides_root: Path | None = None,
    ) -> None:
        docs_root = Path(__file__).resolve().parents[2] / "docs" / "mcp"
        self.catalog_path = catalog_path or (docs_root / "catalogo_features.yaml")
        self.guides_root = guides_root or (docs_root / "features")

    def bootstrap_context(
        self,
        context: MCPDocumentationContext,
        *,
        domain: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        company_required = context.surface != "user"
        if company_required:
            self._require_company_context(context)
        documented_domains = self.list_domains(context.surface)
        published_domains = self._list_published_domains(context.surface)
        features = self.list_features(
            context.surface,
            domain=domain,
            search=search,
        )
        return {
            "user_id": context.user_id,
            "company_id": context.company_id,
            "surface": context.surface,
            "role": context.role,
            "client": context.client,
            "transport": context.transport,
            "thread_id": context.thread_id,
            "catalog_version": str(self._catalog().get("version") or "unknown"),
            "domains": published_domains or documented_domains,
            "documented_domains": documented_domains,
            "published_domains": published_domains,
            "features": features,
            "current_context": {
                "required": ["company"] if company_required else [],
                "resolved": {
                    "company_id": context.company_id,
                    "user_id": context.user_id,
                    "thread_id": context.thread_id,
                },
                "resolution": {
                    "company": "request_context.company_id" if context.company_id is not None else None,
                    "user": "request_context.user_id" if context.user_id is not None else None,
                    "thread": "request_context.thread_id" if context.thread_id else None,
                },
            },
            "context_summary": self._build_context_summary(features),
        }

    @staticmethod
    def _list_published_domains(surface: str) -> list[str]:
        try:
            from src.core.mcp_surface_registry import get_surface_manifest

            manifest = get_surface_manifest(surface, include_tools=True)
            domains = {
                str(tool.get("domain") or "").strip().lower()
                for tool in (manifest.get("tools") or [])
                if str(tool.get("domain") or "").strip()
            }
            return sorted(domains)
        except Exception:
            return []

    def list_domains(self, surface: str) -> list[str]:
        domains: set[str] = set()
        for feature in self._iter_allowed_features(surface):
            domain = str(feature.get("dominio") or "").strip().lower()
            if domain:
                domains.add(domain)
        return sorted(domains)

    def list_features(
        self,
        surface: str,
        *,
        domain: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        normalized_domain = str(domain or "").strip().lower() or None
        normalized_search = str(search or "").strip().lower() or None
        results: list[dict[str, Any]] = []

        for feature in self._iter_allowed_features(surface):
            feature_domain = str(feature.get("dominio") or "").strip().lower()
            if normalized_domain and feature_domain != normalized_domain:
                continue

            haystack = " ".join(
                [
                    str(feature.get("id") or ""),
                    str(feature.get("nome") or ""),
                    str(feature.get("objetivo") or ""),
                    " ".join(str(item) for item in feature.get("quando_usar") or ()),
                ]
            ).lower()
            if normalized_search and normalized_search not in haystack:
                continue

            entradas = feature.get("entradas") or {}
            results.append(
                {
                    "id": feature.get("id"),
                    "nome": feature.get("nome"),
                    "dominio": feature.get("dominio"),
                    "objetivo": feature.get("objetivo"),
                    "quando_usar": list(feature.get("quando_usar") or []),
                    "entradas": list(entradas.get("obrigatorias") or [])
                    + list(entradas.get("opcionais") or []),
                    "required_context": self._infer_required_context(entradas),
                    "saidas": list(feature.get("saidas") or []),
                    "surfaces": list(feature.get("surfaces") or []),
                    "detalhe_disponivel": bool(feature.get("detalhe_disponivel")),
                }
            )
        return results

    def get_feature_guide(self, feature_id: str, surface: str) -> dict[str, Any]:
        feature = self._require_feature(feature_id, surface)
        guide_ref = str(feature.get("guia_ref") or "").strip()
        if not guide_ref:
            raise MCPFeatureCatalogNotFoundError(f"Guide não configurado para a feature {feature_id}.")

        guide_path = (self.guides_root.parent / guide_ref).resolve()
        if not guide_path.exists():
            raise MCPFeatureCatalogNotFoundError(f"Guide não encontrado para a feature {feature_id}.")

        markdown = guide_path.read_text(encoding="utf-8")
        return {
            "feature_id": feature.get("id"),
            "nome": feature.get("nome"),
            "dominio": feature.get("dominio"),
            "guide_markdown": markdown,
            "sensitivity": self._extract_metadata_value(markdown, "sensibilidade") or "nao_definida",
            "allowed_surfaces": list(feature.get("surfaces") or []),
        }

    def get_feature_examples(self, feature_id: str, surface: str) -> dict[str, Any]:
        guide = self.get_feature_guide(feature_id, surface)
        return {
            "feature_id": feature_id,
            "examples": self._extract_bullet_section(guide["guide_markdown"], "Exemplos de solicitação"),
        }

    def get_feature_constraints(self, feature_id: str, surface: str) -> dict[str, Any]:
        feature = self._require_feature(feature_id, surface)
        guide = self.get_feature_guide(feature_id, surface)
        entradas = feature.get("entradas") or {}
        obrigatorias = list(entradas.get("obrigatorias") or [])
        required_context = self._infer_required_context(entradas)
        return {
            "feature_id": feature_id,
            "requires_company_id": "company_id" in obrigatorias,
            "requires_user_id": "user_id" in obrigatorias,
            "required_context": required_context,
            "allowed_surfaces": list(feature.get("surfaces") or []),
            "confirmation_required": False,
            "notes": self._extract_bullet_section(guide["guide_markdown"], "Validações e restrições"),
        }

    def _catalog(self) -> dict[str, Any]:
        if not self.catalog_path.exists():
            raise MCPFeatureCatalogNotFoundError("Catálogo MCP não encontrado.")
        data = yaml.safe_load(self.catalog_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise MCPFeatureCatalogError("Catálogo MCP inválido.")
        return data

    def _iter_allowed_features(self, surface: str):
        normalized_surface = self._normalize_surface(surface)
        for feature in self._catalog().get("features") or []:
            allowed_surfaces = {
                str(item).strip().lower()
                for item in feature.get("surfaces") or []
                if str(item).strip()
            }
            if normalized_surface in allowed_surfaces:
                yield feature

    def _require_feature(self, feature_id: str, surface: str) -> dict[str, Any]:
        normalized_feature_id = str(feature_id or "").strip().lower()
        all_features = self._catalog().get("features") or []
        for feature in all_features:
            current_id = str(feature.get("id") or "").strip().lower()
            if current_id != normalized_feature_id:
                continue
            allowed_surfaces = {
                str(item).strip().lower()
                for item in feature.get("surfaces") or []
                if str(item).strip()
            }
            if self._normalize_surface(surface) not in allowed_surfaces:
                raise MCPFeatureCatalogAccessError(
                    f"Feature {feature_id} não está autorizada para a surface {surface}."
                )
            return feature
        raise MCPFeatureCatalogNotFoundError(f"Feature {feature_id} não encontrada.")


    @staticmethod
    def _infer_required_context(entradas: dict[str, Any]) -> list[str]:
        obrigatorias = {str(item or "").strip().lower() for item in (entradas.get("obrigatorias") or []) if str(item or "").strip()}
        required: list[str] = []
        if "user_id" in obrigatorias:
            required.append("user")
        if "company_id" in obrigatorias:
            required.append("company")
        return required

    @classmethod
    def _build_context_summary(cls, features: list[dict[str, Any]]) -> dict[str, Any]:
        summary = {
            "user_only": 0,
            "company_only": 0,
            "user_and_company": 0,
            "no_explicit_context": 0,
        }
        for feature in features:
            required_context = tuple(feature.get("required_context") or ())
            if required_context == ("user",):
                summary["user_only"] += 1
            elif required_context == ("company",):
                summary["company_only"] += 1
            elif required_context == ("user", "company"):
                summary["user_and_company"] += 1
            else:
                summary["no_explicit_context"] += 1
        return summary

    @staticmethod
    def _normalize_surface(surface: str) -> str:
        normalized = str(surface or "").strip().lower()
        if normalized not in {"user", "admin", "analytics", "ops"}:
            raise MCPFeatureCatalogAccessError(f"Surface MCP inválida: {surface}.")
        return normalized

    @staticmethod
    def _extract_metadata_value(markdown: str, key: str) -> str | None:
        target = f"`{key}`"
        for raw_line in markdown.splitlines():
            line = raw_line.strip()
            if not line.startswith("-"):
                continue
            if target not in line:
                continue
            _, _, value = line.partition(":")
            cleaned = value.strip().strip("`").strip()
            return cleaned or None
        return None

    @staticmethod
    def _extract_bullet_section(markdown: str, heading: str) -> list[str]:
        lines = markdown.splitlines()
        target_heading = f"## {heading}".strip().lower()
        in_section = False
        bullets: list[str] = []

        for raw_line in lines:
            line = raw_line.rstrip()
            normalized_line = line.strip().lower()
            if normalized_line.startswith("## "):
                if in_section:
                    break
                in_section = normalized_line == target_heading
                continue
            if not in_section:
                continue
            stripped = line.strip()
            if stripped.startswith("- "):
                bullets.append(stripped[2:].strip())
        return bullets

    @staticmethod
    def _require_company_context(context: MCPDocumentationContext) -> None:
        if context.company_id is None:
            raise MCPFeatureCatalogContextError(
                "company_id é obrigatório para acessar o catálogo operacional MCP."
            )
