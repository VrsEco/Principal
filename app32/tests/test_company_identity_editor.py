from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

import pytest
from jinja2 import Environment

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "app32"))

from services.company_role_hierarchy_service import (  # noqa: E402
    CompanyRoleHierarchyService,
    RoleHierarchyValidationError,
)
import services.company_role_hierarchy_service as role_service  # noqa: E402


def test_identity_page_exposes_didactic_editor_and_efficient_chart_controls():
    template = (REPO_ROOT / "app32/templates/modules/companies/company_identity_v2.html").read_text(encoding="utf-8")
    Environment().parse(template)

    assert "data-identity-tab=\"editor\"" in template
    assert "Editor da estrutura" in template
    assert "identityRoleParent" in template
    assert "identityEditorPreview" in template
    assert "identityRoleColor" in template
    assert "data-role-color" in template
    assert "identityChartSearch" in template
    assert "identityChartDepartment" in template
    assert "identityChartLayout" in template
    assert "Empilhar último nível" in template
    assert "Organograma Organizacional" in template
    assert "identityChartTotalPlanned" in template
    assert "identityChartTotalEffective" in template
    assert "identityChartCreatedAt" in template
    assert "identityChartUpdatedAt" in template
    assert "Criado em" in template
    assert "Última edição" in template
    assert "Versus Gestão Corporativa - Todos os direitos reservados." in template
    assert "identityChartZoomValue" in template
    assert "data-can-edit" in template
    assert "has_permission('companies', 'edit')" in template


def test_identity_editor_assets_keep_canonical_card_content_and_add_navigation():
    javascript = (REPO_ROOT / "app32/static/js/company_identity.js").read_text(encoding="utf-8")
    stylesheet = (REPO_ROOT / "app32/static/css/company_identity.css").read_text(encoding="utf-8")

    for contract in (
        "identity-node__title",
        "identity-node__department",
        "headcount_planned",
        "active_employee_count",
        "data-toggle-node",
        "zoomIn()",
        "zoomOut()",
        "downloadSvg()",
        "filteredTree",
        "shouldStackChildren",
        "layoutOverrides",
        "identityChartToggleChildrenLayout",
        "safeColor",
        "depthClass",
        "--identity-node-color",
        "identityChartDocumentHeader",
        "identityChartDocumentFooter",
        "formatDateTime",
        "org_chart_created_at",
        "org_chart_updated_at",
    ):
        assert contract in javascript
    assert f"/api/companies/${{companyId}}/roles" in javascript
    assert "Math.max(0.1, Math.min(1, available / treeShell.scrollWidth))" in javascript
    assert "treeShell.style.transform = `scale(${state.scale})`" in javascript
    assert "host.style.transform = 'none'" in javascript
    assert "identity-editor-layout" in stylesheet
    assert "ul.is-stacked" in stylesheet
    assert "identity-node--depth-1" in stylesheet
    assert "identity-node--depth-2" in stylesheet
    assert "identity-node--depth-3" in stylesheet
    assert "--identity-node-width:320px" in stylesheet
    assert "--identity-node-width:280px" in stylesheet
    assert "--identity-node-width:245px" in stylesheet
    assert "identity-color-palette" in stylesheet
    assert "identity-chart-document-header" in stylesheet
    assert "identity-chart-document-footer" in stylesheet
    assert "overflow:auto" in stylesheet.replace(" ", "")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"title": ""}, "Título do cargo é obrigatório."),
        ({"title": "Diretor", "headcount_planned": -1}, "Pessoas previstas não pode ser negativo."),
        ({"title": "Diretor", "parent_role_id": "abc"}, "Cargo superior inválido."),
        ({"title": "Diretor", "color": "blue"}, "Cor do card deve estar no formato hexadecimal"),
    ],
)
def test_role_hierarchy_payload_rejects_invalid_editor_data(payload, message):
    with pytest.raises(RoleHierarchyValidationError, match=message):
        CompanyRoleHierarchyService._normalize_payload(10, payload)


def test_role_hierarchy_normalizes_valid_card_color():
    payload = CompanyRoleHierarchyService._normalize_payload(
        10,
        {"title": "Diretor", "color": "#d9ecff"},
    )

    assert payload["color"] == "#D9ECFF"


def test_role_hierarchy_rejects_cross_tenant_parent(monkeypatch):
    class Query:
        def filter_by(self, **filters):
            self.filters = filters
            return self

        def first(self):
            return None

    monkeypatch.setattr(role_service, "Role", SimpleNamespace(query=Query()))

    with pytest.raises(RoleHierarchyValidationError, match="não pertence a esta empresa"):
        CompanyRoleHierarchyService._validate_parent(company_id=10, role_id=22, parent_id=99)


def test_role_hierarchy_rejects_cycle(monkeypatch):
    roles = {
        20: SimpleNamespace(id=20, parent_role_id=30),
        30: SimpleNamespace(id=30, parent_role_id=40),
        40: SimpleNamespace(id=40, parent_role_id=None),
    }

    class Query:
        def filter_by(self, **filters):
            self.filters = filters
            return self

        def first(self):
            return roles.get(self.filters["id"])

    monkeypatch.setattr(role_service, "Role", SimpleNamespace(query=Query()))

    with pytest.raises(RoleHierarchyValidationError, match="criaria um ciclo"):
        CompanyRoleHierarchyService._validate_parent(company_id=10, role_id=30, parent_id=20)
