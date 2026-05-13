from __future__ import annotations

from typing import Any, Optional

from src.intelligence.mcp_contracts import (
    APP32_PERMISSION_MATRIX_MANIFEST,
    MCPErrorDetail,
    MCPErrorEnvelope,
    MCPResponseMeta,
    MCPSuccessEnvelope,
)


def _meta(operation: str, *, profile: str | None = None, surface: str | None = None) -> MCPResponseMeta:
    tags = ["permission_matrix"]
    if profile:
        tags.append(f"profile:{profile}")
    if surface:
        tags.append(f"surface:{surface}")
    return MCPResponseMeta(
        domain="mcp_permission_matrix",
        operation=operation,
        scope="mcp_user",
        capability=f"mcp_permission_matrix.{operation}",
        permissions=["mcp.permission_matrix.read"],
        tags=tags,
    )


def _success(operation: str, data: Any, *, profile: str | None = None, surface: str | None = None) -> dict[str, Any]:
    return MCPSuccessEnvelope[Any](
        data=data,
        meta=_meta(operation, profile=profile, surface=surface),
    ).model_dump(mode="json")


def _error(operation: str, code: str, message: str, *, profile: str | None = None, surface: str | None = None) -> dict[str, Any]:
    return MCPErrorEnvelope(
        error=MCPErrorDetail(code=code, message=message),
        meta=_meta(operation, profile=profile, surface=surface),
    ).model_dump(mode="json")


def register_permission_matrix_tools(mcp: Any) -> None:
    """Registra tools MCP de descoberta da matriz canônica de permissões por perfil."""

    @mcp.tool()
    def describe_app32_permission_matrix_tool(
        profile: Optional[str] = None,
        surface: Optional[str] = None,
        overlay_role: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Descreve a matriz canônica de permissões do APP32 por perfil e surface:
        colaborador, cliente, administrador e admin_tecnico.
        """
        if not profile and not surface and not overlay_role:
            return _success(
                "permission_matrix.describe",
                APP32_PERMISSION_MATRIX_MANIFEST.model_dump(mode="json"),
            )

        if overlay_role:
            normalized_overlay = overlay_role.strip().lower()
            overlay_matrices = APP32_PERMISSION_MATRIX_MANIFEST.get_overlay(normalized_overlay)
            normalized_surface = surface.strip().lower() if surface else None
            if normalized_surface:
                overlay_matrices = [matrix for matrix in overlay_matrices if matrix.surface == normalized_surface]
            if not overlay_matrices:
                return _error(
                    "permission_matrix.describe",
                    "permission_matrix_not_found",
                    "Nenhuma matriz de permissão encontrada para os filtros informados.",
                    profile=normalized_overlay,
                    surface=normalized_surface,
                )
            if len(overlay_matrices) == 1:
                matrix = overlay_matrices[0]
                return _success(
                    "permission_matrix.describe",
                    matrix.model_dump(mode="json"),
                    profile=matrix.overlay,
                    surface=matrix.surface,
                )
            return _success(
                "permission_matrix.describe",
                [matrix.model_dump(mode="json") for matrix in overlay_matrices],
                profile=normalized_overlay,
                surface=normalized_surface,
            )

        matrices = APP32_PERMISSION_MATRIX_MANIFEST.matrices
        normalized_profile = profile.strip().lower() if profile else None
        if normalized_profile == "administrador_tecnico":
            normalized_profile = "admin_tecnico"
        normalized_surface = surface.strip().lower() if surface else None

        if normalized_profile:
            matrices = [matrix for matrix in matrices if matrix.profile == normalized_profile]
        if normalized_surface:
            matrices = [matrix for matrix in matrices if matrix.surface == normalized_surface]

        if not matrices:
            return _error(
                "permission_matrix.describe",
                "permission_matrix_not_found",
                "Nenhuma matriz de permissão encontrada para os filtros informados.",
                profile=normalized_profile,
                surface=normalized_surface,
            )

        if len(matrices) == 1:
            matrix = matrices[0]
            return _success(
                "permission_matrix.describe",
                matrix.model_dump(mode="json"),
                profile=matrix.profile,
                surface=matrix.surface,
            )

        return _success(
            "permission_matrix.describe",
            [matrix.model_dump(mode="json") for matrix in matrices],
            profile=normalized_profile,
            surface=normalized_surface,
        )


__all__ = ["register_permission_matrix_tools"]
