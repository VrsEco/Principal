from pathlib import Path

import pytest
from pydantic import ValidationError

from src.core.mcp_permission_matrix_tools import register_permission_matrix_tools
from src.intelligence.mcp_contracts import (
    APP32_PERMISSION_MATRIX_MANIFEST,
    PermissionDomainRule,
    PermissionMatrixManifest,
    ProfilePermissionSurfaceMatrix,
)


DOC = Path(__file__).resolve().parents[1] / "docs" / "governance" / "ai_mcp_permission_matrix.md"


class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.registered[kwargs.get("name") or func.__name__] = func
            return func

        if args and callable(args[0]):
            return decorator(args[0])
        return decorator


def test_permission_matrix_manifest_covers_main_profiles_and_surfaces():
    manifest = APP32_PERMISSION_MATRIX_MANIFEST
    profiles = {matrix.profile for matrix in manifest.matrices}
    surfaces = {matrix.surface for matrix in manifest.matrices}

    assert manifest.version == "app32.ai-mcp.permission-matrix.v1"
    assert {"colaborador", "cliente", "administrador", "admin_tecnico"} <= profiles
    assert surfaces == {"user", "admin", "analytics", "ops"}
    assert len(manifest.matrices) == 7
    assert len(manifest.overlay_matrices) == 23


def test_permission_matrix_boundaries_for_cliente_and_finance():
    cliente_matrices = APP32_PERMISSION_MATRIX_MANIFEST.get_profile("cliente")
    admin_analytics = [m for m in APP32_PERMISSION_MATRIX_MANIFEST.get_profile("administrador") if m.surface == "analytics"][0]
    finance_admin = [m for m in APP32_PERMISSION_MATRIX_MANIFEST.get_profile("administrador") if m.surface == "admin"][0]

    assert len(cliente_matrices) == 1
    assert cliente_matrices[0].surface == "user"
    assert all(
        not any(action in rule.allowed_actions for action in {"create", "update", "delete", "audit"})
        for rule in cliente_matrices[0].domains
    )
    assert all(rule.domain != "finance" for rule in cliente_matrices[0].domains)
    assert all(
        not any(action in rule.allowed_actions for action in {"create", "update", "delete"})
        for rule in admin_analytics.domains
    )
    finance_rule = next(rule for rule in finance_admin.domains if rule.domain == "finance")
    assert finance_rule.requires_explicit_company_id is True
    assert {"create", "update", "delete"} <= set(finance_rule.human_gate_for_actions)
    workload_rule = next(rule for rule in admin_analytics.domains if rule.domain == "workload")
    assert workload_rule.requires_explicit_company_id is True
    assert set(workload_rule.allowed_actions) == {"discover", "read", "analyze"}


def test_permission_matrix_ops_is_restricted_to_admin_tecnico():
    ops_matrices = APP32_PERMISSION_MATRIX_MANIFEST.get_surface("ops")

    assert len(ops_matrices) == 1
    assert ops_matrices[0].profile == "admin_tecnico"
    assert any(rule.domain == "operations" for rule in ops_matrices[0].domains)
    assert any(rule.domain == "workload" for rule in ops_matrices[0].domains)


def test_permission_matrix_tool_returns_manifest_and_filters():
    mcp = _FakeMCP()
    register_permission_matrix_tools(mcp)
    tool = mcp.registered["describe_app32_permission_matrix_tool"]

    manifest_payload = tool()
    profile_payload = tool(profile="administrador")
    surface_payload = tool(surface="analytics")
    single_payload = tool(profile="admin_tecnico", surface="ops")
    overlay_payload = tool(overlay_role="operacional_cliente")
    missing_payload = tool(profile="foo")

    assert manifest_payload["success"] is True
    assert manifest_payload["data"]["version"] == "app32.ai-mcp.permission-matrix.v1"
    assert profile_payload["success"] is True
    assert len(profile_payload["data"]) == 3
    assert surface_payload["success"] is True
    assert len(surface_payload["data"]) == 2
    assert single_payload["success"] is True
    assert single_payload["data"]["surface"] == "ops"
    assert single_payload["data"]["profile"] == "admin_tecnico"
    assert overlay_payload["success"] is True
    assert overlay_payload["data"]["overlay"] == "operacional_cliente"
    assert missing_payload["success"] is False
    assert missing_payload["error"]["code"] == "permission_matrix_not_found"


def test_permission_matrix_doc_contains_manifest_tool_and_smoke():
    text = DOC.read_text(encoding="utf-8")

    assert "Matriz Canônica de Permissões IA/MCP por Perfil" in text
    assert "APP32_PERMISSION_MATRIX_MANIFEST" in text
    assert "describe_app32_permission_matrix_tool" in text
    assert "AI_MCP_PERMISSION_MATRIX_OK 7 4" in text
    assert "Colaborador" in text
    assert "Cliente" in text
    assert "Administrador" in text


def test_permission_matrix_contract_rejects_invalid_cliente_and_ops_rules():
    with pytest.raises(ValidationError):
        ProfilePermissionSurfaceMatrix(
            profile="cliente",
            surface="user",
            title="Cliente inválido",
            summary="Cliente não pode mutar.",
            default_scope="active_company",
            domains=[
                PermissionDomainRule(
                    domain="routine",
                    allowed_actions=["read", "create"],
                    denied_actions=["delete"],
                    notes=["Inválido para cliente."],
                )
            ],
        )

    valid_rule = PermissionDomainRule(
        domain="operations",
        allowed_actions=["discover", "read", "audit"],
        denied_actions=["delete"],
        notes=["Regra válida base."],
    )

    with pytest.raises(ValidationError):
        PermissionMatrixManifest(
            matrices=[
                ProfilePermissionSurfaceMatrix(
                    profile="administrador",
                    surface="analytics",
                    title="Admin analytics",
                    summary="Matriz válida analytics.",
                    default_scope="explicit_company_id",
                    domains=[
                        PermissionDomainRule(
                            domain="analytics",
                            allowed_actions=["discover", "read", "analyze"],
                            denied_actions=["create"],
                            requires_explicit_company_id=True,
                            notes=["Ok."],
                        )
                    ],
                ),
                ProfilePermissionSurfaceMatrix(
                    profile="administrador",
                    surface="ops",
                    title="Admin ops inválido",
                    summary="Administrador não pode ops.",
                    default_scope="active_company",
                    domains=[valid_rule],
                ),
            ]
        )


def test_overlay_permission_matrix_for_admfin_cliente_keeps_finance_outside_user_surface():
    matrices = APP32_PERMISSION_MATRIX_MANIFEST.get_overlay("admfin_cliente")

    assert len(matrices) == 1
    matrix = matrices[0]
    assert matrix.surface == "user"
    assert all(rule.domain != "finance" for rule in matrix.domains)
    assert all(
        not any(action in rule.allowed_actions for action in {"create", "update", "delete"})
        for rule in matrix.domains
    )


def test_overlay_permission_matrix_supports_versus_and_engineering_families():
    versus = APP32_PERMISSION_MATRIX_MANIFEST.get_overlay("auditor_versus")
    engineering = APP32_PERMISSION_MATRIX_MANIFEST.get_overlay("coordenador_engenharia")

    assert len(versus) == 1
    assert versus[0].surface == "analytics"
    assert any(rule.domain == "finance" for rule in versus[0].domains)
    assert all("update" not in rule.allowed_actions for rule in versus[0].domains)

    assert len(engineering) == 1
    assert engineering[0].surface == "ops"
    assert any(rule.domain == "operations" for rule in engineering[0].domains)
    assert any("update" in rule.allowed_actions for rule in engineering[0].domains)
